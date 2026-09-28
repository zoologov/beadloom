"""Reindex records test files in their own tables, and never as code (BDL-074 C1).

Every case builds a project under ``tmp_path`` and passes its root explicitly: the
rebuild under test is the one written here, never this repository's own index.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.application.reindex import incremental_reindex, reindex

if TYPE_CHECKING:
    from pathlib import Path

_TWO_TESTS = (
    "from ledger import posting\n\n\n"
    "def test_posts() -> None:\n    posting.post()\n\n\n"
    "def test_reverses() -> None:\n    pass\n"
)
_ONE_TEST = "def test_balances() -> None:\n    pass\n"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_graph(root: Path, *, posting_extra: dict[str, Any] | None = None) -> None:
    posting: dict[str, Any] = {
        "ref_id": "posting",
        "kind": "feature",
        "summary": "Posting",
        "source": "src/ledger/posting.py",
        **(posting_extra or {}),
    }
    graph = {
        "nodes": [
            {"ref_id": "app", "kind": "service", "summary": "App", "source": ""},
            {"ref_id": "ledger", "kind": "domain", "summary": "Ledger", "source": "src/ledger/"},
            posting,
        ],
        "edges": [
            {"src": "posting", "dst": "ledger", "kind": "part_of"},
            {"src": "ledger", "dst": "app", "kind": "part_of"},
        ],
    }
    _write(root, ".beadloom/_graph/ledger.yml", yaml.safe_dump(graph, sort_keys=False))


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    _write(root, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
    _write(root, "src/ledger/__init__.py", '"""The ledger."""\n')
    _write(root, "src/ledger/posting.py", "def post() -> None:\n    pass\n")
    _write(root, "src/ledger/balance.py", "def balance() -> int:\n    return 0\n")
    _write_graph(root)
    _write(root, "tests/unit/ledger/test_posting.py", _TWO_TESTS)
    _write(root, "tests/unit/ledger/test_balance.py", _ONE_TEST)
    _write(root, "tests/test_flat.py", _ONE_TEST)
    _write(root, "tests/acceptance/steps/test_story_steps.py", _ONE_TEST)
    _write(root, "tests/conftest.py", "import pytest\n")
    _write(root, "mutants/tests/unit/ledger/test_posting.py", _TWO_TESTS)
    return root


def _query(root: Path, sql: str, params: tuple[object, ...] = ()) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


def _tests_of(root: Path, ref_id: str) -> dict[str, Any]:
    (extra,) = _query(root, "SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,))[0]
    tests: dict[str, Any] = json.loads(extra)["tests"]
    return tests


class TestTheTestIndex:
    def test_every_test_file_under_tests_is_recorded_with_its_kind_node_and_count(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        reindex(root)
        rows = _query(
            root, "SELECT path, kind, ref_id, placement, test_count FROM test_files ORDER BY path"
        )
        assert rows == [
            ("tests/acceptance/steps/test_story_steps.py", "acceptance", None, "other_kind", 1),
            ("tests/test_flat.py", None, None, "unplaced", 1),
            ("tests/unit/ledger/test_balance.py", "unit", "ledger", "mirror", 1),
            ("tests/unit/ledger/test_posting.py", "unit", "posting", "mirror", 2),
        ]

    def test_a_test_files_imports_are_recorded_and_resolved_to_their_owner(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        reindex(root)
        rows = _query(
            root,
            "SELECT file_path, import_path, resolved_ref_id FROM test_imports ORDER BY file_path",
        )
        assert ("tests/unit/ledger/test_posting.py", "ledger", "ledger") in rows or (
            "tests/unit/ledger/test_posting.py",
            "ledger.posting",
            "posting",
        ) in rows, rows

    def test_tests_do_not_become_code(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        for table, column in (
            ("code_symbols", "file_path"),
            ("code_imports", "file_path"),
            ("file_index", "path"),
        ):
            rows = _query(root, f"SELECT count(*) FROM {table} WHERE {column} LIKE 'tests/%'")  # noqa: S608
            assert rows == [(0,)], table

    def test_no_mutation_copy_is_indexed(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        assert _query(root, "SELECT count(*) FROM test_files WHERE path LIKE 'mutants/%'") == [
            (0,)
        ]

    def test_the_rebuild_reports_what_it_indexed_and_what_is_unplaced(
        self, tmp_path: Path
    ) -> None:
        result = reindex(_project(tmp_path))
        assert (result.test_files_indexed, result.test_files_unplaced) == (4, 1)


class TestExtraTestsFromTheBinding:
    def test_the_four_key_shape_is_built_from_the_bound_files(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        assert _tests_of(root, "posting") == {
            "framework": "pytest",
            "test_files": ["tests/unit/ledger/test_posting.py"],
            "test_count": 2,
            "coverage_estimate": "medium",
        }

    def test_a_parent_holds_the_union_of_its_descendants_files(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        expected = ["tests/unit/ledger/test_balance.py", "tests/unit/ledger/test_posting.py"]
        assert _tests_of(root, "ledger")["test_files"] == expected
        assert _tests_of(root, "app")["test_files"] == expected
        assert _tests_of(root, "app")["test_count"] == 3

    def test_a_flat_test_named_after_a_node_is_not_guessed_into_it(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _write(root, "tests/test_posting.py", _TWO_TESTS)
        reindex(root)
        assert "tests/test_posting.py" not in _tests_of(root, "posting")["test_files"]


class TestTheOverride:
    def test_a_declared_prefix_binds_and_survives_both_rebuilds(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _write_graph(root, posting_extra={"tests": ["tests/test_flat.py"]})
        reindex(root)
        incremental_reindex(root)
        files = _tests_of(root, "posting")["test_files"]
        assert files == ["tests/test_flat.py", "tests/unit/ledger/test_posting.py"]
        assert _query(
            root, "SELECT ref_id, placement FROM test_files WHERE path = 'tests/test_flat.py'"
        ) == [("posting", "override")]

    def test_a_declaration_that_is_not_a_list_of_paths_is_reported_and_ignored(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _write_graph(root, posting_extra={"tests": {"framework": "pytest"}})
        result = reindex(root)
        assert any("posting" in w and "tests:" in w for w in result.warnings), result.warnings
        assert set(_tests_of(root, "posting")) == {
            "framework",
            "test_files",
            "test_count",
            "coverage_estimate",
        }


class TestTheIncrementalRebuild:
    def test_a_test_added_after_the_full_rebuild_is_indexed_by_the_incremental_one(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        reindex(root)
        _write(root, "tests/unit/ledger/test_posting_more.py", _ONE_TEST)
        incremental_reindex(root)
        assert "tests/unit/ledger/test_posting_more.py" in _tests_of(root, "ledger")["test_files"]

    def test_an_edited_test_is_read_again_and_an_unchanged_one_is_kept(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        reindex(root)
        _write(root, "tests/unit/ledger/test_balance.py", _ONE_TEST + _TWO_TESTS)
        incremental_reindex(root)
        counts = dict(_query(root, "SELECT path, test_count FROM test_files"))
        assert counts["tests/unit/ledger/test_balance.py"] == 3
        assert counts["tests/unit/ledger/test_posting.py"] == 2

    def test_a_removed_test_leaves_the_index(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        reindex(root)
        (root / "tests" / "unit" / "ledger" / "test_balance.py").unlink()
        incremental_reindex(root)
        assert _query(
            root, "SELECT count(*) FROM test_files WHERE path LIKE '%test_balance.py'"
        ) == [(0,)]

    def test_an_index_built_before_the_test_index_is_rebuilt_in_full(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _write_graph(root, posting_extra={"tests": ["tests/test_flat.py"]})
        reindex(root)
        with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
            conn.execute("DELETE FROM meta WHERE key = 'test_index_version'")
            conn.execute("DELETE FROM test_overrides")
            conn.execute("DELETE FROM test_files")
        incremental_reindex(root)
        assert "tests/test_flat.py" in _tests_of(root, "posting")["test_files"]
