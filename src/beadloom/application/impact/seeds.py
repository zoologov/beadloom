# beadloom:domain=application
# beadloom:feature=impact
"""Which names the answer is computed over, and the rule that chose them.

This module is the whole reason `impact` is safe to ship. BDL-068 `.3` measured
what happens without it: run over the tree of 2026-08-31, the same derivations
report TWO writers and FOUR branches when seeded with the commit point and NONE
and THREE when seeded with the function the first dev bead was changing — and the
second answer is clean, confident and wrong, with nothing in it to suggest a
fourth branch and a second writer exist. Three is the number that epic carried
for nine review passes.

An agent that reads widely because it does not know the boundary sometimes
stumbles onto the neighbouring shape; that is how several of BDL-067's findings
surfaced at all. An agent given a list trusts it and stops. So the seed is
DERIVED from the target and NAMED in the answer, and a target this rule finds no
sink for is reported as unresolved rather than answered over an empty set.

**The rule, in one sentence.** A seed is a name the target reaches through the
call graph — transitively, not only the names its own bodies call — whose OWN
body performs a declared effect directly.

Both halves are measurements rather than preferences, taken at `af26750d`:

- *transitively.* From `services/commands/setup.py` the first hop holds 71 names
  and not one body that serialises YAML; the forward closure holds 1277 and
  reaches the product's single commit point two hops down.
- *its own body.* 58 names reach a body that serialises YAML and exactly 3 do it
  themselves. Seeding on "reaches one" is how a first-hop rule returned eight
  names for that file and not the sink.

**Why `PUTS_BYTES_ON_DISK` is not one of the declared effects**, stated here
because leaving it out silently would be the same defect one level up. Two
reasons, the second the stronger. It does not contain this product's own commit
point: measured at `af26750d`, 268 names reach a body in that set and
`write_yaml_atomic` is not among them, because it puts its bytes down through
`os.fdopen(...).write` and `Path.replace` while the set spells `write_text`,
`write_bytes` and `open`. And it is not a sound predicate ALONE, because `open`
also READS — seeded on it, the file above yields nineteen sinks and 65
co-writers, most of them readers. BDL-068 `.1` already handed its narrowing to
`.7`; that gap is not repaired here and nothing is built on top of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.source_derivation import (
    LISTS_A_DIRECTORY,
    PARSES_YAML,
    SERIALISES_YAML,
    bodies_calling,
    called_names,
    functions_in,
    names_reached_from,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Set as AbstractSet
    from pathlib import Path

    from beadloom.application.source_derivation import FoundFunction, ModuleSweep

#: The name of the rule, carried in every answer so a reader can argue with it.
THE_SEED_RULE = "reaches-an-effect-sink"

#: The rule as one sentence, carried beside the name for the same reason.
THE_SEED_RULE_STATEMENT = (
    "A seed is a name the target reaches through the call graph — transitively, not only "
    "the names its own bodies call — whose own body performs a declared effect directly."
)


@dataclass(frozen=True)
class EffectRule:
    """One declared effect: what a body must do itself to be a sink."""

    #: The name the answer reports, e.g. ``serialises-yaml``.
    name: str
    #: What the rule claims, in the words a reader can check it against.
    statement: str
    #: The verbs a body must call. Matched on the last segment of the callee, so
    #: ``yaml.safe_dump`` and a ``safe_dump`` imported by name are one shape.
    verbs: frozenset[str]
    #: A second half the same body must also call. Empty when the first half is a
    #: sound predicate on its own.
    and_also: frozenset[str] = frozenset()


#: The declared effects, each a shape this repository has measured. The table is
#: deliberately short: an effect nobody has measured is a rule nobody can argue
#: with, and a wrong seed is the one thing this command can do that is worse than
#: not existing.
THE_EFFECT_RULES: tuple[EffectRule, ...] = (
    EffectRule(
        name="serialises-yaml",
        statement="the body turns data into YAML text itself",
        verbs=SERIALISES_YAML,
    ),
    EffectRule(
        name="reads-a-yaml-directory",
        statement="the body lists a directory AND parses YAML, both in one body",
        verbs=LISTS_A_DIRECTORY,
        and_also=PARSES_YAML,
    ),
)


@dataclass(frozen=True)
class Seed:
    """One name the target reaches whose own body performs a declared effect."""

    name: str
    path: Path
    lineno: int
    #: The effect rule that found it, so the answer says where the seed came from.
    effect: str


def sinks_under(sweep: ModuleSweep) -> dict[str, tuple[FoundFunction, str]]:
    """Every name in *sweep* whose own body performs a declared effect.

    Keyed by bare name, matching the call graph's own key. A name found by more
    than one rule keeps the first rule in the declared order, and the ambiguity
    is a name defined twice — which the unresolved population reports separately.
    """
    found: dict[str, tuple[FoundFunction, str]] = {}
    for rule in THE_EFFECT_RULES:
        for body in bodies_calling(sweep, rule.verbs, and_also=rule.and_also):
            found.setdefault(body.name, (body, rule.name))
    return found


def names_the_target_calls(sweep: ModuleSweep, targets: frozenset[Path]) -> frozenset[str]:
    """Every name called anywhere in the modules the target consists of."""
    return frozenset(
        name
        for path, tree in sweep.parsed
        if path in targets
        for function in functions_in(tree)
        for name in called_names(function)
    )


def seeds_for(
    sweep: ModuleSweep,
    *,
    first_hop: frozenset[str],
    calls: Mapping[str, AbstractSet[str]],
) -> tuple[Seed, ...]:
    """The seeds *first_hop* reaches, in a stable order.

    Empty is a real answer and it means the declared effects found nothing the
    target reaches. The caller must report that as unresolved rather than as a
    co-writer list of length zero: a clean list is trusted and stopped at.
    """
    reached = names_reached_from(calls, first_hop)
    sinks = sinks_under(sweep)
    return tuple(
        sorted(
            (
                Seed(name, body.path, body.lineno, effect)
                for name in reached & frozenset(sinks)
                for body, effect in [sinks[name]]
            ),
            key=lambda seed: seed.name,
        )
    )
