"""Step implementations for `features/layer_view_verdict.feature` (BDL-070 B4).

Against a real project directory, the real reindex, the real linter and the real
site data builder: each scenario writes a graph on disk and runs the shipped
code over it. Nothing is mocked, because a scenario that passes against a double
proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.graph.linter import lint
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE

from .tiered_project import TIERS, graph_with_peer_containers, write_tiered_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/layer_view_verdict.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "tiers": TIERS, "exempt": ""}


@given("a project whose layering is declared as two peer containers in one tier")
def _peer_containers(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_peer_containers()


@given(parsers.parse('the rules file excuses the crossing "{src} -> {dst}"'))
def _excused(world: dict[str, Any], src: str, dst: str) -> None:
    world["exempt"] = (
        "    exempt:\n"
        f"      - from: {src}\n"
        f"        to: {dst}\n"
        '        reason: "the two read one ledger and the read seam is not built yet"\n'
        '        until: "2030-01-01"\n'
    )


@when("the architecture view is built for the project")
def _build(world: dict[str, Any]) -> None:
    project = write_tiered_project(
        world["root"],
        nodes=world["nodes"],
        edges=world["edges"],
        tiers=world["tiers"],
        exempt=world["exempt"],
    )
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        data = build_architecture_view_data(conn, pages={})
    finally:
        conn.close()
    world["verdicts"] = {
        (str(edge["src"]), str(edge["dst"])): edge.get("violation")
        for edge in data["edges"]
        if isinstance(edge, dict) and edge.get("kind") == "depends_on"
    }
    world["violations"] = lint(project).violations


@then(parsers.parse('the edge "{src} -> {dst}" is drawn as a violation'))
def _drawn_red(world: dict[str, Any], src: str, dst: str) -> None:
    assert world["verdicts"][(src, dst)] is True


@then(parsers.parse('the edge "{src} -> {dst}" is drawn as healthy'))
def _drawn_healthy(world: dict[str, Any], src: str, dst: str) -> None:
    assert world["verdicts"][(src, dst)] is False


@then("the edges drawn as violations are the ones the linter reports")
def _same_set(world: dict[str, Any]) -> None:
    drawn = {edge for edge, verdict in world["verdicts"].items() if verdict is True}
    reported = {
        (v.from_ref_id, v.to_ref_id)
        for v in world["violations"]
        if v.rule_type == LAYER_EDGE_RULE_TYPE
    }
    assert drawn == reported
    assert drawn, "the fixture must contain a crossing, or the equality is vacuous"
