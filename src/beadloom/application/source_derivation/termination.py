# beadloom:domain=application
# beadloom:component=source-derivation
"""Whether a statement ends the branch it sits in.

This is the only claim the branch walk makes about control flow, and a
terminator it fails to recognise does not fail anything — it is read as a
statement the branch continues past, so whatever is written below it counts as
reachable. That is not a hypothetical. MEASURED by the review of BDL-067 `.20`:
one defect read *guarded* when the branch left through `sys.exit` and *unguarded*
when it left through `return`, because the walk knew one word and not the other.

So the set is DERIVED rather than listed. A callable annotated `NoReturn` is the
language's own statement that control does not come back, and a helper written
tomorrow joins the terminator set by carrying the annotation. The two standard
exits predate annotations and are matched by identity instead.

The ceiling, stated because it is real: a way out this classifier cannot resolve
is read as a branch that carries on. A derivation over syntax cannot close that;
running the branches can, and that is what the behavioural half of any check
built on this is for.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import NoReturn

from beadloom.application.source_derivation.calls import dotted_name

#: The two exits that end a Python function without returning from it and carry
#: no return annotation at runtime, so they are resolved by IDENTITY.
THE_EXITS_THAT_CARRY_NO_ANNOTATION: tuple[object, ...] = (sys.exit, os._exit)

#: How `typing.NoReturn` reaches a derivation. A module using
#: ``from __future__ import annotations`` holds its return annotation as a
#: STRING at runtime, so comparing against the object alone would silently match
#: nothing.
THE_NO_RETURN_ANNOTATIONS: frozenset[object] = frozenset(
    {NoReturn, "NoReturn", "Never", "typing.NoReturn", "typing.Never"}
)


def never_returns(dotted: str, resolving_in: object) -> bool:
    """Whether calling *dotted* ends the function it is called from.

    The name is resolved through *resolving_in* — the module the source under
    examination lives in — and the object is ASKED. An unresolvable name is read
    as continuing, which is the ceiling this module's docstring states.
    """
    head, *rest = dotted.split(".")
    target: object | None = getattr(resolving_in, head, None)
    for part in rest:
        if target is None:
            return False
        target = getattr(target, part, None)
    if target is None:
        return False
    if any(target is exiting for exiting in THE_EXITS_THAT_CARRY_NO_ANNOTATION):
        return True
    annotations: dict[str, object] = getattr(target, "__annotations__", {})
    return annotations.get("return") in THE_NO_RETURN_ANNOTATIONS


def ends_the_branch(statement: ast.stmt, resolving_in: object) -> bool:
    """Whether nothing after *statement* runs in the branch it sits in.

    Three forms rather than two. Until BDL-067 `.21` this was ``Return | Raise``
    and a branch that wrote two graph files and left through ``sys.exit(0)`` read
    as guarded for two waves.
    """
    if isinstance(statement, ast.Return | ast.Raise):
        return True
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and never_returns(dotted_name(statement.value), resolving_in)
    )


def exit_forms(function: ast.AST, resolving_in: object) -> tuple[str, ...]:
    """Every distinct way *function* ends, as its own source spells it.

    Three forms, because :func:`ends_the_branch` knows three. Rendered from the
    source rather than classified into words, so ``sys.exit(0)`` and ``return``
    read as the branch wrote them and a reader can go and look.
    """
    return tuple(
        sorted(
            {
                ast.unparse(statement)
                for statement in ast.walk(function)
                if isinstance(statement, ast.stmt) and ends_the_branch(statement, resolving_in)
            }
        )
    )


@dataclass(frozen=True)
class ResolvedNames:
    """A namespace terminator names resolve through, and the names it could not bind.

    The unbound half is not a diagnostic, it is part of the answer. A name this
    namespace cannot bind is read by :func:`ends_the_branch` as a call the branch
    CARRIES ON past — so a `NoReturn` helper hiding behind an unbound name is an
    exit form the derivation does not list, and the only honest thing to do with
    that is say which names it is.
    """

    namespace: SimpleNamespace
    unbound: tuple[str, ...]


def _stdlib_object(module: str, attribute: str | None) -> object | None:
    """The named stdlib object, or ``None`` for anything outside the standard library.

    Only the standard library is imported. A project-local or third-party module
    would have to be executed to be asked, and a derivation that runs the tree it
    is reading is a derivation that can change it.
    """
    if module.split(".")[0] not in sys.stdlib_module_names:
        return None
    try:
        imported = importlib.import_module(module)
    except ImportError:
        return None
    return imported if attribute is None else getattr(imported, attribute, None)


def stdlib_names_of(tree: ast.Module) -> ResolvedNames:
    """Bind the module's imported names to their stdlib objects, and name the rest.

    The namespace is built from the source's OWN import statements, so what a
    terminator name means here is what it means in the module under examination
    rather than what it happens to mean in this process.
    """
    bound: dict[str, object] = {}
    unbound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")[0]
                local = alias.asname or head
                target = _stdlib_object(alias.name if alias.asname else head, None)
                if target is None:
                    unbound.add(local)
                else:
                    bound[local] = target
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local = alias.asname or alias.name
                target = _stdlib_object(node.module or "", alias.name)
                if target is None:
                    unbound.add(local)
                else:
                    bound[local] = target
    return ResolvedNames(SimpleNamespace(**bound), tuple(sorted(unbound)))
