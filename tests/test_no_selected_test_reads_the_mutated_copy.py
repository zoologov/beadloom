"""BDL-072 — the CLASS: no test mutmut selects may walk the package it mutates.

`beadloom-ey4m` moved four files onto `tests/package_under_test.py` and locked
those four by name. This file locks the class they belong to, because the defect
is a shape and not a file list: a test that derives a scan root from its own
`__file__` and walks it for Python sources reads `mutants/src/beadloom` when
mutmut runs it, so it reports mutmut's generated bodies as the package's own.
One such test scored nine nightlies at 0 of 7 187 mutants (BDL-UX #289), and a
SECOND instance landed six days later in a file nobody had swept
(`tests/test_one_part_of_ancestry_walk_serves_the_rule_engine.py`, comment on
`beadloom-ey4m`, 2026-09-12).

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

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.package_under_test import PACKAGE_ROOT
from tests.test_mutation_runner_scope import toml_loads

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent

#: Calls that re-express a path instead of reading what it points at. Named so
#: the collector below can say what it passes over: without this, every
#: ``path.relative_to(SRC)`` in the suite is reported as a read of the package.
_PATH_ARITHMETIC = frozenset(
    {
        "Path",
        "as_posix",
        "fspath",
        "is_relative_to",
        "joinpath",
        "relative_to",
        "resolve",
        "str",
        "with_suffix",
    }
)

#: Test files that read the package from a root built from their own location,
#: with what each one reads. None of them is selected for the mutation pool,
#: which is the only reason each is survivable: mutmut never runs them, so they
#: never see `mutants/src`. Adding one to the pool without moving it onto
#: ``tests/package_under_test.py`` fails the sweep above it.
SELF_SCANNING_TESTS_OUTSIDE_THE_POOL: dict[str, str] = {
    "tests/test_bead15_s3b_coverage.py": (
        "lists site*.py under application/; excluded from the pool by name, because "
        "it runs sync-check over the tree it is in and every mutated module is stale there"
    ),
    "tests/test_ci_consolidated_structure.py": (
        "reads two shipped workflow templates under onboarding/templates/, which "
        "mutmut copies and does not mutate"
    ),
    "tests/test_ci_windows_dimension.py": (
        "reads one shipped workflow template under onboarding/templates/"
    ),
    "tests/test_decode_handlers.py": "walks src/beadloom for decode call sites",
    "tests/test_guards_boundary_escapes.py": (
        "reads three named modules of the guards seam and sabotages copies of them"
    ),
    "tests/test_locale_independent_io.py": "walks src/beadloom for ambient-encoding sites",
    "tests/test_mutation_runner_scope.py": "walks src/ for modules importing the runner",
    "tests/test_one_part_of_ancestry_walk_serves_the_rule_engine.py": (
        "walks src/beadloom/graph/rules for the one part_of ancestry walk — the "
        "second instance of this shape, found 2026-09-12 on beadloom-ey4m"
    ),
    "tests/test_s2_seam_crosscutting.py": "reads src/beadloom/tui for seam crossings",
    "tests/test_the_stale_pair_count_is_derived_in_one_place.py": (
        "walks src/beadloom for stale-pair derivations"
    ),
    "tests/test_tui_no_raw_sqlite.py": "walks src/beadloom/tui for raw sqlite3 use",
}

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


@dataclass(frozen=True)
class Scan:
    """One walk for Python sources over a root derived from a test's own file."""

    root: str
    line: int
    pattern: str
    reaches: str


def python_source_scans(source: str, *, at: Path, package_root: Path) -> tuple[Scan, ...]:
    """Every walk in *source* that reads the package under test's own modules.

    *at* is where the file claims to live, so a synthetic file can be judged the
    same way a real one is, and *package_root* is the package it would reach
    from there. A walk enters the population when its root resolves from
    ``__file__`` and its pattern names Python sources; it is reported when that
    root is inside the package, or contains the package and is walked
    recursively.
    """
    tree = ast.parse(source)
    roots = _roots_derived_from_own_file(tree, at=at)
    found: list[Scan] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        scan = _walked_here(node, roots, package_root) or _handed_on_here(
            node, roots, package_root
        )
        if scan is not None:
            found.append(scan)
    return tuple(found)


