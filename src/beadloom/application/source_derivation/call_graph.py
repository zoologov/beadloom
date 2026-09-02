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
    functions_in,
    module_tree,
    python_files,
)

if TYPE_CHECKING:
    from pathlib import Path


def functions_to_their_calls(root: Path) -> dict[str, set[str]]:
    """Map every function defined under *root* to the names it calls.

    Keyed by bare name, so two same-named functions in one tree share an entry.
    That is the ceiling of matching on names rather than on resolved imports,
    and it errs toward reporting: a name that reaches a seed through EITHER body
    is reported as reaching it.
    """
    calls: dict[str, set[str]] = {}
    for path in python_files(root):
        for function in functions_in(module_tree(path)):
            calls.setdefault(function.name, set()).update(called_names(function))
    return calls


def callables_that_reach(root: Path, seed: str) -> frozenset[str]:
    """Names under *root* that end in a *seed* call, directly or transitively.

    A least fixed point: seeded with one name, then grown with anything that
    calls something already in the set. A command reaching any of these names is
    that command reaching *seed*.
    """
    calls = functions_to_their_calls(root)
    reaching = {seed}
    growing = True
    while growing:
        growing = False
        for name, called in calls.items():
            if name not in reaching and called & reaching:
                reaching.add(name)
                growing = True
    return frozenset(reaching)


def direct_callers_of(root: Path, name: str) -> frozenset[str]:
    """The functions under *root* whose own body calls *name*."""
    return frozenset(
        caller
        for caller, called in functions_to_their_calls(root).items()
        if name in called
    )
