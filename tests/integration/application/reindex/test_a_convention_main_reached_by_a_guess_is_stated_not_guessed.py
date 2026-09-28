"""A convention the retired mapper reached only by a guess is stated, never guessed (G5).

``beadloom-2mj3.15``. Main's mapper (db5c3f28) bound a test file it found anywhere
by matching a file name, a folder name or an import against the node ids. The
owner's ruling of 2026-09-28 excludes that: a test binds by the mirror, beside the
code, or through a node's ``tests:`` list. Each case here is a place main reached
by a guess — main's figure beside it, measured by running main's ``map_tests`` on
the same project — and pins what the binding does instead: it reads the file and
says it is unplaced, or it does not read it and says where test files are read,
and a declaration binds it.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.debt_report import _count_untested
from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from tests.support.adopter_test_layouts import (
    declare_config,
    declare_tests,
    jest_top_level_tests_folder,
    python_flat_under,
    python_tests_by_node_folder,
    python_tests_named_by_what_they_import,
    write,
    xcode_project,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: Where the binding reads a test file under Beadloom's defaults, as the debt
#: report and ``ctx`` end their statement of it.
_READ_WHERE = "under the root tests or beside a node's code"


def _tests_of(root: Path, ref_id: str) -> dict[str, Any]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        (extra,) = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    tests: dict[str, Any] = json.loads(extra)["tests"]
    return tests


def _untested(root: Path) -> tuple[int, list[str], str]:
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return _count_untested(conn)
    finally:
        conn.close()


class TestAFileOutsideEveryRootTreeAndSourceIsNotRead:
    """Main: ``pytest``/``jest``/``xctest``, 1 file, 2 tests for billing; ``untested: 0``."""

    @pytest.mark.parametrize(
        "build",
        [
            pytest.param(lambda root: python_flat_under(root, "test"), id="flat test/"),
            pytest.param(jest_top_level_tests_folder, id="top-level __tests__/"),
            pytest.param(xcode_project, id="Xcode ShopTests/"),
        ],
    )
    def test_the_debt_report_says_where_a_test_file_is_read(
        self, tmp_path: Path, build: Callable[[Path], Path]
    ) -> None:
        root = build(tmp_path)
        assert reindex(root).test_files_indexed == 0
        assert _tests_of(root, "billing")["test_files"] == []
        count, _, population = _untested(root)
        assert count == 3
        assert population.startswith("counted over 3 node(s) the test binding covers, all 0")
        assert population.endswith(_READ_WHERE)

    def test_a_declared_root_reads_them_as_unplaced_and_withholds_the_count(
        self, tmp_path: Path
    ) -> None:
        root = python_flat_under(tmp_path, "test")
        declare_config(root, {"roots": ["test"]})
        assert reindex(root).test_files_unplaced == 2
        assert _untested(root)[0] == 0

    def test_a_declared_root_and_a_tests_list_bind_them_as_main_did(self, tmp_path: Path) -> None:
        root = jest_top_level_tests_folder(tmp_path)
        declare_config(root, {"roots": ["tests", "__tests__"]})
        declare_tests(root, "billing", ["__tests__/billing.test.ts"])
        reindex(root)
        assert _tests_of(root, "billing") == {
            "framework": "jest",
            "test_files": ["__tests__/billing.test.ts"],
            "test_count": 2,
            "coverage_estimate": "medium",
        }

    def test_a_declared_mirror_binds_the_xcode_test_target_as_main_did(
        self, tmp_path: Path
    ) -> None:
        root = xcode_project(tmp_path, mirrors={"ShopTests": "Shop"})
        reindex(root)
        assert _tests_of(root, "billing") == {
            "framework": "xctest",
            "test_files": ["ShopTests/BillingTests.swift"],
            "test_count": 2,
            "coverage_estimate": "medium",
        }
        assert _untested(root)[0] == 0


class TestANameAFolderOrAnImportUnderARootIsNotAGuessAtItsNode:
    """Main bound these by ``tests/<ref>/`` and by ``import <ref>``; ``untested: 0``."""

    @pytest.mark.parametrize(
        "build",
        [
            pytest.param(python_tests_by_node_folder, id="tests/<ref>/"),
            pytest.param(python_tests_named_by_what_they_import, id="import <ref>"),
        ],
    )
    def test_the_file_is_unplaced_and_the_count_withheld(
        self, tmp_path: Path, build: Callable[[Path], Path]
    ) -> None:
        root = build(tmp_path)
        assert reindex(root).test_files_unplaced == 2
        assert _tests_of(root, "billing")["test_files"] == []
        count, _, population = _untested(root)
        assert count == 0
        assert population.startswith("not counted: 2 of 2 test file(s) are unplaced")

    def test_a_tests_list_binds_the_folder(self, tmp_path: Path) -> None:
        root = python_tests_by_node_folder(tmp_path)
        declare_tests(root, "billing", ["tests/billing/"])
        reindex(root)
        assert _tests_of(root, "billing")["test_files"] == ["tests/billing/test_flows.py"]


class TestAFrameworkMarkerWithoutATestFileNamesNoFramework:
    """Main named ``pytest``/``jest``/``junit``/``xctest``, ``low``, and ``untested: 0``."""

    @pytest.mark.parametrize(
        "marker", ["conftest.py", "jest.config.js", "src/test/.keep", "ShopTests/.keep"]
    )
    def test_the_project_is_stated_as_having_no_test_file(
        self, tmp_path: Path, marker: str
    ) -> None:
        root = python_tests_by_node_folder(tmp_path)
        for package in ("billing", "orders"):
            (root / f"tests/{package}/test_flows.py").unlink()
        write(root, marker, "")
        reindex(root)
        assert _tests_of(root, "billing")["framework"] == "none"
        assert _tests_of(root, "billing")["coverage_estimate"] == "none"
        count, _, population = _untested(root)
        assert count == 3
        assert population.endswith(_READ_WHERE)
