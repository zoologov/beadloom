# beadloom:domain=application
# beadloom:feature=impact
"""The four questions, answered over a derived seed set.

*Who else commits through the sink this target reaches*, *who else calls this
target*, *how many branches the enclosing command has* and *how many ways it
ends*. Each is read off the source; none of them is a fact of the architecture
graph, which is why this command is not a graph walk with a new name.

The one that matters most is the first, and it is worth saying why in the module
that computes it. BDL-067's second writer — a function the file under change
never called and never mentioned — sat outside its instrument for a whole epic
and its defect reached a fifth wave under 112 green tests. It is reachable in one
step from the sink, and unreachable from the function anyone was looking at.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.source_derivation import (
    call_sites_in,
    called_names,
    callers_among,
    exit_forms,
    functions_in,
    names_that_reach,
    stdlib_names_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from collections.abc import Set as AbstractSet
    from pathlib import Path

    from beadloom.application.source_derivation import FoundFunction


#: The seat a command's branches were read from: the target itself.
THE_TARGET_SEAT = "target"

#: The seat a command's branches were read from: a caller of the target that
#: this answer already named. The distinction is the whole of BDL-068 `.15`'s
#: MAJOR 2 — a branch count is a property of the function it is taken over, and
#: an answer that does not say which function that was is a number with no seat.
THE_CALLER_SEAT = "caller"


@dataclass(frozen=True)
class Branch:
    """One path through a command, named by the conditions it sits under."""

    #: The `if` conditions, outermost first, as the source spells them. The empty
    #: tuple is the fallthrough — the branch a binding-shaped count cannot see,
    #: and the one a human adopter meets first.
    guard: tuple[str, ...]
    callees: tuple[str, ...]
    linenos: tuple[int, ...]


@dataclass(frozen=True)
class Command:
    """One function in the target, its branches and every way it ends."""

    name: str
    path: Path
    lineno: int
    #: The graph node that owns the file this command is in, and the bounded
    #: context above it. A command is a found site like any other, so it carries
    #: its boundary rather than leaving the reader to look it up.
    node: str | None
    domain: str | None
    branches: tuple[Branch, ...]
    exits: tuple[str, ...]
    #: Whether the branches were narrowed to the calls that reach a seed. False
    #: means no seed was derived and every call was read, which is a different
    #: question with a different answer and must not be read as the same one.
    narrowed_to_the_seeds: bool
    #: Which seat this count was taken from — :data:`THE_TARGET_SEAT` or
    #: :data:`THE_CALLER_SEAT`. BDL-067 was told `bootstrap_project` had three
    #: branches, which was true, while the four branches of the command CALLING
    #: it were the ones the epic got wrong. Both counts now appear and each says
    #: whose it is.
    seat: str = THE_TARGET_SEAT


def co_writers(
    located: Mapping[FoundFunction, AbstractSet[str]], seed_names: frozenset[str]
) -> tuple[FoundFunction, ...]:
    """Every function whose own body calls one of the seeds.

    One step, deliberately. A function that reaches the sink through a helper is
    a caller of that helper, and the helper is in this list; widening to the
    whole reaching set would name most of a codebase and name nothing.
    """
    return callers_among(located, seed_names)


def callers_of_the_target(
    located: Mapping[FoundFunction, AbstractSet[str]],
    defined_in_target: frozenset[str],
    target_paths: frozenset[Path],
) -> tuple[FoundFunction, ...]:
    """Every function OUTSIDE the target whose body calls something the target defines."""
    return tuple(
        found
        for found in callers_among(located, defined_in_target)
        if found.path not in target_paths
    )


def commands_in(
    path: Path,
    *,
    seed_names: frozenset[str],
    calls: Mapping[str, AbstractSet[str]],
    owner: Callable[[Path], tuple[str | None, str | None]],
) -> tuple[Command, ...]:
    """Every function defined in *path*, with its branches and its exit forms.

    With seeds, a branch is a path that REACHES one of them, which is the
    question BDL-067 was asking. Without, every call is read instead, so a module
    whose axes live entirely inside it still gets an answer — and the command
    says which of the two it did rather than letting the reader assume.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    resolving_in = stdlib_names_of(tree).namespace
    reaching = names_that_reach(calls, seed_names) if seed_names else frozenset()
    node, domain = owner(path)
    found: list[Command] = []
    for function in functions_in(tree):
        interesting = reaching if seed_names else frozenset(called_names(function))
        sites = call_sites_in(
            source, interesting, command=function.name, marker="", resolving_in=resolving_in
        )
        by_guard: dict[tuple[str, ...], list[tuple[str, int]]] = {}
        for site in sites:
            by_guard.setdefault(site.guard, []).append((site.callee, site.lineno))
        found.append(
            Command(
                name=function.name,
                path=path,
                lineno=function.lineno,
                node=node,
                domain=domain,
                branches=tuple(
                    Branch(
                        guard=guard,
                        callees=tuple(callee for callee, _ in reached),
                        linenos=tuple(lineno for _, lineno in reached),
                    )
                    for guard, reached in by_guard.items()
                ),
                exits=exit_forms(function, resolving_in),
                narrowed_to_the_seeds=bool(seed_names),
            )
        )
    return tuple(found)
