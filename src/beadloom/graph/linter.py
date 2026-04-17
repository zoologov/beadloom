# beadloom:domain=graph
"""Linter orchestrator: load rules, ensure index is fresh, evaluate, format results."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.graph.rule_engine import Violation, evaluate_all, load_rules, validate_rules
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LintError(Exception):
    """Raised when lint encounters a configuration error."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LintResult:
    """Result of a lint run."""

    violations: list[Violation] = field(default_factory=list)
    rules_evaluated: int = 0
    files_scanned: int = 0
    imports_resolved: int = 0
    elapsed_ms: float = 0.0

    @property
    def error_count(self) -> int:
        """Count of violations with severity 'error'."""
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of violations with severity 'warn'."""
        return sum(1 for v in self.violations if v.severity == "warn")

    @property
    def has_errors(self) -> bool:
        """Return True if any violation has severity 'error'."""
        return any(v.severity == "error" for v in self.violations)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def lint(
    project_root: Path,
    *,
    rules_path: Path | None = None,
    reindex_before: bool = True,
) -> LintResult:
    """Run the lint process: reindex, load rules, evaluate, and return results.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).
    rules_path:
        Optional explicit path to ``rules.yml``.  When *None* the default
        location ``<project_root>/.beadloom/_graph/rules.yml`` is used.
    reindex_before:
        When *True* (the default), runs an incremental reindex before
        evaluating rules to ensure the database is fresh.

    Returns
    -------
    LintResult
        Summary with violations, counts, and timing.

    Raises
    ------
    LintError
        When the rules file is present but contains invalid configuration.
    """
    start = time.monotonic()

    # Step a: Incremental reindex (if requested).
    # Lazy import to avoid circular dependency:
    # graph/__init__ → linter → infra.reindex → graph.loader → graph/__init__
    if reindex_before:
        from beadloom.application.reindex import incremental_reindex

        incremental_reindex(project_root)

    # Step b: Open the database.
    db_path = project_root / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = open_db(db_path)
    create_schema(conn)

    try:
        # Step c: Resolve rules path.
        if rules_path is None:
            rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"

        # Step d: If no rules file, return empty result.
        if not rules_path.is_file():
            elapsed = (time.monotonic() - start) * 1000
            return LintResult(elapsed_ms=elapsed)

        # Step e: Load and validate rules.
        try:
            rules = load_rules(rules_path)
        except ValueError as exc:
            msg = f"Invalid rules configuration: {exc}"
            raise LintError(msg) from exc

        _warnings = validate_rules(rules, conn)

        # Step f: Count files_scanned (distinct file_path in code_imports).
        row = conn.execute("SELECT COUNT(DISTINCT file_path) FROM code_imports").fetchone()
        files_scanned: int = int(row[0]) if row is not None else 0

        # Step g: Count imports_resolved (where resolved_ref_id IS NOT NULL).
        row = conn.execute(
            "SELECT COUNT(*) FROM code_imports WHERE resolved_ref_id IS NOT NULL"
        ).fetchone()
        imports_resolved: int = int(row[0]) if row is not None else 0

        # Step h: Evaluate all rules.
        violations = evaluate_all(conn, rules)

        # Step i: Measure elapsed time.
        elapsed = (time.monotonic() - start) * 1000

        return LintResult(
            violations=violations,
            rules_evaluated=len(rules),
            files_scanned=files_scanned,
            imports_resolved=imports_resolved,
            elapsed_ms=elapsed,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_rich(result: LintResult) -> str:
    """Format a LintResult as human-readable Rich-style text (plain text, no Rich dependency).

    Example output with violations::

        Rules: 3 loaded
        Files: 25 scanned, 142 imports resolved

        x billing-auth-boundary
          Billing must not import from auth directly
          src/billing/invoice.py:12 -> imports auth (auth.tokens)

        2 violations found (3 rules evaluated, 0.8s)

    Example output without violations::

        Rules: 3 loaded
        Files: 25 scanned, 142 imports resolved

        No violations found (3 rules evaluated, 0.8s)
    """
    lines: list[str] = []

    # Header
    lines.append(f"Rules: {result.rules_evaluated} loaded")
    lines.append(
        f"Files: {result.files_scanned} scanned, {result.imports_resolved} imports resolved"
    )
    lines.append("")

    elapsed_s = result.elapsed_ms / 1000
    elapsed_str = f"{elapsed_s:.1f}s"

    if result.violations:
        for v in result.violations:
            marker = "\u26d4 [ERROR]" if v.severity == "error" else "\u26a0\ufe0f  [WARN]"
            lines.append(f"{marker} {v.rule_name}")
            lines.append(f"  {v.rule_description}")
            if v.file_path is not None:
                loc = v.file_path
                if v.line_number is not None:
                    loc += f":{v.line_number}"
                lines.append(f"  {loc} \u2192 {v.message}")
            else:
                lines.append(f"  {v.message}")
            lines.append("")

        lines.append(
            f"Errors: {result.error_count}, Warnings: {result.warning_count} "
            f"({result.rules_evaluated} rules evaluated, {elapsed_str})"
        )
    else:
        lines.append(
            f"\u2713 No violations found ({result.rules_evaluated} rules evaluated, {elapsed_str})"
        )

    return "\n".join(lines)


def _finding(v: Violation) -> dict[str, object]:
    """Project a :class:`Violation` to the stable, agent-actionable finding shape.

    Shape (BDL-039 F3 BEAD-02): ``{kind, rule, severity, locations, why,
    remediation}`` — reusable across ``--format json`` and ``--format github``.
    ``locations`` is a list of ``{file, line}`` (omitting ``line`` when absent),
    so the same finding maps cleanly to GitHub annotations. Deterministic by
    construction; ordering is the caller's responsibility (violations are
    pre-sorted by :func:`~beadloom.graph.rule_engine.evaluate_all`).
    """
    locations: list[dict[str, object]] = []
    if v.file_path is not None:
        loc: dict[str, object] = {"file": v.file_path}
        if v.line_number is not None:
            loc["line"] = v.line_number
        locations.append(loc)
    return {
        "kind": v.rule_type,
        "rule": v.rule_name,
        "severity": v.severity,
        "locations": locations,
        "why": v.message,
        "remediation": v.remediation,
    }


def format_json(result: LintResult) -> str:
    """Format a LintResult as structured JSON.

    Returns a JSON string with a ``violations`` array (backward-compatible
    keys, plus an additive ``remediation``), a stable agent-actionable
    ``findings`` array (``{kind, rule, severity, locations, why, remediation}``),
    and a ``summary`` object. The pre-sorted violation order makes the output
    deterministic.
    """
    violations_list: list[dict[str, object]] = []
    for v in result.violations:
        violations_list.append(
            {
                "rule_name": v.rule_name,
                "rule_type": v.rule_type,
                "severity": v.severity,
                "file_path": v.file_path if v.file_path is not None else None,
                "line_number": v.line_number if v.line_number is not None else None,
                "from_ref_id": v.from_ref_id if v.from_ref_id is not None else None,
                "to_ref_id": v.to_ref_id if v.to_ref_id is not None else None,
                "message": v.message,
                "remediation": v.remediation,
            }
        )

    output: dict[str, object] = {
        "violations": violations_list,
        "findings": [_finding(v) for v in result.violations],
        "summary": {
            "rules_evaluated": result.rules_evaluated,
            "violations_count": len(result.violations),
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "files_scanned": result.files_scanned,
            "imports_resolved": result.imports_resolved,
            "elapsed_ms": result.elapsed_ms,
        },
    }

    return json.dumps(output, indent=2)


def format_github(result: LintResult) -> str:
    """Format a LintResult as GitHub Actions workflow commands (BDL-039 F3 G2).

    Emits one ``::error`` / ``::warning`` command per violation so they appear
    as inline PR annotations::

        ::error file=src/billing/invoice.py,line=12::deny billing-no-auth: <why> — <remediation>

    The ``file``/``line`` parameters are included only when the violation has a
    location (graph-level violations omit them). Newlines inside a message are
    escaped to ``%0A`` per the workflow-command spec so the annotation stays on
    one logical line. Output is deterministic (violations are pre-sorted).
    Returns an empty string when there are no violations.
    """
    if not result.violations:
        return ""

    lines: list[str] = []
    for v in result.violations:
        level = "error" if v.severity == "error" else "warning"
        params: list[str] = []
        if v.file_path is not None:
            params.append(f"file={v.file_path}")
            if v.line_number is not None:
                params.append(f"line={v.line_number}")
        param_str = (" " + ",".join(params)) if params else ""
        msg = f"{v.rule_type} {v.rule_name}: {v.message}"
        if v.remediation:
            msg += f" — {v.remediation}"
        msg = msg.replace("\r\n", "%0A").replace("\n", "%0A").replace("\r", "%0A")
        lines.append(f"::{level}{param_str}::{msg}")

    return "\n".join(lines)


def format_porcelain(result: LintResult) -> str:
    """Format a LintResult as machine-readable one-line-per-violation output.

    Format: ``rule_name:rule_type:file_path:line:from_ref:to_ref``

    Empty file_path/line_number/ref_ids are represented as empty strings.
    Returns empty string when there are no violations.
    """
    if not result.violations:
        return ""

    lines: list[str] = []
    for v in result.violations:
        file_path = v.file_path if v.file_path is not None else ""
        line_number = str(v.line_number) if v.line_number is not None else ""
        from_ref = v.from_ref_id if v.from_ref_id is not None else ""
        to_ref = v.to_ref_id if v.to_ref_id is not None else ""
        lines.append(
            f"{v.rule_name}:{v.rule_type}:{v.severity}:{file_path}:{line_number}:{from_ref}:{to_ref}"
        )

    return "\n".join(lines)