def _walked_here(node: ast.Call, roots: dict[str, Path], package_root: Path) -> Scan | None:
    """*node* as a ``glob``/``rglob`` for Python sources over a derived root."""
    if not (isinstance(node.func, ast.Attribute) and node.func.attr in {"glob", "rglob"}):
        return None
    root = _resolve(node.func.value, roots)
    if root is None or not node.args:
        return None
    pattern = node.args[0]
    if not (isinstance(pattern, ast.Constant) and isinstance(pattern.value, str)):
        return None
    if not pattern.value.endswith(".py"):
        return None
    recursive = node.func.attr == "rglob" or "**" in pattern.value
    reaches = _reach(root, package_root, recursive=recursive)
    if reaches is None:
        return None
    return Scan(
        root=_name_of(node.func.value),
        line=node.lineno,
        pattern=pattern.value,
        reaches=reaches,
    )


def _handed_on_here(node: ast.Call, roots: dict[str, Path], package_root: Path) -> Scan | None:
    """*node* as a call handed a derived root that IS the package's own tree.

    The walk need not be spelled in the test. The second instance of this defect
    passes its root to ``beadloom.application.source_derivation.source_tree``'s
    ``python_files``, so a collector reading only ``rglob`` calls reports the
    file that the bead's own comment named as clean.

    Only a root that is the package, a directory inside it, or the ``src``
    directory holding it counts here. A repository root handed to a call is
    every `--project` argument in this suite and says nothing about modules.

    Path arithmetic is not a read: ``path.relative_to(SRC)`` and ``str(SRC)``
    re-express the root and open nothing, so the names in
    :data:`_PATH_ARITHMETIC` are passed over. Every other callee is treated as a
    reader, because the reading happens wherever the root ends up and a list of
    approved reader names is the thing this whole bead distrusts.
    """
    if _name_of(node.func).rpartition(".")[2] in _PATH_ARITHMETIC:
        return None
    for argument in node.args:
        root = _resolve(argument, roots)
        if root is None:
            continue
        if root == package_root or package_root in root.parents or root == package_root.parent:
            return Scan(
                root=_name_of(argument),
                line=node.lineno,
                pattern=f"handed to {_name_of(node.func)}()",
                reaches="inside the package under test",
            )
    return None


def _reach(root: Path, package_root: Path, *, recursive: bool) -> str | None:
    """How *root* reaches *package_root*, or ``None`` when it does not."""
    if root == package_root or package_root in root.parents:
        return "inside the package under test"
    if recursive and root in package_root.parents:
        return "a tree containing the package under test, walked recursively"
    return None


