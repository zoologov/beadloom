"""Step implementations for `features/layer_declaration.feature` (BDL-070 A7).

Against a real project directory, the real reindex and the shipped lookups. The
architecture view is asked through `build_architecture_view_data`, which is what
the generated site calls, rather than through the private helper underneath it —
the scenario's subject is that two INSTRUMENTS agree, so both are asked the way
their own callers ask.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.graph.linter import lint
from beadloom.graph.rule_engine import layer_of, node_tags, part_of_parents
from beadloom.graph.rules.loader import load_rules, validate_rules
from beadloom.graph.rules.types import LayerRule

from .tiered_project import OUR_LAYER_PREFIX, TIERS, write_tiered_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from beadloom.graph.rules import Rule

scenarios("../features/layer_declaration.feature")

#: A layering with one edge that runs the wrong way, so the rule has something
#: to decide. `store -> web` is bottom-up under `enforce: top-down`.
_NODES: list[tuple[str, str, list[str]]] = [
    ("ledger", "service", []),
    ("web", "domain", ["tier-web"]),
    ("core", "domain", ["tier-core"]),
    ("store", "domain", ["tier-store"]),
]
_EDGES: list[tuple[str, str, str]] = [
    ("web", "ledger", "part_of"),
    ("core", "ledger", "part_of"),
    ("store", "ledger", "part_of"),
    ("web", "core", "depends_on"),
    ("core", "store", "depends_on"),
    ("store", "web", "depends_on"),
]

#: The node the fourth scenario adds: no tier of its own, inside one that has a
#: tier. This is the shape an adopter meets and this repository hides.
_INHERITING_NODE = "core-widget"


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
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    world["conn"] = conn
    world["rules"] = load_rules(project / ".beadloom" / "_graph" / "rules.yml")
    return project


def _layer_rule(rules: list[Rule]) -> LayerRule:
    return next(rule for rule in rules if isinstance(rule, LayerRule))


@given("a project whose layering is declared as three tiers")
def _three_tiers(world: dict[str, Any]) -> None:
    world["tiers"] = TIERS
    world["nodes"] = list(_NODES)
    world["edges"] = list(_EDGES)


@given("a node carrying no tier of its own inside a container that carries one")
def _inheriting_node(world: dict[str, Any]) -> None:
    world["nodes"].append((_INHERITING_NODE, "component", []))
    world["edges"].append((_INHERITING_NODE, "core", "part_of"))


@given("the declaration names a fourth tier no node carries")
def _fourth_tier(world: dict[str, Any]) -> None:
    world["tiers"] = (*TIERS, "tier-batch")


@when("the layer rule is evaluated")
def _evaluate(world: dict[str, Any]) -> None:
    world["project"] = _build(world)
    world["violations"] = lint(world["project"]).violations


@when("each instrument is asked what layer every node is in")
def _ask_both(world: dict[str, Any]) -> None:
    _build(world)
    conn = world["conn"]
    rule = _layer_rule(world["rules"])
    parents = part_of_parents(conn)
    tags = node_tags(conn).as_mapping()
    world["engine"] = {
        ref_id: layer_of(ref_id, rule.layers, parents, tags)
        for ref_id, *_ in world["nodes"]
    }
    view = build_architecture_view_data(conn)
    rendered = view["nodes"]
    assert isinstance(rendered, list)
    world["view"] = {str(node["id"]): node["layer_rank"] for node in rendered}


@when("the rules are validated against the graph")
def _validate(world: dict[str, Any]) -> None:
    _build(world)
    world["warnings"] = validate_rules(world["rules"], world["conn"])


@then("the two answers agree node for node")
def _they_agree(world: dict[str, Any]) -> None:
    assert world["engine"] == world["view"]
    assert set(world["engine"]) == {ref_id for ref_id, *_ in world["nodes"]}


@then("the inherited node is placed in its container's tier by both")
def _the_inherited_node(world: dict[str, Any]) -> None:
    """Non-vacuous: equal answers are worthless if both are `None` everywhere."""
    assert world["engine"][_INHERITING_NODE] == world["engine"]["core"]
    assert world["view"][_INHERITING_NODE] == TIERS.index("tier-core")


@then("the bottom tier depending on the top one is reported as an error")
def _the_violation_is_reported(world: dict[str, Any]) -> None:
    found = [v for v in world["violations"] if v.rule_type == "layer"]
    assert [(v.from_ref_id, v.to_ref_id) for v in found] == [("store", "web")]
    assert found[0].severity == "error"


@then("no layer tag this project ships appears anywhere in that project")
def _no_shipped_tag(world: dict[str, Any]) -> None:
    """The scenario's whole point: the rule read a declaration it could not know."""
    graph_dir = world["project"] / ".beadloom" / "_graph"
    for path in sorted(graph_dir.glob("*.yml")):
        assert OUR_LAYER_PREFIX not in path.read_text(encoding="utf-8"), path


@then("the validation names the tier no node carries")
def _names_the_empty_tier(world: dict[str, Any]) -> None:
    assert [w for w in world["warnings"] if "'tier-batch'" in w], world["warnings"]


@then("it says nothing about the three tiers that hold a node")
def _silent_about_the_populated(world: dict[str, Any]) -> None:
    joined = " ".join(world["warnings"])
    for tier in TIERS:
        assert tier not in joined, joined
