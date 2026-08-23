# beadloom:domain=doc-sync
# beadloom:feature=sync-check
"""The declared documentation surface, checked against what is on disk.

**Why this module exists.** The gate's promise is "no code reaches ``main``
without current docs", and the cheapest way to satisfy it used to be to DELETE
the document instead of updating it: the ``docs`` table indexes files *found on
disk*, so a deleted doc stopped being indexed, its pairs stopped existing, and
every check reported clean about a surface that had silently shrunk (BDL-UX
#174, measured: ``275 → 269 pair(s) fresh``, gate exit 0).

The fix is to compare against what the graph DECLARES rather than against what
survives on disk. A declaration lives in the committed graph YAML and cannot be
removed by deleting a file — so a declared doc that does not exist is a
FAILURE, not an absence, and it is named rather than counted.

One responsibility: read the declared surface and say which declarations the
tree no longer satisfies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def count_declared_docs(conn: sqlite3.Connection) -> int:
    """How many docs the graph declares (existing or not)."""
    row = conn.execute("SELECT COUNT(*) FROM declared_docs").fetchone()
    return int(row[0]) if row else 0


def find_missing_declared_docs(
    conn: sqlite3.Connection, project_root: Path
) -> list[dict[str, str]]:
    """Declared docs whose file does not exist, in declaration order.

    Each entry carries ``ref_id``, ``doc_path`` (as the graph declared it, so the
    reader can find the declaration) and ``index_path`` (the docs-dir-relative
    key the rest of the sync machinery uses).
    """
    rows = conn.execute(
        "SELECT declared_path, doc_path, ref_id FROM declared_docs "
        "ORDER BY declared_path"
    ).fetchall()
    return [
        {
            "ref_id": str(row["ref_id"]),
            "doc_path": str(row["declared_path"]),
            "index_path": str(row["doc_path"]),
        }
        for row in rows
        if not (project_root / str(row["declared_path"])).is_file()
    ]
