"""Unified CI gate orchestrator — the single convergence point (BDL-039 F3).

# beadloom:domain=application

``run_ci_gate`` composes the existing checkers — reindex, ``lint --strict``,
``sync-check``, ``config-check`` (AgentConfigAsCode), ``doctor`` (graph
integrity), and (when hub exports are given) ``federate --fail-on`` — into ONE
:class:`GateResult` with a single ``ok`` verdict. It is the principle-7 "CI is
the only true enforcement point": identical for Cursor / Claude Code / human
authors.

Two honesty invariants (the Phase-0 lesson):

1. **No silent skip.** Every step records its outcome — ``PASS`` / ``FAIL`` /
   ``SKIP`` — so the report never shows a green that quietly skipped a step.
2. **No short-circuit.** All steps run and ALL findings are collected even after
   an earlier failure, so one run surfaces every problem at once.

Findings are projected to the shared agent-actionable shape
(``{kind, rule, severity, locations, why, remediation}``, reused from
:mod:`beadloom.graph.linter`) uniformly across every step, so ``--format json``
/ ``--format github`` are identical regardless of which checker produced them.
This module ORCHESTRATES the existing domain code; it does not reimplement any
checker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.application.doctor import Check


# A single finding in the shared, agent-actionable shape (see linter._finding).
Finding = dict[str, object]


def _run_doctor_checks(
    conn: sqlite3.Connection, *, project_root: Path | None = None
) -> list[Check]:
    """Indirection over :func:`beadloom.application.doctor.run_checks`.

    Defined as a module-level seam so the gate's doctor step reuses the exact
    same integrity checks as ``beadloom doctor`` (no parallel reimplementation),
    while staying patchable in tests.
    """
    from beadloom.application.doctor import run_checks

    return run_checks(conn, project_root=project_root)


@dataclass
class GateStep:
    """One step of the gate and its honest outcome.

    - ``name``     — the step identity (``reindex`` / ``lint`` / ``sync-check`` /
      ``config-check`` / ``federate``).
    - ``passed``   — True when the step did not fail the gate. A *skipped* step
      counts as passed (it cannot block the build).
    - ``skipped``  — True when the step did not run (e.g. ``--no-reindex``).
    - ``findings`` — the step's findings in the shared shape (empty on PASS/SKIP).
    - ``summary``  — a short human line for the ``rich`` report.
    """

    name: str
    passed: bool = True
    skipped: bool = False
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""

    @property
    def status(self) -> str:
        """``PASS`` / ``FAIL`` / ``SKIP`` — never an ambiguous green."""
        if self.skipped:
            return "SKIP"
        return "PASS" if self.passed else "FAIL"


@dataclass
class GateResult:
    """Aggregate of every gate step. ``ok`` only when every step passed."""

    steps: list[GateStep] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only if every step passed (honest single verdict)."""
        return all(s.passed for s in self.steps)

    @property
    def findings(self) -> list[Finding]:
        """All findings across every step, in step order."""
        return [f for step in self.steps for f in step.findings]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_ci_gate(
    project_root: Path,
    *,
    fail_on: set[str] | None,
    hub_exports: list[Path],
    no_reindex: bool,
) -> GateResult:
    """Run every gate step in order, collecting all findings; never short-circuit.

    Order: (1) reindex unless *no_reindex*; (2) ``lint --strict``;
    (3) ``sync-check``; (4) ``config-check``; (5) ``doctor`` (graph integrity);
    (6) ``federate --fail-on`` when *hub_exports* is non-empty. Returns a
    :class:`GateResult` whose ``ok`` is True only when every step passed.

    *fail_on* is the federate fail-set; ``None`` selects the safe default set
    (``breaking,drift,orphaned_consumer,undeclared_producer``) — the no-false-gate
    verdicts are never included.
    """
    steps: list[GateStep] = [
        _step_reindex(project_root, no_reindex=no_reindex),
        _step_lint(project_root),
        _step_sync_check(project_root),
        _step_config_check(project_root),
        _step_doctor(project_root),
    ]
    if hub_exports:
        steps.append(_step_federate(project_root, hub_exports, fail_on))
    return GateResult(steps=steps)


