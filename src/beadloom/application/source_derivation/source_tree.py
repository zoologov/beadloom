# beadloom:domain=application
# beadloom:component=source-derivation
"""A directory of Python files, read as functions, imports and definitions.

Every derivation in this package starts here: a root is a set of modules, a
module is a set of function bodies, and a body is where a shape is found. The
sweeps are deliberately re-read on each call rather than cached — a cache would
be a second thing that can disagree with the tree, which is the class this whole
package exists to remove.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: A function definition, either form. Both are matched everywhere in this
#: package: a derivation that read only `def` would walk past an `async def`
#: body holding the same shape.
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


class NoSuchFunctionError(LookupError):
    """A derivation was asked for a function the parsed source does not define."""


@dataclass(frozen=True)
class FoundFunction:
    """One function a sweep found, and where it is.

    The path is the one the sweep walked, so it can be re-read; a failure that
    names a file and a line names a place a human can go to.
    """

    name: str
    path: Path
    lineno: int


def python_files(root: Path) -> list[Path]:
    """Every Python file under *root*, in a stable order."""
    return sorted(root.rglob("*.py"))


def module_tree(path: Path) -> ast.Module:
    """The file at *path*, parsed, carrying its own name for error messages."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


@dataclass(frozen=True)
class UnparsedModule:
    """A file under a swept root that could not be parsed, and why.

    Every sweep in this package walks past it. A sweep that walked past it
    SILENTLY would hand its caller a clean list over an incomplete tree, which is
    the one failure mode this package is built against, so the file travels with
    the answer instead of being dropped.
    """

    path: Path
    reason: str


@dataclass(frozen=True)
class ModuleSweep:
    """Every module under a root, split into the ones that parsed and the ones that did not."""

    parsed: tuple[tuple[Path, ast.Module], ...]
    unparsed: tuple[UnparsedModule, ...]


def sweep_modules(root: Path) -> ModuleSweep:
    """Parse every Python file under *root*, keeping the failures rather than raising.

    A syntax error in one module is a hole in every sweep built on this one, and
    a hole a caller cannot see is worse than one it can. So the failures are
    returned beside the trees instead of ending the walk.
    """
    parsed: list[tuple[Path, ast.Module]] = []
    unparsed: list[UnparsedModule] = []
    for path in python_files(root):
        try:
            parsed.append((path, module_tree(path)))
        except (SyntaxError, ValueError, UnicodeDecodeError) as failure:
            unparsed.append(UnparsedModule(path, f"{type(failure).__name__}: {failure}"))
    return ModuleSweep(tuple(parsed), tuple(unparsed))


def functions_in(node: ast.AST) -> Iterator[FunctionNode]:
    """Every function defined anywhere under *node*, nested ones included."""
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            yield child


def function_named(name: str, tree: ast.Module) -> FunctionNode:
    """The first function called *name* in *tree*.

    A missing one is an error rather than an empty answer: every caller here is
    asking about a function it has already established exists, so `None` would
    travel as far as an assertion about nothing.
    """
    for function in functions_in(tree):
        if function.name == name:
            return function
    raise NoSuchFunctionError(f"no function named {name!r} in the parsed source")


def imports_in(path: Path) -> set[tuple[str, str]]:
    """Every ``from <module> import <name>`` pair in the file at *path*."""
    return {
        (node.module or "", alias.name)
        for node in ast.walk(module_tree(path))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def definitions_named(root: Path, name: str) -> list[str]:
    """Every definition of *name* under *root*, by path relative to it.

    The leading underscore is stripped before comparing, because that is exactly
    how a second copy gets written. BDL-067 `.21` found one invariant in two
    bodies, both spelled `_missing_parent_edges`: a scan matching the public name
    alone would have counted the one shared definition and neither of the two
    private copies it exists to find.
    """
    return [
        str(path.relative_to(root))
        for path in python_files(root)
        for function in functions_in(module_tree(path))
        if function.name.lstrip("_") == name
    ]
