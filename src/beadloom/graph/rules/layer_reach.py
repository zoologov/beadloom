# beadloom:domain=graph
# beadloom:feature=rule-engine
"""How much of its edge set a layer rule actually judged, and how it says so.

``architecture-layers`` is this project's only machine check that dependencies
run in the declared direction, and it ships at ``severity: error``, so what it
evaluates decides whether ``main`` is mergeable. Measured on this repository at
``aa4bfad4`` it judged **16 of 362** live ``depends_on`` edges: it reads a node's
OWN tags and passes over every edge whose ends carry none. The green line said
``0 violations, 16 rules evaluated`` — the same words it would say for 362 of
362.

This module is what makes the two readable apart. It counts the rule's edge set
twice — once by own tags, which is what the rule decides on, and once by layer
membership inherited through ``part_of``, which is what the same declaration
would reach — and states the pair as a finding.

**A finding, not a clause in the summary line**, following
:func:`~beadloom.graph.rules.scenario_coverage._population_statement`: the TUI's
lint panel and the debt report call the evaluators directly and never see a
:class:`~beadloom.graph.linter.LintResult`, so a clause in the summary cannot
reach them.

**Always ``warn``, never the rule's declared severity.** ``architecture-layers``
declares ``error`` here and in every project that copied this rules file, and a
statement about a rule's REACH is not a boundary breach. Emitting it at the
declared severity would turn a green Gate red on upgrade for a graph nobody
changed, which is the one thing this epic's release order exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.rules.cycles import _live_lifecycle_clause
from beadloom.graph.rules.layers import layer_of, layer_population, own_layer_of
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import Violation

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Collection, Mapping, Sequence

    from beadloom.graph.rules.layers import LayerPopulation
    from beadloom.graph.rules.types import LayerRule

#: The rule type a population statement carries. It is NOT ``rule_liveness``:
#: ``lint`` counts a rule with a liveness finding as INERT, and a rule that
#: judged 16 edges is not a rule that could not fire. Two different facts, two
#: different types, so the counter that reports one cannot pick up the other.
LAYER_POPULATION_RULE_TYPE = "layer_population"


@dataclass(frozen=True)
class LayerReach:
    """What one layer rule could see, counted two ways.

    ``own_tags`` is the population the rule DECIDES on today: an edge is judged
    when both ends carry a declared layer tag themselves. ``inherited`` is the
    population the same declaration would reach if a node took its layer from
    the nearest ``part_of`` container that declares one. The difference between
    them is the part of the graph a green result says nothing about.
    """

    rule_name: str
    edge_kind: str
    own_tags: LayerPopulation
    inherited: LayerPopulation

    @property
    def unjudged(self) -> int:
        """Edges inheritance would reach that own tags do not."""
        return self.inherited.evaluated - self.own_tags.evaluated

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``lint --format json``.

        Both pairs of numbers, flattened: a machine reader that wants to watch
        the rule's reach change across Release B needs ``inherited_evaluated``
        beside ``evaluated``, and a nested object would make the common read —
        "how much did it judge" — two lookups instead of one. ``unjudged`` is
        derived and carried anyway, because a consumer that recomputes a
        subtraction is a second place the arithmetic can be wrong.
        """
        return {
            "rule": self.rule_name,
            "edge_kind": self.edge_kind,
            "evaluated": self.own_tags.evaluated,
            "total": self.own_tags.total,
            "skipped_untagged": self.own_tags.skipped_untagged,
            "inherited_evaluated": self.inherited.evaluated,
            "inherited_total": self.inherited.total,
            "unjudged": self.unjudged,
        }


