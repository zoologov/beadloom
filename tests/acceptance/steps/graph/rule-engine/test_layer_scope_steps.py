"""Steps for `graph/rule-engine/layer_scope.feature` (BDL-080 S1b, `beadloom-kgh6`).

Against a real project directory, the real reindex and the real linter: each
scenario writes a graph with two layer rules on disk and lints it. Nothing is
mocked, because a scenario that passes against a double proves the double.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE
from tests.support.tiered_project import (
    graph_with_a_portal,
    slices_rule_yaml,
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/layer_scope.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "stray": False, "scope": None}


@given("a project with a backend layer rule and a frontend layer rule inside its portal")
def _two_rules(world: dict[str, Any]) -> None:
    world["stray"] = False


@given("two slices outside the portal carry the frontend's tags")
def _stray(world: dict[str, Any]) -> None:
    world["stray"] = True


@given(parsers.parse('the frontend\'s layer rule declares the scope "{scope}"'))
def _scoped(world: dict[str, Any], scope: str) -> None:
    world["scope"] = scope


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    nodes, edges = graph_with_a_portal(stray_slices=world["stray"])
    project = write_tiered_project(
        world["root"],
        nodes=nodes,
        edges=edges,
        more_rules=slices_rule_yaml(scope=world["scope"]),
    )
    world["result"] = lint(project)


def _edge_findings(world: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    return [
        (v.rule_name, v.from_ref_id, v.to_ref_id)
        for v in world["result"].violations
        if v.rule_type == LAYER_EDGE_RULE_TYPE
    ]


@then(parsers.parse('"{src} -> {dst}" is reported by "{rule}"'))
def _reported(world: dict[str, Any], src: str, dst: str, rule: str) -> None:
    assert (rule, src, dst) in _edge_findings(world), _edge_findings(world)


@then(parsers.parse('no finding names "{src} -> {dst}"'))
def _not_reported(world: dict[str, Any], src: str, dst: str) -> None:
    assert all((s, d) != (src, dst) for _, s, d in _edge_findings(world))


@then(parsers.parse('"{rule}" judged {evaluated:d} of {total:d} live depends_on edges'))
def _population(world: dict[str, Any], rule: str, evaluated: int, total: int) -> None:
    (reach,) = [r for r in world["result"].layer_populations if r.rule_name == rule]
    assert (reach.population.evaluated, reach.population.total) == (evaluated, total)


@then(
    parsers.parse(
        '"{rule}" is reported as checking nothing because its scope "{scope}" names no node'
    )
)
def _inert(world: dict[str, Any], rule: str, scope: str) -> None:
    messages = [
        v.message
        for v in world["result"].violations
        if v.rule_name == rule and "cannot fire" in v.message
    ]
    assert any(f"scope '{scope}'" in m and "names no node" in m for m in messages), messages
