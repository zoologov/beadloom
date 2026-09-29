"""A layer rule's reach is counted on a shape, and stated once in one wording.

The layer-reach unit layer (BDL-074 E1). :func:`reach_of` is pure by design — "so
the arithmetic is testable on a shape rather than on a database" — and so are the
three readers of its result: the finding :func:`population_statement` makes, the
filter :func:`stated_populations` applies for every surface, and the clause
:func:`population_phrase` writes. Every case below hands them plain mappings: no
index, no filesystem.

The graph is the smallest one that has all three answers an end can get: a node
with its own tier (``web``, ``store``), a node that inherits one through
``part_of`` (``cart``, inside ``web``), and a node in no tier at all (``loose``).
"""

from __future__ import annotations

from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    LayerReach,
    population_phrase,
    population_statement,
    reach_of,
    stated_populations,
)
from beadloom.graph.rules.layers import LayerPopulation
from beadloom.graph.rules.types import LayerDef, LayerRule

TIERS = (LayerDef(name="web", tag="tier-web"), LayerDef(name="store", tag="tier-store"))
PARENTS = {"cart": {"web"}}
TAGS = {"web": {"tier-web"}, "store": {"tier-store"}}


def _rule(edge_kind: str = "depends_on") -> LayerRule:
    return LayerRule(
        name="tier-order",
        description="web above store",
        layers=TIERS,
        enforce="top-down",
        edge_kind=edge_kind,
    )


def _reach(evaluated: int, skipped: int, edge_kind: str = "depends_on") -> LayerReach:
    return LayerReach(
        rule_name="tier-order",
        edge_kind=edge_kind,
        population=LayerPopulation(evaluated=evaluated, skipped_untagged=skipped),
    )


class TestTheReachIsCountedOverTheEdgesItIsHanded:
    """An edge is judged when both ends are in a tier, by their own tag or inherited."""

    def test_an_edge_between_two_tiered_nodes_is_evaluated(self) -> None:
        # Act
        reach = reach_of(_rule(), [("web", "store")], PARENTS, TAGS)

        # Assert
        assert (reach.population.evaluated, reach.population.skipped_untagged) == (1, 0)

    def test_an_end_that_inherits_its_tier_is_inside_the_population(self) -> None:
        # Act
        reach = reach_of(_rule(), [("cart", "store")], PARENTS, TAGS)

        # Assert
        assert reach.population.evaluated == 1

    def test_an_end_in_no_tier_is_skipped_and_counted(self) -> None:
        # Act
        reach = reach_of(_rule(), [("web", "store"), ("loose", "store")], PARENTS, TAGS)

        # Assert
        assert (reach.population.evaluated, reach.population.skipped_untagged) == (1, 1)
        assert reach.population.total == 2

    def test_the_reach_names_its_rule_and_its_edge_kind(self) -> None:
        # Act
        reach = reach_of(_rule(edge_kind="uses"), [], PARENTS, TAGS)

        # Assert
        assert (reach.rule_name, reach.edge_kind) == ("tier-order", "uses")

    def test_the_json_form_is_flat_and_carries_the_three_numbers(self) -> None:
        # Act
        payload = _reach(evaluated=3, skipped=2).to_dict()

        # Assert
        assert payload == {
            "rule": "tier-order",
            "edge_kind": "depends_on",
            "evaluated": 3,
            "total": 5,
            "skipped_untagged": 2,
        }


class TestThePopulationStatement:
    """One warning per rule, and only when some edge went unjudged."""

    def test_a_partial_reach_is_stated_as_a_warning_with_both_numbers(self) -> None:
        # Act
        (finding,) = population_statement(_rule(), _reach(evaluated=3, skipped=2))

        # Assert
        assert finding.rule_type == LAYER_POPULATION_RULE_TYPE
        assert finding.severity == "warn"
        assert finding.message == (
            "this rule evaluated 3 of 5 live `depends_on` edge(s) and skipped 2 "
            "for an end in no declared layer"
        )

    def test_the_statement_carries_the_rule_it_is_about(self) -> None:
        # Arrange
        rule = _rule()

        # Act
        (finding,) = population_statement(rule, _reach(evaluated=1, skipped=1))

        # Assert
        assert (finding.rule_name, finding.rule_description) == (rule.name, rule.description)

    def test_a_reach_of_nothing_is_still_stated(self) -> None:
        """Zero of N is where "found nothing" and "never looked" read the same."""
        # Act
        findings = population_statement(_rule(), _reach(evaluated=0, skipped=4))

        # Assert
        assert len(findings) == 1
        assert "evaluated 0 of 4" in findings[0].message

    def test_a_full_reach_says_nothing(self) -> None:
        # Act / Assert
        assert population_statement(_rule(), _reach(evaluated=5, skipped=0)) == []

    def test_a_rule_handed_no_edge_says_nothing(self) -> None:
        # Act / Assert
        assert population_statement(_rule(), _reach(evaluated=0, skipped=0)) == []


class TestOneWordingForEverySurface:
    """The clause every surface prints, and the filter every surface applies."""

    def test_the_phrase_names_the_rule_the_fraction_and_the_edge_kind(self) -> None:
        # Act
        phrase = population_phrase(_reach(evaluated=1, skipped=1))

        # Assert
        assert phrase == "tier-order judged 1 of 2 live depends_on edge(s)"

    def test_only_a_reach_with_a_denominator_is_stated(self) -> None:
        # Arrange
        handed_nothing = _reach(evaluated=0, skipped=0)
        full = _reach(evaluated=2, skipped=0)
        partial = _reach(evaluated=1, skipped=1)

        # Act
        stated = stated_populations([handed_nothing, full, partial])

        # Assert
        assert stated == [full, partial]
