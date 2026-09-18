"""BDL-072 — the number the pruning protects, measured over the real package.

`beadloom-ey4m` took the deciding measurement against mutmut 3.7.0 itself: its
`write_all_mutants_to_file` over the 33 modules of this project's declared
mutation scope, then the failing guard's own collector over the result. Before
the fix that room read **14 pipe-split sites, 10 of them undeclared**; after it,
**4 — exactly what the package declares**. That check needs the runner
installed, so it is not a test, and what it established is a DISTINCTION rather
than a filter:

* mutmut leaves the declared function under its own name and its own body, and
  adds a decorator. `cells_of` is still there. Declining every name mutmut
  touched would report the site as GONE — a red with the opposite message and
  the same dead nightly;
* beside it sit `x_cells_of__mutmut_orig` and one `x_cells_of__mutmut_N` per
  mutant, and those are what must not enter a population.

This file holds both directions over the real package. The mutated copy is
built here rather than by the runner — `mutate_like_mutmut` applies the shapes
`tests/mutmut_copy.py` records from real output to every module of the declared
scope — so what is measured is this repository's own code, at the size the
nightly reads it, without a three-hour run. It is a PROXY and says so: the
verdict BDL-072 accepts is a dispatched `Mutation` run (`beadloom-e8m4`).
"""

from __future__ import annotations

import ast
import copy
from fnmatch import fnmatch
from pathlib import Path

import pytest

