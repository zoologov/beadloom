"""Step implementations for `features/scenario_coverage.feature` (BDL-061 S4).

The steps are deliberately thin: they arrange a graph and a suite on disk and run
the real rule. Nothing is mocked, because a scenario that passes against a double
proves the double (this epic's FAKES PROVE FAKES).

The module is named ``test_*`` so the default pytest collection picks the
scenarios up — the acceptance suite runs in `uv run pytest`, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    NodeMatcher,
    NonBehaviouralNode,
    ScenarioCoverageRule,
    evaluate_scenario_coverage_rules,
)
from beadloom.graph.scenarios import load_suite
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

import pytest

scenarios("../features/scenario_coverage.feature")
scenarios("../features/scenario_binding.feature")

FEATURE_DIR = "tests/acceptance/features"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path, "nodes": [], "declarations": [], "violations": []}


def _write_feature(root: Path, name: str, text: str) -> None:
    path = root / FEATURE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given(parsers.parse('a graph with the feature nodes "{first}" and "{second}"'))
def _two_nodes(world: dict[str, Any], first: str, second: str) -> None:
    world["nodes"] = [first, second]


@given(parsers.parse('a graph with the feature node "{only}"'))
def _one_node(world: dict[str, Any], only: str) -> None:
    world["nodes"] = [only]


@given(parsers.parse('an acceptance suite whose only scenario is tagged "{tags}"'))
def _suite_with_tags(world: dict[str, Any], tags: str) -> None:
    _write_feature(
        world["root"],
        "one.feature",
        f"{tags}\nFeature: F\n  Scenario: the only one\n    Given a step\n",
    )


@given("no acceptance suite at all")
def _no_suite(world: dict[str, Any]) -> None:
    world["suite_absent"] = True


@given(parsers.parse('"{node}" is declared non-behavioural because "{reason}"'))
def _declare(world: dict[str, Any], node: str, reason: str) -> None:
    world["declarations"].append(NonBehaviouralNode(node=node, reason=reason))


@given(parsers.parse('a feature file tagged "{tags}" with two scenarios'))
def _two_scenarios(world: dict[str, Any], tags: str) -> None:
    _write_feature(
        world["root"],
        "two.feature",
        f"{tags}\nFeature: F\n"
        "  Scenario: first\n    Given a step\n"
        "  Scenario: second\n    Given a step\n",
    )


@given(parsers.parse('a feature file that declares the language "{language}"'))
def _foreign_dialect(world: dict[str, Any], language: str) -> None:
    _write_feature(
        world["root"], "foreign.feature", f"# language: {language}\n機能: なにか\n"
    )


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when("the scenario-coverage rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    conn = open_db(world["root"] / "graph.db")
    create_schema(conn)
    for ref_id in world["nodes"]:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, 'feature', '')", (ref_id,)
        )
    conn.commit()
    rule = ScenarioCoverageRule(
        name="scenario-coverage",
        description="behaviour carries an executable claim",
        for_matcher=NodeMatcher(kind="feature"),
        non_behavioural=tuple(world["declarations"]),
    )
    try:
        world["violations"] = evaluate_scenario_coverage_rules(
            conn, [rule], project_root=world["root"]
        )
    finally:
        conn.close()


@when("the suite is read")
def _read_suite(world: dict[str, Any]) -> None:
    world["suite"] = load_suite(world["root"], f"{FEATURE_DIR}/**/*.feature")


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


def _text(world: dict[str, Any]) -> str:
    return "\n".join(
        f"{v.rule_type} {v.from_ref_id} {v.to_ref_id} {v.message}" for v in world["violations"]
    )


@then(parsers.parse('"{node}" is reported as carrying no scenario'))
def _reported_uncovered(world: dict[str, Any], node: str) -> None:
    reported = [v.from_ref_id for v in world["violations"] if "no scenario binds" in v.message]
    assert node in reported, _text(world)


@then(parsers.parse('"{node}" is not reported'))
def _not_reported(world: dict[str, Any], node: str) -> None:
    reported = [v.from_ref_id for v in world["violations"] if "no scenario binds" in v.message]
    assert node not in reported, _text(world)


@then("the scenario is reported as naming no bead")
def _no_bead(world: dict[str, Any]) -> None:
    assert any("names no bead" in v.message for v in world["violations"]), _text(world)


@then(parsers.parse('"{node}" is reported as not being a node in the graph'))
def _unknown_node(world: dict[str, Any], node: str) -> None:
    assert any(v.to_ref_id == node for v in world["violations"]), _text(world)


@then(parsers.parse('"{node}" is not reported as carrying no scenario'))
def _not_reported_uncovered(world: dict[str, Any], node: str) -> None:
    reported = [v.from_ref_id for v in world["violations"] if "no scenario binds" in v.message]
    assert node not in reported, _text(world)


@then(
    parsers.parse(
        'the run states that {excused:d} of {population:d} nodes is excused, '
        'naming "{reason}"'
    )
)
def _excused_stated(
    world: dict[str, Any], excused: int, population: int, reason: str
) -> None:
    """Accepted WITH A NAMED REASON — accepted in silence is a different promise."""
    statements = [
        v.message for v in world["violations"] if "excused as non-behavioural" in v.message
    ]
    assert len(statements) == 1, _text(world)
    assert f"{excused} of {population} node(s)" in statements[0], statements[0]
    assert reason in statements[0], statements[0]


@then("the rule reports that it could not fire")
def _inert(world: dict[str, Any]) -> None:
    assert any(v.rule_type == LIVENESS_RULE_TYPE for v in world["violations"]), _text(world)


@then("no node is reported as carrying no scenario")
def _no_node_findings(world: dict[str, Any]) -> None:
    assert not [v for v in world["violations"] if "no scenario binds" in v.message], _text(world)


@then(parsers.parse('both scenarios are bound to the node "{node}"'))
def _bound_node(world: dict[str, Any], node: str) -> None:
    scenarios_read = world["suite"].scenarios
    assert len(scenarios_read) == 2
    assert all(node in s.nodes for s in scenarios_read)


@then(parsers.parse('both scenarios are bound to the bead "{bead}"'))
def _bound_bead(world: dict[str, Any], bead: str) -> None:
    assert all(bead in s.beads for s in world["suite"].scenarios)


@then("the file is reported as unreadable")
def _unreadable(world: dict[str, Any]) -> None:
    assert [u.path for u in world["suite"].unreadable] == [
        f"{FEATURE_DIR}/foreign.feature"
    ]


@then("the suite contains no scenario from it")
def _no_scenarios(world: dict[str, Any]) -> None:
    assert world["suite"].scenarios == ()
