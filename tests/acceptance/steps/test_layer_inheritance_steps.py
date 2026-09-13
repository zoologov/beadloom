"""Step implementations for `features/layer_inheritance.feature` (BDL-070 B3).

Against a real project directory, the real reindex and the real linter: each
scenario writes a graph on disk and runs the shipped code over it. Nothing is
mocked, because a scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE

from .tiered_project import (
    TIERS,
    graph_with,
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules.types import Violation

scenarios("../features/layer_inheritance.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "tiers": TIERS}


@given("a project whose layering is declared as two containers in different tiers")
def _nested_parts(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_nested_parts()


@given("a project whose layering is declared as two peer containers in one tier")
def _peer_containers(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_peer_containers()


@given("a project whose layering is declared as three tiers")
def _three_tiers(world: dict[str, Any]) -> None:
    world["tiers"] = TIERS


@given(
    parsers.parse(
        "{tiered:d} dependency edges between tiered nodes and {untiered:d} with an untiered end"
    )
)
def _flat_graph(world: dict[str, Any], tiered: int, untiered: int) -> None:
    world["nodes"], world["edges"] = graph_with(tiered_edges=tiered, untiered_edges=untiered)


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    project = write_tiered_project(
        world["root"], nodes=world["nodes"], edges=world["edges"], tiers=world["tiers"]
    )
    world["violations"] = lint(project).violations


def _layer_findings(world: dict[str, Any]) -> list[Violation]:
    return [v for v in world["violations"] if v.rule_type == "layer"]


def _judged(world: dict[str, Any]) -> set[tuple[str | None, str | None]]:
    return {(v.from_ref_id, v.to_ref_id) for v in _layer_findings(world)}


@then(parsers.parse('"{src} -> {dst}" is reported as a layering violation'))
def _reported_as_a_violation(world: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) in _judged(world), _judged(world)


@then(parsers.parse('the finding says that layer was inherited from "{container}"'))
def _names_the_container(world: dict[str, Any], container: str) -> None:
    assert any(f"inherited from '{container}'" in v.message for v in _layer_findings(world)), [
        v.message for v in _layer_findings(world)
    ]


@then(parsers.parse('"{src} -> {dst}" is reported as a same-layer crossing'))
def _reported_as_a_crossing(world: dict[str, Any], src: str, dst: str) -> None:
    reported = [
        v
        for v in _layer_findings(world)
        if (v.from_ref_id, v.to_ref_id) == (src, dst) and "Same-layer crossing" in v.message
    ]
    assert len(reported) == 1, [v.message for v in _layer_findings(world)]


@then(parsers.parse('no finding names "{src} -> {dst}"'))
def _not_reported(world: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) not in _judged(world)


@then(
    parsers.parse("the run states that it evaluated {evaluated:d} of {total:d} dependency edges")
)
def _states_evaluated(world: dict[str, Any], evaluated: int, total: int) -> None:
    statements = [v for v in world["violations"] if v.rule_type == LAYER_POPULATION_RULE_TYPE]
    assert len(statements) == 1
    assert f"evaluated {evaluated} of {total} live `depends_on` edge(s)" in statements[0].message


@then("no finding is a layering violation")
def _nothing_decided(world: dict[str, Any]) -> None:
    assert _layer_findings(world) == []