from tests.mutmut_copy import TRAMPOLINE_IMPORT
from tests.package_under_test import PACKAGE_ROOT, is_generated_name, modules_under
from tests.test_mutation_runner_scope import toml_loads
from tests.test_two_readers_of_one_markdown_table import (
    DECLARED_PIPE_SPLITS,
    _calls_with_owner,
    _pipe_split_sites,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: The separator mutmut mangles a METHOD with, where a function gets ``_``
#: (`mutmut/mutation/trampoline_templates.py:1`).
_METHOD_SEPARATOR = "ǁ"


def mutate_like_mutmut(source: str, *, mutants: int = 2) -> str:
    """*source* rewritten the way mutmut leaves a module it mutates.

    Every function gains the four things measured in real output: the decorator
    on the declared body, a verbatim ``__mutmut_orig`` copy, one
    ``__mutmut_<n>`` per mutant and the module-level dictionary that holds them.
    The mutant bodies are copies rather than mutations, because what is under
    test here is which NAMES reach a population — a guard that collects a call
    shape finds it in a copy exactly as it finds it in a mutant.
    """
    tree = ast.parse(source)
    generated: list[ast.stmt] = []
    for statement in list(tree.body):
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            generated.extend(_wrap(statement, stem=f"x_{statement.name}__mutmut", mutants=mutants))
        elif isinstance(statement, ast.ClassDef):
            for member in list(statement.body):
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                    stem = (
                        f"x{_METHOD_SEPARATOR}{statement.name}"
                        f"{_METHOD_SEPARATOR}{member.name}__mutmut"
                    )
                    statement.body.extend(_wrap(member, stem=stem, mutants=mutants))
    tree.body.extend(generated)
    tree.body.insert(0, ast.parse(TRAMPOLINE_IMPORT).body[0])
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _wrap(
    function: ast.FunctionDef | ast.AsyncFunctionDef, *, stem: str, mutants: int
) -> list[ast.stmt]:
    """Decorate *function* in place and return the definitions mutmut adds."""
    dictionary = f"mutants_{stem}"
    function.decorator_list.append(
        ast.Call(func=ast.Name(id="_mutmut_mutated", ctx=ast.Load()), args=[], keywords=[])
    )
    added: list[ast.stmt] = [ast.parse(f"{dictionary} = {{}}").body[0]]
    for name in (f"{stem}_orig", *(f"{stem}_{index + 1}" for index in range(mutants))):
        clone = copy.deepcopy(function)
        clone.name = name
        clone.decorator_list = []
        added.append(clone)
        added.append(ast.parse(f"{dictionary}[{name!r}] = {name}").body[0])
    return added


def declared_scope_modules() -> tuple[Path, ...]:
    """The package modules `only_mutate` selects, read from the runner's config.

    Matched against the package's own relative paths rather than the
    repository's, so the answer is the same wherever the package under test is
    installed — which is the half of this defect the helper exists for.
    """
    config = toml_loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = config["tool"]
    assert isinstance(tool, dict)
    mutmut = tool["mutmut"]
    assert isinstance(mutmut, dict)
    selected = mutmut["only_mutate"]
    assert isinstance(selected, list)
    declared = [str(pattern) for pattern in selected]
    assert all(pattern.startswith("src/beadloom/") for pattern in declared), declared
    patterns = [pattern.removeprefix("src/beadloom/") for pattern in declared]
    return tuple(
        path
        for path in modules_under(PACKAGE_ROOT)
        if any(fnmatch(path.relative_to(PACKAGE_ROOT).as_posix(), pattern) for pattern in patterns)
    )


@pytest.fixture(scope="module")
def mutated_package(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The whole package, copied, with its declared scope left as mutmut leaves it.

    Module-scoped because it rewrites every module of the package once and four
    tests read it. Nothing writes to it, so the tests stay independent of each
    other's order.
    """
    root = tmp_path_factory.mktemp("mutants") / "src" / "beadloom"
    scope = set(declared_scope_modules())
    for path in modules_under(PACKAGE_ROOT):
        source = path.read_text(encoding="utf-8")
        target = root / path.relative_to(PACKAGE_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            mutate_like_mutmut(source) if path in scope else source, encoding="utf-8"
        )
    return root


def _generated_function_names(root: Path) -> list[str]:
    """Every function under *root* that mutmut would have written, unpruned.

    *root* is a directory or one module, so a caller can ask the question about
    the whole copy or about the single file it is making a claim about.
    """
    return [
        node.name
        for path in (modules_under(root) if root.is_dir() else (root,))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and is_generated_name(node.name)
    ]


def _pipe_split_sites_without_pruning(root: Path) -> list[tuple[str, str]]:
    """The guard's collector with the one difference under test: a plain parse.

    Everything else is the guard's own code — the same call walker and the same
    shape — so the two measurements differ in `module_tree` and in nothing else.
    """
    sites: list[tuple[str, str]] = []
    for path in modules_under(root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for holder, call in _calls_with_owner(tree):
            func = call.func
            if not isinstance(func, ast.Attribute) or func.attr != "split":
                continue
            if len(call.args) != 1:
                continue
            argument = call.args[0]
            if isinstance(argument, ast.Constant) and argument.value == "|":
                sites.append((path.relative_to(root).as_posix(), holder))
    return sites


class TestTheRoomTheseTestsMeasureIn:
    """What the mutated copy is, stated before anything is concluded from it."""

    def test_the_declared_scope_is_the_runners_own_and_is_not_empty(self) -> None:
        """33 modules on 2026-09-18, and the number is read rather than written.

        `only_mutate` names fifteen targets, one of them a package; a test that
        spelled the count would go stale on the next target and pass.
        """
        scope = declared_scope_modules()

        assert len(scope) > 20, len(scope)
        assert scope[0].is_relative_to(PACKAGE_ROOT)

    def test_the_copy_holds_the_whole_package_and_not_the_scope_alone(
        self, mutated_package: Path
    ) -> None:
        """The guard walks the package; a copy of the scope alone would not be it.

        One of the four declared sites — `active_table/table.py` — is outside
        the declared scope, so a room built from the scope alone would report
        that site as gone and call it a pass.
        """
        copied = {path.relative_to(mutated_package) for path in modules_under(mutated_package)}
        real = {path.relative_to(PACKAGE_ROOT) for path in modules_under(PACKAGE_ROOT)}

        assert copied == real
        assert Path("application/active_table/table.py") in copied
        assert PACKAGE_ROOT / "application/active_table/table.py" not in declared_scope_modules()

    def test_every_module_of_the_declared_scope_carries_generated_names(
        self, mutated_package: Path
    ) -> None:
        """The room is genuinely mutated, so a green below is about the pruning.

        Without this, a copy that silently failed to rewrite anything would give
        the same four sites and read as a proof. The population it asks about is
        the scope modules that DECLARE a function, because mutmut has nothing to
        wrap in the ones that do not and an empty module would answer no here
        for a reason that says nothing.
        """
        wrappable = [path for path in declared_scope_modules() if _has_a_function(path)]
        unmutated = [
            path.relative_to(PACKAGE_ROOT).as_posix()
            for path in wrappable
            if not _generated_function_names(mutated_package / path.relative_to(PACKAGE_ROOT))
        ]

        assert wrappable, "no module of the declared scope declares a function"

        assert unmutated == []
        assert len(_generated_function_names(mutated_package)) > 100


class TestWhatTheGuardReadsInThatRoom:
    """Both directions of the distinction, over this repository's own code."""

    def test_without_the_pruning_the_generated_bodies_enter_the_population(
        self, mutated_package: Path
    ) -> None:
        """The failure as the nine nightlies reported it: undeclared sites.

        The arithmetic is stated rather than the totals, because a mutant count
        is mutmut's to decide: the unpruned reading is strictly larger, and
        every site it adds sits in a function mutmut would have written.
        """
        unpruned = _pipe_split_sites_without_pruning(mutated_package)
        undeclared = [site for site in unpruned if site not in DECLARED_PIPE_SPLITS]

        assert len(unpruned) > len(DECLARED_PIPE_SPLITS)
        assert undeclared, "the room reproduces nothing"
        assert all(is_generated_name(holder) for _, holder in undeclared), undeclared

    def test_the_pruned_population_is_exactly_what_the_package_declares(
        self, mutated_package: Path
    ) -> None:
        """The post-fix number, protected: 4, and each one the declaration's.

        This is the measurement `beadloom-ey4m` took against mutmut's own
        output. It is held as an equality, so a pruning that widened into real
        code fails here as loudly as one that stopped declining generated names.
        """
        pruned = _pipe_split_sites(mutated_package)

        assert set(pruned) == set(DECLARED_PIPE_SPLITS)
        assert len(pruned) == len(DECLARED_PIPE_SPLITS) == 4

    def test_the_declared_function_survives_its_own_decoration(
        self, mutated_package: Path
    ) -> None:
        """The direction a blunt fix gets wrong, read on the real module.

        `doc_sync/tables.py` is in the declared scope, so in this room
        `cells_of` carries `@_mutmut_mutated` and has generated twins. Dropping
        every name mutmut touched would take the declared site with them.
        """
        tables = mutated_package / "doc_sync" / "tables.py"
        twins = _generated_function_names(tables)

        assert [name for name in twins if name.startswith("x_cells_of__mutmut")]
        assert ("doc_sync/tables.py", "cells_of") in _pipe_split_sites(mutated_package)

    def test_a_module_outside_the_declared_scope_reads_as_it_does_on_the_tree(
        self, mutated_package: Path
    ) -> None:
        """mutmut mutates what `only_mutate` selects and copies the rest verbatim."""
        relative = Path("application/active_table/table.py")

        assert (mutated_package / relative).read_text(encoding="utf-8") == (
            PACKAGE_ROOT / relative
        ).read_text(encoding="utf-8")


def _has_a_function(path: Path) -> bool:
    """Whether *path* declares a function mutmut would have anything to wrap."""
    return any(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
    )
