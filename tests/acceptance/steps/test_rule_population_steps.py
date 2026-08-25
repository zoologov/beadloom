"""Step implementations for `features/rule_population.feature` (BDL-061, `.63`).

The steps arrange a graph and a suite on disk and run the real rule; nothing is
mocked, because a scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.rules import (
    NodeMatcher,
    ScenarioCoverageRule,
    evaluate_scenario_coverage_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/rule_population.feature")

FEATURE_DIR = "tests/acceptance/features"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path, "nodes": [], "violations": []}


@given(
    parsers.parse(
        "a graph with {features:d} feature nodes and {components:d} component nodes"
    )
)
def _graph(world: dict[str, Any], features: int, components: int) -> None:
    world["nodes"] = [(f"feat-{i}", "feature") for i in range(features)]
    world["nodes"] += [(f"comp-{i}", "component") for i in range(components)]
    # A suite that exists but binds nothing: an ABSENT suite stands the whole
    # rule down, and this scenario is about the population, not about liveness.
    path = world["root"] / FEATURE_DIR / "one.feature"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "@bead:beadloom-mr2l.63 @node:feat-0\nFeature: F\n"
        "  Scenario: the only one\n    Given a step\n",
        encoding="utf-8",
    )


@given("one feature node is reclassified as a component")
def _reclassify(world: dict[str, Any]) -> None:
    world["nodes"] = [
        (ref, "component" if ref == "feat-1" else kind) for ref, kind in world["nodes"]
    ]


@when("the scenario-coverage rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    conn = open_db(world["root"] / "graph.db")
    create_schema(conn)
    for ref_id, kind in world["nodes"]:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, '')", (ref_id, kind)
        )
    conn.commit()
    rule = ScenarioCoverageRule(
        name="scenario-coverage",
        description="behaviour carries an executable claim",
        for_matcher=NodeMatcher(kind="feature"),
        features=f"{FEATURE_DIR}/**/*.feature",
    )
    try:
        world["violations"] = evaluate_scenario_coverage_rules(
            conn, [rule], project_root=world["root"]
        )
    finally:
        conn.close()


def _population_statements(world: dict[str, Any]) -> list[str]:
    return [v.message for v in world["violations"] if "outside" in v.message]


@then(
    parsers.parse(
        "the run states that {inside:d} of {total:d} graph nodes are in the "
        "rule's population"
    )
)
def _states_population(world: dict[str, Any], inside: int, total: int) -> None:
    statements = _population_statements(world)
    assert len(statements) == 1, statements
    assert f"{inside} of {total} graph node(s)" in statements[0], statements[0]


@then(parsers.parse("it names the kind the {outside:d} nodes outside the population left by"))
def _names_the_kind(world: dict[str, Any], outside: int) -> None:
    [statement] = _population_statements(world)
    assert f"component ({outside})" in statement, statement


@then("the run makes no statement about nodes outside the population")
def _silent(world: dict[str, Any]) -> None:
    assert _population_statements(world) == []
