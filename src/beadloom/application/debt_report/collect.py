# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt-data collection — aggregate health signals into a :class:`DebtData`.

Queries the indexed graph (undocumented/stale/untracked/oversized/high-fan-out
nodes) and the cross-domain signals (rule violations, git dormancy, test gaps)
into the raw counts + per-node issue map the scorer consumes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.debt_report.models import DebtData, DebtWeights

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _count_undocumented(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Count nodes that have no associated documentation.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "LEFT JOIN docs d ON d.ref_id = n.ref_id "
        "WHERE d.id IS NULL"
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_stale(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Count sync_state entries with status='stale'.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM sync_state WHERE status = 'stale'"
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_untracked(conn: sqlite3.Connection) -> tuple[int, list[str]]:
    """Count untracked source files (nodes with source but not tracked).

    This is a simplified check: nodes with a source directory
    that have no sync_state entries.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "WHERE n.source IS NOT NULL "
        "AND n.ref_id NOT IN (SELECT DISTINCT ref_id FROM sync_state)"
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_oversized(
    conn: sqlite3.Connection, threshold: int,
) -> tuple[int, list[str]]:
    """Count nodes whose *own* source directory has more symbols than threshold.

    For each node, child nodes' source prefixes are excluded so that only
    symbols from files directly owned by the node are counted.

    Returns (count, list_of_ref_ids).
    """
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()

    # Build a map of ref_id -> source prefix for all nodes
    source_map: dict[str, str] = {}
    for node in nodes:
        source_map[str(node[0])] = str(node[1]).rstrip("/") + "/"

    # Build child source prefixes per node via part_of edges
    # A child C of parent P means: C --[part_of]--> P
    child_prefixes: dict[str, list[str]] = {}
    edges = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ).fetchall()
    for edge in edges:
        child_ref = str(edge[0])
        parent_ref = str(edge[1])
        child_source = source_map.get(child_ref)
        if child_source is not None:
            child_prefixes.setdefault(parent_ref, []).append(child_source)

    oversized_refs: list[str] = []
    for node in nodes:
        ref_id = str(node[0])
        prefix = source_map[ref_id]

        # Get children's prefixes to exclude
        excludes = child_prefixes.get(ref_id, [])

        if not excludes:
            # No children — count all symbols under this prefix
            row = conn.execute(
                "SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE ?",
                (prefix + "%",),
            ).fetchone()
            count = int(row[0]) if row else 0
        else:
            # Count all symbols under prefix, then subtract those under
            # child prefixes
            row = conn.execute(
                "SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE ?",
                (prefix + "%",),
            ).fetchone()
            total = int(row[0]) if row else 0

            child_count = 0
            for child_prefix in excludes:
                crow = conn.execute(
                    "SELECT COUNT(*) FROM code_symbols WHERE file_path LIKE ?",
                    (child_prefix + "%",),
                ).fetchone()
                child_count += int(crow[0]) if crow else 0

            count = total - child_count

        if count > threshold:
            oversized_refs.append(ref_id)

    return len(oversized_refs), oversized_refs


def _count_high_fan_out(
    conn: sqlite3.Connection, threshold: int,
) -> tuple[int, list[str]]:
    """Count nodes with more outgoing edges than threshold.

    Returns (count, list_of_ref_ids).
    """
    rows = conn.execute(
        "SELECT src_ref_id, COUNT(*) as cnt FROM edges "
        "GROUP BY src_ref_id HAVING cnt > ?",
        (threshold,),
    ).fetchall()
    ref_ids = [str(r[0]) for r in rows]
    return len(ref_ids), ref_ids


def _count_dormant(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, list[str]]:
    """Count dormant domains (no git activity in 90 days).

    Returns (count, list_of_ref_ids).
    """
    try:
        from beadloom.infrastructure.git_activity import analyze_git_activity
    except ImportError:
        return 0, []

    # Build source_dirs from nodes
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    source_dirs: dict[str, str] = {}
    for node in nodes:
        source_dirs[str(node[0])] = str(node[1])

    if not source_dirs:
        return 0, []

    try:
        activities = analyze_git_activity(project_root, source_dirs)
    except (OSError, ValueError):
        return 0, []

    dormant_refs: list[str] = []
    for ref_id, activity in activities.items():
        if activity.activity_level == "dormant":
            dormant_refs.append(ref_id)

    return len(dormant_refs), dormant_refs


def _count_untested(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, list[str]]:
    """Count domains/features with no test coverage.

    Returns (count, list_of_ref_ids).
    """
    try:
        from beadloom.context_oracle.test_mapper import map_tests
    except ImportError:
        return 0, []

    # Build source_dirs from nodes
    nodes = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    source_dirs: dict[str, str] = {}
    for node in nodes:
        source_dirs[str(node[0])] = str(node[1])

    if not source_dirs:
        return 0, []

    try:
        mappings = map_tests(project_root, source_dirs)
    except (OSError, ValueError):
        return 0, []

    untested_refs: list[str] = []
    for ref_id, mapping in mappings.items():
        if mapping.coverage_estimate == "none":
            untested_refs.append(ref_id)

    return len(untested_refs), untested_refs


def _count_violations(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, int, dict[str, list[str]]]:
    """Count rule violations (errors and warnings).

    Returns (error_count, warning_count, per_node_violations).
    """
    try:
        from beadloom.graph.rule_engine import evaluate_all, load_rules
    except ImportError:
        return 0, 0, {}

    rules_path = project_root / "rules.yml"
    if not rules_path.is_file():
        # Also try .beadloom/rules.yml
        rules_path = project_root / ".beadloom" / "rules.yml"
        if not rules_path.is_file():
            return 0, 0, {}

    try:
        rules = load_rules(rules_path)
        violations = evaluate_all(conn, rules, project_root=project_root)
    except (ValueError, OSError):
        return 0, 0, {}

    errors = 0
    warnings = 0
    node_violations: dict[str, list[str]] = {}

    for v in violations:
        if v.severity == "error":
            errors += 1
        else:
            warnings += 1

        # Track per-node with severity prefix for weighted scoring
        if v.from_ref_id:
            sev = "error" if v.severity == "error" else "warning"
            node_violations.setdefault(v.from_ref_id, []).append(
                f"violation:{sev}:{v.rule_name}"
            )

    return errors, warnings, node_violations


def collect_debt_data(
    conn: sqlite3.Connection,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtData:
    """Aggregate debt data from all data sources.

    Collects counts from rule engine, sync state, doctor, git activity,
    and test mapper.
    """
    if weights is None:
        weights = DebtWeights()

    node_issues: dict[str, list[str]] = {}

    # 1. Rule violations
    error_count, warning_count, violation_nodes = _count_violations(
        conn, project_root
    )
    for ref_id, reasons in violation_nodes.items():
        node_issues.setdefault(ref_id, []).extend(reasons)

    # 2. Undocumented nodes
    undocumented_count, undoc_refs = _count_undocumented(conn)
    for ref_id in undoc_refs:
        node_issues.setdefault(ref_id, []).append("undocumented")

    # 3. Stale docs
    stale_count, stale_refs = _count_stale(conn)
    for ref_id in stale_refs:
        node_issues.setdefault(ref_id, []).append("stale_doc")

    # 4. Untracked files
    untracked_count, untracked_refs = _count_untracked(conn)
    for ref_id in untracked_refs:
        node_issues.setdefault(ref_id, []).append("untracked")

    # 5. Oversized domains
    oversized_count, oversized_refs = _count_oversized(
        conn, weights.oversized_symbols
    )
    for ref_id in oversized_refs:
        node_issues.setdefault(ref_id, []).append("oversized")

    # 6. High fan-out
    high_fan_out_count, fan_out_refs = _count_high_fan_out(
        conn, weights.high_fan_out_threshold
    )
    for ref_id in fan_out_refs:
        node_issues.setdefault(ref_id, []).append("high_fan_out")

    # 7. Dormant domains
    dormant_count, dormant_refs = _count_dormant(conn, project_root)
    for ref_id in dormant_refs:
        node_issues.setdefault(ref_id, []).append("dormant")

    # 8. Untested domains
    untested_count, untested_refs = _count_untested(conn, project_root)
    for ref_id in untested_refs:
        node_issues.setdefault(ref_id, []).append("untested")

    return DebtData(
        error_count=error_count,
        warning_count=warning_count,
        undocumented_count=undocumented_count,
        stale_count=stale_count,
        untracked_count=untracked_count,
        oversized_count=oversized_count,
        high_fan_out_count=high_fan_out_count,
        dormant_count=dormant_count,
        untested_count=untested_count,
        node_issues=node_issues,
    )
