"""BDL-072 — the one place the suite asks where the package under test is.

The defect this locks down cost nine nights of measurement (BDL-UX #289). A
guard derived its scan root from its own file, mutmut copies the suite beside
the mutated sources, and so the guard read ``mutants/src/beadloom`` and reported
mutmut's generated bodies as undeclared code. The run stopped at stats and
scored 0 of 7187 mutants.

Two halves, and only both of them are a fix. Measured in mutmut 3.7.0 itself
(``__main__.py:262-276`` puts ``mutants/src`` on ``sys.path`` and removes the
original; ``:479`` runs the pool under ``change_cwd("mutants")``): the imported
package IS the mutated one, so resolving the root through it is necessary and
does not help on its own. What removes the defect is resolving the root through
the import AND declining the names mutmut generated.

**What these tests are and are not.** They run against a mimic built by
``tests/mutmut_copy.py`` from shapes mutmut actually emitted. That is a proxy: a
directory that looks like the room, not the room. The verdict BDL-072 accepts is
a dispatched ``Mutation`` run, and it is bead ``beadloom-e8m4``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import beadloom
from tests.mutmut_copy import (
    DECLARED_SITES_IN_THE_MIMIC,
    GENERATED_NAMES_IN_THE_MIMIC,
    MIMIC_MODULES,
    write_mutmut_copy,
)
from tests.package_under_test import (
    PACKAGE_ROOT,
    is_generated_name,
    module_tree,
    modules_under,
)

#: The tests moved onto the helper by ``beadloom-ey4m``, each with the name it
#: used to build from ``__file__``. Listed so the guard below states its
#: population instead of walking a set nobody decided.
MOVED_ONTO_THE_HELPER: dict[str, str] = {
    "test_two_readers_of_one_markdown_table.py": "_SRC",
    "test_guards_invocation.py": "_SRC",
    "test_the_reference_docs_state_the_population_shapes.py": "TEMPLATES_ROOT",
    "test_s2_move_regression.py": "_TPL",
}

_TESTS_DIR = Path(__file__).resolve().parent


class TestWhereThePackageUnderTestIs:
    """The root is the imported package's own directory, wherever that is."""

    def test_the_root_is_the_imported_package_and_not_a_path_from_here(self) -> None:
        assert Path(beadloom.__file__).resolve().parent == PACKAGE_ROOT
        assert (PACKAGE_ROOT / "__init__.py").is_file()

    def test_the_helper_derives_no_path_from_its_own_file(self) -> None:
        """The property, read from the helper's source rather than trusted.

        A helper that resolved ``__file__`` would answer about wherever it was
        copied to — which is the whole defect, one module further in.
        """
        source = (_TESTS_DIR / "package_under_test.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        own_location = [
            node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == "__file__"
        ]

        assert own_location == [], "the helper locates itself, so it answers about its copy"
        assert "beadloom.__file__" in source, "the root must come from the imported package"

    def test_it_walks_the_modules_under_a_root_in_a_stable_order(self, tmp_path: Path) -> None:
        package = write_mutmut_copy(tmp_path)

        found = modules_under(package)

        assert [path.relative_to(package).as_posix() for path in found] == sorted(MIMIC_MODULES)
        assert list(found) == sorted(found)


class TestWhichNamesAreThePackagesOwn:
    """mutmut's generated names are declined; the package's own are not."""

    @pytest.mark.parametrize("name", GENERATED_NAMES_IN_THE_MIMIC)
    def test_every_generated_name_the_mimic_carries_is_declined(self, name: str) -> None:
        assert is_generated_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "cells_of",
            "_bound",
            "named_but_not_granted",
            "split_table_row",
            "x_axis",
            "max_mutants",
            "_mutmut_trampoline",
        ],
    )
    def test_a_name_the_package_declares_is_not_declined(self, name: str) -> None:
        """Including ``x_axis`` — a real name starting with mutmut's own prefix.

        The predicate keys on ``__mutmut`` and not on the ``x_`` prefix alone,
        because a guard that dropped every ``x_*`` would silently shrink the
        population it is there to hold.
        """
        assert not is_generated_name(name)

    def test_no_name_the_real_package_declares_is_declined(self) -> None:
        """Measured over the package under test, so the predicate has a floor.

        A regex that decayed into matching everything would empty every
        population built on it, and every guard downstream would pass.
        """
        declared = [
            node.name
            for path in modules_under(PACKAGE_ROOT)
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        ]

        assert len(declared) > 1000, len(declared)
        assert [name for name in declared if is_generated_name(name)] == []