def part_of_parents(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Each node's DIRECT ``part_of`` containers.

    Lifecycle is deliberately not filtered, matching
    :func:`beadloom.graph.import_resolver._part_of_ancestors`: containment is
    structure rather than a live dependency, and two readers filtering it
    differently would be a second answer to "what is this node inside" — the
    exact shape this epic was opened to remove. A node that is ``part_of``
    itself, the convention this project's root service follows, is not its own
    parent.
    """
    parents: dict[str, set[str]] = {}
    for row in conn.execute("SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"):
        child, parent = str(row[0]), str(row[1])
        if child != parent:
            parents.setdefault(child, set()).add(parent)
    return parents


def live_edges_of_kind(conn: sqlite3.Connection, edge_kind: str) -> list[tuple[str, str]]:
    """The live edges of *edge_kind* — the set a layer rule is handed.

    ``planned`` / ``deprecated`` / ``dead`` edges are intent or history, not a
    live layering violation, and this reads the same set the rule decides over
    so the population and the verdict cannot be taken from different graphs.
    """
    life_clause, life_params = _live_lifecycle_clause(conn)
    rows = conn.execute(
        f"SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = ?{life_clause}",  # noqa: S608
        (edge_kind, *life_params),
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def reach_of(
    rule: LayerRule,
    edges: Sequence[tuple[str, str]],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> LayerReach:
    """Count *edges* both ways, without reading the graph.

    Pure, so the arithmetic is testable on a shape rather than on a database,
    and so the evaluator can pass the edge list it has already fetched instead
    of fetching it again.
    """
    return LayerReach(
        rule_name=rule.name,
        edge_kind=rule.edge_kind,
        own_tags=layer_population(edges, lambda ref_id: own_layer_of(ref_id, rule.layers, tags)),
        inherited=layer_population(
            edges, lambda ref_id: layer_of(ref_id, rule.layers, parents, tags)
        ),
    )


def layer_rule_reach(conn: sqlite3.Connection, rule: LayerRule) -> LayerReach:
    """The reach of *rule* over the graph in *conn*.

    The entry point for a reader that wants the numbers without running the
    rule — the lint summary, the Gate line, the TUI panel and the agent prime
    header all state a population they do not decide.
    """
    return reach_of(
        rule,
        live_edges_of_kind(conn, rule.edge_kind),
        part_of_parents(conn),
        node_tags(conn).as_mapping(),
    )


def layer_rule_reaches(
    conn: sqlite3.Connection, rules: Sequence[LayerRule]
) -> list[LayerReach]:
    """The reach of every rule in *rules*, in declaration order.

    The containment map and the tag map are read ONCE for the whole list rather
    than once per rule, which is what :func:`layer_rule_reach` would do called
    in a loop. The two agree rule by rule — they hand the same three inputs to
    :func:`reach_of` — and a test holds that, because "the fast one" and "the
    correct one" being different functions is how a population comes to depend
    on which caller asked.
    """
    if not rules:
        return []
    parents = part_of_parents(conn)
    tags = node_tags(conn).as_mapping()
    return [
        reach_of(rule, live_edges_of_kind(conn, rule.edge_kind), parents, tags)
        for rule in rules
    ]


def population_statement(rule: LayerRule, reach: LayerReach) -> list[Violation]:
    """State how much of its edge set the rule judged — once per rule.

    Silent in two cases, each for its own reason. When the rule was handed no
    edge of its kind there is no population to report, and a rule that can look
    at nothing is already the subject of a liveness finding; saying it twice is
    the affirm-it-twice defect this project has filed before. When the rule
    reached every edge it was handed there is nothing it could not see, and a
    line saying so on every run of every project is the noise that trains a
    reader to skip the one that matters.

    A rule that reached NOTHING is not silent: zero of N is the case where "the
    rule found nothing wrong" and "the rule never looked" are the same output,
    and it is reported once for the rule rather than once for each edge that
    went unjudged.
    """
    if reach.own_tags.total == 0 or reach.own_tags.skipped_untagged == 0:
        return []
    message = (
        f"this rule evaluated {reach.own_tags.evaluated} of {reach.own_tags.total} "
        f"live `{reach.edge_kind}` edge(s) and skipped {reach.own_tags.skipped_untagged} "
        f"for an end carrying no layer tag of its own"
    )
    if reach.unjudged > 0:
        message += (
            f"; inheriting layer membership through `part_of` would reach "
            f"{reach.inherited.evaluated} of {reach.inherited.total}, so "
            f"{reach.unjudged} edge(s) pass this rule today by not being looked at"
        )
    return [
        Violation(
            rule_name=rule.name,
            rule_description=rule.description,
            rule_type=LAYER_POPULATION_RULE_TYPE,
            severity="warn",
            file_path=None,
            line_number=None,
            from_ref_id=None,
            to_ref_id=None,
            message=message,
            remediation=(
                f"read the first number as the reach a green result claims: the other "
                f"{reach.own_tags.skipped_untagged} edge(s) were not judged, which is a "
                f"different fact from being clean — tag the ends that carry no layer, or "
                f"place them inside a container that declares one"
            ),
        )
    ]


def stated_populations(reaches: Sequence[LayerReach]) -> list[LayerReach]:
    """The reaches there is anything to say about.

    A rule handed no edge of its kind has no denominator: liveness already
    reports that it could not fire, and a second way of saying it is the
    affirm-it-twice shape this project has filed before. Every surface filters
    the same way through this one function, so "nothing to state" cannot mean
    one thing on the Gate line and another in `prime`.
    """
    return [reach for reach in reaches if reach.own_tags.total]


def population_phrase(reach: LayerReach) -> str:
    """One reach as a clause, for a surface that states it in passing.

    The short form, as distinct from the finding's message: a clause that sits
    on a line somebody is already reading names the rule, the fraction and the
    edge kind and stops, while the finding has room to say what the unjudged
    edges mean and what to do about them.

    Written ONCE because six surfaces state it — the rich summary line, the
    GitHub notice, the Gate's lint step, `prime`'s health line, the debt report
    and the MCP tool's JSON. Six wordings of one fact is the shape this epic
    exists to remove, at the scale of a sentence.
    """
    return (
        f"{reach.rule_name} judged {reach.own_tags.evaluated} of "
        f"{reach.own_tags.total} live {reach.edge_kind} edge(s)"
    )
