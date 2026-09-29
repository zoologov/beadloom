"""The debt report's untested count reads the test binding, and says when it cannot answer yet.

BDL-074 C2, `beadloom-3z94`. A node the binding covers with no bound test file is
untested, and while any test file is unplaced the count is withheld and the report
says why, because such a node may still be tested by an unplaced file.

Split by node by BDL-074 ``beadloom-2mj3.7``: the ``ctx`` half, the placement count
and the sentence both readers print are tested beside their own code (the context
builder, ``ctx``'s markdown, the repository, the binding). Every database here is
written by hand into ``tmp_path``; nothing reads this repository's index.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report import (
    _count_untested,
    collect_debt_data,
    compute_debt_score,
    format_debt_json,
    format_debt_report,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from tests.support.bound_tests_ledger import add_node, open_index, summary_of_tests, write_ledger

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The report is rendered by Rich for a terminal, which colours numbers.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_index(tmp_path / "index.db")


class TestTheUntestedCount:
    def test_a_covered_node_with_no_bound_test_is_untested(self, conn: sqlite3.Connection) -> None:
        write_ledger(conn, unplaced=False)
        count, refs, population = _count_untested(conn)
        assert (count, refs) == (1, ["posting"])
        assert population == (
            "counted over 2 node(s) the test binding covers, all 1 test file(s) placed"
        )

    def test_withheld_while_any_test_file_is_unplaced(self, conn: sqlite3.Connection) -> None:
        write_ledger(conn, unplaced=True)
        count, refs, population = _count_untested(conn)
        assert (count, refs) == (0, [])
        assert population.startswith("not counted: 1 of 2 test file(s) are unplaced")
        assert population.endswith(", so a node with no bound test may still be tested")

    def test_a_project_with_no_test_file_has_every_covered_node_untested(
        self, conn: sqlite3.Connection
    ) -> None:
        add_node(conn, "ledger", source="src/ledger/", tests=summary_of_tests([]))
        add_node(conn, "posting", source="src/ledger/posting.py", tests=summary_of_tests([]))
        conn.commit()
        count, refs, population = _count_untested(conn)
        assert (count, sorted(refs)) == (2, ["ledger", "posting"])
        assert population == (
            "counted over 2 node(s) the test binding covers, all 0 test file(s) placed"
        )

    def test_an_index_without_the_binding_counts_nothing(self, conn: sqlite3.Connection) -> None:
        add_node(conn, "notes", source=None, tests=None)
        conn.commit()
        assert _count_untested(conn) == (
            0,
            [],
            "counted over 0 node(s) the test binding covers, all 0 test file(s) placed",
        )


class TestThePopulationReachesEveryRendering:
    def test_collected_scored_and_rendered(self, conn: sqlite3.Connection, tmp_path: Path) -> None:
        write_ledger(conn, unplaced=True)
        data = collect_debt_data(conn, tmp_path)
        assert data.untested_count == 0
        assert data.test_population.startswith("not counted:")
        report = compute_debt_score(data)
        assert report.test_population == data.test_population
        assert format_debt_json(report)["test_population"] == data.test_population
        rendered = _ANSI.sub("", format_debt_report(report))
        assert "not counted: 1 of 2 test file(s)" in rendered


def test_a_category_filtered_report_keeps_its_populations(tmp_path: Path) -> None:
    """``status --category`` rebuilds the report; the population must survive that."""
    from click.testing import CliRunner

    project = tmp_path / "project"
    (project / ".beadloom").mkdir(parents=True)
    connection = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(connection)
    write_ledger(connection, unplaced=True)
    connection.close()

    result = CliRunner().invoke(
        main, ["status", "--debt-report", "--category", "tests", "--project", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "not counted: 1 of 2 test file(s)" in _ANSI.sub("", result.output)
