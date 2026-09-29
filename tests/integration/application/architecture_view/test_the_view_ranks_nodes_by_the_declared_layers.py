"""The architecture view ranks every node by the declared layers, through the shared lookup.

BDL-070 A5 (`beadloom-06dz`). `application.architecture_view` kept its own tag
table and its own rank table and climbed `part_of` itself; it now calls
`graph.rules.layers`, and the view's rank is that lookup's index, node for node.
The view INHERITS a layer through `part_of`, because a feature has to sit in its
container's lane.

**The declaration is read, never written down.** A fixture below declares
`tier-*` layers, which this project does not use, and the view ranks by them. That
is the property an adopter depends on: Beadloom ships to projects whose layers are
named differently.

Split out of ``tests/test_the_view_and_the_rule_engine_read_one_layer_declaration.py``
by node (BDL-074 E1); the rule engine's half is
``tests/integration/graph/rules/test_liveness_reads_the_layer_the_rule_decides_on.py``.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.graph.rules.layer_reach import part_of_parents
from beadloom.graph.rules.layers import layer_of
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerDef
from tests.support.in_memory_graph import DDD_LAYERS, add_edge, add_node, open_graph

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    import pytest


#: A declaration that is not this project's. Every claim about "the declaration
#: decides" is measured on it as well, because this repository's own tags are
#: exactly the four a hardcoded table would have held.
TIER_LAYERS = (
    LayerDef(name="ui", tag="tier-ui"),
    LayerDef(name="core", tag="tier-core"),
)


def _declare_layers(
    conn: sqlite3.Connection,
    layers: Sequence[LayerDef],
    *,
    name: str = "architecture-layers",
    edge_kind: str = "depends_on",
) -> None:
    """Write the layer declaration where a reindexed project carries it."""
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES (?, ?, 'layers', ?, 1)",
        (
            name,
            "layers, declared",
            json.dumps(
                {
                    "layers": [{"name": layer.name, "tag": layer.tag} for layer in layers],
                    "enforce": "top-down",
                    "allow_skip": True,
                    "edge_kind": edge_kind,
                }
            ),
        ),
    )


def _ddd_graph(conn: sqlite3.Connection) -> None:
    """A graph with the shapes this repository has and two it does not.

    ``deep`` is a component two generations below the nearest tagged container,
    and ``orphan`` carries no tag and no tagged ancestor at all — the two shapes
    this repository hides, because every one of its features is one ``part_of``
    hop from a tagged domain.
    """
    add_node(conn, "beadloom", "service", "layer-service")
    add_node(conn, "application", "domain", "layer-application")
    add_node(conn, "graph", "domain", "layer-domain")
    add_node(conn, "db", "domain", "layer-infra")
    add_node(conn, "site-generation", "feature")
    add_node(conn, "deep", "component")
    add_node(conn, "orphan", "component")
    add_edge(conn, "application", "beadloom", "part_of")
    add_edge(conn, "graph", "beadloom", "part_of")
    add_edge(conn, "db", "beadloom", "part_of")
    add_edge(conn, "site-generation", "application", "part_of")
    add_edge(conn, "deep", "site-generation", "part_of")
    add_edge(conn, "application", "graph", "depends_on")
    add_edge(conn, "graph", "db", "depends_on")


class TestOneAnswerForEveryNode:
    """The view's rank is the shared lookup's index, node for node."""

    def test_the_view_and_the_rule_engine_return_the_same_layer_for_every_node(self) -> None:
        conn = open_graph()
        try:
            _ddd_graph(conn)
            _declare_layers(conn, DDD_LAYERS)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
            parents = part_of_parents(conn)
            tags = node_tags(conn).as_mapping()
        finally:
            conn.close()
        by_id = {str(n["id"]): n for n in data["nodes"]}  # type: ignore[union-attr]
        assert set(by_id) == {
            "beadloom",
            "application",
            "graph",
            "db",
            "site-generation",
            "deep",
            "orphan",
        }
        for ref_id, node in by_id.items():
            assert node["layer_rank"] == layer_of(ref_id, DDD_LAYERS, parents, tags), ref_id

    def test_the_population_holds_both_answers(self) -> None:
        """Guard the guard: the agreement above must not hold vacuously."""
        conn = open_graph()
        try:
            _ddd_graph(conn)
            _declare_layers(conn, DDD_LAYERS)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        ranks = {str(n["id"]): n["layer_rank"] for n in data["nodes"]}  # type: ignore[union-attr]
        assert ranks["beadloom"] == 0
        assert ranks["application"] == 1
        assert ranks["graph"] == 2
        assert ranks["db"] == 3
        assert ranks["site-generation"] == 1
        assert ranks["deep"] == 1
        assert ranks["orphan"] is None

    def test_a_node_keeps_its_own_layer_and_does_not_climb(self) -> None:
        conn = open_graph()
        try:
            _ddd_graph(conn)
            _declare_layers(conn, DDD_LAYERS)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        by_id = {str(n["id"]): n for n in data["nodes"]}  # type: ignore[union-attr]
        # `graph` is part_of `beadloom` (rank 0) and carries its own domain tag.
        assert by_id["graph"]["layer_rank"] == 2


class TestTheDeclarationDecides:
    """No layer tag is written down in the view, so another project's tags work."""

    def test_a_declaration_this_project_does_not_use_still_ranks_the_graph(self) -> None:
        conn = open_graph()
        try:
            add_node(conn, "web", "service", "tier-ui")
            add_node(conn, "engine", "domain", "tier-core")
            add_node(conn, "parser", "feature")
            add_edge(conn, "parser", "engine", "part_of")
            _declare_layers(conn, TIER_LAYERS)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        by_id = {str(n["id"]): n for n in data["nodes"]}  # type: ignore[union-attr]
        assert by_id["web"]["layer_rank"] == 0
        assert by_id["engine"]["layer_rank"] == 1
        assert by_id["parser"]["layer_rank"] == 1
        assert by_id["web"]["layer"] == "tier-ui"

    def test_a_graph_with_no_layer_declaration_reports_no_layer(self) -> None:
        """Honest degradation: no declaration is not "everything is in layer 0"."""
        conn = open_graph()
        try:
            _ddd_graph(conn)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        for node in data["nodes"]:  # type: ignore[union-attr]
            assert node["layer_rank"] is None
            assert node["layer"] == ""

    def test_a_tagged_graph_with_no_declaration_says_so_in_the_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The one adopter-visible move in Release A, made legible where it happens.

        A project that tags its nodes `layer-*` and whose index carries no layer
        rule rendered four lanes before this release and renders none after it.
        The view cannot decide which of the two the project meant, so it reports
        the fact rather than guessing (A8 review, Major 3).
        """
        # Arrange
        conn = open_graph()
        try:
            _ddd_graph(conn)
            conn.commit()
            # Act
            with caplog.at_level(logging.INFO, logger="beadloom.application.architecture_view"):
                build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        # Assert
        logged = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert len(logged) == 1
        assert "4" in logged[0]
        assert "no layer rule" in logged[0]

    def test_a_declared_graph_logs_nothing(self, caplog: pytest.LogCaptureFixture) -> None:
        """The line is absent on the ordinary run, so its presence means something."""
        # Arrange
        conn = open_graph()
        try:
            _ddd_graph(conn)
            _declare_layers(conn, DDD_LAYERS)
            conn.commit()
            # Act
            with caplog.at_level(logging.INFO, logger="beadloom.application.architecture_view"):
                build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        # Assert
        assert [r.getMessage() for r in caplog.records if r.levelno == logging.INFO] == []

    def test_an_untagged_graph_with_no_declaration_logs_nothing_either(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A project with no layering at all lost nothing and is told nothing."""
        # Arrange
        conn = open_graph()
        try:
            add_node(conn, "solo", "domain")
            conn.commit()
            # Act
            with caplog.at_level(logging.INFO, logger="beadloom.application.architecture_view"):
                build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        # Assert
        assert [r.getMessage() for r in caplog.records if r.levelno == logging.INFO] == []

    def test_an_edge_carries_no_violation_flag_without_a_declaration(self) -> None:
        conn = open_graph()
        try:
            _ddd_graph(conn)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        for edge in data["edges"]:  # type: ignore[union-attr]
            assert "violation" not in edge