def _step_reindex(project_root: Path, *, no_reindex: bool) -> GateStep:
    """Incremental reindex so the gate runs against current code."""
    if no_reindex:
        return GateStep("reindex", skipped=True, summary="skipped (--no-reindex)")

    from beadloom.application.reindex import incremental_reindex

    result = incremental_reindex(project_root)
    if result.errors:
        findings = [_simple_finding("reindex", "error", e, None) for e in result.errors]
        return GateStep(
            "reindex",
            passed=False,
            findings=findings,
            summary=f"{len(result.errors)} reindex error(s)",
        )
    summary = "up to date" if result.nothing_changed else "reindexed"
    return GateStep("reindex", summary=summary)


def _step_lint(project_root: Path) -> GateStep:
    """``lint --strict`` — boundary rules at error severity."""
    from beadloom.graph.linter import LintError, _finding
    from beadloom.graph.linter import lint as run_lint

    try:
        # reindex already ran (or was intentionally skipped); do not redo it.
        result = run_lint(project_root, reindex_before=False)
    except LintError as exc:
        return GateStep(
            "lint",
            passed=False,
            findings=[_simple_finding("lint", "error", str(exc), None)],
            summary="rules configuration error",
        )
    findings = [_finding(v) for v in result.violations]
    passed = not result.has_errors
    summary = (
        f"{result.error_count} error(s), {result.warning_count} warning(s)"
        if result.violations
        else f"{result.rules_evaluated} rules, 0 violations"
    )
    return GateStep("lint", passed=passed, findings=findings, summary=summary)


def _step_sync_check(project_root: Path) -> GateStep:
    """``sync-check`` — doc<->code freshness; stale pairs fail the gate."""
    from beadloom.doc_sync.engine import check_sync
    from beadloom.infrastructure.db import open_db

    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return GateStep(
            "sync-check",
            passed=False,
            findings=[
                _simple_finding(
                    "sync-check",
                    "error",
                    "database not found",
                    "run `beadloom reindex` first",
                )
            ],
            summary="database missing",
        )
    conn = open_db(db_path)
    try:
        results = check_sync(conn, project_root=project_root)
    finally:
        conn.close()

    stale = [r for r in results if r.get("status") == "stale"]
    findings = [_sync_finding(r) for r in stale]
    passed = not stale
    summary = f"{len(stale)} stale doc(s)" if stale else f"{len(results)} pair(s) fresh"
    return GateStep("sync-check", passed=passed, findings=findings, summary=summary)


def _step_config_check(project_root: Path) -> GateStep:
    """``config-check`` (AgentConfigAsCode) — generated agent-config freshness."""
    from beadloom.infrastructure.db import open_db
    from beadloom.onboarding import check_config_drift

    db_path = project_root / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    try:
        drifts = check_config_drift(project_root, conn)
    finally:
        conn.close()

    findings = [_config_finding(d.file, d.reason) for d in drifts]
    passed = not drifts
    summary = (
        f"{len(drifts)} drifted artifact(s)" if drifts else "agent-config in sync"
    )
    return GateStep("config-check", passed=passed, findings=findings, summary=summary)


def _step_doctor(project_root: Path) -> GateStep:
    """``doctor`` — graph/data integrity. Only ERROR-severity checks fail the gate.

    Reuses :func:`beadloom.application.doctor.run_checks` (the exact path
    ``beadloom doctor`` calls — no reimplementation). WARNING/INFO/OK checks are
    advisory and never block the build (no false gate): the clean Beadloom repo
    carries non-error advisories and MUST still exit 0.
    """
    from beadloom.application.doctor import Severity
    from beadloom.infrastructure.db import open_db

    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return GateStep(
            "doctor",
            passed=False,
            findings=[
                _simple_finding(
                    "doctor", "error", "database not found", "run `beadloom reindex` first"
                )
            ],
            summary="database missing",
        )
    conn = open_db(db_path)
    try:
        checks = _run_doctor_checks(conn, project_root=project_root)
    finally:
        conn.close()

    errors = [c for c in checks if c.severity is Severity.ERROR]
    findings = [_doctor_finding(c) for c in errors]
    passed = not errors
    summary = (
        f"{len(errors)} integrity error(s)" if errors else f"{len(checks)} check(s) clean"
    )
    return GateStep("doctor", passed=passed, findings=findings, summary=summary)


