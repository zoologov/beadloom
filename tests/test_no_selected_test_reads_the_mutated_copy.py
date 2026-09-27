"""BDL-072 — the CLASS: no test mutmut selects may walk the package it mutates.

`beadloom-ey4m` moved four files onto `tests/support/package_under_test.py` and locked
those four by name. This file locks the class they belong to, because the defect
is a shape and not a file list: a test that derives a scan root from its own
`__file__` and walks it for Python sources reads `mutants/src/beadloom` when
mutmut runs it, so it reports mutmut's generated bodies as the package's own.
One such test scored nine nightlies at 0 of 7 187 mutants (BDL-UX #289), and a
SECOND instance landed six days later in a file nobody had swept
(`tests/unit/application/source_derivation/test_one_part_of_ancestry_walk_serves_the_rule_engine.py`,
comment on `beadloom-ey4m`, 2026-09-12).

**What the guard keys on, and why it resolves paths rather than matching text.**
Three of the four moved files built their root through an intermediate
repository root, so a rule reading one assignment would have called them clean.
This collector follows the binding chain from `__file__` to a PATH — `.parent`,
`.parents[n]`, `/ "src" / "beadloom"` — and then asks whether that path reaches
the package under test. Under `mutmut run` the suite sits at `mutants/tests` and
the package at `mutants/src/beadloom`, the same arrangement as on the tree, so
the question answered here is the question that decides the run.

**Two tiers, and only the first is a rule with no exceptions.**

* Every file in `[tool.mutmut] pytest_add_cli_args_test_selection` is scanned,
  and a hit is a failure. These are the tests that actually run inside the
  mutated room.
* Every other test file carrying the shape is DECLARED below with what it walks.
  Those cannot break a run today and are one `pyproject.toml` line from being
  able to, which is exactly what the second instance was.

**These tests prove the guard catches an offender that does not exist yet**:
each shape is written into a temporary tree arranged like this repository and
run through the same collector the sweep uses. A guard asserted only over the
files of the day passes on the day a fifth file arrives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support import repository_root
from tests.support.package_under_test import PACKAGE_ROOT
from tests.support.package_walks import (
    SELF_SCANNING_TESTS_OUTSIDE_THE_POOL,
    Scan,
    python_source_scans,
)
from tests.support.repository_root import REPO_ROOT


@pytest.fixture
def suite(tmp_path: Path) -> Path:
    """A tree arranged like this repository: a suite beside a package.

    The offenders below are written into it, so the guard is proven against a
    test that does not exist rather than against the four that do.
    """
    (tmp_path / "src" / "beadloom").mkdir(parents=True)
    (tmp_path / "src" / "beadloom" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    support = tmp_path / "tests" / "support"
    support.mkdir(parents=True)
    helper = Path(repository_root.__file__)
    (support / helper.name).write_text(helper.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _scan_new_test(suite: Path, source: str) -> tuple[Scan, ...]:
    """Write *source* as a new test of *suite* and scan it where it would live."""
    path = suite / "tests" / "test_newly_added.py"
    path.write_text(source, encoding="utf-8")
    return python_source_scans(
        path.read_text(encoding="utf-8"), at=path, package_root=suite / "src" / "beadloom"
    )


class TestANewlyAddedTestWithTheShapeIsCaught:
    """The guard against a file that does not exist yet, which is the whole point.

    Each source below is written to disk and read back through the same
    collector the sweep runs, so what is measured is the rule and not a list.
    """

    def test_a_root_built_from_its_own_file_in_one_statement_is_caught(self, suite: Path) -> None:
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            '_SRC = Path(__file__).resolve().parents[1] / "src" / "beadloom"\n'
            'MODULES = sorted(_SRC.rglob("*.py"))\n',
        )

        assert [(scan.root, scan.pattern) for scan in found] == [("_SRC", "*.py")]
        assert found[0].reaches == "inside the package under test"

    def test_a_root_built_through_an_intermediate_is_caught(self, suite: Path) -> None:
        """The case a one-statement reader misses, and three of four files had it."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "REPO_ROOT = Path(__file__).resolve().parents[1]\n"
            'SRC = REPO_ROOT / "src"\n'
            'PACKAGE = SRC / "beadloom"\n'
            'MODULES = list(PACKAGE.rglob("*.py"))\n',
        )

        assert [scan.root for scan in found] == ["PACKAGE"]

    def test_a_recursive_glob_pattern_is_caught_as_well_as_rglob(self, suite: Path) -> None:
        """`glob("**/*.py")` walks the same tree by another spelling."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            'SRC = Path(__file__).resolve().parents[1] / "src"\n'
            'MODULES = list(SRC.glob("**/*.py"))\n',
        )

        assert [scan.pattern for scan in found] == ["**/*.py"]

    def test_a_recursive_walk_of_the_repository_root_is_caught(self, suite: Path) -> None:
        """It never names the package and descends into it on every run."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "REPO_ROOT = Path(__file__).resolve().parents[1]\n"
            'MODULES = list(REPO_ROOT.rglob("*.py"))\n',
        )

        assert [scan.reaches for scan in found] == [
            "a tree containing the package under test, walked recursively"
        ]

    def test_a_root_handed_to_a_reader_rather_than_walked_here_is_caught(
        self, suite: Path
    ) -> None:
        """The shape of the SECOND instance, which spells no walk of its own.

        `tests/unit/application/source_derivation/test_one_part_of_ancestry_walk_serves_the_rule_engine.py`
        hands its root to `beadloom.application.source_derivation.source_tree`'s
        `python_files`, so a collector reading `rglob` calls alone reports the
        file the bead's own comment names as clean.
        """
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "from beadloom.application.source_derivation.source_tree import python_files\n"
            'PACKAGE = Path(__file__).resolve().parents[1] / "src" / "beadloom"\n'
            "MODULES = python_files(PACKAGE)\n",
        )

        assert [scan.pattern for scan in found] == ["handed to python_files()"]

    def test_a_walk_inside_one_package_directory_is_caught(self, suite: Path) -> None:
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            '_TUI = Path(__file__).resolve().parent.parent / "src" / "beadloom" / "tui"\n'
            '_MODULES = list(_TUI.rglob("*.py"))\n',
        )

        assert [scan.root for scan in found] == ["_TUI"]


    def test_a_root_taken_from_the_suites_root_helper_is_caught(self, suite: Path) -> None:
        """BDL-074 B1: the root is found one way now, and it reaches the copy too.

        Under `mutmut run` the helper finds `mutants/pyproject.toml` first, so a
        walk of its `src` reads the mutated package exactly as `parents[1]` did.
        """
        found = _scan_new_test(
            suite,
            "from tests.support.repository_root import REPO_ROOT\n"
            'MODULES = sorted((REPO_ROOT / "src").rglob("*.py"))\n',
        )

        assert [scan.reaches for scan in found] == [
            "a tree containing the package under test, walked recursively"
        ]

    def test_a_root_a_support_module_builds_and_a_test_imports_is_caught(
        self, suite: Path
    ) -> None:
        """The walk is in the test, the root is built one import away."""
        (suite / "tests" / "support" / "paths.py").write_text(
            "from tests.support.repository_root import REPO_ROOT as ROOT\n"
            'PACKAGE = ROOT / "src" / "beadloom"\n',
            encoding="utf-8",
        )
        found = _scan_new_test(
            suite,
            "from tests.support.paths import PACKAGE as TREE\n"
            'MODULES = list(TREE.rglob("*.py"))\n',
        )

        assert [scan.root for scan in found] == ["TREE"]

    def test_a_root_imported_from_a_support_module_that_is_not_there_is_no_root(
        self, suite: Path
    ) -> None:
        found = _scan_new_test(
            suite,
            'from tests.support.absent import PACKAGE\nMODULES = list(PACKAGE.rglob("*.py"))\n',
        )

        assert found == ()


