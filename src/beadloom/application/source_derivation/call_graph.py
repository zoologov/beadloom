# beadloom:domain=application
# beadloom:component=source-derivation
"""Who calls what, and what a name eventually reaches.

The question this answers is *who else calls this*, and it is answered from the
source rather than from a list somebody maintains. BDL-067 `.15` is the
measurement behind the shape: a scan seeded from one writer enumerated the
branches that reach THAT writer while its docstring promised the branches that
reach the graph, so a second writer — `import_docs` — sat outside the instrument
for a whole epic and its defect reached a fifth wave under 112 green tests.

Seeding from a name and growing the set is what makes a third writer arrive
inside the instrument on the day it is written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.source_derivation.calls import called_names
from beadloom.application.source_derivation.source_tree import (
    FoundFunction,
    functions_in,
    sweep_modules,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from collections.abc import Set as AbstractSet
    from pathlib import Path

    from beadloom.application.source_derivation.source_tree import ModuleSweep


def located_calls(sweep: ModuleSweep) -> dict[FoundFunction, frozenset[str]]:
    """Map every function in *sweep*, WITH ITS PLACE, to the names it calls.

    The located form is the primitive and every other shape here is derived from
    it: a finding that cannot name a file and a line is a finding nobody can act
    on, and two sweeps of one tree are two things that can disagree about it.
    """
    return {
        FoundFunction(function.name, path, function.lineno): frozenset(called_names(function))
        for path, tree in sweep.parsed
        for function in functions_in(tree)
    }


def calls_by_name(located: Mapping[FoundFunction, AbstractSet[str]]) -> dict[str, set[str]]:
    """The located call map, keyed by bare name instead of by place.

    Two same-named functions in one tree share an entry. That is the ceiling of
    matching on names rather than on resolved imports, and it errs toward
    reporting: a name that reaches a seed through EITHER body is reported as
    reaching it. The unresolved population names the collisions it caused.
    """
    calls: dict[str, set[str]] = {}
    for found, called in located.items():
        calls.setdefault(found.name, set()).update(called)
    return calls


def functions_to_their_calls(root: Path) -> dict[str, set[str]]:
    """Map every function defined under *root* to the names it calls."""
    return calls_by_name(located_calls(sweep_modules(root)))


def _closure(adjacency: Mapping[str, AbstractSet[str]], seeds: Iterable[str]) -> frozenset[str]:
    """The least fixed point: *seeds*, then anything adjacent to what is already in.

    One implementation for both directions. Reachability read backwards is
    reachability over the reversed edges, and writing that twice is how the two
    directions come to disagree about a tree they are both reading.
    """
    reached = set(seeds)
    growing = True
    while growing:
        growing = False
        for name, adjacent in adjacency.items():
            if name not in reached and adjacent & reached:
                reached.add(name)
                growing = True
    return frozenset(reached)


def reversed_calls(calls: Mapping[str, AbstractSet[str]]) -> dict[str, set[str]]:
    """Who calls whom, turned around: each name mapped to the names it is called BY."""
    callers: dict[str, set[str]] = {}
    for caller, called in calls.items():
        for callee in called:
            callers.setdefault(callee, set()).add(caller)
    return callers


def names_that_reach(
    calls: Mapping[str, AbstractSet[str]], seeds: Iterable[str]
) -> frozenset[str]:
    """The names whose call chains end in one of *seeds*, the seeds included."""
    return _closure(calls, seeds)


def names_reached_from(
    calls: Mapping[str, AbstractSet[str]], starts: Iterable[str]
) -> frozenset[str]:
    """The names *starts* can reach through the call graph, the starts included.

    The FORWARD direction, and it is the one a seed derivation needs. MEASURED at
    `af26750d`: from `services/commands/setup.py` the first hop holds 71 names
    and no body that serialises YAML at all, while the forward closure holds 1277
    and reaches the product's single commit point. A rule that stops at the
    target's own callees returns the first hop and not the sink.
    """
    return _closure(reversed_calls(calls), starts)


def callables_that_reach(root: Path, seed: str) -> frozenset[str]:
    """Names under *root* that end in a *seed* call, directly or transitively.

    A command reaching any of these names is that command reaching *seed*.
    """
    return names_that_reach(functions_to_their_calls(root), [seed])


def callers_among(
    located: Mapping[FoundFunction, AbstractSet[str]], names: Iterable[str]
) -> tuple[FoundFunction, ...]:
    """Every function in *located* whose own body calls one of *names*, in a stable order."""
    wanted = frozenset(names)
    return tuple(
        sorted(
            (found for found, called in located.items() if called & wanted),
            key=lambda found: (str(found.path), found.lineno),
        )
    )


def callers_of(root: Path, names: Iterable[str]) -> tuple[FoundFunction, ...]:
    """Every function under *root* whose own body calls one of *names*, with its place."""
    return callers_among(located_calls(sweep_modules(root)), names)


def direct_callers_of(root: Path, name: str) -> frozenset[str]:
    """The functions under *root* whose own body calls *name*."""
    return frozenset(found.name for found in callers_of(root, [name]))
