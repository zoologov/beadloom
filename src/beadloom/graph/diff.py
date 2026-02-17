"""Graph delta: compare current graph YAML with state at a git ref."""

# beadloom:domain=graph

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from rich.console import Console


@dataclass(frozen=True)
class NodeChange:
    """A single node change."""

    ref_id: str
    kind: str
    change_type: str  # "added" | "removed" | "changed"
    old_summary: str | None = None  # for "changed"
    new_summary: str | None = None  # for "changed"
    old_source: str | None = None
    new_source: str | None = None
    old_tags: tuple[str, ...] = ()
    new_tags: tuple[str, ...] = ()
    symbols_added: int = 0
    symbols_removed: int = 0


@dataclass(frozen=True)
class EdgeChange:
    """A single edge change."""

    src: str
    dst: str
    kind: str
    change_type: str  # "added" | "removed"


@dataclass(frozen=True)
class GraphDiff:
    """Complete diff result."""

    since_ref: str
    nodes: tuple[NodeChange, ...]
    edges: tuple[EdgeChange, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.nodes or self.edges)


def _validate_git_ref(project_root: Path, ref: str) -> bool:
    """Check if the git ref is valid using ``git rev-parse --verify``."""
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--verify", ref],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _read_yaml_at_ref(project_root: Path, rel_path: str, ref: str) -> str | None:
    """Read a file's content at a given git ref.

    Returns the file content as a string, or ``None`` if the file didn't exist
    at that ref.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{rel_path}"],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_yaml_content(
    content: str,
) -> tuple[dict[str, dict[str, object]], set[tuple[str, str, str]]]:
    """Parse YAML content into nodes dict and edges set.

    Returns:
        A tuple of (nodes_dict, edges_set) where:
        - nodes_dict maps ref_id -> {"kind": ..., "summary": ..., "source": ..., "tags": ...}
        - edges_set contains (src, dst, kind) tuples
    """
    data = yaml.safe_load(content)
    if data is None:
        return {}, set()

    nodes_dict: dict[str, dict[str, object]] = {}
    for node in data.get("nodes") or []:
        ref_id = node.get("ref_id", "")
        if ref_id:
            raw_tags = node.get("tags", [])
            tags = tuple(sorted(raw_tags)) if isinstance(raw_tags, list) else ()
            nodes_dict[ref_id] = {
                "kind": node.get("kind", ""),
                "summary": node.get("summary", ""),
                "source": node.get("source", ""),
                "tags": tags,
            }

    edges_set: set[tuple[str, str, str]] = set()
    for edge in data.get("edges") or []:
        src = edge.get("src", "")
        dst = edge.get("dst", "")
        kind = edge.get("kind", "")
        if src and dst:
            edges_set.add((src, dst, kind))

    return nodes_dict, edges_set


def _list_graph_files_at_ref(project_root: Path, ref: str) -> list[str]:
    """List graph YAML files that existed at the given git ref.

    Uses ``git ls-tree -r --name-only <ref> .beadloom/_graph/`` to get the list.
    Returns relative paths from the project root.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "ls-tree", "-r", "--name-only", ref, ".beadloom/_graph/"],  # noqa: S607
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    files = [
        line.strip()
        for line in result.stdout.strip().split("\n")
        if line.strip() and line.strip().endswith(".yml")
    ]
    return files


