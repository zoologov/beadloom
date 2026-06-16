"""Centralized read queries over the graph-index SQLite tables.

# beadloom:domain=infrastructure
# beadloom:component=repository

One responsibility: **named, typed reads of the graph index** (the
``nodes`` / ``edges`` / ``docs`` / ``sync_state`` / ``code_symbols`` tables).
Before this seam, the same row queries — most notably
``SELECT ref_id, kind, summary FROM nodes`` (~16 copies) — were inlined across
services, domains, and the TUI. Centralizing them here removes the duplication
and gives every caller the same typed result objects (:class:`NodeRow`,
:class:`EdgeRow`, :class:`SymbolRow`) instead of bare ``sqlite3.Row`` tuples.

These are pure reads: each function takes an open connection and returns plain
dataclasses, so the module stays in the lowest (infrastructure) layer and is
consumed downward (domains / application / services). The TUI reaches it through
the :mod:`beadloom.application.graph_reads` facade, never directly — the
``tui-no-direct-infra`` boundary forbids a presentation->infrastructure import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


@dataclass(frozen=True)
class NodeRow:
    """A graph node row (``ref_id``, ``kind``, ``summary``, optional ``source``)."""

    ref_id: str
    kind: str
    summary: str
    source: str | None = None


@dataclass(frozen=True)
class EdgeRow:
    """A graph edge row (``src_ref_id`` -> ``dst_ref_id`` with ``kind``)."""

    src_ref_id: str
    dst_ref_id: str
    kind: str


@dataclass(frozen=True)
class SymbolRow:
    """A code-symbol row (``symbol_name``, ``kind``, ``line_start``)."""

    symbol_name: str
    kind: str
    line_start: int


# --- Node reads -------------------------------------------------------------

_NODE_COLS = "SELECT ref_id, kind, summary FROM nodes"
_NODE_SOURCE_COLS = "SELECT ref_id, kind, summary, source FROM nodes"


def _node(row: sqlite3.Row, *, with_source: bool = False) -> NodeRow:
    """Map a ``nodes`` row to a :class:`NodeRow`."""
    return NodeRow(
        ref_id=str(row["ref_id"]),
        kind=str(row["kind"]),
        summary=str(row["summary"]),
        source=row["source"] if with_source else None,
    )


def get_all_nodes(conn: sqlite3.Connection) -> list[NodeRow]:
    """Return every node ordered by ``(kind, ref_id)``."""
    rows = conn.execute(f"{_NODE_COLS} ORDER BY kind, ref_id").fetchall()
    return [_node(r) for r in rows]


def get_node(conn: sqlite3.Connection, ref_id: str) -> NodeRow | None:
    """Return the node with *ref_id*, or ``None`` if absent."""
    row = conn.execute(f"{_NODE_COLS} WHERE ref_id = ?", (ref_id,)).fetchone()
    return None if row is None else _node(row)


def get_node_with_source(conn: sqlite3.Connection, ref_id: str) -> NodeRow | None:
    """Return the node with *ref_id* including its ``source`` path, or ``None``."""
    row = conn.execute(f"{_NODE_SOURCE_COLS} WHERE ref_id = ?", (ref_id,)).fetchone()
    return None if row is None else _node(row, with_source=True)


def get_nodes_by_kind(conn: sqlite3.Connection, kind: str) -> list[NodeRow]:
    """Return every node of *kind* ordered by ``ref_id``."""
    rows = conn.execute(
        f"{_NODE_COLS} WHERE kind = ? ORDER BY ref_id", (kind,)
    ).fetchall()
    return [_node(r) for r in rows]


def get_source_paths(conn: sqlite3.Connection) -> list[str]:
    """Return all non-empty node ``source`` paths."""
    rows = conn.execute(
        "SELECT source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    return [str(r["source"]) for r in rows]


def get_node_sources(conn: sqlite3.Connection) -> dict[str, str]:
    """Return ``{ref_id: source}`` for every node with a non-blank ``source``."""
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL"
    ).fetchall()
    out: dict[str, str] = {}
    for row in rows:
        src = str(row["source"])
        if src.strip():
            out[str(row["ref_id"])] = src
    return out


# --- Edge reads -------------------------------------------------------------


def get_all_edges(conn: sqlite3.Connection) -> list[EdgeRow]:
    """Return every edge ordered by ``src_ref_id``."""
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind FROM edges ORDER BY src_ref_id"
    ).fetchall()
    return [
        EdgeRow(str(r["src_ref_id"]), str(r["dst_ref_id"]), str(r["kind"]))
        for r in rows
    ]


def get_part_of_children(conn: sqlite3.Connection, ref_id: str) -> list[NodeRow]:
    """Return the child nodes of *ref_id* via ``part_of`` edges, ordered by ``ref_id``."""
    rows = conn.execute(
        "SELECT n.ref_id, n.kind, n.summary "
        "FROM edges e JOIN nodes n ON e.src_ref_id = n.ref_id "
        "WHERE e.dst_ref_id = ? AND e.kind = 'part_of' "
        "ORDER BY n.ref_id",
        (ref_id,),
    ).fetchall()
    return [_node(r) for r in rows]


def get_outgoing_edges(conn: sqlite3.Connection, ref_id: str) -> list[EdgeRow]:
    """Return edges leaving *ref_id* ordered by ``(kind, dst_ref_id)``."""
    rows = conn.execute(
        "SELECT dst_ref_id, kind FROM edges WHERE src_ref_id = ? "
        "ORDER BY kind, dst_ref_id",
        (ref_id,),
    ).fetchall()
    return [EdgeRow(ref_id, str(r["dst_ref_id"]), str(r["kind"])) for r in rows]


def get_incoming_edges(conn: sqlite3.Connection, ref_id: str) -> list[EdgeRow]:
    """Return edges entering *ref_id* ordered by ``(kind, src_ref_id)``."""
    rows = conn.execute(
        "SELECT src_ref_id, kind FROM edges WHERE dst_ref_id = ? "
        "ORDER BY kind, src_ref_id",
        (ref_id,),
    ).fetchall()
    return [EdgeRow(str(r["src_ref_id"]), ref_id, str(r["kind"])) for r in rows]


def count_edges_touching(conn: sqlite3.Connection, ref_id: str) -> int:
    """Return the number of edges with *ref_id* as either endpoint."""
    row = conn.execute(
        "SELECT count(*) FROM edges WHERE src_ref_id = ? OR dst_ref_id = ?",
        (ref_id, ref_id),
    ).fetchone()
    return int(row[0])


# --- Doc reads --------------------------------------------------------------


def get_doc_ref_ids(conn: sqlite3.Connection) -> set[str]:
    """Return the set of ``ref_id``s that have at least one associated doc."""
    rows = conn.execute(
        "SELECT DISTINCT ref_id FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()
    return {str(r["ref_id"]) for r in rows}


def count_docs(conn: sqlite3.Connection) -> int:
    """Return the total number of indexed docs."""
    row = conn.execute("SELECT count(*) FROM docs").fetchone()
    return int(row[0])


def count_docs_for_ref(conn: sqlite3.Connection, ref_id: str) -> int:
    """Return the number of docs associated with *ref_id*."""
    row = conn.execute(
        "SELECT count(*) FROM docs WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    return int(row[0])


def get_docs_for_ref(conn: sqlite3.Connection, ref_id: str) -> list[tuple[str, str]]:
    """Return ``(path, kind)`` pairs for docs associated with *ref_id*, by path."""
    rows = conn.execute(
        "SELECT path, kind FROM docs WHERE ref_id = ? ORDER BY path", (ref_id,)
    ).fetchall()
    return [(str(r["path"]), str(r["kind"])) for r in rows]


# --- Sync-state reads -------------------------------------------------------


def get_stale_pairs_for_ref(
    conn: sqlite3.Connection, ref_id: str
) -> list[tuple[str, str]]:
    """Return ``(doc_path, code_path)`` pairs marked ``stale`` for *ref_id*."""
    rows = conn.execute(
        "SELECT doc_path, code_path FROM sync_state "
        "WHERE ref_id = ? AND status = 'stale'",
        (ref_id,),
    ).fetchall()
    return [(str(r["doc_path"]), str(r["code_path"])) for r in rows]


# --- Code-symbol reads ------------------------------------------------------


def get_symbols_for_source(
    conn: sqlite3.Connection, source: str
) -> list[SymbolRow]:
    """Return symbols whose ``file_path`` matches a node *source* prefix.

    A directory source (``src/dom/``) matches every file beneath it via a
    ``LIKE`` prefix; a file source (``src/dom/feat.py``) matches exactly.
    """
    pattern = source + "%" if source.endswith("/") else source
    rows = conn.execute(
        "SELECT symbol_name, kind, line_start FROM code_symbols "
        "WHERE file_path LIKE ? ORDER BY file_path, line_start",
        (pattern,),
    ).fetchall()
    return [
        SymbolRow(str(r["symbol_name"]), str(r["kind"]), int(r["line_start"]))
        for r in rows
    ]


# --- Search fallback --------------------------------------------------------


def search_nodes_like(
    conn: sqlite3.Connection, query: str, *, limit: int
) -> list[NodeRow]:
    """Return nodes whose ``ref_id`` or ``summary`` matches *query* (SQL LIKE).

    The non-FTS5 fallback used by search when the FTS5 index is unavailable.
    """
    like_pattern = f"%{query}%"
    rows = conn.execute(
        f"{_NODE_COLS} WHERE ref_id LIKE ? OR summary LIKE ? "
        "ORDER BY ref_id LIMIT ?",
        (like_pattern, like_pattern, limit),
    ).fetchall()
    return [_node(r) for r in rows]
