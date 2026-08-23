# beadloom:domain=application
# beadloom:feature=ci-gate
"""Unified CI gate orchestrator — the single convergence point (BDL-039 F3).

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

from beadloom.doc_sync.declared_docs import count_declared_docs
from beadloom.doc_sync.engine import (
    BLOCKING_STATUSES,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_STALE,
    STATUS_UNVERIFIED,
)
from beadloom.doc_sync.surface_ledger import SurfaceVerdict, compare_surface, read_ledger

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.application.doctor import Check
    from beadloom.doc_sync.audit import AuditFinding, AuditResult


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


def _run_audit(
    project_root: Path, conn: sqlite3.Connection
) -> AuditResult:
    """Indirection over :func:`beadloom.doc_sync.audit.run_audit`.

    Defined as a module-level seam so the gate's docs-audit step reuses the
    exact same fact-freshness detection as ``beadloom docs audit`` (no parallel
    reimplementation), while staying patchable in tests.
    """
    from beadloom.doc_sync.audit import run_audit

    return run_audit(project_root, conn)


@dataclass
class GateStep:
    """One step of the gate and its honest outcome.

    - ``name``     — the step identity (``reindex`` / ``lint`` / ``sync-check`` /
      ``config-check`` / ``federate``).
    - ``passed``   — True when the step did not fail the gate. A *skipped* step
      counts as passed (it cannot block the build).
    - ``skipped``  — True when the step did not run (e.g. ``--no-reindex``).
    - ``not_verified`` — True when the step ran, found nothing wrong, and could
      not actually check part of what it reports on. It stays ``passed`` (a
      project that cannot supply a baseline is not thereby broken) but it prints
      ``WARN``, because *unverifiable is not clean*: a green that describes the
      checker's own ignorance is the defect BDL-UX #174/#175/#178 are all made
      of, and the honest word costs nothing.
    - ``findings`` — the step's findings in the shared shape (empty on PASS/SKIP).
    - ``summary``  — a short human line for the ``rich`` report.
    """

    name: str
    passed: bool = True
    skipped: bool = False
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    not_verified: bool = False

    @property
    def status(self) -> str:
        """``PASS`` / ``WARN`` / ``FAIL`` / ``SKIP`` — never an ambiguous green."""
        if self.skipped:
            return "SKIP"
        if not self.passed:
            return "FAIL"
        return "WARN" if self.not_verified else "PASS"


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
    (3) ``sync-check``; (4) ``docs-audit`` (fact freshness, blocks on
    ``stale>0``); (5) ``config-check``; (6) ``doctor`` (graph integrity);
    (7) ``federate --fail-on`` when *hub_exports* is non-empty. Returns a
    :class:`GateResult` whose ``ok`` is True only when every step passed.

    *fail_on* is the federate fail-set; ``None`` selects the safe default set
    (``breaking,drift,orphaned_consumer,undeclared_producer``) — the no-false-gate
    verdicts are never included.
    """
    steps: list[GateStep] = [
        _step_reindex(project_root, no_reindex=no_reindex),
        _step_lint(project_root),
        _step_sync_check(project_root),
        _step_docs_audit(project_root),
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
        result = run_lint(project_root)
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
    from beadloom.infrastructure.db import connection

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
    with connection(db_path) as conn:
        results = check_sync(conn, project_root=project_root)
        declared_docs = count_declared_docs(conn)

    pairs = [r for r in results if r.get("code_path")]
    blocking = [r for r in results if r.get("status") in BLOCKING_STATUSES]
    unverified = [r for r in results if r.get("status") == STATUS_UNVERIFIED]
    surface = compare_surface(
        read_ledger(project_root),
        declared_pairs=len(pairs),
        declared_docs=declared_docs,
    )

    findings = [_sync_finding(r) for r in blocking]
    findings.extend(_sync_unverified_finding(r) for r in unverified)
    if surface.shrank:
        findings.append(_surface_finding(surface.message))

    return GateStep(
        "sync-check",
        passed=not blocking,
        not_verified=bool(unverified) or surface.shrank,
        findings=findings,
        summary=_sync_summary(results, unverified, surface),
    )


def _sync_summary(
    results: list[dict[str, object]],
    unverified: list[dict[str, object]],
    surface: SurfaceVerdict,
) -> str:
    """The sync-check line, which must never print a count that means nothing.

    It says how many pairs were CHECKED and found fresh, how many could not be
    checked at all, and — when the recorded declared surface moved — that it
    moved. A bare ``N pair(s) fresh`` was true of a run in which six pairs had
    just been deleted (BDL-UX #174) and of a run that could not detect staleness
    at all (BDL-UX #175).
    """
    missing = [r for r in results if r.get("status") == STATUS_MISSING]
    stale = [r for r in results if r.get("status") == STATUS_STALE]
    suffix = f"; {surface.headline}" if surface.headline else ""
    if missing or stale:
        parts = []
        if missing:
            parts.append(f"{len(missing)} missing doc(s)/code file(s)")
        if stale:
            parts.append(f"{len(stale)} stale doc(s)")
        # The surface headline rides along HERE too: a run that deleted a doc is
        # precisely the run whose count fell, and suppressing the number in
        # favour of the failure would discard the signal again.
        return ", ".join(parts) + suffix
    fresh = [r for r in results if r.get("status") == STATUS_OK]
    summary = f"{len(fresh)} pair(s) fresh"
    if unverified:
        summary += f", {len(unverified)} NOT VERIFIED (no baseline — index rebuilt)"
    return summary + suffix


def _step_docs_audit(project_root: Path) -> GateStep:
    """``docs audit`` — numeric/version fact freshness; blocks on ``stale>0``.

    Reuses :func:`beadloom.doc_sync.audit.run_audit` (the exact path
    ``beadloom docs audit`` calls — no reimplementation) and fails the step when
    any documentation mention disagrees with a ground-truth fact. The audit's
    false-positive masking + per-fact tolerances already keep this honest.
    """
    from beadloom.infrastructure.db import connection

    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        return GateStep(
            "docs-audit",
            passed=False,
            findings=[
                _simple_finding(
                    "docs-audit",
                    "error",
                    "database not found",
                    "run `beadloom reindex` first",
                )
            ],
            summary="database missing",
        )
    with connection(db_path) as conn:
        result = _run_audit(project_root, conn)

    stale = [f for f in result.findings if f.status == "stale"]
    findings = [_audit_finding(f) for f in stale]
    return GateStep(
        "docs-audit",
        passed=not stale,
        findings=findings,
        summary=_audit_summary(result, stale),
    )


def _audit_summary(result: AuditResult, stale: list[AuditFinding]) -> str:
    """The docs-audit line, which must say what it COVERED, not only what it found.

    ``13 mention(s) fresh`` was measured to be thirteen restatements of one of
    NINE declared facts: the line reported the checker's activity and read as a
    verdict on the docs (BDL-UX #173). It now carries the declared surface, so a
    reader can see that a green audit checked two facts of nine.

    Coverage does not fail or WARN the step, deliberately. Silence in the docs
    about a fact is not a defect in the code, and a WARN every project would
    carry on every run would spend the channel ``sync-check`` needs for a real
    missing baseline. The number is on the line everybody reads, and
    ``docs audit --fail-if unverified>N`` is there for a project that wants it
    enforced.
    """
    declared = len(result.facts)
    unverified = result.unverified_facts
    head = (
        f"{len(stale)} stale fact(s)"
        if stale
        else f"{len(result.findings)} mention(s) fresh"
    )
    coverage = f"{declared - len(unverified)}/{declared} declared fact(s) verified"
    if unverified:
        coverage += f", NOT VERIFIED: {', '.join(unverified)}"
    return f"{head}; {coverage}"


def _step_config_check(project_root: Path) -> GateStep:
    """``config-check`` (AgentConfigAsCode) — generated agent-config freshness."""
    from beadloom.infrastructure.db import connection
    from beadloom.onboarding import check_config_drift

    db_path = project_root / ".beadloom" / "beadloom.db"
    if not db_path.exists():
        # Guard mirrored from the sibling steps. Without it ``connection``
        # CREATES an empty database, so a later step that only checks for the
        # file's existence found one with no tables and crashed — a gate step
        # manufacturing the state the next step reads (BDL-UX #147's shape).
        return GateStep(
            "config-check",
            passed=False,
            findings=[
                _simple_finding(
                    "config-check",
                    "error",
                    "database not found",
                    "run `beadloom reindex` first",
                )
            ],
            summary="database missing",
        )
    with connection(db_path) as conn:
        drifts = check_config_drift(project_root, conn)

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
    from beadloom.infrastructure.db import connection

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
    with connection(db_path) as conn:
        checks = _run_doctor_checks(conn, project_root=project_root)

    errors = [c for c in checks if c.severity is Severity.ERROR]
    findings = [_doctor_finding(c) for c in errors]
    return GateStep(
        "doctor", passed=not errors, findings=findings, summary=_doctor_summary(checks)
    )


def _doctor_summary(checks: list[Check]) -> str:
    """Count the CHECKS, and never call a warning clean.

    ``run_checks`` returns one entry per FINDING, so ``len(checks)`` counted
    problems, not checks: deleting a declared doc added a ``nodes_without_docs``
    warning and the gate reported ``21 check(s) clean`` where it had reported 20
    — the count rose while the tree shrank (BDL-UX #174). The distinct check
    names are the number of checks; the severities say what they found.
    """
    from beadloom.application.doctor import Severity

    ran = len({c.name for c in checks})
    errors = sum(1 for c in checks if c.severity is Severity.ERROR)
    if errors:
        return f"{errors} integrity error(s) across {ran} check(s)"
    warnings = sum(1 for c in checks if c.severity is Severity.WARNING)
    infos = sum(1 for c in checks if c.severity is Severity.INFO)
    if not warnings and not infos:
        return f"{ran} check(s) clean"
    return f"{ran} check(s): 0 error(s), {warnings} warning(s), {infos} info"


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
    """Project a BLOCKING sync pair onto the shared finding shape.

    *Missing* and *stale* are different facts and read differently: a stale doc
    is behind the code, a missing one is not there to be behind it, and telling
    an agent to re-attest a file that does not exist is not a remediation.
    """
    doc_path = str(row.get("doc_path", ""))
    reason = str(row.get("reason", "stale"))
    ref_id = str(row.get("ref_id", ""))
    locations: list[Finding] = [{"file": doc_path}] if doc_path else []
    if str(row.get("status")) == STATUS_MISSING:
        return {
            "kind": "sync-check",
            "rule": "doc-missing",
            "severity": "error",
            "locations": locations,
            "why": (
                f"{ref_id}: {_MISSING_WHY.get(reason, reason)} — "
                f"'{doc_path}' does not exist"
            ),
            "remediation": (
                "restore the file, or remove the declaration from the graph "
                "if the doc is genuinely gone — the gate is not satisfied by "
                "having less to check"
            ),
        }
    return {
        "kind": "sync-check",
        "rule": "doc-stale",
        "severity": "error",
        "locations": locations,
        "why": f"{ref_id}: doc out of sync with code ({reason})",
        "remediation": f"run `beadloom sync-update {ref_id}` to review and re-attest",
    }


#: What each ``missing`` reason means to a reader, in the reader's terms.
_MISSING_WHY = {
    "doc_missing": "the linked doc file is gone",
    "code_missing": "the paired code file is gone",
    "declared_doc_missing": "the graph declares a doc that is not on disk",
}


def _sync_unverified_finding(row: dict[str, object]) -> Finding:
    """A pair that could not be checked at all — a warning, and never silent."""
    doc_path = str(row.get("doc_path", ""))
    ref_id = str(row.get("ref_id", ""))
    locations: list[Finding] = [{"file": doc_path}] if doc_path else []
    return {
        "kind": "sync-check",
        "rule": "doc-not-verified",
        "severity": "warning",
        "locations": locations,
        "why": (
            f"{ref_id}: NOT checked — the index was rebuilt, so its baseline is "
            f"the current tree, and git could not supply one either"
        ),
        "remediation": (
            "reindex incrementally on the existing index, run inside a git "
            "work tree, or attest the pair with `beadloom sync-update`"
        ),
    }


def _surface_finding(message: str) -> Finding:
    """The declared surface shrank since it was recorded."""
    return {
        "kind": "sync-check",
        "rule": "declared-surface-shrank",
        "severity": "warning",
        "locations": [],
        "why": message,
        "remediation": (
            "restore what was removed, or re-record deliberately with "
            "`beadloom sync-check --record-surface`"
        ),
    }


def _audit_finding(finding: object) -> Finding:
    """Project a stale :class:`~beadloom.doc_sync.audit.AuditFinding` onto the shape.

    Uses ``getattr`` so the gate has no hard structural dependency on the audit
    dataclass internals beyond the documented ``mention`` / ``fact`` / ``status``
    surface.
    """
    mention = getattr(finding, "mention", None)
    fact = getattr(finding, "fact", None)
    fact_name = getattr(fact, "name", "")
    expected = getattr(fact, "value", "")
    found = getattr(mention, "value", "")
    file_path = str(getattr(mention, "file", ""))
    line = getattr(mention, "line", None)
    location: Finding = {}
    if file_path:
        location["file"] = file_path
    if isinstance(line, int):
        location["line"] = line
    locations: list[Finding] = [location] if location else []
    return {
        "kind": "docs-audit",
        "rule": "doc-fact-stale",
        "severity": "error",
        "locations": locations,
        "why": (
            f"{fact_name}: doc says {found!r} but project state is {expected!r}"
        ),
        "remediation": (
            "update the doc to the current value, or add a tolerance / extra "
            "fact under `docs_audit` in `.beadloom/config.yml`"
        ),
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
