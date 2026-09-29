"""An adopter whose tests are not `tests/**/test_*.py` scores what it scored before (BDL-074 G2).

Review ``beadloom-b9ll`` M3: on the reviewer's Go module the debt report said
``untested: 0`` on main and ``untested: 3 ... all 0 test file(s) placed`` after the
binding replaced the name-guessing mapper, because the binding found none of the
module's tests. ``_count_untested``'s docstring claimed such a project "scores what
it scored before"; these cases are that claim, run.

Main's figure is written down, not recomputed: the mapper it came from is retired.
Every project is built under ``tmp_path`` and reindexed before the count is read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report import _count_untested
from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from tests.support.adopter_test_layouts import (
    CONVENTIONS_MAIN_READ,
    go_module,
    gradle_kotlin_project,
    jest_flat_spec,
    jest_top_level_tests_folder,
    maven_project,
    python_beside_the_code,
    python_flat_under,
    python_with_a_test_root,
    swift_package,
    write,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: `status --debt-report` on main (db5c3f28) said `untested: 0` for every project
#: here: the retired mapper counted a node untested only when it detected no test
#: framework anywhere, and it detected pytest or go_test in each of them.
UNTESTED_ON_MAIN = 0

#: Beadloom's default patterns, as the population names them.
DEFAULT_PATTERNS_STATED = (
    "go_test (*_test.go), "
    "jest (*.test.*, *.spec.*, __tests__/**/*.[jt]s, __tests__/**/*.[jt]sx), "
    "junit (*Test.java, *Tests.java, *TestCase.java, *IT.java, *ITCase.java, *Test.kt, "
    "*Tests.kt, src/test/**/*.java, src/test/**/*.kt), pytest (test_*.py, *_test.py) or "
    "xctest (*Tests.swift, *Tests/**/*.swift)"
)
#: What the population says a test file is read by, under Beadloom's defaults, for
#: a project with no test root such as the Go module (``beadloom-2mj3.15``: stated on
#: every population; ``.17``: only the roots that exist are named).
READ_BY_DEFAULT = (
    f"a test file is read when its path matches a pattern of {DEFAULT_PATTERNS_STATED} "
    "and it lies beside a node's code, since none of the roots tests, test, spec, "
    "__tests__ exists"
)


def _untested(root: Path) -> tuple[int, list[str], str]:
    reindex(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return _count_untested(conn)
    finally:
        conn.close()


class TestNoWorseThanMain:
    def test_the_go_module_counts_every_package_tested(self, tmp_path: Path) -> None:
        count, refs, population = _untested(go_module(tmp_path))
        assert (count, refs) == (UNTESTED_ON_MAIN, [])
        assert population == (
            "counted over 3 node(s) the test binding covers, all 2 test file(s) placed; "
            f"{READ_BY_DEFAULT}"
        )

    def test_python_tests_beside_the_code_count_every_package_tested(self, tmp_path: Path) -> None:
        count, _, _ = _untested(python_beside_the_code(tmp_path))
        assert count == UNTESTED_ON_MAIN

    def test_python_tests_mirrored_under_a_declared_root_count_every_package_tested(
        self, tmp_path: Path
    ) -> None:
        count, _, _ = _untested(python_with_a_test_root(tmp_path, mirrored=True))
        assert count == UNTESTED_ON_MAIN

    def test_python_tests_flat_under_a_declared_root_withhold_the_count(
        self, tmp_path: Path
    ) -> None:
        count, _, population = _untested(python_with_a_test_root(tmp_path, mirrored=False))
        assert count == UNTESTED_ON_MAIN
        assert population.startswith(
            "not counted: 2 of 2 test file(s) are unplaced (not under test/integration/ "
            "or test/unit/, nor inside a node's source)"
        )
        assert population.endswith(
            f"a test file is read when its path matches a pattern of {DEFAULT_PATTERNS_STATED} "
            "under the root test or beside a node's code"
        )


class TestJavaKotlinAndSwiftNoWorseThanMain:
    """``beadloom-2mj3.13``: main read junit or xctest in each and counted 0 untested."""

    def test_the_maven_project_counts_every_package_tested(self, tmp_path: Path) -> None:
        assert _untested(maven_project(tmp_path))[:2] == (UNTESTED_ON_MAIN, [])

    def test_the_gradle_kotlin_project_counts_every_package_tested(self, tmp_path: Path) -> None:
        assert _untested(gradle_kotlin_project(tmp_path))[:2] == (UNTESTED_ON_MAIN, [])

    def test_the_swift_package_counts_every_target_folder_tested(self, tmp_path: Path) -> None:
        assert _untested(swift_package(tmp_path))[:2] == (UNTESTED_ON_MAIN, [])


@pytest.mark.parametrize(
    "build", [pytest.param(row[1], id=row[0]) for row in CONVENTIONS_MAIN_READ]
)
def test_every_convention_main_read_scores_what_it_scored_on_main(
    tmp_path: Path, build: Callable[[Path], Path]
) -> None:
    """``beadloom-2mj3.15``: main read each of these and counted 0 untested (measured)."""
    assert _untested(build(tmp_path))[:2] == (UNTESTED_ON_MAIN, [])


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda root: python_flat_under(root, "test"), id="flat test/"),
        pytest.param(jest_flat_spec, id="flat spec/"),
        pytest.param(jest_top_level_tests_folder, id="top-level __tests__/"),
    ],
)
def test_a_default_root_main_read_by_name_scores_what_it_scored_on_main(
    tmp_path: Path, build: Callable[[Path], Path]
) -> None:
    """The owner's NG1 ruling (``beadloom-2mj3.15``, ``.17``): main bound these files by
    their names and counted 0; they are read unplaced, so the count is withheld."""
    count, refs, population = _untested(build(tmp_path))
    assert (count, refs) == (UNTESTED_ON_MAIN, [])
    assert population.startswith("not counted: 2 of 2 test file(s) are unplaced")


class TestWhatTheCountStillSays:
    def test_a_package_without_a_test_is_counted_once_every_file_is_placed(
        self, tmp_path: Path
    ) -> None:
        root = go_module(tmp_path)
        (root / "internal/orders/orders_test.go").unlink()
        count, refs, _ = _untested(root)
        assert (count, refs) == (1, ["orders"])

    def test_a_project_with_no_test_file_says_what_a_test_file_is_read_by(
        self, tmp_path: Path
    ) -> None:
        root = go_module(tmp_path)
        for package in ("billing", "orders"):
            (root / f"internal/{package}/{package}_test.go").unlink()
        count, _, population = _untested(root)
        assert count == 3
        assert population == (
            "counted over 3 node(s) the test binding covers, all 0 test file(s) placed; "
            f"{READ_BY_DEFAULT}"
        )

    def test_a_framework_no_pattern_names_is_stated_as_not_read(self, tmp_path: Path) -> None:
        root = go_module(tmp_path)
        write(
            root,
            ".beadloom/config.yml",
            "scan_paths: [internal]\ntests:\n  patterns:\n    junit: ['*Test.java']\n",
        )
        _, _, population = _untested(root)
        assert population.endswith(
            "a test file is read when its path matches a pattern of junit (*Test.java) "
            "and it lies beside a node's code, since none of the roots tests, test, spec, "
            "__tests__ exists"
        )
