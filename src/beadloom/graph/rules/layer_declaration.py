# beadloom:domain=graph
# beadloom:feature=rule-engine
"""A layer the declaration names and no node is in, and how that is reported.

`validate_rules` checks that a ref_id a rule mentions exists. It had no
``LayerRule`` in its ``isinstance`` chain, and a layer rule mentions no ref_id:
it names TAGS, and a tag no node carries is the same class of mistake — the
declaration refers to something the graph does not hold. The rule keeps running
and keeps reporting green, and the direction check it performs is one step
shorter than the declaration reads.

The population this reports is the DECLARATION, not the graph. "16 of 362 edges
were judged" (:mod:`.layer_reach`) is a statement about how far the rule reached;
"the declaration names a layer nothing is in" is a statement about whether the
declaration describes this project at all. Two facts, two rule types, so a
counter that reports one cannot pick up the other.

**The predicate is written once and both surfaces ask it.** `validate_rules` is
a public API that answers into a list of warning strings; the evaluator answers
into a :class:`~beadloom.graph.rules.types.Violation` that every reader of
``evaluate_all`` receives, including the TUI panel and the debt report, which
never see a ``LintResult``. Two implementations of "which declared layer is
empty" would be free to disagree — the defect this epic is about, one level up.

**They differ in one stated way, and only one.** The evaluator is SILENT when
fewer than :data:`~beadloom.graph.rules.layers.MIN_POPULATED_LAYERS` layers are
populated AND the rule is inert, because
:func:`beadloom.graph.rules.liveness._layer_reasons` names the empty layers for
exactly that graph and reporting it twice is the affirm-it-twice defect this
project has filed before. **Both halves are needed since BDL-070 B5-fix**
(`beadloom-5tcc.6`): a rule whose one inhabited layer holds two peers that cross
is live, so liveness says nothing about it, and deferring on the layer count
alone would have dropped the report that two of three declared tiers are
inhabited by nobody (BDL-UX #296). `validate_rules` has no such neighbour —
liveness reaches it only for a rule kind it does not model — so it answers
unconditionally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.layers import MIN_POPULATED_LAYERS
from beadloom.graph.rules.types import Violation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from beadloom.graph.rules.types import LayerDef, LayerRule

#: The rule type a declaration statement carries. It is NOT ``layer``: a rule
#: that names an empty layer has decided nothing about an edge, and the counter
#: that reports layering violations must not pick this up. It is not
#: ``layer_population`` either — how far the rule reached and whether its
#: declaration describes this project are two different questions.
LAYER_DECLARATION_RULE_TYPE = "layer_declaration"


def layers_no_node_is_in(
    layers: Sequence[LayerDef],
    tags: Mapping[str, Collection[str]],
) -> tuple[str, ...]:
    """The declared layer tags no node in *tags* carries, in declaration order.

    Iterates the DECLARATION rather than the tags, so the answer is ordered by
    the file a person edits instead of by a dictionary's iteration order, and a
    node carrying two declared tags populates both of them.
    """
    carried = {tag for node_tags in tags.values() for tag in node_tags}
    return tuple(layer.tag for layer in layers if layer.tag not in carried)


def declaration_warnings(
    rule: LayerRule,
    tags: Mapping[str, Collection[str]],
) -> list[str]:
    """*rule*'s empty layers as ``validate_rules`` states them — one per rule.

    One warning naming every empty layer, not one warning per layer: the subject
    is the rule's declaration, and a reader asked to act on it acts on the file
    once.
    """
    empty = layers_no_node_is_in(rule.layers, tags)
    if not empty:
        return []
    named = ", ".join(f"'{tag}'" for tag in empty)
    return [
        f"Rule '{rule.name}' declares layer tag(s) {named} that no node carries "
        f"(not found in nodes table)"
    ]


def declaration_statement(
    rule: LayerRule,
    tags: Mapping[str, Collection[str]],
    *,
    can_fire: bool = True,
) -> list[Violation]:
    """*rule*'s empty layers as a finding, or nothing when there is none.

    Silent in two cases. When every declared layer holds a node there is nothing
    to say, and a line saying so on every run of every project is the noise that
    trains a reader to skip the one that matters. When fewer than
    :data:`~beadloom.graph.rules.layers.MIN_POPULATED_LAYERS` layers are
    populated AND *can_fire* is false, the rule checks nothing and liveness
    reports it as inert naming the same tags.

    *can_fire* is the caller's answer from
    :func:`~beadloom.graph.rules.layers.can_fire_on`, which is the predicate
    liveness decides inertness with. It is a parameter rather than a second
    computation here because this module answers from the declaration and the tag
    map alone, and it defaults to ``True`` so a caller that knows nothing about
    the edge set reports rather than hides the fact.
    """
    empty = layers_no_node_is_in(rule.layers, tags)
    if not empty:
        return []
    if not can_fire and len(rule.layers) - len(empty) < MIN_POPULATED_LAYERS:
        return []
    named = ", ".join(f"`{tag}`" for tag in empty)
    populated = len(rule.layers) - len(empty)
    return [
        Violation(
            rule_name=rule.name,
            rule_description=rule.description,
            rule_type=LAYER_DECLARATION_RULE_TYPE,
            severity="warn",
            file_path=None,
            line_number=None,
            from_ref_id=None,
            to_ref_id=None,
            message=(
                f"this rule declares {len(rule.layers)} layer(s) and {populated} of them "
                f"{'holds' if populated == 1 else 'hold'} a node: no node carries {named}, "
                f"so the direction this rule checks is shorter than the declaration reads"
            ),
            remediation=(
                f"tag a node with {named}, or drop the layer from the declaration — an "
                f"empty layer cannot be an end of any edge, so every rule about what may "
                f"depend on it is unenforceable while it stays"
            ),
        )
    ]
