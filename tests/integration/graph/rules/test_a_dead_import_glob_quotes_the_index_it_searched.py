"""A ``forbid_import`` glob that matches nothing says how much of the index it searched.

``evaluate_import_boundary_rules`` reads every import row of the index once and hands each
rule two population sizes: the distinct source files and the distinct import paths. The
dead-glob finding quotes them, so "matches 0 of 2" can be told from "matches 0 of 0".

A ``to`` glob that CAN match an import path and matches none of them is not dead (BDL-083
D2): the statement that it is live quotes the same count, at ``info``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import ImportBoundaryRule, evaluate_import_boundary_rules
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator

#: Two distinct files and three distinct import paths; one path is imported twice.
ROWS = [
    ("src/app/ui/panel.py", 3, "app.store.rows"),
    ("src/app/ui/panel.py", 4, "app.logic.plan"),
    ("src/app/ui/menu.py", 7, "app.store.rows"),
    ("src/app/ui/menu.py", 8, "app.logic.draft"),
]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    db = open_graph()
    db.executemany(
        "INSERT INTO code_imports (file_path, line_number, import_path, file_hash) "
        "VALUES (?, ?, ?, 'h')",
        ROWS,
    )
    yield db
    db.close()


@pytest.mark.parametrize(
    ("from_glob", "to_glob", "stated"),
    [
        pytest.param(
            "src/app/cli/*", "app/store/*", "matches 0 of 2 indexed source files", id="from"
        ),
        pytest.param(
            "src/app/ui/*", "src/app/nowhere/*", "matches 0 of 3 indexed import paths", id="to"
        ),
    ],
)
def test_the_dead_glob_finding_counts_the_distinct_rows_of_the_index(
    conn: sqlite3.Connection, from_glob: str, to_glob: str, stated: str
) -> None:
    rule = ImportBoundaryRule(
        name="ui-reads-no-store", description="d", from_glob=from_glob, to_glob=to_glob
    )

    (dead,) = evaluate_import_boundary_rules(conn, [rule])

    assert stated in dead.message


def test_a_to_glob_that_can_match_quotes_the_count_in_its_live_statement(
    conn: sqlite3.Connection,
) -> None:
    rule = ImportBoundaryRule(
        name="ui-reads-no-store",
        description="d",
        from_glob="src/app/ui/*",
        to_glob="app/nowhere/*",
    )

    (live,) = evaluate_import_boundary_rules(conn, [rule])

    assert (live.rule_type, live.severity) == ("nothing_to_ban", "info")
    assert "matches 0 of 3 indexed import paths" in live.message
