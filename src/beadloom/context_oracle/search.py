"""Search engine: FTS5 keyword search with optional sqlite-vec semantic search."""

# beadloom:domain=context-oracle

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


def _escape_fts5_query(query: str) -> str:
    """Escape and prepare a query string for FTS5 MATCH.

    Splits into words and double-quotes each token so that special
    characters (``*``, ``-``, ``:``, etc.) are treated as literals.
    """
    words = query.strip().split()
    if not words:
        return ""
    return " ".join(f'"{w}"' for w in words)


def search_fts5(
    conn: sqlite3.Connection,
    query: str,
    *,
    kind: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search using FTS5 full-text search.

    Returns list of dicts with ref_id, kind, summary, snippet, rank.
    """
    safe_query = _escape_fts5_query(query)
    if not safe_query:
        return []

    if kind:
        rows = conn.execute(
            "SELECT ref_id, kind, summary, "
            "snippet(search_index, 3, '<b>', '</b>', '...', 32) AS snippet, "
            "rank "
            "FROM search_index "
            "WHERE search_index MATCH ? AND kind = ? "
            "ORDER BY rank "
            "LIMIT ?",
            (safe_query, kind, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ref_id, kind, summary, "
            "snippet(search_index, 3, '<b>', '</b>', '...', 32) AS snippet, "
            "rank "
            "FROM search_index "
            "WHERE search_index MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (safe_query, limit),
        ).fetchall()

    return [
        {
            "ref_id": r["ref_id"],
            "kind": r["kind"],
            "summary": r["summary"],
            "snippet": r["snippet"],
            "rank": r["rank"],
        }
        for r in rows
    ]


def populate_search_index(conn: sqlite3.Connection) -> int:
    """Populate the ``search_index`` FTS5 table from nodes + unlinked documents.

    Clears existing data and rebuilds.  Returns row count.

    A row per node, plus a row per document bound to no node. The second half is
    what makes the TO-BE space searchable (BDL-061 S5): a planning document
    describes intent rather than one node's code, so it carries no ``ref_id``,
    and a node-only index could never return it however well it was chunked.
    """
    conn.execute("DELETE FROM search_index")

    nodes = conn.execute("SELECT ref_id, kind, summary FROM nodes").fetchall()

    count = 0
    for node in nodes:
        ref_id: str = node["ref_id"]
        kind: str = node["kind"]
        summary: str = node["summary"]

        # Concatenate chunk content linked to this ref_id.
        chunks = conn.execute(
            "SELECT c.content FROM chunks c JOIN docs d ON c.doc_id = d.id WHERE d.ref_id = ?",
            (ref_id,),
        ).fetchall()
        content = "\n".join(c["content"] for c in chunks)

        conn.execute(
            "INSERT INTO search_index (ref_id, kind, summary, content) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, content),
        )
        count += 1

    count += _index_unlinked_documents(conn)
    conn.commit()
    return count


def _index_unlinked_documents(conn: sqlite3.Connection) -> int:
    """One FTS row per document bound to no node, keyed by its path.

    ``ref_id`` holds the document's path — the only identifier such a row has,
    and the one a reader needs to open the file. ``kind`` holds its SPACE, so
    ``search --kind to_be`` narrows to intent without a second index.
    """
    rows = conn.execute(
        "SELECT d.id, d.path, d.space, "
        "       (SELECT group_concat(c.content, char(10)) FROM chunks c "
        "        WHERE c.doc_id = d.id) AS content "
        "FROM docs d WHERE d.ref_id IS NULL ORDER BY d.path"
    ).fetchall()
    for row in rows:
        conn.execute(
            "INSERT INTO search_index (ref_id, kind, summary, content) "
            "VALUES (?, ?, ?, ?)",
            (row["path"], row["space"], row["path"], row["content"] or ""),
        )
    return len(rows)


def has_fts5(conn: sqlite3.Connection) -> bool:
    """Check if the FTS5 ``search_index`` exists and is populated."""
    try:
        row = conn.execute("SELECT count(*) FROM search_index").fetchone()
        return bool(row[0] > 0)
    except Exception:  # table may not exist
        return False
