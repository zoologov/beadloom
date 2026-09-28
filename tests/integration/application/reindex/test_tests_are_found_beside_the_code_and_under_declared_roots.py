"""Reindex finds tests beside the code and under the roots a project declares (BDL-074 G2).

Review ``beadloom-b9ll`` M3: the reindex walked ``tests/`` for pytest names only,
so on the reviewer's Go module ``ctx billing`` went from ``go_test, 1 tests in 1
files`` (main, the retired mapper) to ``none, 0 tests in 0 files``. Review m5: a
``tests:`` declaration that binds nothing said nothing.

Every case builds its project under ``tmp_path`` from ``tests.support.adopter_test_layouts``
and reads the index the rebuild wrote.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.application.reindex.test_index import describe_placements
from beadloom.context_oracle.test_binding import (
    PLACEMENT_BESIDE_CODE,
    PLACEMENT_MIRROR,
    PLACEMENT_UNPLACED,
)
from tests.support.adopter_test_layouts import (
    go_module,
    python_beside_the_code,
    python_with_a_test_root,
    write,
)

if TYPE_CHECKING:
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


class TestTheGoModule:
    def test_each_go_test_binds_to_the_package_it_sits_in(self, tmp_path: Path) -> None:
        root = go_module(tmp_path)
        reindex(root)
        assert _rows(root) == [
            ("internal/billing/billing_test.go", "billing", PLACEMENT_BESIDE_CODE, 1),
            ("internal/orders/orders_test.go", "orders", PLACEMENT_BESIDE_CODE, 1),
        ]

    def test_ctx_reads_what_main_read_go_test_one_test_in_one_file(self, tmp_path: Path) -> None:
        root = go_module(tmp_path)
        reindex(root)
        assert _tests_of(root, "billing") == {
            "framework": "go_test",
            "test_files": ["internal/billing/billing_test.go"],
            "test_count": 1,
            "coverage_estimate": "medium",
        }
        assert _tests_of(root, "shop")["test_files"] == [
            "internal/billing/billing_test.go",
            "internal/orders/orders_test.go",
        ]

    def test_the_rebuild_counts_them_as_bound(self, tmp_path: Path) -> None:
        result = reindex(go_module(tmp_path))
        assert (result.test_files_indexed, result.test_files_unplaced) == (2, 0)

    def test_the_tests_line_names_the_files_bound_beside_the_code(self) -> None:
        assert describe_placements({PLACEMENT_BESIDE_CODE: 2}, {}) == (
            "2 files (2 bound to a node (2 beside the code), 0 unplaced)"
        )

    def test_an_unchanged_module_is_a_no_op_for_the_incremental_rebuild(
        self, tmp_path: Path
    ) -> None:
        root = go_module(tmp_path)
        reindex(root)
        assert incremental_reindex(root).nothing_changed


class TestAPythonProject:
    def test_tests_under_a_declared_root_are_found_and_mirrored(self, tmp_path: Path) -> None:
        root = python_with_a_test_root(tmp_path, mirrored=True)
        reindex(root)
        assert _rows(root) == [
            ("test/unit/billing/test_billing.py", "billing", PLACEMENT_MIRROR, 2),
            ("test/unit/orders/test_orders.py", "orders", PLACEMENT_MIRROR, 2),
        ]
        assert _tests_of(root, "billing")["framework"] == "pytest"

    def test_tests_flat_under_a_declared_root_are_found_and_unplaced(self, tmp_path: Path) -> None:
        root = python_with_a_test_root(tmp_path, mirrored=False)
        reindex(root)
        assert _rows(root) == [
            ("test/test_billing.py", None, PLACEMENT_UNPLACED, 2),
            ("test/test_orders.py", None, PLACEMENT_UNPLACED, 2),
        ]
        assert _tests_of(root, "billing")["framework"] == "pytest"

    def test_tests_beside_the_code_bind_to_their_package(self, tmp_path: Path) -> None:
        root = python_beside_the_code(tmp_path)
        reindex(root)
        assert _rows(root) == [
            ("src/shop/billing/test_billing.py", "billing", PLACEMENT_BESIDE_CODE, 2),
            ("src/shop/orders/test_orders.py", "orders", PLACEMENT_BESIDE_CODE, 2),
        ]

    def test_tests_beside_the_code_are_not_read_when_switched_off(self, tmp_path: Path) -> None:
        root = python_beside_the_code(tmp_path)
        write(
            root,
            ".beadloom/config.yml",
            "languages: [.py]\nscan_paths: [src]\ntests:\n  beside_code: false\n",
        )
        reindex(root)
        assert _rows(root) == []

    def test_a_changed_layout_is_rebuilt_by_the_incremental_rebuild(self, tmp_path: Path) -> None:
        root = python_with_a_test_root(tmp_path, mirrored=True)
        reindex(root)
        write(root, ".beadloom/config.yml", "languages: [.py]\nscan_paths: [src]\n")
        incremental_reindex(root)
        assert _rows(root) == []


class TestADeclarationThatBindsNothing:
    def _declare(self, root: Path, prefixes: list[str]) -> None:
        path = root / ".beadloom" / "_graph" / "services.yml"
        graph = yaml.safe_load(path.read_text(encoding="utf-8"))
        for node in graph["nodes"]:
            if node["ref_id"] == "billing":
                node["tests"] = prefixes
        path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")

    def test_a_prefix_that_covers_no_test_file_is_reported_by_node_and_prefix(
        self, tmp_path: Path
    ) -> None:
        root = python_with_a_test_root(tmp_path, mirrored=False)
        self._declare(root, ["test/e2e", "test/test_billing.py"])
        result = reindex(root)
        assert [w for w in result.warnings if "binds nothing" in w] == [
            "Node 'billing': `tests:` prefix 'test/e2e' covers no indexed test file, so it "
            "binds nothing (a folder is declared with a trailing '/')"
        ]

    def test_a_prefix_that_binds_a_file_is_not_reported(self, tmp_path: Path) -> None:
        root = python_with_a_test_root(tmp_path, mirrored=False)
        self._declare(root, ["test/"])
        result = reindex(root)
        assert not [w for w in result.warnings if "binds nothing" in w]

    def test_a_malformed_tests_config_is_reported(self, tmp_path: Path) -> None:
        root = python_beside_the_code(tmp_path)
        write(root, ".beadloom/config.yml", "scan_paths: [src]\ntests:\n  roots: test\n")
        result = reindex(root)
        assert any("`tests.roots`" in w for w in result.warnings), result.warnings