class TestAFileThatDoesNotHaveTheShapeIsNotCaught:
    """The other direction: a predicate that widened would empty the sweep.

    Every guard in this repository that walks a tree rests on a collector like
    this one, so a rule that reported everything would be reported as a red on
    the day it was written and as noise on every day after.
    """

    def test_a_test_that_reads_the_package_through_the_helper_is_not_caught(
        self, suite: Path
    ) -> None:
        """The shape `beadloom-ey4m` moved the four files to: no `__file__`."""
        found = _scan_new_test(
            suite,
            "from tests.support.package_under_test import PACKAGE_ROOT, modules_under\n"
            "MODULES = modules_under(PACKAGE_ROOT)\n",
        )

        assert found == ()

    def test_a_walk_of_the_suites_own_files_is_not_caught(self, suite: Path) -> None:
        """mutmut copies the suite; it does not mutate it.

        A test reading `mutants/tests` reads a verbatim copy of itself, which is
        a different question from the one this guard asks.
        """
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "TESTS_ROOT = Path(__file__).resolve().parent\n"
            'FILES = list(TESTS_ROOT.rglob("*.py"))\n',
        )

        assert found == ()

    def test_a_shallow_glob_at_the_repository_root_is_not_caught(self, suite: Path) -> None:
        """`glob("*.py")` at the root reads the root's own files and descends nowhere."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "REPO_ROOT = Path(__file__).resolve().parents[1]\n"
            'FILES = list(REPO_ROOT.glob("*.py"))\n',
        )

        assert found == ()

    def test_a_walk_for_documents_rather_than_sources_is_not_caught(self, suite: Path) -> None:
        """mutmut copies `.md`/`.txt` under `also_copy` and mutates neither."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            'DOCS = Path(__file__).resolve().parents[1] / "src"\n'
            'FILES = list(DOCS.rglob("*.md"))\n',
        )

        assert found == ()

    def test_a_root_that_is_only_re_expressed_is_not_caught(self, suite: Path) -> None:
        """`relative_to` and `str` open nothing, and the suite spells them often.

        Reporting them would put every path-printing test into the declared
        population, where the reasons nobody can write are the reasons nobody
        reads.
        """
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            'SRC = Path(__file__).resolve().parents[1] / "src" / "beadloom"\n'
            "def test_it(tmp_path: Path) -> None:\n"
            "    assert str(SRC).endswith('beadloom')\n"
            "    assert (SRC / 'x.py').relative_to(SRC).name == 'x.py'\n",
        )

        assert found == ()

    def test_a_root_that_is_not_built_from_its_own_file_is_not_caught(self, suite: Path) -> None:
        """A fixture root handed in at runtime cannot point at the mutated copy."""
        found = _scan_new_test(
            suite,
            "from pathlib import Path\n"
            "def test_it(tmp_path: Path) -> None:\n"
            '    assert list(tmp_path.rglob("*.py")) == []\n',
        )

        assert found == ()


class TestEveryOtherSelfScanningTestIsOnePyprojectLineAway:
    """Tier two: the shape outside the pool is declared, not ignored.

    The second instance of this defect arrived in a file nobody had swept and
    was survivable only because it was unselected. That is a property of
    `pyproject.toml` and not of the test, so the set is held rather than
    described.
    """

    def test_the_declared_set_is_what_the_repository_carries(self) -> None:
        carrying = {
            str(path.relative_to(REPO_ROOT))
            for path in sorted(REPO_ROOT.joinpath("tests").rglob("test_*.py"))
            if python_source_scans(
                path.read_text(encoding="utf-8"), at=path, package_root=PACKAGE_ROOT
            )
        }

        assert carrying == set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL), (
            "a test walks the package from a root built from its own file and "
            "nobody has classified it. Move it onto `tests/support/package_under_test.py`, "
            "or declare here what it walks and why selecting it would be safe — "
            f"undeclared {sorted(carrying - set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL))}, "
            f"gone {sorted(set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL) - carrying)}"
        )

