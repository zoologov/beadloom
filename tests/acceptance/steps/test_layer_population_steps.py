"""Step implementations for `features/layer_population.feature` (BDL-070 A7).

Against a real project directory, the real reindex and the real linter: the
scenarios arrange a graph on disk and run the shipped code over it. Nothing is
mocked, because a scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint
from beadloom.graph.rule_engine import evaluate_all
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE, layer_rule_reach
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerRule

from .tiered_project import TIERS, graph_with, write_tiered_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from beadloom.graph.rules import Rule

scenarios("../features/layer_population.feature")


@pytest.fixture()
def world(tmp_path: Path) -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"root": tmp_path / "ledger", "conn": None}
    try:
        yield state
    finally:
        if state["conn"] is not None:
            state["conn"].close()


def _build(world: dict[str, Any]) -> Path:
    """Write and index the project the Given steps described."""
    project = write_tiered_project(
        world["root"], nodes=world["nodes"], edges=world["edges"], tiers=world["tiers"]
    )
    world["conn"] = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    world["rules"] = load_rules(project / ".beadloom" / "_graph" / "rules.yml")
    return project


def _layer_rule(rules: list[Rule]) -> LayerRule:
    return next(rule for rule in rules if isinstance(rule, LayerRule))


def _statements(world: dict[str, Any]) -> list[Any]:
    return [v for v in world["violations"] if v.rule_type == LAYER_POPULATION_RULE_TYPE]


@given("a project whose layering is declared as three tiers")
def _three_tiers(world: dict[str, Any]) -> None:
    world["tiers"] = TIERS


@given(
    parsers.parse(
        "{tiered:d} dependency edges between tiered nodes and {untiered:d} "
        "with an untiered end"
    )
)
def _graph(world: dict[str, Any], tiered: int, untiered: int) -> None:
    world["nodes"], world["edges"] = graph_with(
        tiered_edges=tiered, untiered_edges=untiered
    )


@when("the layer rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    project = _build(world)
    world["violations"] = lint(project).violations
    world["reach"] = layer_rule_reach(world["conn"], _layer_rule(world["rules"]))


@when("the evaluators are called the way a reader past lint calls them")
def _evaluate_without_lint(world: dict[str, Any]) -> None:
    """`evaluate_all` directly — the call the TUI panel and the debt report make."""
    project = _build(world)
    world["violations"] = evaluate_all(
        world["conn"], world["rules"], project_root=project
    )


@then(
    parsers.parse(
        "the run states that it evaluated {evaluated:d} of {total:d} dependency edges"
    )
)
def _states_evaluated(world: dict[str, Any], evaluated: int, total: int) -> None:
    [statement] = _statements(world)
    assert f"evaluated {evaluated} of {total} live `depends_on` edge(s)" in statement.message
    assert world["reach"].own_tags.evaluated == evaluated
    assert world["reach"].own_tags.total == total


@then(parsers.parse("it states that it skipped {skipped:d} for an end carrying no declared layer"))
def _states_skipped(world: dict[str, Any], skipped: int) -> None:
    [statement] = _statements(world)
    assert f"skipped {skipped} for an end carrying no layer tag of its own" in statement.message
    assert world["reach"].own_tags.skipped_untagged == skipped


@then(parsers.parse("the rule's reach reports {skipped:d} skipped edges"))
def _reach_reports_skipped(world: dict[str, Any], skipped: int) -> None:
    assert world["reach"].own_tags.skipped_untagged == skipped
    assert world["reach"].own_tags.evaluated == world["reach"].own_tags.total


@then("the run makes no statement about its population")
def _silent(world: dict[str, Any]) -> None:
    assert _statements(world) == []


@then("that reader receives the population statement")
def _reader_receives_it(world: dict[str, Any]) -> None:
    [statement] = _statements(world)
    assert "evaluated 3 of 5" in statement.message


@then("the statement is a warning even though the rule is declared an error")
def _it_is_a_warning(world: dict[str, Any]) -> None:
    [statement] = _statements(world)
    assert _layer_rule(world["rules"]).severity == "error"
    assert statement.severity == "warn"