def _step_federate(
    project_root: Path, hub_exports: list[Path], fail_on: set[str] | None
) -> GateStep:
    """``federate --fail-on`` — the cross-service landscape gate (optional)."""
    import json

    from beadloom.graph.federation import (
        SAFE_DEFAULT_FAIL_ON,
        aggregate_exports,
        gate_failure_remediation,
        gate_failures,
        serialize_federation,
    )

    fail_set = set(SAFE_DEFAULT_FAIL_ON) if fail_on is None else fail_on

    artifacts: list[dict[str, object]] = []
    for path in hub_exports:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return GateStep(
                "federate",
                passed=False,
                findings=[
                    _simple_finding("federate", "error", f"cannot read {path}: {exc}", None)
                ],
                summary="export read error",
            )
        if not isinstance(parsed, dict):
            return GateStep(
                "federate",
                passed=False,
                findings=[
                    _simple_finding("federate", "error", f"{path} is not a JSON object", None)
                ],
                summary="malformed export",
            )
        artifacts.append(parsed)

    fed = aggregate_exports(artifacts, now=datetime.now(tz=timezone.utc).isoformat())
    # Always write the federated artifact first (CI must be able to upload it).
    out_dir = project_root / ".beadloom"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "federated.json").write_text(serialize_federation(fed) + "\n", encoding="utf-8")

    failures = gate_failures(fed, fail_set)
    findings = [
        _gate_failure_finding(f, gate_failure_remediation(f)) for f in failures
    ]
    passed = not failures
    summary = (
        f"{len(failures)} verdict(s) in fail-set" if failures else "landscape clean"
    )
    return GateStep("federate", passed=passed, findings=findings, summary=summary)


# ---------------------------------------------------------------------------
# Finding constructors (shared agent-actionable shape)
# ---------------------------------------------------------------------------


def _simple_finding(
    kind: str, severity: str, why: str, remediation: str | None
) -> Finding:
    """A finding with no file location (step-level error)."""
    return {
        "kind": kind,
        "rule": kind,
        "severity": severity,
        "locations": [],
        "why": why,
        "remediation": remediation,
    }


def _sync_finding(row: dict[str, object]) -> Finding:
    """Project a stale sync pair onto the shared finding shape."""
    doc_path = str(row.get("doc_path", ""))
    reason = str(row.get("reason", "stale"))
    ref_id = str(row.get("ref_id", ""))
    locations: list[Finding] = [{"file": doc_path}] if doc_path else []
    return {
        "kind": "sync-check",
        "rule": "doc-stale",
        "severity": "error",
        "locations": locations,
        "why": f"{ref_id}: doc out of sync with code ({reason})",
        "remediation": f"run `beadloom sync-update {ref_id}` to review and re-attest",
    }


def _config_finding(file: str, reason: str) -> Finding:
    """Project an AgentConfigAsCode drift onto the shared finding shape."""
    locations: list[Finding] = [{"file": file}] if file else []
    return {
        "kind": "config-check",
        "rule": "config-drift",
        "severity": "error",
        "locations": locations,
        "why": reason,
        "remediation": "run `beadloom setup-rules --refresh` (or `config-check --fix`)",
    }


def _doctor_finding(check: Check) -> Finding:
    """Project a doctor :class:`Check` (ERROR severity) onto the shared shape."""
    return {
        "kind": "doctor",
        "rule": check.name,
        "severity": "error",
        "locations": [],
        "why": check.description,
        "remediation": "run `beadloom doctor` and fix the reported integrity error",
    }


def _gate_failure_finding(failure: object, remediation: str | None) -> Finding:
    """Project a federate :class:`GateFailure` onto the shared finding shape."""
    kind = getattr(failure, "kind", "")
    identity = getattr(failure, "identity", "")
    verdict = getattr(failure, "verdict", "")
    missing = getattr(failure, "missing", ())
    why = f"[{kind}] {identity}: {str(verdict).upper()}"
    if missing:
        why += f" — missing: {', '.join(missing)}"
    return {
        "kind": "federate",
        "rule": str(verdict),
        "severity": "error",
        "locations": [],
        "why": why,
        "remediation": remediation,
    }