def _roots_derived_from_own_file(tree: ast.Module, *, at: Path) -> dict[str, Path]:
    """Each assigned name whose value resolves to a path built from ``__file__``.

    Followed transitively to a fixpoint: three of the four files this bead's
    predecessor moved bound an intermediate repository root first, and a reader
    of the single statement would have reported them clean.
    """
    bound: dict[str, list[ast.expr]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.setdefault(target.id, []).append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            bound.setdefault(node.target.id, []).append(node.value)

    resolved: dict[str, Path] = {}
    changed = True
    while changed:
        changed = False
        for name, values in bound.items():
            if name in resolved:
                continue
            for value in values:
                path = _resolve(value, resolved, own_file=at)
                if path is not None:
                    resolved[name] = path
                    changed = True
                    break
    return resolved


def _resolve(
    node: ast.expr, roots: dict[str, Path], *, own_file: Path | None = None
) -> Path | None:
    """*node* as the path it builds, or ``None`` when it builds none from here."""
    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return own_file
        return roots.get(node.id)
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _resolve(node.value, roots, own_file=own_file)
        return base.parent if base is not None else None
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
        if node.value.attr != "parents" or not isinstance(node.slice, ast.Constant):
            return None
        base = _resolve(node.value.value, roots, own_file=own_file)
        index = node.slice.value
        if base is None or not isinstance(index, int):
            return None
        return base.parents[index] if index < len(base.parents) else None
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "resolve":
            return _resolve(node.func.value, roots, own_file=own_file)
        if isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
            return _resolve(node.args[0], roots, own_file=own_file)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        base = _resolve(node.left, roots, own_file=own_file)
        if base is None or not isinstance(node.right, ast.Constant):
            return None
        part = node.right.value
        return base / part if isinstance(part, str) else None
    return None


def _name_of(node: ast.expr) -> str:
    """The name a walked expression is spelled with, for the failure message."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name_of(node.value)}.{node.attr}"
    return ast.dump(node)


def _pool() -> tuple[str, ...]:
    """The test files mutmut selects, read from where the runner reads them."""
    config = toml_loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = config["tool"]
    assert isinstance(tool, dict)
    mutmut = tool["mutmut"]
    assert isinstance(mutmut, dict)
    selection = mutmut["pytest_add_cli_args_test_selection"]
    assert isinstance(selection, list)
    return tuple(str(entry) for entry in selection)


def _scan_repository_file(relative: str) -> tuple[Scan, ...]:
    """Scan a file of this repository as it will be read under `mutmut run`."""
    path = _REPO_ROOT / relative
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


@pytest.fixture
def suite(tmp_path: Path) -> Path:
    """A tree arranged like this repository: a suite beside a package.

    The offenders below are written into it, so the guard is proven against a
    test that does not exist rather than against the four that do.
    """
    (tmp_path / "src" / "beadloom").mkdir(parents=True)
    (tmp_path / "src" / "beadloom" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "tests").mkdir()
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

        `tests/test_one_part_of_ancestry_walk_serves_the_rule_engine.py` hands
        its root to `beadloom.application.source_derivation.source_tree`'s
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
            "from tests.package_under_test import PACKAGE_ROOT, modules_under\n"
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


class TestNoTestTheRunnerSelectsWalksThePackageItMutates:
    """The sweep, over the pool mutmut actually runs — tier one, no exceptions."""

    def test_the_pool_it_scans_is_the_runners_own_and_is_not_empty(self) -> None:
        """Stated because a sweep over an empty population passes silently."""
        pool = _pool()

        assert len(pool) > 100, len(pool)
        assert all((_REPO_ROOT / entry).is_file() for entry in pool)

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
            f"`tests/package_under_test.py`: {offenders}"
        )


class TestEveryOtherSelfScanningTestIsOnePyprojectLineAway:
    """Tier two: the shape outside the pool is declared, not ignored.

    The second instance of this defect arrived in a file nobody had swept and
    was survivable only because it was unselected. That is a property of
    `pyproject.toml` and not of the test, so the set is held rather than
    described.
    """

    def test_the_declared_set_is_what_the_repository_carries(self) -> None:
        carrying = {
            str(path.relative_to(_REPO_ROOT))
            for path in sorted(_REPO_ROOT.joinpath("tests").rglob("test_*.py"))
            if python_source_scans(
                path.read_text(encoding="utf-8"), at=path, package_root=PACKAGE_ROOT
            )
        }

        assert carrying == set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL), (
            "a test walks the package from a root built from its own file and "
            "nobody has classified it. Move it onto `tests/package_under_test.py`, "
            "or declare here what it walks and why selecting it would be safe — "
            f"undeclared {sorted(carrying - set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL))}, "
            f"gone {sorted(set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL) - carrying)}"
        )

    def test_the_declared_set_is_not_empty_and_none_of_it_is_selected(self) -> None:
        """Both halves in one place: the population is real, and it is unselected.

        An empty declared set would make the test above pass by asserting that
        nothing equals nothing.
        """
        pool = set(_pool())

        assert SELF_SCANNING_TESTS_OUTSIDE_THE_POOL
        assert set(SELF_SCANNING_TESTS_OUTSIDE_THE_POOL) & pool == set()
