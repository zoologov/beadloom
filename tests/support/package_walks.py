"""Which test files walk the package under test from a root built from their own location.

The collector behind ``tests/test_no_selected_test_reads_the_mutated_copy.py``
and its self-check: a test that derives a scan root from ``__file__`` and walks
it for Python sources reads ``mutants/src/beadloom`` when mutmut runs it, so it
reports mutmut's generated bodies as the package's own (BDL-UX #289). The
reasoning, and the two tiers the sweep enforces, are in that test's docstring.

Since BDL-074 B1 the suite finds the repository root through
:mod:`tests.support.repository_root`, so the collector follows a name imported
from ``tests.support`` into the module that binds it; a root built there from
``__file__`` reaches the mutated copy exactly as one built in the test does.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.support.repository_root import RepositoryRootNotFoundError, repository_root

if TYPE_CHECKING:
    from pathlib import Path

#: The package whose modules a test may take a root from (BDL-074 B1).
_SUPPORT_PACKAGE = "tests.support."

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
#: ``tests/support/package_under_test.py`` fails the sweep above it.
SELF_SCANNING_TESTS_OUTSIDE_THE_POOL: dict[str, str] = {
    "tests/self_check/architecture/test_one_part_of_ancestry_walk_serves_the_rule_engine.py": (
        "walks src/beadloom/graph/rules for the one part_of ancestry walk, as its "
        "origin does; visible since BDL-074 B1, when it stopped importing the root "
        "from a test module the collector did not follow"
    ),
    "tests/self_check/config/test_ci_consolidated_structure.py": (
        "reads the shipped workflow templates under onboarding/templates/, "
        "through tests/support/ci_workflows.py"
    ),
    "tests/self_check/config/test_decode_handlers.py": (
        "hands src/beadloom and tests/ to ruff under this repository's own rule selection"
    ),
    "tests/self_check/config/test_mutation_runner_scope.py": (
        "walks src/ for modules importing the runner"
    ),
    "tests/test_ci_windows_dimension.py": (
        "reads one shipped workflow template under onboarding/templates/"
    ),
    "tests/test_ci_locale_dimension.py": (
        "reads one shipped workflow template under onboarding/templates/, "
        "through tests/support/ci_workflows.py"
    ),
    "tests/test_decode_handlers.py": "walks src/beadloom for decode call sites",
    "tests/test_guards_boundary_escapes.py": (
        "reads three named modules of the guards seam and sabotages copies of them"
    ),
    "tests/test_locale_independent_io.py": "walks src/beadloom for ambient-encoding sites",
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


def _roots_derived_from_own_file(
    tree: ast.Module, *, at: Path, visiting: frozenset[Path] = frozenset()
) -> dict[str, Path]:
    """Each name bound to a path built from ``__file__``, here or in a support module.

    Followed transitively to a fixpoint: three of the four files this bead's
    predecessor moved bound an intermediate repository root first, and a reader
    of the single statement would have reported them clean.

    A name imported from ``tests.support`` is followed into that module and
    resolved there, from ITS file (BDL-074 B1). The suite finds the repository
    root one way now, through :mod:`tests.support.repository_root`, so a root
    built one import away is the common case; without this the collector would
    have gone blind on the day the suite stopped counting parents.
    """
    resolved: dict[str, Path] = _roots_imported_from_support(tree, at=at, visiting=visiting | {at})
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


def _roots_imported_from_support(
    tree: ast.Module, *, at: Path, visiting: frozenset[Path]
) -> dict[str, Path]:
    """Each name *tree* imports from a ``tests.support`` module that resolves there.

    The module is looked up beside *at*'s own suite — under the repository root
    found from *at* — so a synthetic tree is judged against its own support
    package and never against this repository's. A module that is not there,
    or one already being resolved (an import cycle), contributes nothing.
    """
    try:
        root = repository_root(at)
    except RepositoryRootNotFoundError:
        return {}
    found: dict[str, Path] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level or node.module is None:
            continue
        if not node.module.startswith(_SUPPORT_PACKAGE):
            continue
        module = root.joinpath(*node.module.split(".")).with_suffix(".py")
        if not module.is_file() or module in visiting:
            continue
        roots = _roots_derived_from_own_file(
            ast.parse(module.read_text(encoding="utf-8")), at=module, visiting=visiting
        )
        for alias in node.names:
            if alias.name in roots:
                found[alias.asname or alias.name] = roots[alias.name]
    return found


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
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == repository_root.__name__
            and node.args
        ):
            return _root_above(_resolve(node.args[0], roots, own_file=own_file))
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        base = _resolve(node.left, roots, own_file=own_file)
        if base is None or not isinstance(node.right, ast.Constant):
            return None
        part = node.right.value
        return base / part if isinstance(part, str) else None
    return None


def _root_above(start: Path | None) -> Path | None:
    """The root :func:`repository_root` finds from *start*, or ``None``."""
    if start is None:
        return None
    try:
        return repository_root(start)
    except RepositoryRootNotFoundError:
        return None


def _name_of(node: ast.expr) -> str:
    """The name a walked expression is spelled with, for the failure message."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name_of(node.value)}.{node.attr}"
    return ast.dump(node)
