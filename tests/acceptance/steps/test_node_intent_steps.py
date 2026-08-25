"""Step implementations for the node-intent acceptance suite (BDL-061 `.87`).

Thin by design: each step writes a real planning document, indexes a real
project and builds a real bundle. Nothing is doubled — a scenario that passes
against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up; the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.intent_reader import read_node_intent
from beadloom.application.reindex import reindex
from beadloom.context_oracle.builder import build_context
from beadloom.context_oracle.intent import (
    INTENT_DECLARED,
    INTENT_NONE_DECLARED,
    INTENT_NOT_CHECKED,
)
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/node_intent.feature")

_EPIC_ROOT = ".claude/development/docs/features"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _index(root: Path) -> None:
    _write(
        root,
        ".beadloom/_graph/features.yml",
        yaml.safe_dump(
            {
                "nodes": [
                    {"ref_id": "checkout", "kind": "feature", "summary": "Checkout"},
                    {"ref_id": "shipping", "kind": "feature", "summary": "Shipping"},
                ],
                "edges": [],
            }
        ),
    )
    reindex(root)


@given(parsers.parse('an epic whose CONTEXT declares the node "{ref_id}"'))
def _epic_declares(world: dict[str, Any], ref_id: str) -> None:
    root: Path = world["root"]
    _write(
        root,
        f"{_EPIC_ROOT}/ORD-4/CONTEXT.md",
        f"# ORD-4 — one-click {ref_id}\n\n## Related Files\n\n- `{ref_id}`\n",
    )
    _index(root)


def _build(world: dict[str, Any], ref_id: str, *, with_intent: bool) -> None:
    root: Path = world["root"]
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        reading = read_node_intent(conn, root) if with_intent else None
        world["bundle"] = build_context(conn, [ref_id], intent=reading)
    finally:
        conn.close()


@when(parsers.parse('a context bundle is built for "{ref_id}"'))
def _build_with_intent(world: dict[str, Any], ref_id: str) -> None:
    _build(world, ref_id, with_intent=True)


@when(parsers.parse('a context bundle is built for "{ref_id}" without reading the intent space'))
def _build_without_intent(world: dict[str, Any], ref_id: str) -> None:
    _build(world, ref_id, with_intent=False)


@then("the bundle names the epic that declared it")
def _names_the_epic(world: dict[str, Any]) -> None:
    intent = world["bundle"]["intent"]
    assert intent["status"] == INTENT_DECLARED
    assert [d["epic"] for d in intent["declared_by"]] == ["ORD-4"]


@then("the bundle points at the intent document that declares it")
def _points_at_the_document(world: dict[str, Any]) -> None:
    declaration = world["bundle"]["intent"]["declared_by"][0]
    assert declaration["document"] == f"{_EPIC_ROOT}/ORD-4/CONTEXT.md"
    assert declaration["line"] > 0


@then("the bundle reports that no epic declares it")
def _reports_none_declared(world: dict[str, Any]) -> None:
    assert world["bundle"]["intent"]["status"] == INTENT_NONE_DECLARED


@then("the bundle states how many epics were read")
def _states_the_population(world: dict[str, Any]) -> None:
    intent = world["bundle"]["intent"]
    assert intent["epics_read"] == 1
    assert intent["epics_declaring_nodes"] == 1


@then("the bundle reports that intent was not checked")
def _reports_not_checked(world: dict[str, Any]) -> None:
    intent = world["bundle"]["intent"]
    assert intent["status"] == INTENT_NOT_CHECKED
    assert intent["reason"]


@then("the bundle does not claim that no epic declares it")
def _makes_no_absence_claim(world: dict[str, Any]) -> None:
    intent = world["bundle"]["intent"]
    assert intent["status"] != INTENT_NONE_DECLARED
    assert intent["epics_read"] == 0
