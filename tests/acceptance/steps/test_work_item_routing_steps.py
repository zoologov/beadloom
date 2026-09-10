"""Step implementations for BDL-068 S6 / BDL-UX #259 — the routing table's boundary.

Thin by design: every step arranges the REAL composed ``/task-init`` command and
runs the real derivation over it. Nothing is doubled, because a scenario that
passes against a double proves the double.

The extra table each scenario appends is not invented prose. It is copied from
the shipped `docs/guides/document-kinds.md`, which documents the same two flows
in a table of its own — one of the seventeen rows this repository already carries
that the vocabulary guard admits.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.work_item_routing import (
    TASK_INIT_COMMAND,
    Routing,
    read_routing,
)
from beadloom.onboarding.composer import compose
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG

scenarios("../features/work_item_routing.feature")

#: The routes the shipped command states, read from the command rather than
#: written down here would be circular; written down here is the point.
_STATED = (
    ("epic", "full"),
    ("feature", "full"),
    ("bug", "simplified"),
    ("task", "simplified"),
    ("chore", "simplified"),
)

#: A second table describing the same two flows, the shape a project layer adds.
#: Its rows pass the vocabulary guard the reader survives on today.
_SECOND_TABLE = """
## How the two flows are checked

| Finding | When it fires | Judged over |
|---------|---------------|-------------|
| `routed-without-axes` | a work item on the simplified route carrying no axes | the folder |
| `route-not-supported-by-the-axes` | a simplified route whose axes name two nodes | the folder |
"""

#: A table stated BEFORE the routing table that QUOTES a routing row as an
#: example. A command documenting its own table does exactly this, and the row
#: it quotes is the header the reader matched on.
_QUOTING_TABLE = """
## What this command reads

| Artifact | Read for | Notes |
|----------|----------|-------|
| Type | Flow | Docs created |
| `epic` | Full: PRD → RFC | the example row above |
"""


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _shipped() -> str:
    return compose(*TASK_INIT_COMMAND, config=DEFAULT_DOC_CONFIG).text


@given("a task-init command whose project layer adds a second table describing the two flows")
def _layered(world: dict[str, Any]) -> None:
    world["text"] = _shipped() + "\n" + _SECOND_TABLE


@given("a task-init command in which an earlier table quotes a routing row as an example")
def _quoted(world: dict[str, Any]) -> None:
    text = _shipped()
    marker = "| Type | Flow |"
    head, _, tail = text.partition(marker)
    world["text"] = head + _QUOTING_TABLE + "\n" + marker + tail


@given("a task-init command whose routing table adds a type routed through a third flow")
def _third_flow(world: dict[str, Any]) -> None:
    text = _shipped()
    marker = "| `chore` | Simplified: BRIEF → ACTIVE | BRIEF, ACTIVE |"
    assert marker in text
    world["text"] = text.replace(marker, marker + "\n| `spike` | Timeboxed: NOTES | NOTES |")


@when("the routing is read from it")
def _read(world: dict[str, Any]) -> None:
    world["routing"] = read_routing(world["text"])


@then("the routes read are the ones the routing table states")
def _states(world: dict[str, Any]) -> None:
    routing: Routing = world["routing"]
    assert tuple((route.type, route.flow) for route in routing.routes) == _STATED


@then("no row of the second table is read as a route")
def _no_second(world: dict[str, Any]) -> None:
    routing: Routing = world["routing"]
    types = {route.type for route in routing.routes}
    assert "`routed-without-axes`" not in types
    assert "routed-without-axes" not in types


@then("the routing names that row as one it could not read")
def _named(world: dict[str, Any]) -> None:
    routing: Routing = world["routing"]
    assert any("spike" in note for note in routing.notes), routing.notes


@then("the type decision is located at the routing table")
def _decision_line(world: dict[str, Any]) -> None:
    routing: Routing = world["routing"]
    lines = world["text"].splitlines()
    assert routing.decision_line is not None
    assert lines[routing.decision_line - 1].startswith("| Type | Flow | Docs created |")


@then("the document every route writes is still named")
def _shared(world: dict[str, Any]) -> None:
    routing: Routing = world["routing"]
    assert routing.shared_kinds == frozenset({"ACTIVE"})
