"""Architecture snapshot storage: save, list, and compare graph states."""

# beadloom:domain=graph

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


@dataclass(frozen=True)
class SnapshotInfo:
    """Metadata for a saved architecture snapshot."""

    id: int
    label: str | None
    created_at: str
    node_count: int
    edge_count: int
    symbols_count: int


@dataclass(frozen=True)
class SnapshotDiff:
    """Diff result between two architecture snapshots."""

    old_id: int
    new_id: int
    added_nodes: list[dict[str, str]] = field(default_factory=list)
    removed_nodes: list[dict[str, str]] = field(default_factory=list)
    changed_nodes: list[dict[str, str]] = field(default_factory=list)
    added_edges: list[dict[str, str]] = field(default_factory=list)
    removed_edges: list[dict[str, str]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Return True if any differences exist between the two snapshots."""
        return bool(
            self.added_nodes
            or self.removed_nodes
            or self.changed_nodes
            or self.added_edges
            or self.removed_edges
        )


def save_snapshot(conn: sqlite3.Connection, label: str | None = None) -> int:
    """Save current graph state as a snapshot.

    Queries the ``nodes``, ``edges``, and ``code_symbols`` tables,
    serializes node/edge data to JSON, and stores it in
    ``graph_snapshots``.

    Returns:
        The snapshot_id of the newly created snapshot.
    """
    # Serialize nodes
    node_rows = conn.execute(
        "SELECT ref_id, kind, summary, source, extra FROM nodes ORDER BY ref_id"
    ).fetchall()
    nodes_data = [
        {
            "ref_id": row["ref_id"],
            "kind": row["kind"],
            "summary": row["summary"],
            "source": row["source"],
            "extra": row["extra"],
        }
        for row in node_rows
    ]

    # Serialize edges
    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, extra FROM edges "
        "ORDER BY src_ref_id, dst_ref_id, kind"
    ).fetchall()
    edges_data = [
        {
            "src_ref_id": row["src_ref_id"],
            "dst_ref_id": row["dst_ref_id"],
            "kind": row["kind"],
            "extra": row["extra"],
        }
        for row in edge_rows
    ]

    # Count symbols
    symbols_count: int = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]

    nodes_json = json.dumps(nodes_data, ensure_ascii=False)
    edges_json = json.dumps(edges_data, ensure_ascii=False)

    cursor = conn.execute(
        "INSERT INTO graph_snapshots (label, nodes_json, edges_json, symbols_count) "
        "VALUES (?, ?, ?, ?)",
        (label, nodes_json, edges_json, symbols_count),
    )
    conn.commit()

    return cursor.lastrowid  # type: ignore[return-value]


def list_snapshots(conn: sqlite3.Connection) -> list[SnapshotInfo]:
    """List all saved snapshots, newest first.

    Returns:
        A list of :class:`SnapshotInfo` objects ordered by ``created_at`` descending.
    """
    rows = conn.execute(
        "SELECT id, label, created_at, nodes_json, edges_json, symbols_count "
        "FROM graph_snapshots ORDER BY created_at DESC, id DESC"
    ).fetchall()

    result: list[SnapshotInfo] = []
    for row in rows:
        nodes = json.loads(row["nodes_json"])
        edges = json.loads(row["edges_json"])
        result.append(
            SnapshotInfo(
                id=row["id"],
                label=row["label"],
                created_at=row["created_at"],
                node_count=len(nodes),
                edge_count=len(edges),
                symbols_count=row["symbols_count"],
            )
        )
    return result


def _load_snapshot_data(
    conn: sqlite3.Connection, snapshot_id: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Load and deserialize a snapshot's nodes and edges.

    Raises:
        ValueError: If the snapshot_id is not found.
    """
    row = conn.execute(
        "SELECT nodes_json, edges_json FROM graph_snapshots WHERE id = ?",
        (snapshot_id,),
    ).fetchone()
    if row is None:
        msg = f"Snapshot {snapshot_id} not found"
        raise ValueError(msg)
    nodes: list[dict[str, str]] = json.loads(row["nodes_json"])
    edges: list[dict[str, str]] = json.loads(row["edges_json"])
    return nodes, edges


def compare_snapshots(conn: sqlite3.Connection, old_id: int, new_id: int) -> SnapshotDiff:
    """Compare two snapshots and return the differences.

    Computes added, removed, and changed nodes, plus added and removed edges.

    Args:
        conn: Database connection.
        old_id: The baseline snapshot ID.
        new_id: The target snapshot ID.

    Returns:
        A :class:`SnapshotDiff` with all detected differences.

    Raises:
        ValueError: If either snapshot ID is not found.
    """
    old_nodes, old_edges = _load_snapshot_data(conn, old_id)
    new_nodes, new_edges = _load_snapshot_data(conn, new_id)

    # Build lookup dicts by ref_id
    old_nodes_map: dict[str, dict[str, str]] = {n["ref_id"]: n for n in old_nodes}
    new_nodes_map: dict[str, dict[str, str]] = {n["ref_id"]: n for n in new_nodes}

    added_nodes: list[dict[str, str]] = []
    removed_nodes: list[dict[str, str]] = []
    changed_nodes: list[dict[str, str]] = []

    # Detect added and changed nodes
    for ref_id, new_node in sorted(new_nodes_map.items()):
        if ref_id not in old_nodes_map:
            added_nodes.append(new_node)
        else:
            old_node = old_nodes_map[ref_id]
            if old_node.get("kind") != new_node.get("kind") or old_node.get(
                "summary"
            ) != new_node.get("summary"):
                changed_nodes.append(
                    {
                        "ref_id": ref_id,
                        "kind": new_node.get("kind", ""),
                        "old_summary": old_node.get("summary", ""),
                        "new_summary": new_node.get("summary", ""),
                    }
                )

    # Detect removed nodes
    for ref_id, old_node in sorted(old_nodes_map.items()):
        if ref_id not in new_nodes_map:
            removed_nodes.append(old_node)

    # Compare edges using (src, dst, kind) as identity
    def _edge_key(e: dict[str, str]) -> tuple[str, str, str]:
        return (e["src_ref_id"], e["dst_ref_id"], e["kind"])

    old_edge_set = {_edge_key(e) for e in old_edges}
    new_edge_set = {_edge_key(e) for e in new_edges}

    old_edge_map = {_edge_key(e): e for e in old_edges}
    new_edge_map = {_edge_key(e): e for e in new_edges}

    added_edges = [new_edge_map[k] for k in sorted(new_edge_set - old_edge_set)]
    removed_edges = [old_edge_map[k] for k in sorted(old_edge_set - new_edge_set)]

    return SnapshotDiff(
        old_id=old_id,
        new_id=new_id,
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        changed_nodes=changed_nodes,
        added_edges=added_edges,
        removed_edges=removed_edges,
    )
