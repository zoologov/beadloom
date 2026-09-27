"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_no_selected_test_reads_the_mutated_copy.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from tests.support.package_under_test import PACKAGE_ROOT
from tests.support.package_walks import (
    SELF_SCANNING_TESTS_OUTSIDE_THE_POOL,
    Scan,
    python_source_scans,
)
from tests.support.repository_root import REPO_ROOT
from tests.support.toml_reader import toml_loads

#: The files `beadloom-ey4m` moved onto the helper. Held here so the sweep has a
#: floor: a scan that matched nothing because it stopped parsing would still
#: report an empty offender list, and this says the population contains the very
#: files the defect was found in.
MOVED_ONTO_THE_HELPER = (
    "tests/test_two_readers_of_one_markdown_table.py",
    "tests/test_guards_invocation.py",
    "tests/test_the_reference_docs_state_the_population_shapes.py",
    "tests/test_s2_move_regression.py",
)


def _pool() -> tuple[str, ...]:
    """The test files mutmut selects, read from where the runner reads them."""
    config = toml_loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = config["tool"]
    assert isinstance(tool, dict)
    mutmut = tool["mutmut"]
    assert isinstance(mutmut, dict)
    selection = mutmut["pytest_add_cli_args_test_selection"]
    assert isinstance(selection, list)
    return tuple(str(entry) for entry in selection)


def _scan_repository_file(relative: str) -> tuple[Scan, ...]:
    """Scan a file of this repository as it will be read under `mutmut run`."""
    path = REPO_ROOT / relative
    return python_source_scans(
        path.read_text(encoding="utf-8"), at=path, package_root=PACKAGE_ROOT
    )


def _offenders(entries: tuple[str, ...]) -> dict[str, list[str]]:
    """Each file of *entries* that reads the package, with how it reads it."""
    found = {entry: _scan_repository_file(entry) for entry in entries}
    return {
        entry: [
            f"{scan.root} ({scan.pattern}) at line {scan.line} reaches {scan.reaches}"
            for scan in scans
        ]
        for entry, scans in found.items()
        if scans
    }


class TestNoTestTheRunnerSelectsWalksThePackageItMutates:
    """The sweep, over the pool mutmut actually runs — tier one, no exceptions."""

    def test_the_pool_it_scans_is_the_runners_own_and_is_not_empty(self) -> None:
        """Stated because a sweep over an empty population passes silently."""
        pool = _pool()

        assert len(pool) > 100, len(pool)
        assert all((REPO_ROOT / entry).is_file() for entry in pool)

    def test_the_files_the_defect_was_found_in_are_in_what_it_scans(self) -> None:
        """The floor under the green: the sweep covers the four moved files.

        Without this, a pool that stopped naming them would leave the sweep
        green over tests that never had the shape.
        """
        pool = set(_pool())

        assert set(MOVED_ONTO_THE_HELPER) <= pool, sorted(set(MOVED_ONTO_THE_HELPER) - pool)

    def test_it_reports_a_carrier_that_is_selected(self) -> None:
        """The sweep run over a pool that DOES hold one, so its green is readable.

        A sweep whose collector had stopped matching would report an empty
        offender list and read exactly like a clean repository. This hands it
        the pool that the one remaining `pyproject.toml` line would create.
        """
        would_be_selected = "tests/test_tui_no_raw_sqlite.py"

        offenders = _offenders((*_pool(), would_be_selected))

        assert list(offenders) == [would_be_selected]
        assert offenders[would_be_selected]

    def test_no_selected_test_derives_a_python_scan_root_from_its_own_file(self) -> None:
        offenders = _offenders(_pool())

        assert offenders == {}, (
            f"{len(offenders)} test file(s) mutmut SELECTS walk a root built from "
            f"their own location, so under `mutmut run` they read "
            f"`mutants/src/beadloom` and report its generated bodies as the "
            f"package's own — the failure that scored nine nightlies at 0 of "
            f"7187 mutants. Read the package through "
            f"`tests/support/package_under_test.py`: {offenders}"
        )


class TestEveryOtherSelfScanningTestIsOnePyprojectLineAway:
    """Tier two: the shape outside the pool is declared, not ignored.

    The second instance of this defect arrived in a file nobody had swept and
    was survivable only because it was unselected. That is a property of
    `pyproject.toml` and not of the test, so the set is held rather than
    described.
    """

    def test_the_declared_set_is_not_empty_and_none_of_it_is_selected(self) -> None:
        """Both halves in one place: the population is real, and it is unselected.

        An empty declared set would make the test above pass by asserting that
        nothing equals nothing.
        """
        pool = set(_pool())

        assert SELF_SCANNING_TESTS_OUTSIDE_THE_POOL
        assert set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL) & pool == set()
