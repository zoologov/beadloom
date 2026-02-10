"""Impact analysis: bidirectional BFS from a target node."""

# beadloom:domain=impact-analysis

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.context_builder import suggest_ref_id

if TYPE_CHECKING:
    import sqlite3

    from rich.console import Console
    from rich.tree import Tree


@dataclass(frozen=True)
class NodeInfo:
    """Basic node information."""

    ref_id: str
    kind: str
    summary: str


@dataclass(frozen=True)
class TreeNode:
    """Recursive tree node for upstream/downstream display."""

    ref_id: str
    kind: str
    summary: str
    edge_kind: str
    children: tuple[TreeNode, ...] = ()


@dataclass(frozen=True)
class ImpactSummary:
    """Aggregated impact metrics."""

    downstream_direct: int
    downstream_transitive: int
    doc_coverage: float  # percentage 0-100
    stale_count: int


@dataclass(frozen=True)
class WhyResult:
    """Complete result of impact analysis."""

    node: NodeInfo
    upstream: tuple[TreeNode, ...]
    downstream: tuple[TreeNode, ...]
    impact: ImpactSummary


def _build_tree(
    conn: sqlite3.Connection,
    start_ref_id: str,
    direction: str,
    depth: int,
    max_nodes: int,
) -> tuple[TreeNode, ...]:
    """Build a recursive tree via BFS in the given direction.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    start_ref_id:
        The node to start traversal from (NOT included in the tree).
    direction:
        "upstream" — follow outgoing edges (src_ref_id = current).
        "downstream" — follow incoming edges (dst_ref_id = current).
    depth:
        Maximum traversal depth.
    max_nodes:
        Maximum total nodes to include.

    Returns a tuple of top-level TreeNode entries.
    """
    if depth <= 0:
        return ()

    visited: set[str] = {start_ref_id}
    node_count = 0

    # BFS queue: (current_ref_id, current_depth, parent_ref_id, edge_kind)
    queue: deque[tuple[str, int, str, str]] = deque()

    # Children map: parent_ref_id -> list of (child_ref_id, edge_kind)
    children_map: dict[str, list[tuple[str, str]]] = {}
    # Node info cache
    node_cache: dict[str, tuple[str, str]] = {}  # ref_id -> (kind, summary)

    # Seed the queue with immediate neighbors
    neighbors = _get_neighbors(conn, start_ref_id, direction)
    for neighbor_id, edge_kind in neighbors:
        if neighbor_id not in visited and node_count < max_nodes:
            visited.add(neighbor_id)
            node_count += 1
            queue.append((neighbor_id, 1, start_ref_id, edge_kind))
            children_map.setdefault(start_ref_id, []).append((neighbor_id, edge_kind))
            _cache_node(conn, neighbor_id, node_cache)

    # BFS expansion
    while queue:
        current_id, current_depth, _parent, _ekind = queue.popleft()
        if current_depth >= depth:
            continue
        if node_count >= max_nodes:
            break

        next_neighbors = _get_neighbors(conn, current_id, direction)
        for neighbor_id, edge_kind in next_neighbors:
            if neighbor_id in visited:
                continue
            if node_count >= max_nodes:
                break
            visited.add(neighbor_id)
            node_count += 1
            queue.append((neighbor_id, current_depth + 1, current_id, edge_kind))
            children_map.setdefault(current_id, []).append((neighbor_id, edge_kind))
            _cache_node(conn, neighbor_id, node_cache)

    # Build tree recursively from children_map
    def _build(parent_id: str) -> tuple[TreeNode, ...]:
        child_list = children_map.get(parent_id, [])
        result: list[TreeNode] = []
        for child_id, edge_kind in child_list:
            kind, summary = node_cache.get(child_id, ("", ""))
            result.append(
                TreeNode(
                    ref_id=child_id,
                    kind=kind,
                    summary=summary,
                    edge_kind=edge_kind,
                    children=_build(child_id),
                )
            )
        return tuple(result)

    return _build(start_ref_id)


