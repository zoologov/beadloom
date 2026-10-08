"""Steps for `application/site-generation/every_layer_rule_in_the_data_file.feature`.

BDL-080 S1b (`beadloom-kgh6`). Against a real project directory, the real
reindex, the real linter and the real site generator: each scenario writes a
graph with two layer rules on disk, generates the site from it with
`generate_site` — the node's source — and reads `public/architecture.data.json`,
the artifact `docs site` writes. Nothing is mocked.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.site.generate import generate_site
from beadloom.graph.linter import lint
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE
from tests.support.tiered_project import (
    graph_with_a_portal,
    slices_rule_yaml,
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/every_layer_rule_in_the_data_file.feature")

#: The site's published copy of the architecture view, under the site root.
_VIEW_DATA = "public/architecture.data.json"

#: A fixed instant for the one metrics point `generate_site` records.
_NOW = "2026-10-08T00:00:00+00:00"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {
        "root": tmp_path / "shop",
        "site": tmp_path / "site",
        "stray": False,
        "scope": None,
        "title": None,
    }


@given("a project with a backend layer rule and a frontend layer rule inside its portal")
def _two_rules(world: dict[str, Any]) -> None:
    world["stray"] = False


@given("two slices outside the portal carry the frontend's tags")
def _stray(world: dict[str, Any]) -> None:
    world["stray"] = True


@given(parsers.parse('the frontend\'s layer rule declares the scope "{scope}"'))
def _scoped(world: dict[str, Any], scope: str) -> None:
    world["scope"] = scope


@given(parsers.parse('the frontend\'s layer rule declares the title "{title}"'))
def _titled(world: dict[str, Any], title: str) -> None:
    world["title"] = title


@when("the site is generated for the project")
def _generate(world: dict[str, Any]) -> None:
    nodes, edges = graph_with_a_portal(stray_slices=world["stray"])
    project = write_tiered_project(
        world["root"],
        nodes=nodes,
        edges=edges,
        more_rules=slices_rule_yaml(scope=world["scope"], title=world["title"]),
    )
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        generate_site(conn, world["site"], project_root=project, now_ts=_NOW)
    finally:
        conn.close()
    world["data"] = json.loads((world["site"] / _VIEW_DATA).read_text(encoding="utf-8"))
    world["violations"] = lint(project).violations


def _node(world: dict[str, Any], ref_id: str) -> dict[str, Any]:
    nodes = {str(node["id"]): node for node in world["data"]["nodes"]}
    return dict(nodes[ref_id])


def _verdicts(world: dict[str, Any]) -> dict[tuple[str, str], object]:
    return {
        (str(edge["src"]), str(edge["dst"])): edge.get("violation")
        for edge in world["data"]["edges"]
        if edge.get("kind") == "depends_on"
    }


@then(
    parsers.parse(
        'the data file\'s layer rules are "{first}" over "{first_scope}" '
        'and "{second}" over "{second_scope}"'
    )
)
def _rules_and_scopes(
    world: dict[str, Any], first: str, first_scope: str, second: str, second_scope: str
) -> None:
    rules = [(rule["name"], rule["scope"]) for rule in world["data"]["layer_rules"]]
    assert rules == [(first, first_scope), (second, second_scope)]


@then(parsers.parse('the layers of "{rule}" carry their names as tokens: "{tokens}"'))
def _tokens(world: dict[str, Any], rule: str, tokens: str) -> None:
    (declared,) = [r for r in world["data"]["layer_rules"] if r["name"] == rule]
    assert [layer["token"] for layer in declared["layers"]] == tokens.split(", ")
    assert [layer["rank"] for layer in declared["layers"]] == list(range(len(declared["layers"])))
    assert declared["edge_kind"] == "depends_on"


@then(parsers.parse('the node "{ref_id}" is placed by "{rule}" at rank {rank:d}'))
def _placed(world: dict[str, Any], ref_id: str, rule: str, rank: int) -> None:
    node = _node(world, ref_id)
    assert (node["layer_rule"], node["layer_rule_rank"]) == (rule, rank)


@then(parsers.parse('the node "{ref_id}" is placed by no layer rule'))
def _unplaced(world: dict[str, Any], ref_id: str) -> None:
    node = _node(world, ref_id)
    assert (node["layer_rule"], node["layer_rule_rank"]) == ("", None)


@then(
    parsers.parse(
        'the node "{ref_id}" keeps the layer rank {rank:d} the first rule by name gives it'
    )
)
def _legacy_rank(world: dict[str, Any], ref_id: str, rank: int) -> None:
    assert _node(world, ref_id)["layer_rank"] == rank
    assert [layer["tag"] for layer in world["data"]["layers"]] == [
        "tier-web",
        "tier-core",
        "tier-store",
    ]


@then(parsers.parse('the edge "{src} -> {dst}" is drawn as a violation'))
def _drawn_red(world: dict[str, Any], src: str, dst: str) -> None:
    assert _verdicts(world)[(src, dst)] is True


@then(parsers.parse('the edge "{src} -> {dst}" is drawn as healthy'))
def _drawn_healthy(world: dict[str, Any], src: str, dst: str) -> None:
    assert _verdicts(world)[(src, dst)] is False


@then("the edges drawn as violations are the ones the linter reports")
def _same_set(world: dict[str, Any]) -> None:
    drawn = {edge for edge, verdict in _verdicts(world).items() if verdict is True}
    reported = {
        (v.from_ref_id, v.to_ref_id)
        for v in world["violations"]
        if v.rule_type == LAYER_EDGE_RULE_TYPE
    }
    assert drawn == reported
    # Both rules found something, so the equality is not one rule's verdict twice.
    reporting = {v.rule_name for v in world["violations"] if v.rule_type == LAYER_EDGE_RULE_TYPE}
    assert reporting == {"tier-order", "ui-slices"}


def _declared_rule(world: dict[str, Any], rule: str) -> dict[str, Any]:
    (declared,) = [r for r in world["data"]["layer_rules"] if r["name"] == rule]
    return dict(declared)


@then(parsers.parse('the data file\'s layer rule "{rule}" is titled "{title}"'))
def _rule_titled(world: dict[str, Any], rule: str, title: str) -> None:
    assert _declared_rule(world, rule)["title"] == title


@then(parsers.parse('the data file\'s layer rule "{rule}" carries no title'))
def _rule_untitled(world: dict[str, Any], rule: str) -> None:
    assert _declared_rule(world, rule)["title"] == ""
