# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt-data collection — aggregate health signals into a :class:`DebtData`.

Queries the indexed graph (undocumented/stale/untracked/oversized/high-fan-out
nodes) and the cross-domain signals (rule violations, git dormancy, test gaps)
into the raw counts + per-node issue map the scorer consumes. The test-gap
signal is read from the test binding the reindex recorded, not guessed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.activity_settings import activity_exclusions
from beadloom.application.debt_report.models import DebtData, DebtWeights
from beadloom.context_oracle.test_binding import (
    describe_test_file_recognition,
    describe_unplaced,
)
from beadloom.infrastructure.repository import (
    count_test_files_by_placement,
    get_node_sources,
    get_part_of_containers,
    read_test_layout,
)

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
    """Count dormant nodes (no git activity in 90 days).

    A box is read with its ``part_of`` parts, as the node card reads it
    (BDL-078 F-activity): a box whose parts changed is not dormant because its
    own files stood still. A change only to files the project declares
    machine-written is no change (``beadloom-btkd.1``).

    Returns (count, list_of_ref_ids).
    """
    try:
        from beadloom.infrastructure.git_activity import analyze_git_activity
    except ImportError:
        return 0, []

    source_dirs = get_node_sources(conn)
    if not source_dirs:
        return 0, []

    try:
        activities = analyze_git_activity(
            project_root,
            source_dirs,
            get_part_of_containers(conn),
            excluded=activity_exclusions(project_root),
        )
    except (OSError, ValueError):
        return 0, []

    dormant_refs: list[str] = []
    for ref_id, activity in activities.items():
        if activity.activity_level == "dormant":
            dormant_refs.append(ref_id)

    return len(dormant_refs), dormant_refs


def _count_untested(conn: sqlite3.Connection) -> tuple[int, list[str], str]:
    """Count the nodes the test binding covers that no test file binds to.

    Returns (count, list_of_ref_ids, population). The binding is what the reindex
    wrote into each node's ``extra["tests"]`` (BDL-074 C1): the population is every
    node carrying that key, and a node whose ``test_files`` is empty is untested.

    While any test file is unplaced the count is WITHHELD — 0, with the reason as
    the population — because an unplaced file binds to no node, so a node with no
    bound test may still be tested by one. Counting it would charge a project for
    its layout, not its tests.

    The name-guessing mapper this replaces counted a node only when it detected
    no test framework anywhere, so it scored 0 for any project with a test file.
    The binding scores 0 while any file is unplaced, and once every one is placed
    it charges only the nodes none of them binds to. It reads the conventions
    that mapper read, each in the place its ecosystem keeps it (``beadloom-2mj3.15``):
    pytest, Go and Jest files beside the code or under a root, Jest's
    ``__tests__/`` folders, every Java and Kotlin file in ``src/test/``, and every
    Swift file in a ``*Tests`` folder — the five default groups of
    :mod:`beadloom.context_oracle.test_layout`. A file the mapper bound only by its
    name, in a ``tests/``, ``test/``, ``spec/`` or top-level ``__tests__/`` folder,
    is read under those default roots and unplaced, so the count is withheld — 0,
    as on main (the owner's NG1 ruling; ``beadloom-2mj3.15``, ``.17``). The debt
    report's integration test ``test_an_adopter_scores_what_it_scored_before`` runs
    that claim on one project per convention.

    The limit it keeps: a test file outside every root, test tree and node source
    is not read — an Xcode test target such as ``ShopTests/``, whose folder is
    named after the project, until ``tests.mirrors`` declares it (NG2, accepted by
    the owner) — and a marker such as ``conftest.py`` without a test file names no
    framework (NG4). Such a project has every covered node counted where the mapper
    counted 0. So the population ALWAYS ends with the patterns and the roots a test
    file is read by, and "all N test file(s) placed" reads as "all N files those
    patterns matched".
    """
    placements = count_test_files_by_placement(conn)
    layout = read_test_layout(conn)
    recognition = "" if layout is None else f"; {describe_test_file_recognition(layout)}"
    unplaced = describe_unplaced(placements, layout)
    if unplaced is not None:
        return (
            0,
            [],
            f"not counted: {unplaced}, so a node with no bound test may still be tested"
            f"{recognition}",
        )

    covered = 0
    untested_refs: list[str] = []
    for row in conn.execute("SELECT ref_id, extra FROM nodes ORDER BY ref_id").fetchall():
        tests = _bound_tests(row["extra"])
        if tests is None:
            continue
        covered += 1
        if not tests.get("test_files"):
            untested_refs.append(str(row["ref_id"]))
    population = (
        f"counted over {covered} node(s) the test binding covers, "
        f"all {sum(placements.values())} test file(s) placed{recognition}"
    )
    return len(untested_refs), untested_refs, population