def _get_neighbors(
    conn: sqlite3.Connection,
    ref_id: str,
    direction: str,
) -> list[tuple[str, str]]:
    """Get neighbors in the given direction.

    Returns list of (neighbor_ref_id, edge_kind).
    """
    if direction == "upstream":
        # Outgoing edges: this node depends on / uses something
        rows = conn.execute(
            "SELECT dst_ref_id, kind FROM edges WHERE src_ref_id = ?",
            (ref_id,),
        ).fetchall()
        return [(row["dst_ref_id"], row["kind"]) for row in rows]
    # downstream: incoming edges — something depends on this node
    rows = conn.execute(
        "SELECT src_ref_id, kind FROM edges WHERE dst_ref_id = ?",
        (ref_id,),
    ).fetchall()
    return [(row["src_ref_id"], row["kind"]) for row in rows]


def _cache_node(
    conn: sqlite3.Connection,
    ref_id: str,
    cache: dict[str, tuple[str, str]],
) -> None:
    """Fetch and cache node kind/summary."""
    if ref_id in cache:
        return
    row = conn.execute(
        "SELECT kind, summary FROM nodes WHERE ref_id = ?",
        (ref_id,),
    ).fetchone()
    if row is not None:
        cache[ref_id] = (row["kind"], row["summary"])
    else:
        cache[ref_id] = ("", "")


def _count_tree_nodes(trees: tuple[TreeNode, ...], depth: int = 0) -> tuple[int, int]:
    """Count direct (depth 1) and transitive (depth > 1) nodes.

    Returns (direct_count, transitive_count).
    """
    direct = 0
    transitive = 0
    for node in trees:
        if depth == 0:
            direct += 1
        else:
            transitive += 1
        child_d, child_t = _count_tree_nodes(node.children, depth + 1)
        direct += child_d
        transitive += child_t
    return direct, transitive


def _collect_all_refs(trees: tuple[TreeNode, ...]) -> set[str]:
    """Recursively collect all ref_ids from a tree tuple."""
    refs: set[str] = set()
    for node in trees:
        refs.add(node.ref_id)
        refs.update(_collect_all_refs(node.children))
    return refs


def _compute_doc_coverage(
    conn: sqlite3.Connection,
    downstream_refs: set[str],
) -> float:
    """Compute % of downstream nodes that have at least one doc."""
    if not downstream_refs:
        return 100.0

    placeholders = ",".join("?" for _ in downstream_refs)
    row = conn.execute(
        f"SELECT COUNT(DISTINCT ref_id) FROM docs "  # noqa: S608
        f"WHERE ref_id IN ({placeholders})",
        tuple(downstream_refs),
    ).fetchone()
    covered = int(row[0])
    return covered / len(downstream_refs) * 100


def _count_stale_docs(
    conn: sqlite3.Connection,
    downstream_refs: set[str],
) -> int:
    """Count stale sync_state entries for downstream nodes."""
    if not downstream_refs:
        return 0

    placeholders = ",".join("?" for _ in downstream_refs)
    row = conn.execute(
        f"SELECT COUNT(*) FROM sync_state "  # noqa: S608
        f"WHERE ref_id IN ({placeholders}) AND status = 'stale'",
        tuple(downstream_refs),
    ).fetchone()
    return int(row[0])


