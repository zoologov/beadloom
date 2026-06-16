# beadloom:domain=graph
# beadloom:feature=rule-engine
"""Cycle detection: find circular ``depends_on``/``uses`` chains in the graph.

The detector (BDL-059 S3 / #124) uses an explicit WHITE/GREY/BLACK colored DFS.
Each ``start_node``'s search keeps its live path as a *set* (GREY membership)
alongside the path list, so the cycle-closing test is O(1) instead of the prior
O(n) ``neighbor in path`` scan. WHITE = not on the current path, GREY = on it
(an edge into a GREY node closes a cycle), BLACK = popped off the current path.

A global, cross-start prune is deliberately NOT applied: the recorded cycle
*representative* is the raw rotation of whichever path first reaches it, so the
per-start traversal is kept identical to the original to preserve that rotation
byte-for-byte. The win here is the O(1) GREY-membership test; output is
preserved exactly — the same set of unique normalized cycles, the same
representative rotation per cycle, the ``seen_cycles`` dedup, and ``max_depth``
semantics — pinned by the golden-parity test (``tests/test_cycle_rule.py``).

This module also owns the edge-*liveness* SQL helpers (``active`` edges are the
only live reality for structural checks — BDL-037 Principle 8), which the layer
evaluator shares for the same "structural reality" reason.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.types import LIVE_EDGE_LIFECYCLES, CycleRule, Violation

if TYPE_CHECKING:
    import sqlite3

def _normalize_cycle(path: list[str]) -> tuple[str, ...]:
    """Normalize a cycle path so that the smallest element is first.

    This ensures that cycle A->B->C->A is the same as B->C->A->B.
    The path should NOT include the repeated start node at the end.
    """
    if not path:
        return ()
    min_idx = path.index(min(path))
    rotated = path[min_idx:] + path[:min_idx]
    return tuple(rotated)


def _has_lifecycle_column(conn: sqlite3.Connection) -> bool:
    """Return True if the ``edges`` table has a ``lifecycle`` column.

    Guards against pre-migration databases so structural checks degrade
    gracefully (treating every edge as live) rather than raising.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(edges)").fetchall()}
    return "lifecycle" in columns


def _live_lifecycle_clause(conn: sqlite3.Connection) -> tuple[str, tuple[str, ...]]:
    """Build a SQL filter restricting edges to live (``active``) lifecycles.

    Returns an ``(sql_fragment, params)`` pair. When the column is absent
    (old DB), returns an empty fragment so all edges are treated as live.
    """
    if not _has_lifecycle_column(conn):
        return "", ()
    live = tuple(sorted(LIVE_EDGE_LIFECYCLES))
    placeholders = ", ".join("?" for _ in live)
    return f" AND lifecycle IN ({placeholders})", live


def _build_adjacency(
    conn: sqlite3.Connection,
    edge_kinds: tuple[str, ...],
) -> dict[str, list[str]]:
    """Build an adjacency list from the edges table for given edge kinds.

    Only live (``active``) edges are included: ``planned``/``deprecated``/
    ``dead`` edges represent intent or history, not a live cycle (BDL-037).
    """
    placeholders = ", ".join("?" for _ in edge_kinds)
    life_clause, life_params = _live_lifecycle_clause(conn)
    query = (
        f"SELECT src_ref_id, dst_ref_id FROM edges "  # noqa: S608
        f"WHERE kind IN ({placeholders}){life_clause}"
    )
    rows = conn.execute(query, (*edge_kinds, *life_params)).fetchall()
    adj: dict[str, list[str]] = {}
    for row in rows:
        src = str(row[0])
        dst = str(row[1])
        adj.setdefault(src, []).append(dst)
    return adj


def _record_cycle(
    rule: CycleRule,
    path: list[str],
    closing: str,
    seen_cycles: set[tuple[str, ...]],
    violations: list[Violation],
) -> None:
    """Record a newly-discovered cycle closing on *closing* along *path*.

    *path* is the GREY stack from the start node to the current node; the cycle
    is the slice from the first occurrence of *closing* to the end. Dedups via
    the normalized form, so each unique cycle is reported once.
    """
    cycle_start_idx = path.index(closing)
    cycle_path = path[cycle_start_idx:]

    normalized = _normalize_cycle(cycle_path)
    if normalized in seen_cycles:
        return
    seen_cycles.add(normalized)

    display_path = " → ".join([*cycle_path, closing])
    violations.append(
        Violation(
            rule_name=rule.name,
            rule_description=rule.description,
            rule_type="cycle",
            severity=rule.severity,
            file_path=None,
            line_number=None,
            from_ref_id=cycle_path[0],
            to_ref_id=cycle_path[-1],
            message=(
                f"Circular dependency detected: {display_path} (rule '{rule.name}')"
            ),
        )
    )


def _walk_cycles(
    start_node: str,
    adj: dict[str, list[str]],
    rule: CycleRule,
    seen_cycles: set[tuple[str, ...]],
    violations: list[Violation],
) -> None:
    """Iterative DFS from *start_node*, recording every cycle on its live path.

    Each stack frame carries its own GREY path: the ``path`` list (for the
    recorded representative + display order) and a twin ``path_set`` for the
    O(1) cycle-closing membership test. A neighbor already in ``path_set`` is a
    GREY node and closes a cycle; otherwise, while the path is shorter than
    ``rule.max_depth``, the neighbor is pushed as a new GREY frame. This mirrors
    the original per-start traversal exactly (preserving the representative
    rotation), trading only the O(n) ``neighbor in path`` scan for O(1).
    """
    # Stack of (node, path_list, path_set). The path_set is the GREY membership
    # for that frame; both are bounded by max_depth so per-frame copies are cheap.
    stack: list[tuple[str, list[str], set[str]]] = [
        (start_node, [start_node], {start_node})
    ]

    while stack:
        current, path, path_set = stack.pop()

        for neighbor in adj.get(current, []):
            if neighbor in path_set:
                # GREY back-edge: a cycle on the current path.
                _record_cycle(rule, path, neighbor, seen_cycles, violations)
            elif len(path) < rule.max_depth:
                stack.append((neighbor, [*path, neighbor], {*path_set, neighbor}))


def evaluate_cycle_rules(conn: sqlite3.Connection, rules: list[CycleRule]) -> list[Violation]:
    """Evaluate cycle rules against the edges table using colored DFS.

    For each rule, walks outgoing edges of the specified kind(s) looking for
    cycles. Reports each unique cycle once with the full path in the message.
    """
    if not rules:
        return []

    violations: list[Violation] = []

    for rule in rules:
        # Normalize edge_kind to a tuple
        if isinstance(rule.edge_kind, str):
            edge_kinds: tuple[str, ...] = (rule.edge_kind,)
        else:
            edge_kinds = rule.edge_kind

        # Build adjacency list once per rule.
        adj = _build_adjacency(conn, edge_kinds)

        # Collect all nodes that participate in edges.
        all_nodes: set[str] = set(adj.keys())
        for neighbors in adj.values():
            all_nodes.update(neighbors)

        # Track found cycles (normalized) to avoid duplicates across all starts.
        seen_cycles: set[tuple[str, ...]] = set()

        for start_node in sorted(all_nodes):
            _walk_cycles(start_node, adj, rule, seen_cycles, violations)

    return violations
