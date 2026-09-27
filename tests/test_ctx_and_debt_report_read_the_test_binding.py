"""ctx and the debt report read the test binding, and say when it cannot answer yet.

BDL-074 C2, `beadloom-3z94`. C1 rebuilt ``nodes.extra["tests"]`` from the binding
and recorded every test file's placement in ``test_files``. These tests pin the
two readers that were left:

- ``ctx`` keeps the four-key ``tests`` dict and gains a top-level
  ``test_placements`` count, from which the markdown states how many of the
  repository's test files are unplaced — so "0 tests" on a repository whose tests
  are not laid out reads differently from "0 tests" on a node nobody tested;
- the debt report's untested count reads the binding. A node the binding covers
  with no bound test file is untested, and while any test file is unplaced the
  count is withheld and the report says why, because such a node may still be
  tested by an unplaced file.

Every database here is written by hand into ``tmp_path``; nothing reads this
repository's index.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report import (
    _count_untested,
    collect_debt_data,
    compute_debt_score,
    format_debt_json,
    format_debt_report,
)
from beadloom.context_oracle.builder import build_context
from beadloom.context_oracle.test_binding import (
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_UNPLACED,
    describe_unplaced,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.repository import count_test_files_by_placement
from beadloom.services.cli import _format_markdown, main

if TYPE_CHECKING:
    from pathlib import Path

#: The report is rendered by Rich for a terminal, which colours numbers.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

_FOUR_KEYS = {"framework", "test_files", "test_count", "coverage_estimate"}

_UNPLACED_SENTENCE = (
    "2 of 4 test file(s) are unplaced (not under tests/integration/ or tests/unit/) "
    "and bind to no node"
)


def _tests(files: list[str]) -> dict[str, object]:
    return {
        "framework": "pytest",
        "test_files": files,
        "test_count": 2 * len(files),
        "coverage_estimate": "medium" if files else "low",
    }


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = open_db(tmp_path / "index.db")
    create_schema(connection)
    connection.execute(
        "INSERT INTO meta (key, value) VALUES ('last_reindex_at', '2026-09-27T00:00:00')"
    )
    return connection


def _node(
    conn: sqlite3.Connection,
    ref_id: str,
    *,
    source: str | None,
    tests: dict[str, object] | None,
) -> None:
    extra = {"tests": tests} if tests is not None else {}
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, "feature", ref_id.title(), source, json.dumps(extra)),
    )


def _test_file(conn: sqlite3.Connection, path: str, placement: str, ref_id: str | None) -> None:
    conn.execute(
        "INSERT INTO test_files (path, kind, ref_id, placement, test_count, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (path, None, ref_id, placement, 2, "h"),
    )


def _ledger(conn: sqlite3.Connection, *, unplaced: bool) -> None:
    """Two nodes the binding covers, one bound test, one node with none."""
    _node(conn, "ledger", source="src/ledger/", tests=_tests(["tests/unit/ledger/test_a.py"]))
    _node(conn, "posting", source="src/ledger/posting.py", tests=_tests([]))
    _node(conn, "notes", source=None, tests=None)
    _test_file(conn, "tests/unit/ledger/test_a.py", PLACEMENT_MIRROR, "ledger")
    if unplaced:
        _test_file(conn, "tests/test_flat.py", PLACEMENT_UNPLACED, None)
    conn.commit()


# ---------------------------------------------------------------------------
# The sentence both readers print
# ---------------------------------------------------------------------------


class TestDescribeUnplaced:
    def test_no_test_file_at_all_has_nothing_to_say(self) -> None:
        assert describe_unplaced({}) is None

    def test_every_file_placed_has_nothing_to_say(self) -> None:
        assert describe_unplaced({PLACEMENT_MIRROR: 3, PLACEMENT_OTHER_KIND: 1}) is None

    def test_names_the_unplaced_share_of_every_test_file(self) -> None:
        counts = {PLACEMENT_UNPLACED: 2, PLACEMENT_MIRROR: 1, PLACEMENT_OTHER_KIND: 1}
        assert describe_unplaced(counts) == _UNPLACED_SENTENCE


# ---------------------------------------------------------------------------
# The index read
# ---------------------------------------------------------------------------


class TestCountTestFilesByPlacement:
    def test_counts_each_placement(self, conn: sqlite3.Connection) -> None:
        _ledger(conn, unplaced=True)
        assert count_test_files_by_placement(conn) == {
            PLACEMENT_MIRROR: 1,
            PLACEMENT_UNPLACED: 1,
        }

    def test_an_index_older_than_the_test_tables_holds_no_count(self, tmp_path: Path) -> None:
        old = sqlite3.connect(tmp_path / "old.db")
        old.row_factory = sqlite3.Row
        assert count_test_files_by_placement(old) == {}


# ---------------------------------------------------------------------------
# ctx
# ---------------------------------------------------------------------------


class TestTheContextBundle:
    def test_carries_the_placements_beside_the_four_key_tests(
        self, conn: sqlite3.Connection
    ) -> None:
        _ledger(conn, unplaced=True)
        bundle = build_context(conn, ["ledger"], depth=0, max_nodes=5, max_chunks=5)
        assert set(bundle["tests"]) == _FOUR_KEYS
        assert bundle["tests"]["test_files"] == ["tests/unit/ledger/test_a.py"]
        assert bundle["test_placements"] == {PLACEMENT_MIRROR: 1, PLACEMENT_UNPLACED: 1}


def _bundle(tests: dict[str, object] | None, placements: dict[str, int]) -> dict[str, object]:
    return {
        "version": 2,
        "focus": {"ref_id": "posting", "kind": "feature", "summary": "Posting"},
        "graph": {"nodes": [], "edges": []},
        "text_chunks": [],
        "code_symbols": [],
        "sync_status": {"stale_docs": [], "last_reindex": None},
        "constraints": [],
        "warning": None,
        "tests": tests,
        "test_placements": placements,
    }


_PLACEMENTS = MappingProxyType(
    {PLACEMENT_UNPLACED: 2, PLACEMENT_MIRROR: 1, PLACEMENT_OTHER_KIND: 1}
)


class TestTheContextMarkdown:
    def test_the_tests_line_is_unchanged(self) -> None:
        md = _format_markdown(_bundle(_tests([]), dict(_PLACEMENTS)))
        assert "Tests: pytest, 0 tests in 0 files (low coverage)" in md.splitlines()

    def test_states_the_unplaced_share_under_the_tests_line(self) -> None:
        lines = _format_markdown(_bundle(_tests([]), dict(_PLACEMENTS))).splitlines()
        tests_at = lines.index("Tests: pytest, 0 tests in 0 files (low coverage)")
        assert lines[tests_at + 1] == f"  {_UNPLACED_SENTENCE}, so the count above can be short"

    def test_says_nothing_when_every_file_is_placed(self) -> None:
        md = _format_markdown(_bundle(_tests([]), {PLACEMENT_MIRROR: 4}))
        assert "unplaced" not in md

    def test_says_nothing_for_a_node_the_binding_does_not_cover(self) -> None:
        md = _format_markdown(_bundle(None, dict(_PLACEMENTS)))
        assert "unplaced" not in md
        assert "Tests:" not in md

    def test_a_bundle_without_placements_still_renders(self) -> None:
        bundle = _bundle(_tests([]), {})
        del bundle["test_placements"]
        assert "unplaced" not in _format_markdown(bundle)


# ---------------------------------------------------------------------------
# The debt report
# ---------------------------------------------------------------------------


class TestTheUntestedCount:
    def test_a_covered_node_with_no_bound_test_is_untested(self, conn: sqlite3.Connection) -> None:
        _ledger(conn, unplaced=False)
        count, refs, population = _count_untested(conn)
        assert (count, refs) == (1, ["posting"])
        assert population == (
            "counted over 2 node(s) the test binding covers, all 1 test file(s) placed"
        )

    def test_withheld_while_any_test_file_is_unplaced(self, conn: sqlite3.Connection) -> None:
        _ledger(conn, unplaced=True)
        count, refs, population = _count_untested(conn)
        assert (count, refs) == (0, [])
        assert population.startswith("not counted: 1 of 2 test file(s) are unplaced")
        assert population.endswith(", so a node with no bound test may still be tested")

    def test_a_project_with_no_test_file_has_every_covered_node_untested(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "ledger", source="src/ledger/", tests=_tests([]))
        _node(conn, "posting", source="src/ledger/posting.py", tests=_tests([]))
        conn.commit()
        count, refs, population = _count_untested(conn)
        assert (count, sorted(refs)) == (2, ["ledger", "posting"])
        assert population == (
            "counted over 2 node(s) the test binding covers, all 0 test file(s) placed"
        )

    def test_an_index_without_the_binding_counts_nothing(self, conn: sqlite3.Connection) -> None:
        _node(conn, "notes", source=None, tests=None)
        conn.commit()
        assert _count_untested(conn) == (
            0,
            [],
            "counted over 0 node(s) the test binding covers, all 0 test file(s) placed",
        )


class TestThePopulationReachesEveryRendering:
    def test_collected_scored_and_rendered(self, conn: sqlite3.Connection, tmp_path: Path) -> None:
        _ledger(conn, unplaced=True)
        data = collect_debt_data(conn, tmp_path)
        assert data.untested_count == 0
        assert data.test_population.startswith("not counted:")
        report = compute_debt_score(data)
        assert report.test_population == data.test_population
        assert format_debt_json(report)["test_population"] == data.test_population
        rendered = _ANSI.sub("", format_debt_report(report))
        assert "not counted: 1 of 2 test file(s)" in rendered


def test_the_name_guessing_mapper_is_retired() -> None:
    assert importlib.util.find_spec("beadloom.context_oracle.test_mapper") is None


def test_a_category_filtered_report_keeps_its_populations(tmp_path: Path) -> None:
    """``status --category`` rebuilds the report; the population must survive that."""
    from click.testing import CliRunner

    project = tmp_path / "project"
    (project / ".beadloom").mkdir(parents=True)
    connection = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(connection)
    _ledger(connection, unplaced=True)
    connection.close()

    result = CliRunner().invoke(
        main, ["status", "--debt-report", "--category", "tests", "--project", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "not counted: 1 of 2 test file(s)" in _ANSI.sub("", result.output)
