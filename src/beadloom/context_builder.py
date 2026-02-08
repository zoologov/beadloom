"""Context builder: BFS subgraph traversal + context bundle assembly."""

from __future__ import annotations

import json
from collections import deque
from typing import TYPE_CHECKING, Any

from beadloom.db import get_meta

if TYPE_CHECKING:
    import sqlite3

# Edge kinds ordered by traversal priority (lower = higher priority).
_EDGE_PRIORITY: dict[str, int] = {
    "part_of": 1,
    "touches_entity": 2,
    "uses": 3,
    "implements": 3,
    "depends_on": 4,
    "touches_code": 5,
}

# Default parameters.
DEFAULT_DEPTH = 2
DEFAULT_MAX_NODES = 20
DEFAULT_MAX_CHUNKS = 10

# Max Levenshtein suggestions to return.
_MAX_SUGGESTIONS = 5


def _levenshtein(s: str, t: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(s) < len(t):
        return _levenshtein(t, s)
    if len(t) == 0:
        return len(s)

    prev_row = list(range(len(t) + 1))
    for i, c_s in enumerate(s):
        curr_row = [i + 1]
        for j, c_t in enumerate(t):
            cost = 0 if c_s == c_t else 1
            curr_row.append(min(
                curr_row[j] + 1,       # insert
                prev_row[j + 1] + 1,   # delete
                prev_row[j] + cost,    # replace
            ))
        prev_row = curr_row

    return prev_row[-1]


def suggest_ref_id(conn: sqlite3.Connection, ref_id: str) -> list[str]:
    """Suggest existing ref_ids similar to a missing one.

    Uses prefix matching (case-insensitive) as primary strategy,
    supplemented by Levenshtein distance for typo correction.
    Returns up to 5 suggestions sorted by relevance.
    """
    row = conn.execute(
        "SELECT ref_id FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is not None:
        return []

    all_ids = [
        r[0] for r in conn.execute("SELECT ref_id FROM nodes").fetchall()
    ]
    if not all_ids:
        return []

    ref_lower = ref_id.lower()

    # Strategy 1: Prefix matches (case-insensitive).
    prefix_matches = [
        rid for rid in all_ids
        if rid.lower().startswith(ref_lower) or ref_lower.startswith(rid.lower())
    ]

    # Strategy 2: Levenshtein distance within threshold.
    scored = [(rid, _levenshtein(ref_id, rid)) for rid in all_ids]
    scored.sort(key=lambda x: x[1])
    max_dist = max(len(ref_id) // 2, 3)
    lev_matches = [rid for rid, dist in scored if dist <= max_dist]

    # Combine: prefix first, then Levenshtein, deduplicated.
    seen: set[str] = set()
    combined: list[str] = []
    for rid in prefix_matches + lev_matches:
        if rid not in seen:
            seen.add(rid)
            combined.append(rid)

    return combined[:_MAX_SUGGESTIONS]


# beadloom:domain=context-oracle
def bfs_subgraph(
    conn: sqlite3.Connection,
    focus_ref_ids: list[str],
    depth: int = DEFAULT_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """BFS traversal from focus nodes, expanding by edge priority.

    Returns (nodes, edges) where nodes are dicts with ref_id/kind/summary
    and edges are dicts with src/dst/kind.
    """
    visited: set[str] = set()
    collected_nodes: list[dict[str, Any]] = []
    collected_edges: list[dict[str, Any]] = []

    # Seed with focus nodes.
    queue: deque[tuple[str, int]] = deque()
    for rid in focus_ref_ids:
        if rid not in visited and len(visited) < max_nodes:
            visited.add(rid)
            row = conn.execute(
                "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
                (rid,),
            ).fetchone()
            if row is not None:
                collected_nodes.append({
                    "ref_id": row["ref_id"],
                    "kind": row["kind"],
                    "summary": row["summary"],
                })
                queue.append((rid, 0))

    while queue:
        current_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue

        # Gather neighbors from both outgoing and incoming edges.
        neighbors: list[tuple[str, str, str, str]] = []  # (neighbor_id, src, dst, kind)

        # Outgoing edges.
        for erow in conn.execute(
            "SELECT e.src_ref_id, e.dst_ref_id, e.kind "
            "FROM edges e WHERE e.src_ref_id = ?",
            (current_id,),
        ).fetchall():
            neighbors.append((
                erow["dst_ref_id"],
                erow["src_ref_id"],
                erow["dst_ref_id"],
                erow["kind"],
            ))

        # Incoming edges.
        for erow in conn.execute(
            "SELECT e.src_ref_id, e.dst_ref_id, e.kind "
            "FROM edges e WHERE e.dst_ref_id = ?",
            (current_id,),
        ).fetchall():
            neighbors.append((
                erow["src_ref_id"],
                erow["src_ref_id"],
                erow["dst_ref_id"],
                erow["kind"],
            ))

        # Sort by edge priority.
        neighbors.sort(key=lambda x: _EDGE_PRIORITY.get(x[3], 99))

        for neighbor_id, src, dst, ekind in neighbors:
            # Record edge regardless of visit status.
            edge_dict = {"src": src, "dst": dst, "kind": ekind}
            if edge_dict not in collected_edges:
                collected_edges.append(edge_dict)

            if neighbor_id in visited:
                continue
            if len(visited) >= max_nodes:
                break

            visited.add(neighbor_id)
            nrow = conn.execute(
                "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
                (neighbor_id,),
            ).fetchone()
            if nrow is not None:
                collected_nodes.append({
                    "ref_id": nrow["ref_id"],
                    "kind": nrow["kind"],
                    "summary": nrow["summary"],
                })
                queue.append((neighbor_id, current_depth + 1))

    return collected_nodes, collected_edges


def collect_chunks(
    conn: sqlite3.Connection,
    ref_ids: set[str],
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> list[dict[str, str]]:
    """Collect text chunks for nodes in the subgraph, ordered by section priority.

    Returns list of dicts with doc_path, section, heading, content.
    """
    if not ref_ids:
        return []

    placeholders = ",".join("?" for _ in ref_ids)
    rows = conn.execute(
        f"SELECT d.path AS doc_path, c.section, c.heading, c.content "  # noqa: S608
        f"FROM chunks c "
        f"JOIN docs d ON c.doc_id = d.id "
        f"WHERE d.ref_id IN ({placeholders}) "
        "ORDER BY "
        "  CASE c.section "
        "    WHEN 'spec' THEN 1 "
        "    WHEN 'invariants' THEN 2 "
        "    WHEN 'constraints' THEN 3 "
        "    WHEN 'api' THEN 4 "
        "    WHEN 'tests' THEN 5 "
        "    ELSE 6 "
        "  END, "
        "  c.chunk_index "
        f"LIMIT ?",
        (*ref_ids, max_chunks),
    ).fetchall()

    return [
        {
            "doc_path": r["doc_path"],
            "section": r["section"],
            "heading": r["heading"],
            "content": r["content"],
        }
        for r in rows
    ]


def _collect_code_symbols(
    conn: sqlite3.Connection,
    ref_ids: set[str],
) -> list[dict[str, Any]]:
    """Collect code symbols linked to subgraph nodes via annotations."""
    if not ref_ids:
        return []

    all_symbols: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for row in conn.execute("SELECT * FROM code_symbols").fetchall():
        annotations: dict[str, str] = json.loads(row["annotations"])
        for _key, val in annotations.items():
            if val in ref_ids:
                key = (row["file_path"], row["symbol_name"])
                if key not in seen:
                    seen.add(key)
                    all_symbols.append({
                        "file_path": row["file_path"],
                        "symbol_name": row["symbol_name"],
                        "kind": row["kind"],
                        "line_start": row["line_start"],
                        "line_end": row["line_end"],
                    })
                break

    return all_symbols


def _check_sync_status(
    conn: sqlite3.Connection,
    ref_ids: set[str],
) -> list[dict[str, str]]:
    """Check sync_state for stale doc↔code pairs within the subgraph."""
    if not ref_ids:
        return []

    placeholders = ",".join("?" for _ in ref_ids)
    rows = conn.execute(
        f"SELECT doc_path, code_path, status FROM sync_state "  # noqa: S608
        f"WHERE ref_id IN ({placeholders}) AND status = 'stale'",
        tuple(ref_ids),
    ).fetchall()

    return [
        {"doc_path": r["doc_path"], "code_path": r["code_path"]}
        for r in rows
    ]


def build_context(
    conn: sqlite3.Connection,
    ref_ids: list[str],
    *,
    depth: int = DEFAULT_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> dict[str, Any]:
    """Build a full context bundle for the given focus ref_ids.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    ref_ids:
        One or more focus ref_ids.
    depth:
        BFS traversal depth (default 2).
    max_nodes:
        Maximum nodes in subgraph (default 20).
    max_chunks:
        Maximum text chunks in bundle (default 10).

    Returns
    -------
    dict
        Context bundle in the format specified by RFC section 4.5.

    Raises
    ------
    LookupError
        If any focus ref_id is not found (with Levenshtein suggestions).
    """
    # Step 1: Validate focus nodes exist.
    for rid in ref_ids:
        row = conn.execute(
            "SELECT ref_id FROM nodes WHERE ref_id = ?", (rid,)
        ).fetchone()
        if row is None:
            suggestions = suggest_ref_id(conn, rid)
            msg = f'"{rid}" not found.'
            if suggestions:
                msg += f" Did you mean: {', '.join(suggestions)}?"
            raise LookupError(msg)

    # Step 2: BFS subgraph expansion.
    nodes, edges = bfs_subgraph(conn, ref_ids, depth=depth, max_nodes=max_nodes)
    subgraph_ref_ids = {n["ref_id"] for n in nodes}

    # Step 3: Collect chunks.
    text_chunks = collect_chunks(conn, subgraph_ref_ids, max_chunks=max_chunks)

    # Step 4: Collect code symbols.
    code_symbols = _collect_code_symbols(conn, subgraph_ref_ids)

    # Step 5: Build focus info (first ref_id).
    focus_node = conn.execute(
        "SELECT ref_id, kind, summary FROM nodes WHERE ref_id = ?",
        (ref_ids[0],),
    ).fetchone()

    # Step 6: Check sync status.
    stale_docs = _check_sync_status(conn, subgraph_ref_ids)

    # Step 7: Check stale index warning.
    last_reindex = get_meta(conn, "last_reindex_at")
    warning: str | None = None
    # Warning is set externally when file mtimes are newer than last_reindex_at.
    # This module only checks meta; CLI layer handles mtime comparison.
    _ = last_reindex  # Used by CLI layer for mtime comparison.

    return {
        "version": 1,
        "focus": {
            "ref_id": focus_node["ref_id"],
            "kind": focus_node["kind"],
            "summary": focus_node["summary"],
        },
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
        "text_chunks": text_chunks,
        "code_symbols": code_symbols,
        "sync_status": {
            "stale_docs": stale_docs,
            "last_reindex": last_reindex,
        },
        "warning": warning,
    }
