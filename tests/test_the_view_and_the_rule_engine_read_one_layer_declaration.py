"""The architecture view and the rule engine answer "what layer" from one lookup.

BDL-070 A5 (`beadloom-06dz`). Two more bodies answered the question the epic is
about. `application.architecture_view` kept its own tag table and its own rank
table and climbed `part_of` itself; `graph.rules.liveness` read a node's tags
into a third map of its own. Both now call
`graph.rules.layers`, and this file holds the properties that say so.

**Each caller keeps the verdict it had.** The view INHERITS a layer through
`part_of`, because a feature has to sit in its container's lane; liveness reads
OWN TAGS ONLY, because inheriting would change which rules it calls inert, and
Release A changes no verdict. The disagreement between the view's edge predicate
and the rule engine's is NOT resolved here — `beadloom-w34m` (B4) owns it.

**The declaration is read, never written down.** A fixture below declares
`tier-*` layers, which this project does not use, and the view ranks by them.
That is the property an adopter depends on: Beadloom ships to projects whose
layers are named differently.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.graph.rules.layer_reach import part_of_parents
from beadloom.graph.rules.layers import layer_of
from beadloom.graph.rules.liveness import inert_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerDef, LayerRule
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)

#: A declaration that is not this project's. Every claim about "the declaration
#: decides" is measured on it as well, because this repository's own tags are
#: exactly the four a hardcoded table would have held.
TIER_LAYERS = (
    LayerDef(name="ui", tag="tier-ui"),
    LayerDef(name="core", tag="tier-core"),
)


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _node(conn: sqlite3.Connection, ref_id: str, kind: str, *tags: str) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, f"{ref_id} summary.", None, json.dumps({"tags": list(tags)})),
    )


def _edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)", (src, dst, kind)
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


def _layer_rule(layers: Sequence[LayerDef], edge_kind: str = "depends_on") -> LayerRule:
    return LayerRule(
        name="architecture-layers",
        description="layers, declared",
        layers=tuple(layers),
        enforce="top-down",
        allow_skip=True,
        edge_kind=edge_kind,
    )


def _ddd_graph(conn: sqlite3.Connection) -> None:
    """A graph with the shapes this repository has and two it does not.

    ``deep`` is a component two generations below the nearest tagged container,
    and ``orphan`` carries no tag and no tagged ancestor at all — the two shapes
    this repository hides, because every one of its features is one ``part_of``
    hop from a tagged domain.
    """
    _node(conn, "beadloom", "service", "layer-service")
    _node(conn, "application", "domain", "layer-application")
    _node(conn, "graph", "domain", "layer-domain")
    _node(conn, "db", "domain", "layer-infra")
    _node(conn, "site-generation", "feature")
    _node(conn, "deep", "component")
    _node(conn, "orphan", "component")
    _edge(conn, "application", "beadloom", "part_of")
    _edge(conn, "graph", "beadloom", "part_of")
    _edge(conn, "db", "beadloom", "part_of")
    _edge(conn, "site-generation", "application", "part_of")
    _edge(conn, "deep", "site-generation", "part_of")
    _edge(conn, "application", "graph", "depends_on")
    _edge(conn, "graph", "db", "depends_on")


class TestOneAnswerForEveryNode:
    """The view's rank is the shared lookup's index, node for node."""

    def test_the_view_and_the_rule_engine_return_the_same_layer_for_every_node(self) -> None:
        conn = _open()
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
        conn = _open()
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
        conn = _open()
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
        conn = _open()
        try:
            _node(conn, "web", "service", "tier-ui")
            _node(conn, "engine", "domain", "tier-core")
            _node(conn, "parser", "feature")
            _edge(conn, "parser", "engine", "part_of")
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
        conn = _open()
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
        conn = _open()
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

    def test_a_declared_graph_logs_nothing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The line is absent on the ordinary run, so its presence means something."""
        # Arrange
        conn = _open()
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
        conn = _open()
        try:
            _node(conn, "solo", "domain")
            conn.commit()
            # Act
            with caplog.at_level(logging.INFO, logger="beadloom.application.architecture_view"):
                build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        # Assert
        assert [r.getMessage() for r in caplog.records if r.levelno == logging.INFO] == []

    def test_an_edge_carries_no_violation_flag_without_a_declaration(self) -> None:
        conn = _open()
        try:
            _ddd_graph(conn)
            conn.commit()
            data = build_architecture_view_data(conn, pages={})
        finally:
            conn.close()
        for edge in data["edges"]:  # type: ignore[union-attr]
            assert "violation" not in edge


class TestLivenessKeepsItsOwnVerdict:
    """Liveness reads OWN tags, because inheriting would move a verdict."""

    def test_an_edge_between_two_inheriting_nodes_does_not_wake_the_rule(self) -> None:
        """The verdict Release A must not change, stated as the case that would.

        ``deep`` and ``other`` both inherit a layer through ``part_of``, so the
        inheriting lookup sees an edge between two layers where the own-tag
        lookup sees none. Liveness must report the rule inert, exactly as it did
        before the shared lookup existed.
        """
        conn = _open()
        try:
            _node(conn, "api", "service", "layer-service")
            _node(conn, "store", "domain", "layer-infra")
            _node(conn, "deep", "feature")
            _node(conn, "other", "feature")
            _edge(conn, "deep", "api", "part_of")
            _edge(conn, "other", "store", "part_of")
            _edge(conn, "deep", "other", "depends_on")
            conn.commit()
            found = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
            inert = {rule.name: reason for rule, reason in found}
        finally:
            conn.close()
        assert inert == {
            "architecture-layers": "no live 'depends_on' edge runs between two of its layers"
        }

    def test_a_single_populated_layer_names_the_empty_tags_in_the_old_words(self) -> None:
        conn = _open()
        try:
            _node(conn, "graph", "domain", "layer-domain")
            _node(conn, "feature", "feature")
            _edge(conn, "feature", "graph", "part_of")
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
        conn = _open()
        try:
            _node(conn, "api", "service", "layer-service")
            _node(conn, "store", "domain", "layer-infra")
            _edge(conn, "api", "store", "depends_on")
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
        conn = _open()
        try:
            _node(conn, "api", "service", "layer-service")
            _node(conn, "store", "domain", "layer-infra")
            _edge(conn, "api", "store", "depends_on")
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
                ("odd", "component", "odd summary.", '"not an object"'),
            )
            conn.commit()
            inert = inert_rules(conn, [_layer_rule(DDD_LAYERS)])
        finally:
            conn.close()
        assert inert == []
