# beadloom:domain=application
# beadloom:feature=impact
"""Answer four questions about a change from the source, over a DERIVED seed.

*Who else commits through the sink this target reaches*, *who else calls it*,
*how many branches the enclosing command has* and *how many ways it ends* — plus
the boundary from the graph, which says when a change leaves a bounded context,
and the population the derivation could not resolve.

**What this is not.** It is not `why` at a new name. Not one axis BDL-067 needed
is a fact of the architecture graph: the writers of a directory, the branches of
a command, its exit forms, the readers and their policies all live INSIDE one
node, and a graph walk would answer confidently and miss every one of them. The
graph supplies the boundary; the source supplies the sites.

**The one thing this command can do that is worse than not existing** is give a
clean, confident, wrong answer. An agent that reads widely because it does not
know the boundary occasionally stumbles onto the neighbouring shape; an agent
handed a list trusts it and stops. So the seed is derived from the target and
named in the answer, the rule that derived it is named beside it, and a target
the rule finds no sink for is reported as unresolved rather than answered over an
empty set. :mod:`.seeds` carries the measurement that made that the first
criterion instead of a caveat.
"""

from __future__ import annotations

from beadloom.application.impact.answer import (
    Boundary,
    ImpactAnswer,
    NoSuchTargetError,
    Population,
    Site,
    impact_of,
    package_root_of,
    source_root_of,
)
from beadloom.application.impact.axes import (
    THE_CALLER_SEAT,
    THE_TARGET_SEAT,
    Branch,
    Command,
)
from beadloom.application.impact.render import answer_to_dict, render_impact
from beadloom.application.impact.seeds import (
    THE_EFFECT_RULES,
    THE_SEED_RULE,
    THE_SEED_RULE_STATEMENT,
    EffectRule,
    Seed,
)
from beadloom.application.impact.unresolved import Unresolved

__all__ = [
    "THE_CALLER_SEAT",
    "THE_EFFECT_RULES",
    "THE_SEED_RULE",
    "THE_SEED_RULE_STATEMENT",
    "THE_TARGET_SEAT",
    "Boundary",
    "Branch",
    "Command",
    "EffectRule",
    "ImpactAnswer",
    "NoSuchTargetError",
    "Population",
    "Seed",
    "Site",
    "Unresolved",
    "answer_to_dict",
    "impact_of",
    "package_root_of",
    "render_impact",
    "source_root_of",
]
