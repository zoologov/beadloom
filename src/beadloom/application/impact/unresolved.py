# beadloom:domain=application
# beadloom:feature=impact
"""What the derivation could not resolve, as a field of the answer.

The epic's rule, and the reason this module exists rather than being a paragraph
in a docstring: a derivation that omits what it could not parse hands an agent a
clean list, and a clean list is trusted and stopped at. Recall over precision —
the failure mode this command moves toward is false confidence, which is worse
than the ignorance it replaces.

Every entry names a KIND, so a consumer can act on the class rather than parse a
sentence, and a place, so a human can go and look. The kinds are the ways this
derivation is known to be blind:

``no-seed``
    No declared effect rule found a sink the target reaches, so the co-writer
    axis has no population at all. Reported instead of an empty list.
``no-graph-index``
    There was no index to read the boundary out of.
``unparsed-module``
    A file under the root that no sweep could read, so every axis has a hole
    exactly the size of that file.
``call-through-a-variable``
    A call whose callee is not a name or an attribute. The call graph cannot
    name it, so whatever it reaches is outside every answer here.
``dynamic-dispatch``
    A ``getattr`` call. The name it resolves to is a value at runtime.
``unresolved-terminator-name``
    A name the module imports from outside the standard library. A ``NoReturn``
    helper hiding behind one is an exit form this answer does not list, because
    asking the object would mean importing the tree under examination.
``name-defined-more-than-once``
    A name in this answer that has more than one definition under the root. The
    call graph is keyed by bare name, so the two definitions share an entry and
    a caller of either is reported as a caller of both.
``no-node-for-path``
    A found site the graph does not own, so its boundary is unknown rather than
    inside.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.source_derivation import functions_in, stdlib_names_of

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from beadloom.application.source_derivation import ModuleSweep

#: The dispatch this derivation cannot follow, by the name the source spells it.
_DYNAMIC_DISPATCH = "getattr"


@dataclass(frozen=True)
class Unresolved:
    """One thing the derivation could not resolve, and where."""

    kind: str
    detail: str
    where: str = ""


def unparsed_modules(sweep: ModuleSweep, root: Path) -> tuple[Unresolved, ...]:
    """Every file under the root no sweep could read."""
    return tuple(
        Unresolved(
            kind="unparsed-module",
            detail=module.reason,
            where=module.path.relative_to(root).as_posix(),
        )
        for module in sweep.unparsed
    )


def unnameable_calls(sweep: ModuleSweep, targets: frozenset[Path], root: Path) -> tuple[
    Unresolved, ...
]:
    """Calls in the target's own modules that the call graph cannot name.

    Scoped to the target rather than the whole tree on purpose: this is a
    statement about how far THIS answer reaches, and a tree-wide count would bury
    it under noise from files no axis touched.
    """
    found: list[Unresolved] = []
    for path, tree in sweep.parsed:
        if path not in targets:
            continue
        where = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == _DYNAMIC_DISPATCH:
                found.append(
                    Unresolved(
                        kind="dynamic-dispatch",
                        detail=ast.unparse(node),
                        where=f"{where}:{node.lineno}",
                    )
                )
            elif not isinstance(node.func, ast.Name | ast.Attribute):
                found.append(
                    Unresolved(
                        kind="call-through-a-variable",
                        detail=ast.unparse(node),
                        where=f"{where}:{node.lineno}",
                    )
                )
    return tuple(found)


def unresolved_terminators(
    sweep: ModuleSweep, targets: frozenset[Path], root: Path
) -> tuple[Unresolved, ...]:
    """Imported names in the target's modules that could hide a way out."""
    return tuple(
        Unresolved(
            kind="unresolved-terminator-name",
            detail=name,
            where=path.relative_to(root).as_posix(),
        )
        for path, tree in sweep.parsed
        if path in targets
        for name in stdlib_names_of(tree).unbound
    )


def ambiguous_names(
    sweep: ModuleSweep, names: Iterable[str], root: Path
) -> tuple[Unresolved, ...]:
    """The names IN THIS ANSWER that have more than one definition under the root."""
    wanted = frozenset(names)
    places: dict[str, list[str]] = {}
    for path, tree in sweep.parsed:
        for function in functions_in(tree):
            if function.name in wanted:
                places.setdefault(function.name, []).append(
                    f"{path.relative_to(root).as_posix()}:{function.lineno}"
                )
    return tuple(
        Unresolved(
            kind="name-defined-more-than-once",
            detail=name,
            where=", ".join(sorted(where)),
        )
        for name, where in sorted(places.items())
        if len(where) > 1
    )
