"""Every test-file convention the retired mapper read is read, no worse than main (G5).

``beadloom-2mj3.15``. The conventions are enumerated from main's mapper
(``git show db5c3f28:src/beadloom/context_oracle/test_mapper.py``): its file-name
patterns and its folder conventions, each in the place its ecosystem keeps it. Each
row is a two-package project from ``tests.support.adopter_test_layouts``; main's
figures were measured by running main's ``map_tests`` and ``aggregate_parent_tests``
on the same project (2026-09-28), and are written down here because that mapper is
retired; the table is ``CONVENTIONS_MAIN_READ``. For each node HEAD must name the
same framework, the same files and the same test count.

Three rows were worse than main before this bead, measured the same way: a Jest
``__tests__/`` folder, a JVM test-tree file with a name no pattern matches, and a
SwiftPM test-target file with a name no pattern matches. ``*.test.tsx`` and
``*.spec.tsx`` were the reverse: main detected no framework from them and read
nothing, and the binding reads them.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.reindex import reindex
from tests.support.adopter_test_layouts import CONVENTIONS_MAIN_READ, PACKAGES, jest_project

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _tests_of(root: Path, ref_id: str) -> dict[str, Any]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        (extra,) = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    tests: dict[str, Any] = json.loads(extra)["tests"]
    return tests


@pytest.mark.parametrize(
    ("build", "test_path", "framework", "per_file"),
    [pytest.param(*row[1:], id=row[0]) for row in CONVENTIONS_MAIN_READ],
)
class TestNoWorseThanMain:
    def test_each_package_is_shown_with_the_test_main_showed(
        self,
        tmp_path: Path,
        build: Callable[[Path], Path],
        test_path: str,
        framework: str,
        per_file: int,
    ) -> None:
        root = build(tmp_path)
        reindex(root)
        for package in PACKAGES:
            assert _tests_of(root, package) == {
                "framework": framework,
                "test_files": [test_path.format(p=package, c=package.title())],
                "test_count": per_file,
                "coverage_estimate": "medium",
            }

    def test_the_root_node_holds_both_as_main_aggregated_them(
        self,
        tmp_path: Path,
        build: Callable[[Path], Path],
        test_path: str,
        framework: str,
        per_file: int,
    ) -> None:
        root = build(tmp_path)
        reindex(root)
        shop = _tests_of(root, "shop")
        assert shop["test_files"] == sorted(
            test_path.format(p=package, c=package.title()) for package in PACKAGES
        )
        assert (shop["framework"], shop["test_count"]) == (framework, 2 * per_file)


@pytest.mark.parametrize("name", ["test", "spec"])
def test_a_tsx_test_main_did_not_read_is_read(tmp_path: Path, name: str) -> None:
    """Main listed ``*.test.tsx`` and ``*.spec.tsx`` among Jest's files but detected
    Jest only from ``.ts`` and ``.js`` names, so on a project whose tests are all
    ``.tsx`` it read none: ``none, 0 tests``, every node untested (measured)."""
    root = jest_project(tmp_path, f"src/{{p}}/{{p}}.{name}.tsx")
    reindex(root)
    assert _tests_of(root, "billing") == {
        "framework": "jest",
        "test_files": [f"src/billing/billing.{name}.tsx"],
        "test_count": 2,
        "coverage_estimate": "medium",
    }