def _bound_tests(raw_extra: object) -> dict[str, object] | None:
    """A node's ``extra["tests"]`` when the binding covers it, else ``None``."""
    if not isinstance(raw_extra, str) or not raw_extra:
        return None
    try:
        extra = json.loads(raw_extra)
    except json.JSONDecodeError:
        return None
    tests = extra.get("tests") if isinstance(extra, dict) else None
    return tests if isinstance(tests, dict) else None


def _count_violations(
    conn: sqlite3.Connection,
    project_root: Path,
) -> tuple[int, int, dict[str, list[str]], list[str]]:
    """Count rule violations, and state the population they were counted over.

    Returns (error_count, warning_count, per_node_violations, layer_populations).

    The fourth value is why this function changed at all. The counts beside it
    are counts over whatever set the rules could look at, and a layer rule judges
    only edges whose ends are both in a declared layer — by a node's own tag, or
    since BDL-070 B3 by its nearest ``part_of`` container's. No figure is quoted
    here, because it moves with the graph, and on this repository this function
    loads no rules at all until BDL-UX #291 is repaired: it looks for the rules
    file at ``rules.yml`` and ``.beadloom/rules.yml``, and this project declares
    them in ``.beadloom/_graph/rules.yml``. The debt-report SPEC carries that
    measurement with its date.

    This collector is one of the two surfaces that call ``evaluate_all`` without
    ever building a ``LintResult``, so the population is read here from the same
    ``reach_of`` the evaluator uses rather than parsed back out of a finding's
    prose (BDL-070 A4).

    Nothing here re-counts: the population advisory is counted exactly as A2
    left it counted, among the warnings.
    """
    try:
        from beadloom.graph.rule_engine import (
            LayerRule,
            evaluate_all,
            layer_rule_reaches,
            load_rules,
            population_phrase,
            stated_populations,
        )
    except ImportError:
        return 0, 0, {}, []

    rules_path = project_root / "rules.yml"
    if not rules_path.is_file():
        # Also try .beadloom/rules.yml
        rules_path = project_root / ".beadloom" / "rules.yml"
        if not rules_path.is_file():
            return 0, 0, {}, []

    try:
        rules = load_rules(rules_path)
        violations = evaluate_all(conn, rules, project_root=project_root)
        reaches = layer_rule_reaches(
            conn, [rule for rule in rules if isinstance(rule, LayerRule)]
        )
    except (ValueError, OSError):
        return 0, 0, {}, []

    populations = [population_phrase(reach) for reach in stated_populations(reaches)]
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

    return errors, warnings, node_violations, populations


def collect_debt_data(
    conn: sqlite3.Connection,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtData:
    """Aggregate debt data from all data sources.

    Collects counts from rule engine, sync state, doctor, git activity,
    and the test binding.
    """
    if weights is None:
        weights = DebtWeights()

    node_issues: dict[str, list[str]] = {}

    # 1. Rule violations
    error_count, warning_count, violation_nodes, layer_populations = _count_violations(
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

    # 8. Untested nodes, read from the test binding
    untested_count, untested_refs, test_population = _count_untested(conn)
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
        layer_populations=layer_populations,
        test_population=test_population,
    )
