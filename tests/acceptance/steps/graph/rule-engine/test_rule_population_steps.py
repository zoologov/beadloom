"""Steps for `graph/rule-engine/rule_population.feature` (BDL-061 `.63`; BDL-074 E1).

The steps state the graph; :class:`~tests.support.rule_engine_driver.CoveragePopulation`
writes it into an index beside a suite that binds one node, and runs the real
``scenario_coverage`` rule, whose population is ``kind: feature``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.rule_engine_driver import CoveragePopulation, Outcome

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/rule_population.feature")


@pytest.fixture()
def population(tmp_path: Path) -> CoveragePopulation:
    return CoveragePopulation(tmp_path)


@pytest.fixture()
def outcome() -> Outcome:
    return Outcome()


def _population_statements(outcome: Outcome) -> list[str]:
    return [m for m in outcome.run.messages() if "outside" in m]


@given(parsers.parse("a graph with {features:d} feature nodes and {components:d} component nodes"))
def _graph(population: CoveragePopulation, features: int, components: int) -> None:
    population.graph(features=features, components=components)


@given("one feature node is reclassified as a component")
def _reclassify(population: CoveragePopulation) -> None:
    population.reclassify("feat-1", "component")


@when("the scenario-coverage rule is evaluated")
def _evaluate(population: CoveragePopulation, outcome: Outcome) -> None:
    outcome.run = population.evaluate()


@then(
    parsers.parse(
        "the run states that {inside:d} of {total:d} graph nodes are in the rule's population"
    )
)
def _states_population(outcome: Outcome, inside: int, total: int) -> None:
    [statement] = _population_statements(outcome)
    assert f"{inside} of {total} graph node(s)" in statement, statement


@then(parsers.parse("it names the kind the {outside:d} nodes outside the population left by"))
def _names_the_kind(outcome: Outcome, outside: int) -> None:
    [statement] = _population_statements(outcome)
    assert f"component ({outside})" in statement, statement


@then("the run makes no statement about nodes outside the population")
def _silent(outcome: Outcome) -> None:
    assert _population_statements(outcome) == []