def compute_diff(project_root: Path, since: str = "HEAD") -> GraphDiff:
    """Compare current graph YAML with state at a git ref.

    Args:
        project_root: Path to the project root directory.
        since: Git ref to compare against (default: HEAD).

    Returns:
        A :class:`GraphDiff` with all detected changes.

    Raises:
        ValueError: If the git ref is invalid.
    """
    if not _validate_git_ref(project_root, since):
        msg = f"Invalid git ref: '{since}'"
        raise ValueError(msg)

    graph_dir = project_root / ".beadloom" / "_graph"

    # --- Current state: read from disk ---
    current_nodes: dict[str, dict[str, object]] = {}
    current_edges: set[tuple[str, str, str]] = set()

    current_files: set[str] = set()
    if graph_dir.is_dir():
        for yml_path in sorted(graph_dir.glob("*.yml")):
            rel_path = str(yml_path.relative_to(project_root))
            current_files.add(rel_path)
            content = yml_path.read_text(encoding="utf-8")
            nodes, edges = _parse_yaml_content(content)
            current_nodes.update(nodes)
            current_edges.update(edges)

    # --- Previous state: read from git ref ---
    prev_nodes: dict[str, dict[str, object]] = {}
    prev_edges: set[tuple[str, str, str]] = set()

    prev_files = _list_graph_files_at_ref(project_root, since)
    for rel_path in prev_files:
        prev_content = _read_yaml_at_ref(project_root, rel_path, since)
        if prev_content is not None:
            nodes, edges = _parse_yaml_content(prev_content)
            prev_nodes.update(nodes)
            prev_edges.update(edges)

    # --- Compare nodes ---
    node_changes: list[NodeChange] = []

    all_ref_ids = set(current_nodes.keys()) | set(prev_nodes.keys())
    for ref_id in sorted(all_ref_ids):
        in_current = ref_id in current_nodes
        in_prev = ref_id in prev_nodes

        if in_current and not in_prev:
            node_changes.append(
                NodeChange(
                    ref_id=ref_id,
                    kind=current_nodes[ref_id]["kind"],
                    change_type="added",
                )
            )
        elif not in_current and in_prev:
            node_changes.append(
                NodeChange(
                    ref_id=ref_id,
                    kind=prev_nodes[ref_id]["kind"],
                    change_type="removed",
                )
            )
        elif in_current and in_prev:
            curr = current_nodes[ref_id]
            prev = prev_nodes[ref_id]
            curr_source = str(curr.get("source", ""))
            prev_source = str(prev.get("source", ""))
            curr_tags = curr.get("tags", ())
            prev_tags = prev.get("tags", ())
            if not isinstance(curr_tags, tuple):
                curr_tags = ()
            if not isinstance(prev_tags, tuple):
                prev_tags = ()
            if (
                curr["kind"] != prev["kind"]
                or curr["summary"] != prev["summary"]
                or curr_source != prev_source
                or curr_tags != prev_tags
            ):
                node_changes.append(
                    NodeChange(
                        ref_id=ref_id,
                        kind=str(curr["kind"]),
                        change_type="changed",
                        old_summary=str(prev["summary"]) if prev["summary"] else None,
                        new_summary=str(curr["summary"]) if curr["summary"] else None,
                        old_source=prev_source or None,
                        new_source=curr_source or None,
                        old_tags=prev_tags,
                        new_tags=curr_tags,
                    )
                )

    # --- Compare edges ---
    edge_changes: list[EdgeChange] = []

    added_edges = current_edges - prev_edges
    removed_edges = prev_edges - current_edges

    for src, dst, kind in sorted(added_edges):
        edge_changes.append(
            EdgeChange(
                src=src,
                dst=dst,
                kind=kind,
                change_type="added",
            )
        )

    for src, dst, kind in sorted(removed_edges):
        edge_changes.append(
            EdgeChange(
                src=src,
                dst=dst,
                kind=kind,
                change_type="removed",
            )
        )

    return GraphDiff(
        since_ref=since,
        nodes=tuple(node_changes),
        edges=tuple(edge_changes),
    )


def compute_diff_from_snapshot(
    conn: sqlite3.Connection,
    snapshot_id: int,
) -> GraphDiff:
    """Compare a saved snapshot with the current graph state in the database.

    Unlike :func:`compute_diff` which reads YAML on disk vs a git ref, this
    function compares a saved snapshot (from ``graph_snapshots`` table) with
    the current live state in ``nodes`` and ``edges`` tables.

    Args:
        conn: Database connection.
        snapshot_id: The snapshot ID to compare against.

    Returns:
        A :class:`GraphDiff` with all detected changes.

    Raises:
        ValueError: If the snapshot ID is not found.
    """
    from beadloom.graph.snapshot import _load_snapshot_data

    snap_nodes, snap_edges = _load_snapshot_data(conn, snapshot_id)

    # Build snapshot lookup: ref_id -> node dict
    snap_nodes_map: dict[str, dict[str, object]] = {}
    for n in snap_nodes:
        ref_id = n.get("ref_id", "")
        if ref_id:
            extra_raw = n.get("extra")
            extra = json.loads(extra_raw) if extra_raw else {}
            tags = tuple(sorted(extra.get("tags", [])))
            snap_nodes_map[ref_id] = {
                "kind": n.get("kind", ""),
                "summary": n.get("summary", ""),
                "source": n.get("source", ""),
                "tags": tags,
            }

    # Build current state from DB
    current_nodes_map: dict[str, dict[str, object]] = {}
    for row in conn.execute(
        "SELECT ref_id, kind, summary, source, extra FROM nodes ORDER BY ref_id"
    ).fetchall():
        extra = json.loads(row["extra"]) if row["extra"] else {}
        tags = tuple(sorted(extra.get("tags", [])))
        current_nodes_map[row["ref_id"]] = {
            "kind": row["kind"],
            "summary": row["summary"] or "",
            "source": row["source"] or "",
            "tags": tags,
        }

    # Compare nodes
    node_changes: list[NodeChange] = []
    all_ref_ids = set(current_nodes_map.keys()) | set(snap_nodes_map.keys())
    for ref_id in sorted(all_ref_ids):
        in_current = ref_id in current_nodes_map
        in_snap = ref_id in snap_nodes_map

        if in_current and not in_snap:
            node_changes.append(
                NodeChange(
                    ref_id=ref_id,
                    kind=str(current_nodes_map[ref_id]["kind"]),
                    change_type="added",
                )
            )
        elif not in_current and in_snap:
            node_changes.append(
                NodeChange(
                    ref_id=ref_id,
                    kind=str(snap_nodes_map[ref_id]["kind"]),
                    change_type="removed",
                )
            )
        elif in_current and in_snap:
            curr = current_nodes_map[ref_id]
            snap = snap_nodes_map[ref_id]
            curr_source = str(curr.get("source", ""))
            snap_source = str(snap.get("source", ""))
            curr_tags = curr.get("tags", ())
            snap_tags = snap.get("tags", ())
            if not isinstance(curr_tags, tuple):
                curr_tags = ()
            if not isinstance(snap_tags, tuple):
                snap_tags = ()
            if (
                curr["kind"] != snap["kind"]
                or curr["summary"] != snap["summary"]
                or curr_source != snap_source
                or curr_tags != snap_tags
            ):
                node_changes.append(
                    NodeChange(
                        ref_id=ref_id,
                        kind=str(curr["kind"]),
                        change_type="changed",
                        old_summary=str(snap["summary"]) if snap["summary"] else None,
                        new_summary=str(curr["summary"]) if curr["summary"] else None,
                        old_source=snap_source or None,
                        new_source=curr_source or None,
                        old_tags=snap_tags,
                        new_tags=curr_tags,
                    )
                )

    # Compare edges
    snap_edge_set: set[tuple[str, str, str]] = set()
    for e in snap_edges:
        snap_edge_set.add((e["src_ref_id"], e["dst_ref_id"], e["kind"]))

    current_edge_set: set[tuple[str, str, str]] = set()
    for row in conn.execute("SELECT src_ref_id, dst_ref_id, kind FROM edges").fetchall():
        current_edge_set.add((row["src_ref_id"], row["dst_ref_id"], row["kind"]))

    edge_changes: list[EdgeChange] = []
    for src, dst, kind in sorted(current_edge_set - snap_edge_set):
        edge_changes.append(EdgeChange(src=src, dst=dst, kind=kind, change_type="added"))
    for src, dst, kind in sorted(snap_edge_set - current_edge_set):
        edge_changes.append(EdgeChange(src=src, dst=dst, kind=kind, change_type="removed"))

    return GraphDiff(
        since_ref=f"snapshot:{snapshot_id}",
        nodes=tuple(node_changes),
        edges=tuple(edge_changes),
    )


