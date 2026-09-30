"""Liveness reads the layer a node is in the way the layer rule decides it.

BDL-070 A5 (`beadloom-06dz`) moved `graph.rules.liveness` onto the shared layer
lookup. Release A pinned liveness to OWN tags, because inheriting changes which
rules it calls inert and Release A changes no verdict. Release B made that change
in `beadloom-5tcc.6`, because a rule reporting an error while the same run counted
it inert was a false signal (BDL-UX #296). The class below says which case moved
and which did not.

Split out of ``tests/test_the_view_and_the_rule_engine_read_one_layer_declaration.py``
by node (BDL-074 E1); the architecture view's half is
``tests/integration/application/site/architecture_view/test_the_view_ranks_nodes_by_the_declared_layers.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.liveness import inert_rules
from beadloom.graph.rules.types import LayerDef, LayerRule
from tests.support.in_memory_graph import DDD_LAYERS, add_edge, add_node, open_graph

if TYPE_CHECKING:
    from collections.abc import Sequence


def _layer_rule(layers: Sequence[LayerDef], edge_kind: str = "depends_on") -> LayerRule:
    return LayerRule(
        name="architecture-layers",
        description="layers, declared",
        layers=tuple(layers),
        enforce="top-down",
        allow_skip=True,
        edge_kind=edge_kind,
    )


class TestLivenessReadsTheLayerTheRuleDecidesOn:
    """The one verdict Release B moved, and the graphs it did not move.

    Release A pinned liveness to OWN tags here and said why: inheriting changes
    which rules it calls inert. `beadloom-5tcc.6` made that change in the release
    that announces it, so the first test below is the verdict that moved — it
    asserted an inert rule and now asserts a live one, on the same graph.
    """

    def test_an_edge_between_two_inheriting_nodes_wakes_the_rule(self) -> None:
        """The verdict Release B moved, on the graph Release A pinned it with.

        ``deep`` and ``other`` both inherit a layer through ``part_of``, so the
        rule judges ``deep -> other`` as an edge from the service layer to the
        infrastructure one. Liveness reported the rule inert here until
        BDL-UX #296 was closed, which is a rule reported inert on 4.0.0 and not
        reported on the next release, on a graph nobody edited.
        """
        conn = open_graph()
        try:
            add_node(conn, "api", "service", "layer-service")
            add_node(conn, "store", "domain", "layer-infra")
            add_node(conn, "deep", "feature")
            add_node(conn, "other", "feature")
            add_edge(conn, "deep", "api", "part_of")
            add_edge(conn, "other", "store", "part_of")
            add_edge(conn, "deep", "other", "depends_on")
            conn.commit()
            found = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
        finally:
            conn.close()
        assert found == []

    def test_a_single_populated_layer_names_the_empty_tags_in_the_old_words(self) -> None:
        conn = open_graph()
        try:
            add_node(conn, "graph", "domain", "layer-domain")
            add_node(conn, "feature", "feature")
            add_edge(conn, "feature", "graph", "part_of")
            conn.commit()
            found = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
            inert = {rule.name: reason for rule, reason in found}
        finally:
            conn.close()
        assert inert == {
            "architecture-layers": (
                "fewer than two of its layers are populated (no node carries "
                "'layer-application', 'layer-infra', 'layer-service')"
            )
        }

    def test_an_edge_between_two_tagged_nodes_leaves_the_rule_live(self) -> None:
        conn = open_graph()
        try:
            add_node(conn, "api", "service", "layer-service")
            add_node(conn, "store", "domain", "layer-infra")
            add_edge(conn, "api", "store", "depends_on")
            conn.commit()
            inert = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
        finally:
            conn.close()
        assert inert == []

    def test_a_node_whose_extra_is_not_an_object_does_not_break_an_unrelated_rule(self) -> None:
        """One malformed row answers "no tags", rather than ending the run.

        Reading every node's tags in one pass means a row nobody asked about is
        read anyway, so the tolerance is a consequence of the shared reader and
        is asserted rather than left to be discovered.
        """
        conn = open_graph()
        try:
            add_node(conn, "api", "service", "layer-service")
            add_node(conn, "store", "domain", "layer-infra")
            add_edge(conn, "api", "store", "depends_on")
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
                ("odd", "component", "odd summary.", '"not an object"'),
            )
            conn.commit()
            inert = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
        finally:
            conn.close()
        assert inert == []
