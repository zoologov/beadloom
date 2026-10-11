"""The portal's data file carries ``via: "@x"`` on the edge that records it, and nowhere else.

BDL-082 S1a (``beadloom-r15q``), RFC D1. A ``depends_on`` edge every import of which goes
through the target's ``@x`` cross-import API carries ``via: "@x"`` in its ``extra``; the
architecture data file shows it on that edge as ``via``, beside ``violation``. The verdict
stays the rules': on the entities layer such an edge is no violation, and on any other
layer it is one.
"""

from __future__ import annotations

import json
from typing import Any

from beadloom.application.site.architecture_view import build_architecture_view_data
from tests.support.in_memory_graph import add_node, open_graph

_RULE = {
    "layers": [
        {"name": "features", "tag": "fsd-features"},
        {"name": "entities", "tag": "fsd-entities"},
    ],
    "enforce": "top-down",
    "allow_skip": True,
    "edge_kind": "depends_on",
}


def _view() -> dict[str, dict[str, Any]]:
    conn = open_graph()
    for ref_id, tag in (
        ("entities-artist", "fsd-entities"),
        ("entities-song", "fsd-entities"),
        ("features-b", "fsd-features"),
        ("features-a", "fsd-features"),
    ):
        add_node(conn, ref_id, "component", tag)
    for src, dst, extra in (
        ("entities-artist", "entities-song", {"derived": "imports", "via": "@x"}),
        ("features-b", "features-a", {"derived": "imports", "via": "@x"}),
        ("features-a", "entities-song", {"derived": "imports"}),
    ):
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) "
            "VALUES (?, ?, 'depends_on', ?)",
            (src, dst, json.dumps(extra)),
        )
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES ('fsd-layers', '', 'layers', ?, 1)",
        (json.dumps(_RULE),),
    )
    conn.commit()
    data = build_architecture_view_data(conn, pages={})
    edges = data["edges"]
    assert isinstance(edges, list)
    return {f"{e['src']}->{e['dst']}": e for e in edges}


def test_an_entities_edge_via_x_carries_it_and_is_no_violation() -> None:
    edge = _view()["entities-artist->entities-song"]

    assert edge["via"] == "@x"
    assert edge["violation"] is False


def test_a_features_edge_via_x_carries_it_and_is_a_violation() -> None:
    edge = _view()["features-b->features-a"]

    assert edge["via"] == "@x"
    assert edge["violation"] is True


def test_an_edge_without_the_fact_has_no_via_key() -> None:
    assert "via" not in _view()["features-a->entities-song"]