def render_diff(diff: GraphDiff, console: Console) -> None:
    """Render a GraphDiff using Rich console output.

    Displays:
    - Header with ref
    - Nodes section with ``+`` (green), ``~`` (yellow), ``-`` (red) markers
    - Edges section with ``+`` (green), ``-`` (red) markers
    - Summary line with counts
    """
    if not diff.has_changes:
        console.print(f"No graph changes since {diff.since_ref}.")
        return

    console.print(f"[bold]Graph diff (since {diff.since_ref}):[/bold]")
    console.print()

    # --- Nodes section ---
    if diff.nodes:
        console.print("[bold]Nodes:[/bold]")
        for node in diff.nodes:
            if node.change_type == "added":
                console.print(f"  [green]+ {node.ref_id}[/green] ({node.kind})")
            elif node.change_type == "removed":
                console.print(f"  [red]- {node.ref_id}[/red] ({node.kind})")
            elif node.change_type == "changed":
                console.print(f"  [yellow]~ {node.ref_id}[/yellow] ({node.kind})")
                if node.old_summary != node.new_summary:
                    console.print(f"    [dim]{node.old_summary}[/dim]")
                    console.print(f"    [bold]{node.new_summary}[/bold]")
                if node.old_source != node.new_source:
                    console.print(
                        f"    source: {node.old_source or '(none)'}"
                        f" \u2192 {node.new_source or '(none)'}"
                    )
                if node.old_tags != node.new_tags:
                    console.print(f"    tags: {list(node.old_tags)} \u2192 {list(node.new_tags)}")
                if node.symbols_added or node.symbols_removed:
                    console.print(f"    symbols: +{node.symbols_added} -{node.symbols_removed}")
        console.print()

    # --- Edges section ---
    if diff.edges:
        console.print("[bold]Edges:[/bold]")
        for edge in diff.edges:
            if edge.change_type == "added":
                console.print(f"  [green]+ {edge.src} --[{edge.kind}]--> {edge.dst}[/green]")
            elif edge.change_type == "removed":
                console.print(f"  [red]- {edge.src} --[{edge.kind}]--> {edge.dst}[/red]")
        console.print()

    # --- Summary ---
    added_nodes = sum(1 for n in diff.nodes if n.change_type == "added")
    changed_nodes = sum(1 for n in diff.nodes if n.change_type == "changed")
    removed_nodes = sum(1 for n in diff.nodes if n.change_type == "removed")
    added_edges = sum(1 for e in diff.edges if e.change_type == "added")
    removed_edges = sum(1 for e in diff.edges if e.change_type == "removed")

    console.print(
        f"{added_nodes} added, {changed_nodes} changed, {removed_nodes} removed nodes; "
        f"{added_edges} added, {removed_edges} removed edges"
    )


def diff_to_dict(diff: GraphDiff) -> dict[str, object]:
    """Serialize a GraphDiff to a JSON-compatible dict."""
    return {
        "since_ref": diff.since_ref,
        "has_changes": diff.has_changes,
        "nodes": [asdict(n) for n in diff.nodes],
        "edges": [asdict(e) for e in diff.edges],
    }
