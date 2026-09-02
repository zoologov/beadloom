# beadloom:domain=application
# beadloom:component=source-derivation
"""The callee of a call, spelled two ways, and every callee under a node.

This is the vocabulary the rest of the package is written in. Two spellings,
because two different questions are asked of one call:

- :func:`callee_name` drops what a call is an attribute of, because reachability
  is matched on bare names — ``project.bootstrap_project(...)`` and
  ``bootstrap_project(...)`` reach the same body and a scan that told them apart
  would report the second and walk past the first.
- :func:`dotted_name` keeps it, because "which object is being called" cannot be
  answered by ``exit`` alone: ``sys.exit`` and a local ``exit`` are two
  functions.

The ceiling, stated because it is real and inherited from the modules this was
lifted out of: a name is a name, not a resolved import. Two same-named functions
in one package are one name here.
"""

from __future__ import annotations

import ast


def callee_name(call: ast.Call) -> str:
    """The bare name a call names, ignoring what it is an attribute of.

    A call whose callee is neither a name nor an attribute — through a
    subscript, a lambda, or the result of another call — names nothing here and
    answers with the empty string.
    """
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def dotted_name(call: ast.Call) -> str:
    """The callee as the source writes it: ``sys.exit``, not ``exit``."""
    parts: list[str] = []
    node: ast.expr = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def called_names(node: ast.AST) -> set[str]:
    """Every callee name used anywhere under *node*, attribute calls by last segment.

    A callee that names nothing is not in the answer. The two copies this was
    lifted from disagreed about that — one carried the empty string in the set
    and one dropped it — and MEASURED on both call sites, the empty string never
    matched a seed, a verdict name or a writer, so the answers were identical.
    """
    return {
        name
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        for name in [callee_name(child)]
        if name
    }
