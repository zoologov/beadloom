"""Every place the package splits a line on the pipe, and which are declared table readers."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from tests.support.package_under_test import PACKAGE_ROOT, module_tree, modules_under

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The package under test, asked of the IMPORT and not of this file. Under
#: `mutmut run` the suite is copied beside the mutated sources, so a root built
#: from `__file__` pointed at the copy and this guard read mutmut's generated
#: bodies as undeclared pipe splits — nine nightlies scored 0 of 7187 mutants
#: (BDL-UX #289). `tests/support/package_under_test.py` answers both halves: where the
#: package is, and which of its names it actually declares.
_SRC = PACKAGE_ROOT


#: Every place in the package that turns a line into cells by splitting on a
#: pipe, as ``(module path, enclosing function)``, with what each one is. The
#: derivation below finds these from the source; this list is what a reader has
#: DECIDED about them, so a fourth site fails the guard rather than joining a
#: population nobody looked at.
DECLARED_PIPE_SPLITS: dict[tuple[str, str], str] = {
    ("doc_sync/tables.py", "cells_of"): "row-reader",
    ("application/active_table/table.py", "split_table_row"): "row-reader",
    ("application/guards/surface.py", "named_but_not_granted"): "not-a-table",
    ("application/guards/surface.py", "_bound"): "not-a-table",
}


def pipe_split_sites(root: Path = _SRC) -> list[tuple[str, str]]:
    """Every ``<expr>.split("|")`` under *root*, with the function holding it.

    A SHAPE and not a spelling: the call is found in the parsed tree, so a body
    that writes ``line.split('|')``, ``stripped.strip('|').split("|")`` or
    ``match.group(1).split(SEP)`` where ``SEP`` is the literal is found the same
    way. What it cannot see is a split through a variable holding the pipe, which
    is stated here rather than left for a reader to discover.

    Each module is read through ``module_tree``, so mutmut's generated bodies do
    not enter the population when this runs inside a mutation run. *root* is a
    parameter so the mimic in ``tests/support/mutmut_copy.py`` can be walked by the same
    code the guard uses.
    """
    sites: list[tuple[str, str]] = []
    for path in modules_under(root):
        tree = module_tree(path)
        for holder, call in calls_with_owner(tree):
            func = call.func
            if not isinstance(func, ast.Attribute) or func.attr != "split":
                continue
            if len(call.args) != 1:
                continue
            arg = call.args[0]
            if not (isinstance(arg, ast.Constant) and arg.value == "|"):
                continue
            sites.append((path.relative_to(root).as_posix(), holder))
    return sites


def calls_with_owner(tree: ast.AST) -> Iterator[tuple[str, ast.Call]]:
    """Every call in *tree*, paired with the name of the function holding it."""
    stack: list[tuple[str, ast.AST]] = [("<module>", tree)]
    while stack:
        owner, node = stack.pop()
        for child in ast.iter_child_nodes(node):
            name = owner
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = child.name
            if isinstance(child, ast.Call):
                yield owner, child
            stack.append((name, child))
