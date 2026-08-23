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


# --- Node file ownership ----------------------------------------------------
#
# A node's ``source`` is a path PREFIX, and graphs nest: ``src/pkg/`` (a domain)
# holds ``src/pkg/feature/`` (a feature) holds ``src/pkg/feature/impl.py``.
# Attributing by raw prefix counts a child's files against its parent too, so
# carving a subpackage into its own node never relieves the parent — the exact
# remedy a size limit exists to prompt (BDL-UX #144). The rule below is the
# single answer every counter, sizer and linker must share:
#
#   **a file belongs to exactly one node — the most specific one whose source
#   covers it.**


_FACADE_FILENAME = "__init__.py"


def covering_prefix(source: str) -> str:
    """The path prefix a node *source* covers, normalised to end with ``/``.

    A directory source covers everything beneath it. A package façade
    (``pkg/__init__.py``) covers its PACKAGE: the façade only re-exports, so
    treating it as a lone file reports an empty node for a package full of code
    (BDL-UX #157). Any other file source covers only itself, which
    :func:`source_covers` handles separately.

    Public since BDL-061.50: ownership is the rule by which the linter now
    attributes an imported-FROM file to a node, so the two must not each keep
    their own copy of it.
    """
    if source.endswith("/"):
        return source
    if source.endswith(f"/{_FACADE_FILENAME}"):
        return source[: -len(_FACADE_FILENAME)]
    return source


def source_covers(source: str, file_path: str) -> bool:
    """Whether a node *source* covers *file_path* at all (ignoring specificity)."""
    prefix = covering_prefix(source)
    if prefix.endswith("/"):
        return file_path.startswith(prefix)
    return file_path == source


def get_owning_ref_id(
    conn: sqlite3.Connection, file_path: str
) -> str | None:
    """Return the ref_id of the node that OWNS *file_path*, or ``None``.

    Ownership is most-specific-wins: among the nodes whose source covers the
    file, the one with the longest covering prefix. Ties cannot occur — two
    nodes with the same source would be the same scope.
    """
    rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    best: tuple[int, str] | None = None
    for row in rows:
        source = str(row["source"])
        if not source_covers(source, file_path):
            continue
        specificity = len(covering_prefix(source))
        if best is None or specificity > best[0]:
            best = (specificity, str(row["ref_id"]))
    return best[1] if best is not None else None


def owns_file(conn: sqlite3.Connection, ref_id: str, file_path: str) -> bool:
    """Whether *ref_id* is the node that owns *file_path* (most specific wins)."""
    return get_owning_ref_id(conn, file_path) == ref_id


def _owned_file_clause(
    conn: sqlite3.Connection, source: str
) -> tuple[str, tuple[str, ...]]:
    """SQL fragment + params selecting the files a node with *source* owns.

    Built as "under my prefix, and not under any strictly-more-specific node's
    prefix" so the exclusion happens in SQL rather than by post-filtering every
    symbol row.
    """
    prefix = covering_prefix(source)
    if prefix.endswith("/"):
        clause = "file_path LIKE ?"
        params: list[str] = [f"{prefix}%"]
    else:
        clause = "file_path = ?"
        params = [source]

    rows = conn.execute(
        "SELECT source FROM nodes WHERE source IS NOT NULL AND source != ''"
    ).fetchall()
    for row in rows:
        other = str(row["source"])
        other_prefix = covering_prefix(other)
        if other_prefix == prefix:
            continue
        # Strictly more specific: covered by me, and longer than my prefix.
        if not other_prefix.startswith(prefix):
            continue
        if other_prefix.endswith("/"):
            clause += " AND file_path NOT LIKE ?"
            params.append(f"{other_prefix}%")
        else:
            clause += " AND file_path != ?"
            params.append(other)
    return clause, tuple(params)


def count_symbols_owned_by_node(conn: sqlite3.Connection, ref_id: str) -> int:
    """Count the symbols in the files *ref_id* owns (nested nodes excluded).

    This is what a size limit must measure: the code the node itself holds, so
    that splitting a subpackage out genuinely relieves it.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return 0
    clause, params = _owned_file_clause(conn, str(row["source"]))
    count = conn.execute(
        f"SELECT count(*) FROM code_symbols WHERE {clause}",  # noqa: S608
        params,
    ).fetchone()
    return int(count[0])


def count_files_owned_by_node(conn: sqlite3.Connection, ref_id: str) -> int:
    """Count the indexed FILES *ref_id* owns (nested nodes excluded).

    The file-count sibling of :func:`count_symbols_owned_by_node`, over
    ``file_index`` rather than ``code_symbols``.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return 0
    clause, params = _owned_file_clause(conn, str(row["source"]))
    count = conn.execute(
        f"SELECT count(*) FROM file_index WHERE {clause.replace('file_path', 'path')}",  # noqa: S608
        params,
    ).fetchone()
    return int(count[0])


def get_owned_code_files(conn: sqlite3.Connection, ref_id: str) -> list[tuple[str, str]]:
    """Return ``(path, hash)`` for the indexed CODE files *ref_id* owns.

    The same most-specific-source ownership rule as the counters above, so a
    node never claims a nested node's files. Used to pair a node's doc with its
    code when no symbol carries the node's annotation — without it a node that
    declares ``docs:`` could contribute no sync pair at all and still be
    reported as clean (BDL-UX #146).

    Read from ``file_index``, not ``code_symbols``, since BDL-061.50: the #146
    fallback was itself keyed on SYMBOLS, so a module holding no top-level
    ``def``/``class`` — a pure re-export facade — was unreachable by BOTH the
    annotation path and the fallback, and ``sync-check`` reported it as "no
    indexed code" while the index held it (review .7 MAJOR 3). A file with no
    symbol is still a file whose content can change under a doc.
    """
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return []
    clause, params = _owned_file_clause(conn, str(row["source"]))
    rows = conn.execute(
        "SELECT path, hash FROM file_index "  # noqa: S608
        f"WHERE kind = 'code' AND {clause.replace('file_path', 'path')} ORDER BY path",
        params,
    ).fetchall()
    return [(str(r["path"]), str(r["hash"])) for r in rows]


def get_owned_symbols(conn: sqlite3.Connection, ref_id: str) -> list[SymbolRow]:
    """Return the symbols in the files *ref_id* owns (nested nodes excluded)."""
    row = conn.execute(
        "SELECT source FROM nodes WHERE ref_id = ?", (ref_id,)
    ).fetchone()
    if row is None or not row["source"]:
        return []
    clause, params = _owned_file_clause(conn, str(row["source"]))
    rows = conn.execute(
        "SELECT symbol_name, kind, line_start FROM code_symbols "  # noqa: S608
        f"WHERE {clause} ORDER BY file_path, line_start",
        params,
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
