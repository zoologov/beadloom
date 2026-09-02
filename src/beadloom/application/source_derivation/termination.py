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
import os
import sys
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
