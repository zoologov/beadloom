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
        from beadloom.infrastructure.reindex import incremental_reindex

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
            lines.append(f"\u2717 {v.rule_name}")
            lines.append(f"  {v.rule_description}")
            if v.file_path is not None:
                loc = v.file_path
                if v.line_number is not None:
                    loc += f":{v.line_number}"
                lines.append(f"  {loc} \u2192 {v.message}")
            else:
                lines.append(f"  {v.message}")
            lines.append("")

        count = len(result.violations)
        lines.append(
            f"{count} violations found ({result.rules_evaluated} rules evaluated, {elapsed_str})"
        )
    else:
        lines.append(
            f"\u2713 No violations found ({result.rules_evaluated} rules evaluated, {elapsed_str})"
        )

    return "\n".join(lines)


def format_json(result: LintResult) -> str:
    """Format a LintResult as structured JSON.

    Returns a JSON string with ``violations`` array and ``summary`` object.
    """
    violations_list: list[dict[str, object]] = []
    for v in result.violations:
        violations_list.append(
            {
                "rule_name": v.rule_name,
                "rule_type": v.rule_type,
                "file_path": v.file_path if v.file_path is not None else None,
                "line_number": v.line_number if v.line_number is not None else None,
                "from_ref_id": v.from_ref_id if v.from_ref_id is not None else None,
                "to_ref_id": v.to_ref_id if v.to_ref_id is not None else None,
                "message": v.message,
            }
        )

    output: dict[str, object] = {
        "violations": violations_list,
        "summary": {
            "rules_evaluated": result.rules_evaluated,
            "violations_count": len(result.violations),
            "files_scanned": result.files_scanned,
            "imports_resolved": result.imports_resolved,
            "elapsed_ms": result.elapsed_ms,
        },
    }

    return json.dumps(output, indent=2)


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
        lines.append(f"{v.rule_name}:{v.rule_type}:{file_path}:{line_number}:{from_ref}:{to_ref}")

    return "\n".join(lines)
