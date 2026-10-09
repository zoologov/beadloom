# beadloom:domain=graph
"""An inert matcher's reason names the field no node carries, not the first field set.

BDL-080 S2d (``beadloom-af99.10``), from the S2 review (``beadloom-cp4u``, minor 1). A
matcher may set ``tag`` and ``tag_prefix`` together. Before this fix a rule inert
because of the prefix was reported as "its `for` tag '<tag>' is carried by no node"
while a node carried that tag: the reason named the first field that was set, whether
or not it was the one that selected nothing. Each field is now named only when no node
carries it; when every field is carried by some node and no node carries them
together, the reason says the matcher matches none of the nodes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import CardinalityRule, NodeMatcher, evaluate_all
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

LIVENESS = "rule_liveness"


@pytest.fixture()
def graph_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A service and two domains, each with one tag."""
    conn = open_db(tmp_path / "test.db")
    create_schema(conn)
    for ref_id, kind, tags in (
        ("app", "service", ["layer-svc"]),
        ("board", "component", ["ui-widgets"]),
        ("ledger", "domain", ["tier-core"]),
    ):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, kind, f"{ref_id} node", f"src/{ref_id}/", json.dumps({"tags": tags})),
        )
    conn.commit()
    yield conn
    conn.close()


def _reason(conn: sqlite3.Connection, matcher: NodeMatcher) -> str:
    """The one liveness message a size check over *matcher* is reported with."""
    rule = CardinalityRule(
        name="both-cohesion",
        description="a slice owns few symbols",
        for_matcher=matcher,
        max_symbols=10,
    )
    messages = [v.message for v in evaluate_all(conn, [rule]) if v.rule_type == LIVENESS]
    assert len(messages) == 1, messages
    return messages[0]


def test_a_prefix_no_tag_begins_with_is_named_although_the_tag_is_carried(
    graph_db: sqlite3.Connection,
) -> None:
    message = _reason(graph_db, NodeMatcher(kind="component", tag="ui-widgets", tag_prefix="fsd-"))

    assert "no node carries a tag beginning with 'fsd-'" in message, message
    assert "is carried by no node" not in message, message


def test_a_tag_no_node_carries_is_still_named_when_the_prefix_is_carried(
    graph_db: sqlite3.Connection,
) -> None:
    message = _reason(graph_db, NodeMatcher(tag="ui-pages", tag_prefix="ui-"))

    assert "tag 'ui-pages' is carried by no node" in message, message


def test_a_tag_and_a_prefix_each_carried_but_never_together_name_neither(
    graph_db: sqlite3.Connection,
) -> None:
    message = _reason(graph_db, NodeMatcher(tag="ui-widgets", tag_prefix="tier-"))

    assert "is carried by no node" not in message, message
    assert "beginning with" not in message, message
    assert "matches none of the 3 nodes in the graph" in message, message


def test_a_kind_some_node_has_is_not_named_when_its_tag_sits_on_another_kind(
    graph_db: sqlite3.Connection,
) -> None:
    message = _reason(graph_db, NodeMatcher(kind="service", tag="ui-widgets"))

    assert "kind 'service' matches none" not in message, message
    assert "is carried by no node" not in message, message
    assert "matches none of the 3 nodes in the graph" in message, message


def test_a_kind_no_node_has_is_still_named(graph_db: sqlite3.Connection) -> None:
    message = _reason(graph_db, NodeMatcher(kind="feature"))

    assert "kind 'feature' matches none of the 3 nodes in the graph" in message, message
