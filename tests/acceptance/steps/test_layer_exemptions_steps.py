"""Step implementations for `features/layer_exemptions.feature` (BDL-070 B2).

Against a real project directory, the real reindex and the real linter: each
scenario writes a `rules.yml` with an `exempt:` block on disk and runs the
shipped loader and evaluator over it. Nothing is mocked, because a scenario that
passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import LintError, lint
from beadloom.graph.rules.layer_reach import live_edges_of_kind, part_of_parents
from beadloom.graph.rules.layers import same_layer_crossings
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerRule

from .tiered_project import graph_with_peer_containers, write_tiered_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

scenarios("../features/layer_exemptions.feature")


@pytest.fixture()
def world(tmp_path: Path) -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"root": tmp_path / "ledger", "conn": None, "exempt": ""}
    try:
        yield state
    finally:
        if state["conn"] is not None:
            state["conn"].close()


def _build(world: dict[str, Any]) -> Path:
    """Write and index the project the Given steps described."""
    project = write_tiered_project(
        world["root"],
        nodes=world["nodes"],
        edges=world["edges"],
        exempt=world["exempt"],
    )
    world["conn"] = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    return project


@given("a project whose layering is declared as two peer containers in one tier")
def _peer_containers(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_peer_containers()


@given(parsers.parse('the rule excuses "{src} -> {dst}" until "{until}"'))
def _excused(world: dict[str, Any], src: str, dst: str, until: str) -> None:
    world["exempt"] = (
        "    exempt:\n"
        f"      - from: {src}\n"
        f"        to: {dst}\n"
        '        reason: "the two read one ledger, and the read seam is not built yet"\n'
        f'        until: "{until}"\n'
    )


@given(parsers.parse('the rule excuses "{src} -> {dst}" with no reason'))
def _excused_without_reason(world: dict[str, Any], src: str, dst: str) -> None:
    world["exempt"] = (
        "    exempt:\n"
        f"      - from: {src}\n"
        f"        to: {dst}\n"
        '        until: "2030-01-01"\n'
    )


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    project = _build(world)
    try:
        world["violations"] = lint(project).violations
    except LintError as exc:
        world["violations"] = []
        world["error"] = str(exc)


@when("the same-layer crossings are read off the graph")
def _crossings(world: dict[str, Any]) -> None:
    project = _build(world)
    rule = next(
        r
        for r in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(r, LayerRule)
    )
    world["rule"] = rule
    world["crossings"] = same_layer_crossings(
        live_edges_of_kind(world["conn"], rule.edge_kind),
        rule.layers,
        part_of_parents(world["conn"]),
        node_tags(world["conn"]).as_mapping(),
    )


def _messages(world: dict[str, Any]) -> list[str]:
    return [v.message for v in world["violations"]]


@then(parsers.parse('the run reports that the exemption for "{end}" excuses nothing'))
def _reported_dead(world: dict[str, Any], end: str) -> None:
    assert any(
        "excuses nothing" in message and f"'{end}'" in message for message in _messages(world)
    ), _messages(world)


@then("the run makes no finding about an exemption that excuses nothing")
def _not_reported_dead(world: dict[str, Any]) -> None:
    assert not [m for m in _messages(world) if "excuses nothing" in m]


@then(parsers.parse('the run reports that the exemption for "{end}" expired'))
def _reported_expired(world: dict[str, Any], end: str) -> None:
    assert any(
        "expired on" in message and f"'{end}'" in message for message in _messages(world)
    ), _messages(world)


@then("the lint fails, naming the entry that carries no reason")
def _refused(world: dict[str, Any]) -> None:
    assert "layers.exempt[0]" in world["error"]
    assert "reason" in world["error"]


@then(parsers.parse('"{src} -> {dst}" is still a crossing no entry excuses'))
def _still_a_crossing(world: dict[str, Any], src: str, dst: str) -> None:
    from beadloom.graph.rules.layer_exemptions import excused_crossings

    reported, _ = excused_crossings(world["rule"], world["crossings"])
    assert (src, dst) in reported


@then(parsers.parse('"{src} -> {dst}" is not among them'))
def _not_a_crossing(world: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) not in world["crossings"]