def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
) -> WhyResult:
    """Perform impact analysis on a node.

    Parameters
    ----------
    conn:
        Open SQLite connection with beadloom schema.
    ref_id:
        The node to analyze.
    depth:
        Maximum BFS traversal depth (default 3).
    max_nodes:
        Maximum nodes per direction to prevent explosion (default 50).

    Returns
    -------
    WhyResult
        Complete impact analysis result.

    Raises
    ------
    LookupError
        If ref_id does not exist (with suggestions).
    """
    # Validate node exists
    row = conn.execute(
        "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
        (ref_id,),
    ).fetchone()
    if row is None:
        suggestions = suggest_ref_id(conn, ref_id)
        msg = f'"{ref_id}" not found.'
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        raise LookupError(msg)

    node = NodeInfo(ref_id=row["ref_id"], kind=row["kind"], summary=row["summary"])

    # Build upstream tree (outgoing edges: what this node depends on)
    upstream = _build_tree(conn, ref_id, "upstream", depth, max_nodes)

    # Build downstream tree (incoming edges: what depends on this node)
    downstream = _build_tree(conn, ref_id, "downstream", depth, max_nodes)

    # Compute impact summary
    direct, transitive = _count_tree_nodes(downstream)
    downstream_refs = _collect_all_refs(downstream)
    doc_coverage = _compute_doc_coverage(conn, downstream_refs)
    stale_count = _count_stale_docs(conn, downstream_refs)

    impact = ImpactSummary(
        downstream_direct=direct,
        downstream_transitive=transitive,
        doc_coverage=doc_coverage,
        stale_count=stale_count,
    )

    return WhyResult(
        node=node,
        upstream=upstream,
        downstream=downstream,
        impact=impact,
    )


def _render_tree(
    tree_nodes: tuple[TreeNode, ...],
    parent: Tree,
) -> None:
    """Recursively add TreeNode entries to a Rich Tree."""
    for tnode in tree_nodes:
        label = f"[bold]{tnode.ref_id}[/] ({tnode.kind}) [dim]--[{tnode.edge_kind}]--[/]"
        if tnode.summary:
            label += f" {tnode.summary}"
        child = parent.add(label)
        _render_tree(tnode.children, child)


def render_why(result: WhyResult, console: Console) -> None:
    """Render a WhyResult using Rich panels and trees.

    Parameters
    ----------
    result:
        The impact analysis result.
    console:
        Rich Console instance for output.
    """
    from rich.panel import Panel
    from rich.tree import Tree

    # Header panel
    header = f"[bold]{result.node.ref_id}[/] ({result.node.kind})\n{result.node.summary}"
    console.print(Panel(header, title="Impact Analysis", border_style="blue"))

    # Upstream tree
    if result.upstream:
        up_tree = Tree("[bold cyan]Upstream (dependencies)[/]")
        _render_tree(result.upstream, up_tree)
        console.print(up_tree)
    else:
        console.print("[dim]No upstream dependencies.[/]")

    console.print()

    # Downstream tree
    if result.downstream:
        down_tree = Tree("[bold green]Downstream (dependents)[/]")
        _render_tree(result.downstream, down_tree)
        console.print(down_tree)
    else:
        console.print("[dim]No downstream dependents.[/]")

    console.print()

    # Impact summary panel
    impact_lines = [
        f"Direct dependents:     {result.impact.downstream_direct}",
        f"Transitive dependents: {result.impact.downstream_transitive}",
        f"Doc coverage:          {result.impact.doc_coverage:.0f}%",
        f"Stale docs:            {result.impact.stale_count}",
    ]
    console.print(
        Panel(
            "\n".join(impact_lines),
            title="Impact Summary",
            border_style="yellow",
        )
    )


def _tree_node_to_dict(tnode: TreeNode) -> dict[str, object]:
    """Convert a TreeNode to a JSON-compatible dict."""
    return {
        "ref_id": tnode.ref_id,
        "kind": tnode.kind,
        "summary": tnode.summary,
        "edge_kind": tnode.edge_kind,
        "children": [_tree_node_to_dict(child) for child in tnode.children],
    }


def result_to_dict(result: WhyResult) -> dict[str, object]:
    """Serialize a WhyResult to a JSON-compatible dict.

    Parameters
    ----------
    result:
        The impact analysis result.

    Returns
    -------
    dict
        JSON-serializable dictionary.
    """
    return {
        "node": {
            "ref_id": result.node.ref_id,
            "kind": result.node.kind,
            "summary": result.node.summary,
        },
        "upstream": [_tree_node_to_dict(t) for t in result.upstream],
        "downstream": [_tree_node_to_dict(t) for t in result.downstream],
        "impact": {
            "downstream_direct": result.impact.downstream_direct,
            "downstream_transitive": result.impact.downstream_transitive,
            "doc_coverage": result.impact.doc_coverage,
            "stale_count": result.impact.stale_count,
        },
    }
