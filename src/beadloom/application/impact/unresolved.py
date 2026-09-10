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

``target-outside-the-sweep``
    A file the answer is about that does not lie under the swept root. Nothing
    it defines was read, so the caller axis has no population at all rather than
    an empty one.
``unreadable-target``
    A file the answer is about that this derivation could not read as Python: a
    document, or a module saved half-way through an edit. Nothing it defines was
    read, so the axes over it are unresolved rather than empty. BDL-UX #255 is
    the absence of this entry — a target that EXISTS and is not Python reached
    ``ast.parse`` and ended the command in a traceback, while an ABSENT target
    was answered in one sentence, so the worse failure belonged to the more
    plausible request.
``sweep-narrower-than-the-project``
    The swept root is not the project's source root, so every axis is an answer
    about a subtree. BDL-068 `.15` measured what its absence did: on a PEP 420
    tree the sweep narrowed to one subpackage and a caller one directory across
    read as ``none found.``, cleanly, with nothing to say the answer was partial.
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

from beadloom.application.source_derivation import (
    UNPARSEABLE,
    functions_in,
    module_tree,
    stdlib_names_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from beadloom.application.source_derivation import ModuleSweep

#: The dispatch this derivation cannot follow, by the name the source spells it.
_DYNAMIC_DISPATCH = "getattr"

#: The suffix this derivation reads. A target carrying any other one exists, is
#: a file and holds nothing an AST derivation can answer about.
_PYTHON_SUFFIX = ".py"


@dataclass(frozen=True)
class Unresolved:
    """One thing the derivation could not resolve, and where."""

    kind: str
    detail: str
    where: str = ""


def readable_targets(
    targets: frozenset[Path], spell: Callable[[Path], str]
) -> tuple[frozenset[Path], tuple[Unresolved, ...]]:
    """The targets this derivation can parse, and a gap for each one it cannot.

    *spell* renders a path the way the answer spells it, so the gap names the
    place a human would go to rather than an absolute path.

    The file is parsed here and again where its branches are read. That is the
    same trade :func:`~beadloom.application.source_derivation.sweep_modules`
    makes and for the same reason: a cache of what parsed would be a second
    thing that can disagree with the tree.
    """
    readable: set[Path] = set()
    gaps: list[Unresolved] = []
    for path in sorted(targets):
        reason = _why_it_is_not_python(path)
        if reason is None:
            readable.add(path)
            continue
        where = spell(path)
        gaps.append(
            Unresolved(
                kind="unreadable-target",
                detail=f"{where} could not be read as Python source: {reason}",
                where=where,
            )
        )
    return frozenset(readable), tuple(gaps)


def _why_it_is_not_python(path: Path) -> str | None:
    """Why *path* cannot be read as Python source, or ``None`` when it can.

    Two classes, one call. The suffix is checked first because a document is the
    request a reader of this flow actually makes, and reporting it as a
    ``SyntaxError`` at some line of prose would name a symptom of the wrong
    thing.
    """
    if path.suffix != _PYTHON_SUFFIX:
        spelt = path.suffix or "(none)"
        return f"its suffix is {spelt} and this derivation reads {_PYTHON_SUFFIX} source"
    try:
        module_tree(path)
    except UNPARSEABLE as failure:
        return f"{type(failure).__name__}: {failure}"
    return None


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
