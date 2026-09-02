# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Linter orchestrator: load rules, ensure index is fresh, evaluate, format results."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    Violation,
    count_unattributed_import_files,
    evaluate_all,
    inert_rule_names,
    load_rules,
    suppressed_crossings,
)
from beadloom.infrastructure.db import connection, create_schema, readonly_connection

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from beadloom.graph.rules import Rule, SuppressedCrossing


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
    #: How many of ``rules_evaluated`` could not fire at all — an empty matcher,
    #: an absent edge kind, a threshold nobody set, a source root with no module.
    #: Reported next to the rule count because the two together are the honest
    #: statement: "13 rules evaluated" alone reads the same whether the rules
    #: passed or never looked (BDL-UX #172 / BDL-061.48). Rules whose only
    #: liveness finding is a dead *exemption* are NOT counted here: the rule
    #: itself fires, and that finding belongs to `beadloom-mr2l.49`.
    rules_inert: int = 0
    #: Every crossing a ``forbid_import`` exemption excused on this run. Carried
    #: as the crossings themselves, not merely a number, so the count can be
    #: audited rather than trusted: "3 crossings suppressed" invites the question
    #: "which three", and a result that cannot answer it is another green count
    #: nobody checked (review .7 MAJOR 2 / BDL-061.49).
    suppressed: list[SuppressedCrossing] = field(default_factory=list)
    files_scanned: int = 0
    #: How many of ``files_scanned`` belong to no node at all — no annotation
    #: naming one, and under no node's ``source``. Every ``deny`` rule is blind
    #: to them, so a clean deny result covers ``files_scanned`` MINUS this
    #: number. Measured on this repository before BDL-061.50 the equivalent was
    #: 22 of 128 (annotation-only attribution); the count is printed so the
    #: coverage of a green result is stated rather than assumed.
    files_unattributed: int = 0
    imports_resolved: int = 0
    elapsed_ms: float = 0.0

    @property
    def violations_suppressed(self) -> int:
        """How many real crossings an exemption kept out of ``violations``."""
        return len(self.suppressed)

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
    reindex: Callable[[Path], object] | None = None,
) -> LintResult:
    """Run the lint process: (optionally) reindex, load rules, evaluate, return.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).
    rules_path:
        Optional explicit path to ``rules.yml``.  When *None* the default
        location ``<project_root>/.beadloom/_graph/rules.yml`` is used.
    reindex:
        Optional reindex callback invoked with ``project_root`` before rules are
        evaluated, to ensure the database is fresh.  Injected by the caller so
        that this (domain-layer) module does not depend on the application-layer
        reindex orchestrator — the dependency points DOWN/IN, never UP.  When
        *None* (the default) no reindex is performed and the existing index is
        used as-is.

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

    # Step a: Refresh the index, if the caller injected a reindex callback.
    if reindex is not None:
        reindex(project_root)

    # Step b: Resolve rules and return early when there are none. This happens
    # BEFORE the database is touched: "no rules" is a truthful empty result
    # whatever the index looks like, and it must not require an index to exist.
    if rules_path is None:
        rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if not rules_path.is_file():
        return LintResult(elapsed_ms=(time.monotonic() - start) * 1000)

    try:
        rules = load_rules(rules_path)
    except ValueError as exc:
        msg = f"Invalid rules configuration: {exc}"
        raise LintError(msg) from exc

    # Step c: Open the index. Without a reindex callback this is a pure read,
    # so the index is opened read-only and an ABSENT one is an error rather
    # than an empty-but-clean result: linting a database that does not exist
    # reported "0 violations" while creating it (BDL-UX #147).
    db_path = project_root / ".beadloom" / "beadloom.db"
    if reindex is None:
        with _read_only_index(db_path) as conn:
            return _evaluate(conn, rules, project_root=project_root, start=start)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connection(db_path) as conn:
        create_schema(conn)
        return _evaluate(conn, rules, project_root=project_root, start=start)


@contextmanager
def _read_only_index(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the index read-only, translating a missing file into a LintError."""
    try:
        with readonly_connection(db_path) as conn:
            yield conn
    except FileNotFoundError as exc:
        msg = (
            f"index not found at {db_path} — nothing to lint against. "
            "Run `beadloom reindex` first, or drop --no-reindex."
        )
        raise LintError(msg) from exc


