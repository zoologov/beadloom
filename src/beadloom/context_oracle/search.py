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
    """Populate the ``search_index`` FTS5 table from nodes + chunks.

    Clears existing data and rebuilds.  Returns row count.
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

    conn.commit()
    return count


def has_fts5(conn: sqlite3.Connection) -> bool:
    """Check if the FTS5 ``search_index`` exists and is populated."""
    try:
        row = conn.execute("SELECT count(*) FROM search_index").fetchone()
        return bool(row[0] > 0)
    except Exception:  # table may not exist
        return False
