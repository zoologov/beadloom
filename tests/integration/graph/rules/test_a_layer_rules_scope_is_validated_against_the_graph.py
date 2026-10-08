"""A layer rule's ``scope`` is checked against the graph like any ref_id a rule names.

BDL-080 S1b (``beadloom-kgh6``). The loader refuses a scope that cannot be a
ref_id; whether it names a NODE is a question about the graph, answered by
:func:`validate_rules` with the warning every other unknown ref_id gets. And a
scoped rule's layers are populated by the nodes inside its scope only, so a
layer whose tag is carried outside the scope is reported as carried by no node.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.loader import validate_rules
from beadloom.graph.rules.types import LayerDef, LayerRule
from tests.support.in_memory_graph import add_edge, add_node, open_graph

if TYPE_CHECKING:
    import sqlite3

_LAYERS = (LayerDef(name="pages", tag="ui-pages"), LayerDef(name="shared", tag="ui-shared"))


def _rule(scope: str | None) -> LayerRule:
    return LayerRule(
        name="ui-slices",
        description="",
        layers=_LAYERS,
        enforce="top-down",
        edge_kind="depends_on",
        scope=scope,
    )


def _graph() -> sqlite3.Connection:
    conn = open_graph()
    add_node(conn, "shop", "service")
    add_node(conn, "portal", "service")
    add_node(conn, "pages", "component", "ui-pages")
    add_node(conn, "stray-shared", "component", "ui-shared")
    add_edge(conn, "portal", "shop", "part_of")
    add_edge(conn, "pages", "portal", "part_of")
    add_edge(conn, "stray-shared", "shop", "part_of")
    conn.commit()
    return conn


def test_a_scope_naming_no_node_is_warned_about() -> None:
    conn = _graph()
    warnings = validate_rules([_rule("no-such-node")], conn)
    assert "Rule references unknown ref_id 'no-such-node' (not found in nodes table)" in warnings


def test_a_layer_carried_only_outside_the_scope_is_carried_by_no_node() -> None:
    conn = _graph()
    scoped = validate_rules([_rule("portal")], conn)
    unscoped = validate_rules([_rule(None)], conn)
    assert scoped == [
        "Rule 'ui-slices' declares layer tag(s) 'ui-shared' that no node carries "
        "(not found in nodes table)"
    ]
    assert unscoped == []