def _evaluate(
    conn: sqlite3.Connection,
    rules: list[Rule],
    *,
    project_root: Path,
    start: float,
) -> LintResult:
    """Evaluate *rules* against an open index connection and time the run."""
    try:
        # Which rules cannot fire at all. `evaluate_all` reports each one as a
        # `rule_liveness` finding; the count is carried separately so the
        # summary line can qualify "N rules evaluated" instead of leaving the
        # reader to infer it from the findings (BDL-UX #172 / BDL-061.48).
        inert = inert_rule_names(conn, rules, project_root=project_root)

        # What the boundaries DID catch and excused. Reported on every run, not
        # only when something is wrong: an exemption that suppresses a crossing
        # silently is how "0 violations" comes to mean "0 violations we counted".
        excused = suppressed_crossings(
            conn, [rule for rule in rules if isinstance(rule, ImportBoundaryRule)]
        )

        # files_scanned: distinct file_path in code_imports.
        row = conn.execute("SELECT COUNT(DISTINCT file_path) FROM code_imports").fetchone()
        files_scanned: int = int(row[0]) if row is not None else 0

        # How many of those files no rule can attribute to a node (BDL-061.50).
        files_unattributed: int = count_unattributed_import_files(conn)

        # imports_resolved: where resolved_ref_id IS NOT NULL.
        row = conn.execute(
            "SELECT COUNT(*) FROM code_imports WHERE resolved_ref_id IS NOT NULL"
        ).fetchone()
        imports_resolved: int = int(row[0]) if row is not None else 0

        # ``project_root`` roots the on-disk module enumeration used by the
        # module-coverage rule (closes the zero-symbol false-negative —
        # BDL-051 S3a / BEAD-17).
        violations = evaluate_all(conn, rules, project_root=project_root)
    except sqlite3.OperationalError as exc:
        msg = (
            f"index cannot be read ({exc}) — it predates the current schema. "
            "Run `beadloom reindex` to rebuild it."
        )
        raise LintError(msg) from exc

    return LintResult(
        violations=violations,
        rules_evaluated=len(rules),
        rules_inert=len(inert),
        suppressed=excused,
        files_scanned=files_scanned,
        files_unattributed=files_unattributed,
        imports_resolved=imports_resolved,
        elapsed_ms=(time.monotonic() - start) * 1000,
    )


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _inert_note(result: LintResult) -> str:
    """The clause that stops the rule count from over-claiming, or "" when it does not.

    Absent when every rule can fire, so the common line keeps its shape; present
    the moment a rule is counted as evaluated while checking nothing.
    """
    if not result.rules_inert:
        return ""
    return f", {result.rules_inert} of them unable to check anything"


def _suppressed_note(result: LintResult) -> str:
    """The clause that stops "no violations" from over-claiming, or "" when it does not.

    Same treatment as :func:`_inert_note` and for the same reason: a count is
    honest only next to what it did not count. Absent when nothing was excused,
    so the common line keeps its shape; present the moment a real crossing was
    kept out of the violation list by an exemption (BDL-061.49).
    """
    excused = result.violations_suppressed
    if not excused:
        return ""
    crossings = "crossing" if excused == 1 else "crossings"
    return f", {excused} {crossings} suppressed by an exemption"


def _unattributed_note(result: LintResult) -> str:
    """The clause that stops the scanned count from over-claiming, or "".

    Same treatment as :func:`_inert_note` and :func:`_suppressed_note`: absent
    when every scanned file has an owner, so the common line keeps its shape;
    present the moment a file no deny rule can see is counted as scanned
    (BDL-061.50).
    """
    if not result.files_unattributed:
        return ""
    return f", {result.files_unattributed} attributable to no node"


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
        f"{_unattributed_note(result)}"
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
            f"({result.rules_evaluated} rules evaluated{_inert_note(result)}"
            f"{_suppressed_note(result)}, {elapsed_str})"
        )
    else:
        lines.append(
            f"\u2713 No violations found ({result.rules_evaluated} rules evaluated"
            f"{_inert_note(result)}{_suppressed_note(result)}, {elapsed_str})"
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

    ``node`` is the violating node's ref_id, or ``None`` for a finding that is
    about no single node. It was added by BDL-067 `.14`: the node was named in
    ``why`` as prose and nowhere else, so a reader that needed it — ``init``,
    telling an adopter which graph file to open — had to parse an English
    sentence to get it. A require rule fires on one node and a location the
    reader can act on is the point of this shape.
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
        "node": v.from_ref_id,
        "locations": locations,
        "why": v.message,
        "remediation": v.remediation,
    }


def format_json(result: LintResult) -> str:
    """Format a LintResult as structured JSON.

    Returns a JSON string with a ``violations`` array (backward-compatible
    keys, plus an additive ``remediation``), a stable agent-actionable
    ``findings`` array (``{kind, rule, severity, locations, why, remediation}``),
    a ``suppressed`` array naming every crossing an exemption excused, and a
    ``summary`` object. The pre-sorted violation order makes the output
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
        # What an exemption kept OUT of `violations`, so a machine reader can
        # audit the suppressed count instead of taking it on trust.
        "suppressed": [crossing.to_dict() for crossing in result.suppressed],
        "summary": {
            "rules_evaluated": result.rules_evaluated,
            "rules_inert": result.rules_inert,
            "violations_suppressed": result.violations_suppressed,
            "violations_count": len(result.violations),
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "files_scanned": result.files_scanned,
            "files_unattributed": result.files_unattributed,
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

    Format: ``rule_name:rule_type:severity:file_path:line:from_ref:to_ref``

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