class TestReadingAModuleOfTheCopy:
    """The two halves together, over a directory shaped like mutmut's room."""

    def test_the_generated_definitions_do_not_reach_a_population(self, tmp_path: Path) -> None:
        """The failure itself, in the shape the guard reports it.

        Over the mimic the declared names are exactly the two the package
        writes; without the pruning they would be eleven, seven of them mutmut's.
        """
        package = write_mutmut_copy(tmp_path)

        defined = sorted(
            node.name
            for path in modules_under(package)
            for node in ast.walk(module_tree(path))
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        )

        assert defined == ["cells", "cells_of"]

    def test_a_declared_body_survives_the_pruning(self, tmp_path: Path) -> None:
        """The other direction, and the one a blunt fix gets wrong.

        mutmut leaves the declared function under its own name, so dropping
        every name it touched would report the site as GONE rather than as
        undeclared — a red with the opposite message and the same dead run.
        """
        package = write_mutmut_copy(tmp_path)

        sites = sorted(
            (path.relative_to(package).as_posix(), holder)
            for path in modules_under(package)
            for holder, call in _calls_with_owner(module_tree(path))
            if _is_a_pipe_split(call)
        )

        assert tuple(sites) == DECLARED_SITES_IN_THE_MIMIC

    def test_an_unmutated_module_is_unchanged_by_the_pruning(self) -> None:
        """On this tree nothing is generated, so the helper is a plain parse."""
        path = PACKAGE_ROOT / "doc_sync" / "tables.py"

        assert ast.dump(module_tree(path)) == ast.dump(ast.parse(path.read_text(encoding="utf-8")))


class TestTheTestsThatWalkThePackageStayOnTheHelper:
    """The regression lock for the four files this bead moved.

    Narrow on purpose: it names the four and the constant each one used to build
    from ``__file__``, so a revert is a red that says which file reverted. The
    sweep over every test file is a separate bead (``beadloom-hz0n``).
    """

    @pytest.mark.parametrize(("filename", "constant"), sorted(MOVED_ONTO_THE_HELPER.items()))
    def test_it_builds_no_source_root_from_its_own_file(
        self, filename: str, constant: str
    ) -> None:
        """The chain is followed, not the one statement.

        Three of the four built their root through an intermediate repository
        root, so a check that read the binding alone would have reported them
        clean while they still resolved into the copy.
        """
        tree = ast.parse((_TESTS_DIR / filename).read_text(encoding="utf-8"))
        bound = _module_level_bindings(tree)

        assert constant in bound, f"{filename} no longer binds {constant}"
        assert constant not in _derived_from_own_file(tree), (
            f"{filename} builds {constant} from its own location again, so under "
            f"mutation it reads the copied tree"
        )


def _module_level_bindings(tree: ast.Module) -> dict[str, ast.expr]:
    """Each module-level name assigned in *tree*, with the expression it got."""
    bound: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            bound[node.target.id] = node.value
    return bound


def _derived_from_own_file(tree: ast.Module) -> set[str]:
    """Every module-level name whose value reaches ``__file__``, transitively."""
    bound = _module_level_bindings(tree)
    derived: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, value in bound.items():
            if name in derived:
                continue
            referenced = {node.id for node in ast.walk(value) if isinstance(node, ast.Name)}
            if "__file__" in referenced or referenced & derived:
                derived.add(name)
                changed = True
    return derived


def _calls_with_owner(tree: ast.AST) -> list[tuple[str, ast.Call]]:
    """Every call in *tree*, paired with the function holding it."""
    found: list[tuple[str, ast.Call]] = []
    stack: list[tuple[str, ast.AST]] = [("<module>", tree)]
    while stack:
        owner, node = stack.pop()
        for child in ast.iter_child_nodes(node):
            name = owner
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = child.name
            if isinstance(child, ast.Call):
                found.append((owner, child))
            stack.append((name, child))
    return found


def _is_a_pipe_split(call: ast.Call) -> bool:
    """Whether *call* is ``<expr>.split("|")`` — the shape the guard collects."""
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "split":
        return False
    if len(call.args) != 1:
        return False
    arg = call.args[0]
    return isinstance(arg, ast.Constant) and arg.value == "|"
