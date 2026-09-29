"""Reindex binds Java, Kotlin and Swift tests in their build tool's test tree (BDL-074 G2b).

``beadloom-2mj3.13``: on main (db5c3f28) the retired mapper read ``junit, 2 tests
in 1 files`` for a Maven or Gradle-Kotlin package and ``xctest, 2 tests in 1
files`` for a Swift package's target; after G2 the binding found no test file in
any of them. Each project is its ecosystem's standard layout, built under
``tmp_path`` by ``tests.support.adopter_test_layouts``.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.context_oracle.test_binding import PLACEMENT_MIRROR
from tests.support.adopter_test_layouts import (
    gradle_kotlin_project,
    maven_project,
    swift_package,
    write,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _rows(root: Path) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [
            tuple(row)
            for row in conn.execute(
                "SELECT path, ref_id, placement, test_count FROM test_files ORDER BY path"
            ).fetchall()
        ]


def _tests_of(root: Path, ref_id: str) -> dict[str, Any]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        (extra,) = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    tests: dict[str, Any] = json.loads(extra)["tests"]
    return tests


_PROJECTS: list[tuple[Callable[[Path], Path], str, str]] = [
    (maven_project, "src/test/java/com/example/shop/{p}/{c}Test.java", "junit"),
    (gradle_kotlin_project, "src/test/kotlin/com/example/shop/{p}/{c}Test.kt", "junit"),
    (swift_package, "Tests/ShopTests/{c}Tests.swift", "xctest"),
]


@pytest.mark.parametrize(("build", "test_path", "framework"), _PROJECTS)
class TestEachEcosystem:
    def test_each_test_binds_to_the_package_it_mirrors(
        self, tmp_path: Path, build: Callable[[Path], Path], test_path: str, framework: str
    ) -> None:
        root = build(tmp_path)
        reindex(root)
        assert _rows(root) == sorted(
            (test_path.format(p=p, c=p.title()), p, PLACEMENT_MIRROR, 2)
            for p in ("billing", "orders")
        )

    def test_ctx_reads_what_main_read(
        self, tmp_path: Path, build: Callable[[Path], Path], test_path: str, framework: str
    ) -> None:
        root = build(tmp_path)
        reindex(root)
        assert _tests_of(root, "billing") == {
            "framework": framework,
            "test_files": [test_path.format(p="billing", c="Billing")],
            "test_count": 2,
            "coverage_estimate": "medium",
        }

    def test_an_unchanged_project_is_a_no_op_for_the_incremental_rebuild(
        self, tmp_path: Path, build: Callable[[Path], Path], test_path: str, framework: str
    ) -> None:
        root = build(tmp_path)
        reindex(root)
        assert incremental_reindex(root).nothing_changed


class TestAFolderIsNamedAsItIsSpelled:
    def test_a_swift_packages_tests_folder_is_not_also_read_as_the_tests_root(
        self, tmp_path: Path
    ) -> None:
        """On a case-insensitive disk `tests` opens `Tests/`; the file is indexed once."""
        root = swift_package(tmp_path)
        reindex(root)
        assert [path for path, *_ in _rows(root)] == [
            "Tests/ShopTests/BillingTests.swift",
            "Tests/ShopTests/OrdersTests.swift",
        ]

    def test_a_project_without_a_test_tree_records_no_mirror_root(self, tmp_path: Path) -> None:
        root = tmp_path / "plain"
        write(root, ".beadloom/config.yml", "scan_paths: [src]\n")
        write(root, "src/app.py", "x = 1\n")
        write(root, "tests/test_app.py", "def test_x() -> None:\n    pass\n")
        reindex(root)
        with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
            (value,) = conn.execute("SELECT value FROM meta WHERE key = 'test_layout'").fetchone()
        assert json.loads(value)["mirror_roots"] == []
