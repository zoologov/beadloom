"""An index written by hand with a few nodes, their bound tests and one unplaced test file.

Moved out of ``test_ctx_and_debt_report_read_the_test_binding.py`` when BDL-074
``beadloom-2mj3.7`` split it by node: the placement count, the context bundle and
the debt report each read the same small index, and ``ctx``'s markdown and the
binding state the same sentence about it, so what they share lives here rather
than in any one of them. Nothing here reads this repository's index.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.context_oracle.test_binding import PLACEMENT_MIRROR, PLACEMENT_UNPLACED
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: What ``describe_unplaced`` says of 2 unplaced files among 4, and ``ctx`` prints.
UNPLACED_SENTENCE = (
    "2 of 4 test file(s) are unplaced (not under tests/integration/ or tests/unit/) "
    "and bind to no node"
)


def summary_of_tests(files: list[str]) -> dict[str, object]:
    """The four-key ``tests`` dict a node carries for *files*, two tests each."""
    return {
        "framework": "pytest",
        "test_files": files,
        "test_count": 2 * len(files),
        "coverage_estimate": "medium" if files else "low",
    }


def open_index(path: Path) -> sqlite3.Connection:
    """A new index at *path* with the schema and a recorded reindex time."""
    connection = open_db(path)
    create_schema(connection)
    connection.execute(
        "INSERT INTO meta (key, value) VALUES ('last_reindex_at', '2026-09-27T00:00:00')"
    )
    return connection


def add_node(
    conn: sqlite3.Connection,
    ref_id: str,
    *,
    source: str | None,
    tests: dict[str, object] | None,
) -> None:
    """Insert a feature node, with a ``tests`` entry in its extra when *tests* is given."""
    extra = {"tests": tests} if tests is not None else {}
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, "feature", ref_id.title(), source, json.dumps(extra)),
    )


def add_test_file(conn: sqlite3.Connection, path: str, placement: str, ref_id: str | None) -> None:
    """Record one test file of two tests with its *placement* and bound node."""
    conn.execute(
        "INSERT INTO test_files (path, kind, ref_id, placement, test_count, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (path, None, ref_id, placement, 2, "h"),
    )


def write_ledger(conn: sqlite3.Connection, *, unplaced: bool) -> None:
    """Two nodes the binding covers, one bound test, one node with none."""
    add_node(
        conn,
        "ledger",
        source="src/ledger/",
        tests=summary_of_tests(["tests/unit/ledger/test_a.py"]),
    )
    add_node(conn, "posting", source="src/ledger/posting.py", tests=summary_of_tests([]))
    add_node(conn, "notes", source=None, tests=None)
    add_test_file(conn, "tests/unit/ledger/test_a.py", PLACEMENT_MIRROR, "ledger")
    if unplaced:
        add_test_file(conn, "tests/test_flat.py", PLACEMENT_UNPLACED, None)
    conn.commit()
