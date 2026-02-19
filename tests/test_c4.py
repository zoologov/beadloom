"""Tests for beadloom.graph.c4 — C4 level mapping and renderers."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.c4 import (
    C4Node,
    C4Relationship,
    _c4_element_name,
    filter_c4_nodes,
    map_to_c4,
    render_c4_mermaid,
    render_c4_plantuml,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """In-memory DB with minimal schema for nodes + edges."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE nodes (
            ref_id  TEXT PRIMARY KEY,
            kind    TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            source  TEXT,
            extra   TEXT DEFAULT '{}'
        );
        CREATE TABLE edges (
            src_ref_id TEXT NOT NULL,
            dst_ref_id TEXT NOT NULL,
            kind       TEXT NOT NULL,
            extra      TEXT DEFAULT '{}',
            PRIMARY KEY (src_ref_id, dst_ref_id, kind)
        );
        """
    )
    return db


def _insert_node(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str = "domain",
    summary: str = "",
    source: str | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    """Helper to insert a node with optional extra JSON."""
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, summary, source, extra_json),
    )
    conn.commit()


def _insert_edge(
    conn: sqlite3.Connection,
    src: str,
    dst: str,
    kind: str = "part_of",
) -> None:
    """Helper to insert an edge."""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) VALUES (?, ?, ?, '{}')",
        (src, dst, kind),
    )
    conn.commit()


# ===========================================================================
# Dataclass basics
# ===========================================================================


class TestC4NodeDataclass:
    def test_frozen(self) -> None:
        node = C4Node(
            ref_id="app",
            label="App",
            c4_level="System",
            description="",
            boundary=None,
            is_external=False,
            is_database=False,
        )
        with pytest.raises(AttributeError):
            node.ref_id = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        node = C4Node(
            ref_id="svc",
            label="Service",
            c4_level="Container",
            description="A service",
            boundary="app",
            is_external=True,
            is_database=False,
        )
        assert node.ref_id == "svc"
        assert node.label == "Service"
        assert node.c4_level == "Container"
        assert node.description == "A service"
        assert node.boundary == "app"
        assert node.is_external is True
        assert node.is_database is False


class TestC4RelationshipDataclass:
    def test_frozen(self) -> None:
        rel = C4Relationship(src="a", dst="b", label="uses")
        with pytest.raises(AttributeError):
            rel.src = "c"  # type: ignore[misc]

    def test_fields(self) -> None:
        rel = C4Relationship(src="a", dst="b", label="depends_on")
        assert rel.src == "a"
        assert rel.dst == "b"
        assert rel.label == "depends_on"


# ===========================================================================
# map_to_c4 — empty / trivial cases
# ===========================================================================


class TestMapToC4Empty:
    def test_empty_graph(self, conn: sqlite3.Connection) -> None:
        nodes, rels = map_to_c4(conn)
        assert nodes == []
        assert rels == []

    def test_single_root_node(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "app", kind="service", summary="Main app")
        nodes, _rels = map_to_c4(conn)
        assert len(nodes) == 1
        assert nodes[0].ref_id == "app"
        assert nodes[0].c4_level == "System"
        assert nodes[0].boundary is None


# ===========================================================================
# Depth heuristic: root=System, depth1=Container, depth2+=Component
# ===========================================================================


class TestDepthHeuristic:
    def test_root_is_system(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "child", kind="domain", summary="Child")
        _insert_edge(conn, "child", "root", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["root"].c4_level == "System"

    def test_depth1_is_container(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "child", kind="domain", summary="Child")
        _insert_edge(conn, "child", "root", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["child"].c4_level == "Container"

    def test_depth2_is_component(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "mid", kind="domain", summary="Mid")
        _insert_node(conn, "leaf", kind="feature", summary="Leaf")
        _insert_edge(conn, "mid", "root", "part_of")
        _insert_edge(conn, "leaf", "mid", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["root"].c4_level == "System"
        assert by_id["mid"].c4_level == "Container"
        assert by_id["leaf"].c4_level == "Component"

    def test_depth3_is_still_component(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "mid", kind="domain", summary="Mid")
        _insert_node(conn, "leaf", kind="feature", summary="Leaf")
        _insert_node(conn, "deep", kind="feature", summary="Deep")
        _insert_edge(conn, "mid", "root", "part_of")
        _insert_edge(conn, "leaf", "mid", "part_of")
        _insert_edge(conn, "deep", "leaf", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["deep"].c4_level == "Component"


# ===========================================================================
# Explicit c4_level overrides heuristic
# ===========================================================================


class TestExplicitC4Level:
    def test_explicit_overrides_depth(self, conn: sqlite3.Connection) -> None:
        _insert_node(
            conn,
            "root",
            kind="service",
            summary="Root",
            extra={"c4_level": "Container"},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].c4_level == "Container"

    def test_explicit_on_child(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(
            conn,
            "child",
            kind="domain",
            summary="Child",
            extra={"c4_level": "System"},
        )
        _insert_edge(conn, "child", "root", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        # depth would give Container, but explicit says System
        assert by_id["child"].c4_level == "System"


# ===========================================================================
# Tag detection
# ===========================================================================


class TestTagDetection:
    def test_external_tag(self, conn: sqlite3.Connection) -> None:
        _insert_node(
            conn,
            "ext",
            kind="service",
            summary="External",
            extra={"tags": ["external"]},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_external is True
        assert nodes[0].is_database is False

    def test_database_tag(self, conn: sqlite3.Connection) -> None:
        _insert_node(
            conn,
            "db",
            kind="service",
            summary="Database",
            extra={"tags": ["database"]},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_database is True
        assert nodes[0].is_external is False

    def test_storage_tag(self, conn: sqlite3.Connection) -> None:
        _insert_node(
            conn,
            "store",
            kind="service",
            summary="Store",
            extra={"tags": ["storage"]},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_database is True

    def test_no_tags(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "plain", kind="domain", summary="Plain")
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_external is False
        assert nodes[0].is_database is False

    def test_multiple_tags(self, conn: sqlite3.Connection) -> None:
        _insert_node(
            conn,
            "ext_db",
            kind="service",
            summary="Ext DB",
            extra={"tags": ["external", "database"]},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_external is True
        assert nodes[0].is_database is True


# ===========================================================================
# Boundary grouping via part_of parent
# ===========================================================================


class TestBoundaryGrouping:
    def test_child_boundary_is_parent(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "child", kind="domain", summary="Child")
        _insert_edge(conn, "child", "root", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["child"].boundary == "root"

    def test_root_has_no_boundary(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        nodes, _ = map_to_c4(conn)
        assert nodes[0].boundary is None


# ===========================================================================
# Relationships from uses/depends_on edges
# ===========================================================================


class TestRelationships:
    def test_uses_edge(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "a", kind="service", summary="A")
        _insert_node(conn, "b", kind="service", summary="B")
        _insert_edge(conn, "a", "b", "uses")

        _, rels = map_to_c4(conn)
        assert len(rels) == 1
        assert rels[0].src == "a"
        assert rels[0].dst == "b"
        assert rels[0].label == "uses"

    def test_depends_on_edge(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "a", kind="service", summary="A")
        _insert_node(conn, "b", kind="service", summary="B")
        _insert_edge(conn, "a", "b", "depends_on")

        _, rels = map_to_c4(conn)
        assert len(rels) == 1
        assert rels[0].label == "depends_on"

    def test_part_of_not_relationship(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "child", kind="domain", summary="Child")
        _insert_edge(conn, "child", "root", "part_of")

        _, rels = map_to_c4(conn)
        assert rels == []

    def test_multiple_relationships(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "a", kind="service", summary="A")
        _insert_node(conn, "b", kind="service", summary="B")
        _insert_node(conn, "c", kind="service", summary="C")
        _insert_edge(conn, "a", "b", "uses")
        _insert_edge(conn, "b", "c", "depends_on")

        _, rels = map_to_c4(conn)
        assert len(rels) == 2


# ===========================================================================
# Label uses summary
# ===========================================================================


class TestLabel:
    def test_label_from_summary(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "my-service", kind="service", summary="My Great Service")
        nodes, _ = map_to_c4(conn)
        assert nodes[0].label == "My Great Service"

    def test_label_fallback_to_ref_id(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "my-service", kind="service", summary="")
        nodes, _ = map_to_c4(conn)
        assert nodes[0].label == "my-service"


# ===========================================================================
# Integration: full graph
# ===========================================================================


class TestFullGraph:
    def test_realistic_graph(self, conn: sqlite3.Connection) -> None:
        """A small but realistic graph: system -> 2 domains -> features."""
        _insert_node(conn, "beadloom", kind="service", summary="Beadloom")
        _insert_node(conn, "graph", kind="domain", summary="Graph domain")
        _insert_node(conn, "infra", kind="domain", summary="Infrastructure")
        _insert_node(conn, "loader", kind="feature", summary="YAML Loader")
        _insert_node(conn, "diff", kind="feature", summary="Graph Diff")
        _insert_node(
            conn,
            "ext-db",
            kind="service",
            summary="External DB",
            extra={"tags": ["external", "database"]},
        )

        _insert_edge(conn, "graph", "beadloom", "part_of")
        _insert_edge(conn, "infra", "beadloom", "part_of")
        _insert_edge(conn, "loader", "graph", "part_of")
        _insert_edge(conn, "diff", "graph", "part_of")
        _insert_edge(conn, "graph", "infra", "uses")
        _insert_edge(conn, "infra", "ext-db", "depends_on")

        nodes, rels = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}

        # Depth heuristic
        assert by_id["beadloom"].c4_level == "System"
        assert by_id["graph"].c4_level == "Container"
        assert by_id["infra"].c4_level == "Container"
        assert by_id["loader"].c4_level == "Component"
        assert by_id["diff"].c4_level == "Component"
        # ext-db has no parent → root → System
        assert by_id["ext-db"].c4_level == "System"

        # Boundaries
        assert by_id["beadloom"].boundary is None
        assert by_id["graph"].boundary == "beadloom"
        assert by_id["infra"].boundary == "beadloom"
        assert by_id["loader"].boundary == "graph"
        assert by_id["diff"].boundary == "graph"
        assert by_id["ext-db"].boundary is None

        # Tags
        assert by_id["ext-db"].is_external is True
        assert by_id["ext-db"].is_database is True
        assert by_id["graph"].is_external is False

        # Relationships (only uses + depends_on)
        assert len(rels) == 2
        rel_pairs = {(r.src, r.dst) for r in rels}
        assert ("graph", "infra") in rel_pairs
        assert ("infra", "ext-db") in rel_pairs


# ===========================================================================
# _c4_element_name — helper for determining C4 macro name
# ===========================================================================


class TestC4ElementName:
    """Test the helper that picks the right C4 macro name based on flags."""

    def test_system_normal(self) -> None:
        node = C4Node(
            ref_id="app", label="App", c4_level="System",
            description="", boundary=None, is_external=False, is_database=False,
        )
        assert _c4_element_name(node) == "System"

    def test_system_external(self) -> None:
        node = C4Node(
            ref_id="gh", label="GitHub", c4_level="System",
            description="", boundary=None, is_external=True, is_database=False,
        )
        assert _c4_element_name(node) == "System_Ext"

    def test_container_normal(self) -> None:
        node = C4Node(
            ref_id="web", label="Web", c4_level="Container",
            description="", boundary=None, is_external=False, is_database=False,
        )
        assert _c4_element_name(node) == "Container"

    def test_container_external(self) -> None:
        node = C4Node(
            ref_id="cdn", label="CDN", c4_level="Container",
            description="", boundary=None, is_external=True, is_database=False,
        )
        assert _c4_element_name(node) == "Container_Ext"

    def test_container_database(self) -> None:
        node = C4Node(
            ref_id="db", label="DB", c4_level="Container",
            description="", boundary=None, is_external=False, is_database=True,
        )
        assert _c4_element_name(node) == "ContainerDb"

    def test_container_external_and_database_prefers_ext(self) -> None:
        """When both is_external and is_database, _Ext takes precedence."""
        node = C4Node(
            ref_id="ext_db", label="Ext DB", c4_level="Container",
            description="", boundary=None, is_external=True, is_database=True,
        )
        assert _c4_element_name(node) == "Container_Ext"

    def test_component_normal(self) -> None:
        node = C4Node(
            ref_id="loader", label="Loader", c4_level="Component",
            description="", boundary=None, is_external=False, is_database=False,
        )
        assert _c4_element_name(node) == "Component"

    def test_component_external(self) -> None:
        node = C4Node(
            ref_id="ext_lib", label="Ext Lib", c4_level="Component",
            description="", boundary=None, is_external=True, is_database=False,
        )
        assert _c4_element_name(node) == "Component_Ext"

    def test_component_database(self) -> None:
        node = C4Node(
            ref_id="cache", label="Cache", c4_level="Component",
            description="", boundary=None, is_external=False, is_database=True,
        )
        assert _c4_element_name(node) == "ComponentDb"

    def test_system_database_uses_system_ext_not_db(self) -> None:
        """System level has no Db variant in C4; database at System level stays System."""
        node = C4Node(
            ref_id="store", label="Store", c4_level="System",
            description="", boundary=None, is_external=False, is_database=True,
        )
        # System level doesn't have a Db variant; just plain System
        assert _c4_element_name(node) == "System"


# ===========================================================================
# render_c4_mermaid — Mermaid C4 renderer
# ===========================================================================


class TestRenderC4MermaidStructure:
    """Test basic Mermaid C4 structure."""

    def test_empty_graph_produces_valid_skeleton(self) -> None:
        result = render_c4_mermaid([], [])
        assert "C4Container" in result

    def test_single_system_node(self) -> None:
        nodes = [
            C4Node(
                ref_id="app", label="My App", c4_level="System",
                description="Main app", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "System(app" in result
        assert "My App" in result

    def test_container_node(self) -> None:
        nodes = [
            C4Node(
                ref_id="web", label="Web Frontend", c4_level="Container",
                description="React SPA", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "Container(web" in result

    def test_component_node(self) -> None:
        nodes = [
            C4Node(
                ref_id="loader", label="Loader", c4_level="Component",
                description="Loads files", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "Component(loader" in result


class TestRenderC4MermaidExternalAndDb:
    """Test external and database variants in Mermaid C4."""

    def test_external_system(self) -> None:
        nodes = [
            C4Node(
                ref_id="github", label="GitHub", c4_level="System",
                description="Git hosting", boundary=None,
                is_external=True, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "System_Ext(github" in result

    def test_external_container(self) -> None:
        nodes = [
            C4Node(
                ref_id="cdn", label="CDN", c4_level="Container",
                description="Content delivery", boundary=None,
                is_external=True, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "Container_Ext(cdn" in result

    def test_database_container(self) -> None:
        nodes = [
            C4Node(
                ref_id="db", label="SQLite", c4_level="Container",
                description="App database", boundary=None,
                is_external=False, is_database=True,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "ContainerDb(db" in result

    def test_database_component(self) -> None:
        nodes = [
            C4Node(
                ref_id="cache", label="Redis Cache", c4_level="Component",
                description="In-memory cache", boundary=None,
                is_external=False, is_database=True,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "ComponentDb(cache" in result

    def test_external_database_prefers_ext(self) -> None:
        """When both is_external and is_database, _Ext takes precedence."""
        nodes = [
            C4Node(
                ref_id="cloud_db", label="Cloud DB", c4_level="Container",
                description="External database", boundary=None,
                is_external=True, is_database=True,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "Container_Ext(cloud_db" in result


class TestRenderC4MermaidBoundary:
    """Test boundary grouping in Mermaid C4."""

    def test_children_grouped_in_boundary(self) -> None:
        nodes = [
            C4Node(
                ref_id="app", label="My App", c4_level="System",
                description="Main app", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="web", label="Web", c4_level="Container",
                description="Web frontend", boundary="app",
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "System_Boundary" in result or "Boundary_" in result


class TestRenderC4MermaidRelationships:
    """Test Rel() in Mermaid C4."""

    def test_rel_rendered(self) -> None:
        nodes = [
            C4Node(
                ref_id="a", label="A", c4_level="System",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="b", label="B", c4_level="System",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        rels = [C4Relationship(src="a", dst="b", label="uses")]
        result = render_c4_mermaid(nodes, rels)
        assert "Rel(a, b" in result


class TestRenderC4MermaidMultipleRels:
    """Test multiple Rel() rendering."""

    def test_two_relationships(self) -> None:
        nodes = [
            C4Node(
                ref_id="a", label="A", c4_level="Container",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="b", label="B", c4_level="Container",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="c", label="C", c4_level="Container",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        rels = [
            C4Relationship(src="a", dst="b", label="uses"),
            C4Relationship(src="b", dst="c", label="depends_on"),
        ]
        result = render_c4_mermaid(nodes, rels)
        assert result.count("Rel(") == 2
        assert 'Rel(a, b, "uses")' in result
        assert 'Rel(b, c, "depends_on")' in result


class TestRenderC4MermaidSanitization:
    """Test that ref_ids with hyphens are sanitized for Mermaid."""

    def test_hyphenated_ref_id(self) -> None:
        nodes = [
            C4Node(
                ref_id="my-service", label="My Service", c4_level="System",
                description="A service", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "my_service" in result

    def test_hyphenated_boundary(self) -> None:
        nodes = [
            C4Node(
                ref_id="my-app", label="My App", c4_level="System",
                description="App", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="my-api", label="API", c4_level="Container",
                description="REST API", boundary="my-app",
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "my_app" in result
        assert "my_api" in result

    def test_hyphenated_relationship_refs(self) -> None:
        nodes = [
            C4Node(
                ref_id="svc-a", label="A", c4_level="Container",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="svc-b", label="B", c4_level="Container",
                description="", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        rels = [C4Relationship(src="svc-a", dst="svc-b", label="uses")]
        result = render_c4_mermaid(nodes, rels)
        assert "Rel(svc_a, svc_b," in result


class TestRenderC4MermaidMultipleBoundaries:
    """Test multiple boundaries."""

    def test_two_system_boundaries(self) -> None:
        nodes = [
            C4Node(
                ref_id="sys1", label="System 1", c4_level="System",
                description="First", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="sys2", label="System 2", c4_level="System",
                description="Second", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="c1", label="Container 1", c4_level="Container",
                description="In sys1", boundary="sys1",
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="c2", label="Container 2", c4_level="Container",
                description="In sys2", boundary="sys2",
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "System_Boundary(sys1" in result
        assert "System_Boundary(sys2" in result
        assert "Container(c1" in result
        assert "Container(c2" in result


class TestRenderC4MermaidIntegration:
    """Full end-to-end integration tests for Mermaid C4 rendering."""

    def test_realistic_diagram(self) -> None:
        """Render a realistic graph with boundaries and relationships."""
        nodes = [
            C4Node(
                ref_id="beadloom", label="Beadloom", c4_level="System",
                description="Architecture tool", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="graph", label="Graph Domain", c4_level="Container",
                description="YAML graph", boundary="beadloom",
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="infra", label="Infrastructure", c4_level="Container",
                description="SQLite layer", boundary="beadloom",
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="ext-api", label="External API", c4_level="System",
                description="Third party", boundary=None,
                is_external=True, is_database=False,
            ),
        ]
        rels = [
            C4Relationship(src="graph", dst="infra", label="uses"),
            C4Relationship(src="infra", dst="ext-api", label="depends_on"),
        ]
        result = render_c4_mermaid(nodes, rels)

        # Diagram type
        assert result.startswith("C4Container")
        # Boundary for beadloom
        assert "System_Boundary(beadloom" in result
        # Containers inside boundary
        assert "Container(graph" in result
        assert "Container(infra" in result
        # External system (hyphens sanitized)
        assert "System_Ext(ext_api" in result
        # Relationships (hyphens sanitized)
        assert "Rel(graph, infra," in result
        assert "Rel(infra, ext_api," in result
        # Braces balance
        open_count = result.count("{")
        close_count = result.count("}")
        assert open_count == close_count

    def test_db_via_map_and_render(self, conn: sqlite3.Connection) -> None:
        """End-to-end: DB -> map_to_c4 -> render_c4_mermaid."""
        _insert_node(conn, "app", kind="service", summary="My App")
        _insert_node(conn, "api", kind="domain", summary="API Service")
        _insert_node(conn, "db", kind="service", summary="Database", extra={"tags": ["database"]})
        _insert_edge(conn, "api", "app", "part_of")
        _insert_edge(conn, "api", "db", "uses")

        nodes, rels = map_to_c4(conn)
        result = render_c4_mermaid(nodes, rels)

        assert "C4Container" in result
        assert "System_Boundary(app" in result
        assert "Container(api" in result
        assert "Rel(api, db," in result

    def test_nested_boundaries(self) -> None:
        """Test that nested boundaries (Container containing Components) work."""
        nodes = [
            C4Node(
                ref_id="app", label="App", c4_level="System",
                description="Root", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="graph", label="Graph", c4_level="Container",
                description="Graph domain", boundary="app",
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="loader", label="Loader", c4_level="Component",
                description="YAML Loader", boundary="graph",
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "System_Boundary(app" in result
        # The nested boundary for "graph" containing "loader"
        assert "Component(loader" in result


# ===========================================================================
# render_c4_plantuml — PlantUML C4 renderer
# ===========================================================================


class TestRenderC4PlantUMLStructure:
    """Test basic PlantUML structure: @startuml/@enduml, !include."""

    def test_empty_graph_produces_valid_skeleton(self) -> None:
        result = render_c4_plantuml([], [])
        assert result.startswith("@startuml")
        assert result.rstrip().endswith("@enduml")
        assert "!include" in result
        assert "C4_Container.puml" in result

    def test_include_url(self) -> None:
        result = render_c4_plantuml([], [])
        assert (
            "https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml"
            in result
        )


class TestRenderC4PlantUMLMacros:
    """Test that correct C4-PlantUML macros are used for each level."""

    def test_system_uses_system_macro(self) -> None:
        nodes = [
            C4Node(
                ref_id="app",
                label="My App",
                c4_level="System",
                description="Main application",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'System(app, "My App", "Main application")' in result

    def test_container_uses_container_macro(self) -> None:
        nodes = [
            C4Node(
                ref_id="web",
                label="Web Frontend",
                c4_level="Container",
                description="React SPA",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'Container(web, "Web Frontend", "", "React SPA")' in result

    def test_component_uses_component_macro(self) -> None:
        nodes = [
            C4Node(
                ref_id="loader",
                label="YAML Loader",
                c4_level="Component",
                description="Loads YAML files",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'Component(loader, "YAML Loader", "", "Loads YAML files")' in result


class TestRenderC4PlantUMLExternalAndDb:
    """Test external and database macro variants."""

    def test_external_system_uses_system_ext(self) -> None:
        nodes = [
            C4Node(
                ref_id="github",
                label="GitHub",
                c4_level="System",
                description="Git hosting",
                boundary=None,
                is_external=True,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'System_Ext(github, "GitHub", "Git hosting")' in result

    def test_database_container_uses_container_db(self) -> None:
        nodes = [
            C4Node(
                ref_id="db",
                label="SQLite DB",
                c4_level="Container",
                description="Application database",
                boundary=None,
                is_external=False,
                is_database=True,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'ContainerDb(db, "SQLite DB", "", "Application database")' in result

    def test_external_database_prefers_ext(self) -> None:
        """When both is_external and is_database, _Ext wins."""
        nodes = [
            C4Node(
                ref_id="ext_db",
                label="Cloud DB",
                c4_level="Container",
                description="External database",
                boundary=None,
                is_external=True,
                is_database=True,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'Container_Ext(ext_db, "Cloud DB", "", "External database")' in result


class TestRenderC4PlantUMLBoundary:
    """Test System_Boundary grouping."""

    def test_children_grouped_in_boundary(self) -> None:
        nodes = [
            C4Node(
                ref_id="app",
                label="My App",
                c4_level="System",
                description="Main app",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="web",
                label="Web",
                c4_level="Container",
                description="Web frontend",
                boundary="app",
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="api",
                label="API",
                c4_level="Container",
                description="REST API",
                boundary="app",
                is_external=False,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'System_Boundary(app_boundary, "My App")' in result
        assert 'Container(web, "Web", "", "Web frontend")' in result
        assert 'Container(api, "API", "", "REST API")' in result

    def test_nodes_without_boundary_are_top_level(self) -> None:
        nodes = [
            C4Node(
                ref_id="ext",
                label="External",
                c4_level="System",
                description="Ext system",
                boundary=None,
                is_external=True,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert "System_Boundary" not in result
        assert 'System_Ext(ext, "External", "Ext system")' in result


class TestRenderC4PlantUMLRelationships:
    """Test Rel() macro for relationships."""

    def test_rel_macro(self) -> None:
        nodes = [
            C4Node(
                ref_id="a",
                label="A",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="b",
                label="B",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        rels = [C4Relationship(src="a", dst="b", label="uses")]
        result = render_c4_plantuml(nodes, rels)
        assert 'Rel(a, b, "uses")' in result

    def test_multiple_rels(self) -> None:
        nodes = [
            C4Node(
                ref_id="a",
                label="A",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="b",
                label="B",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="c",
                label="C",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        rels = [
            C4Relationship(src="a", dst="b", label="uses"),
            C4Relationship(src="b", dst="c", label="depends_on"),
        ]
        result = render_c4_plantuml(nodes, rels)
        assert 'Rel(a, b, "uses")' in result
        assert 'Rel(b, c, "depends_on")' in result


class TestRenderC4PlantUMLIntegration:
    """Full integration test with realistic graph."""

    def test_realistic_graph(self, conn: sqlite3.Connection) -> None:
        """Build a realistic graph via DB, map, then render."""
        _insert_node(conn, "beadloom", kind="service", summary="Beadloom")
        _insert_node(conn, "graph", kind="domain", summary="Graph domain")
        _insert_node(conn, "infra", kind="domain", summary="Infrastructure")
        _insert_node(conn, "loader", kind="feature", summary="YAML Loader")
        _insert_node(
            conn,
            "ext-db",
            kind="service",
            summary="External DB",
            extra={"tags": ["external", "database"]},
        )

        _insert_edge(conn, "graph", "beadloom", "part_of")
        _insert_edge(conn, "infra", "beadloom", "part_of")
        _insert_edge(conn, "loader", "graph", "part_of")
        _insert_edge(conn, "graph", "infra", "uses")
        _insert_edge(conn, "infra", "ext-db", "depends_on")

        nodes, rels = map_to_c4(conn)
        result = render_c4_plantuml(nodes, rels)

        # Structure
        assert result.startswith("@startuml")
        assert result.rstrip().endswith("@enduml")
        assert "!include" in result

        # System-level nodes rendered
        assert "beadloom" in result
        assert "ext-db" in result or "ext_db" in result

        # Boundaries
        assert "System_Boundary" in result

        # Relationships
        assert 'Rel(graph, infra, "uses")' in result
        assert (
            'Rel(infra, ext_db, "depends_on")' in result
            or 'Rel(infra, ext-db, "depends_on")' in result
        )

    def test_ref_id_sanitization(self) -> None:
        """Ref IDs with hyphens should be sanitized for PlantUML identifiers."""
        nodes = [
            C4Node(
                ref_id="my-service",
                label="My Service",
                c4_level="System",
                description="A service",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        # PlantUML identifiers should use underscores, not hyphens
        assert "my_service" in result


# ===========================================================================
# filter_c4_nodes — C4 level selection (BEAD-04)
# ===========================================================================


def _build_realistic_nodes() -> tuple[list[C4Node], list[C4Relationship]]:
    """Build a realistic set of C4 nodes for filter tests.

    Graph structure:
      beadloom (System, root)
        +-- graph (Container, boundary=beadloom)
        |   +-- loader (Component, boundary=graph)
        |   +-- diff (Component, boundary=graph)
        +-- infra (Container, boundary=beadloom)
      ext-db (System, external, database, root)

    Relationships:
      graph -> infra (uses)
      infra -> ext-db (depends_on)
      loader -> diff (uses)
    """
    nodes = [
        C4Node(
            ref_id="beadloom",
            label="Beadloom",
            c4_level="System",
            description="Main system",
            boundary=None,
            is_external=False,
            is_database=False,
        ),
        C4Node(
            ref_id="graph",
            label="Graph domain",
            c4_level="Container",
            description="YAML graph",
            boundary="beadloom",
            is_external=False,
            is_database=False,
        ),
        C4Node(
            ref_id="infra",
            label="Infrastructure",
            c4_level="Container",
            description="DB layer",
            boundary="beadloom",
            is_external=False,
            is_database=False,
        ),
        C4Node(
            ref_id="loader",
            label="YAML Loader",
            c4_level="Component",
            description="Loads YAML",
            boundary="graph",
            is_external=False,
            is_database=False,
        ),
        C4Node(
            ref_id="diff",
            label="Graph Diff",
            c4_level="Component",
            description="Computes diffs",
            boundary="graph",
            is_external=False,
            is_database=False,
        ),
        C4Node(
            ref_id="ext-db",
            label="External DB",
            c4_level="System",
            description="External database",
            boundary=None,
            is_external=True,
            is_database=True,
        ),
    ]
    rels = [
        C4Relationship(src="graph", dst="infra", label="uses"),
        C4Relationship(src="infra", dst="ext-db", label="depends_on"),
        C4Relationship(src="loader", dst="diff", label="uses"),
    ]
    return nodes, rels


class TestFilterContextLevel:
    """--level=context: show only System-level nodes and external actors."""

    def test_keeps_system_nodes(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="context")
        ref_ids = {n.ref_id for n in filtered}
        assert "beadloom" in ref_ids
        assert "ext-db" in ref_ids

    def test_excludes_container_and_component(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="context")
        ref_ids = {n.ref_id for n in filtered}
        assert "graph" not in ref_ids
        assert "infra" not in ref_ids
        assert "loader" not in ref_ids
        assert "diff" not in ref_ids

    def test_keeps_external_node(self) -> None:
        """External Container nodes should be kept at context level."""
        nodes = [
            C4Node(
                ref_id="ext-svc",
                label="External SVC",
                c4_level="Container",
                description="",
                boundary=None,
                is_external=True,
                is_database=False,
            ),
        ]
        filtered, _ = filter_c4_nodes(nodes, [], level="context")
        assert len(filtered) == 1
        assert filtered[0].ref_id == "ext-svc"

    def test_filters_relationships(self) -> None:
        nodes, rels = _build_realistic_nodes()
        _, filtered_rels = filter_c4_nodes(nodes, rels, level="context")
        # graph and infra are Container -> excluded
        # Only beadloom (System) and ext-db (System) kept, no direct rel
        assert len(filtered_rels) == 0

    def test_keeps_rels_between_system_nodes(self) -> None:
        """If two System nodes have a direct relationship, it is kept."""
        nodes = [
            C4Node(
                ref_id="sys-a",
                label="A",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
            C4Node(
                ref_id="sys-b",
                label="B",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        rels = [C4Relationship(src="sys-a", dst="sys-b", label="uses")]
        _, filtered_rels = filter_c4_nodes(nodes, rels, level="context")
        assert len(filtered_rels) == 1


class TestFilterContainerLevel:
    """--level=container: show System and Container nodes (default)."""

    def test_keeps_system_and_container(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="container")
        ref_ids = {n.ref_id for n in filtered}
        assert "beadloom" in ref_ids
        assert "graph" in ref_ids
        assert "infra" in ref_ids
        assert "ext-db" in ref_ids

    def test_excludes_component(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="container")
        ref_ids = {n.ref_id for n in filtered}
        assert "loader" not in ref_ids
        assert "diff" not in ref_ids

    def test_filters_relationships(self) -> None:
        nodes, rels = _build_realistic_nodes()
        _, filtered_rels = filter_c4_nodes(nodes, rels, level="container")
        rel_pairs = {(r.src, r.dst) for r in filtered_rels}
        assert ("graph", "infra") in rel_pairs
        assert ("infra", "ext-db") in rel_pairs
        assert ("loader", "diff") not in rel_pairs

    def test_default_level_is_container(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered_default, _ = filter_c4_nodes(nodes, rels)
        filtered_explicit, _ = filter_c4_nodes(nodes, rels, level="container")
        assert {n.ref_id for n in filtered_default} == {
            n.ref_id for n in filtered_explicit
        }


class TestFilterComponentLevel:
    """--level=component --scope=<ref-id>: show internals of one container."""

    def test_shows_children_of_scope(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="component", scope="graph")
        ref_ids = {n.ref_id for n in filtered}
        assert "loader" in ref_ids
        assert "diff" in ref_ids

    def test_excludes_non_children(self) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level="component", scope="graph")
        ref_ids = {n.ref_id for n in filtered}
        assert "beadloom" not in ref_ids
        assert "infra" not in ref_ids
        assert "ext-db" not in ref_ids
        assert "graph" not in ref_ids

    def test_keeps_internal_relationships(self) -> None:
        nodes, rels = _build_realistic_nodes()
        _, filtered_rels = filter_c4_nodes(
            nodes, rels, level="component", scope="graph"
        )
        assert len(filtered_rels) == 1
        assert filtered_rels[0].src == "loader"
        assert filtered_rels[0].dst == "diff"

    def test_excludes_cross_boundary_relationships(self) -> None:
        nodes, rels = _build_realistic_nodes()
        _, filtered_rels = filter_c4_nodes(
            nodes, rels, level="component", scope="graph"
        )
        rel_pairs = {(r.src, r.dst) for r in filtered_rels}
        assert ("graph", "infra") not in rel_pairs

    def test_error_without_scope(self) -> None:
        nodes, rels = _build_realistic_nodes()
        with pytest.raises(ValueError, match="--level=component requires --scope"):
            filter_c4_nodes(nodes, rels, level="component")

    def test_error_with_unknown_scope(self) -> None:
        nodes, rels = _build_realistic_nodes()
        with pytest.raises(ValueError, match="not found in graph"):
            filter_c4_nodes(nodes, rels, level="component", scope="nonexistent")

    def test_empty_scope_returns_empty(self) -> None:
        """Scope with no children returns empty lists."""
        nodes, rels = _build_realistic_nodes()
        filtered, filtered_rels = filter_c4_nodes(
            nodes, rels, level="component", scope="ext-db"
        )
        assert filtered == []
        assert filtered_rels == []


class TestFilterEdgeCases:
    """Edge cases for filter_c4_nodes."""

    def test_empty_nodes(self) -> None:
        filtered, filtered_rels = filter_c4_nodes([], [], level="context")
        assert filtered == []
        assert filtered_rels == []

    def test_empty_container_level(self) -> None:
        filtered, filtered_rels = filter_c4_nodes([], [], level="container")
        assert filtered == []
        assert filtered_rels == []

    def test_single_system_node_context(self) -> None:
        nodes = [
            C4Node(
                ref_id="app",
                label="App",
                c4_level="System",
                description="",
                boundary=None,
                is_external=False,
                is_database=False,
            ),
        ]
        filtered, _ = filter_c4_nodes(nodes, [], level="context")
        assert len(filtered) == 1

    def test_integration_map_then_filter(self, conn: sqlite3.Connection) -> None:
        """Integration: map_to_c4 -> filter_c4_nodes pipeline."""
        _insert_node(conn, "beadloom", kind="service", summary="Beadloom")
        _insert_node(conn, "graph", kind="domain", summary="Graph domain")
        _insert_node(conn, "infra", kind="domain", summary="Infrastructure")
        _insert_node(conn, "loader", kind="feature", summary="YAML Loader")
        _insert_node(conn, "diff", kind="feature", summary="Graph Diff")
        _insert_node(
            conn,
            "ext-db",
            kind="service",
            summary="External DB",
            extra={"tags": ["external", "database"]},
        )

        _insert_edge(conn, "graph", "beadloom", "part_of")
        _insert_edge(conn, "infra", "beadloom", "part_of")
        _insert_edge(conn, "loader", "graph", "part_of")
        _insert_edge(conn, "diff", "graph", "part_of")
        _insert_edge(conn, "graph", "infra", "uses")
        _insert_edge(conn, "infra", "ext-db", "depends_on")
        _insert_edge(conn, "loader", "diff", "uses")

        all_nodes, all_rels = map_to_c4(conn)

        # Context level
        ctx_nodes, _ = filter_c4_nodes(all_nodes, all_rels, level="context")
        ctx_ids = {n.ref_id for n in ctx_nodes}
        assert ctx_ids == {"beadloom", "ext-db"}

        # Container level
        ctr_nodes, _ = filter_c4_nodes(all_nodes, all_rels, level="container")
        ctr_ids = {n.ref_id for n in ctr_nodes}
        assert ctr_ids == {"beadloom", "graph", "infra", "ext-db"}

        # Component level for graph
        comp_nodes, _ = filter_c4_nodes(
            all_nodes, all_rels, level="component", scope="graph"
        )
        comp_ids = {n.ref_id for n in comp_nodes}
        assert comp_ids == {"loader", "diff"}


# ===========================================================================
# BEAD-06: Test augmentation — edge cases, uncovered lines, CLI integration
# ===========================================================================


class TestOrphanNodeDepth:
    """Cover line 90 in _compute_depths: orphan nodes not reached by BFS."""

    def test_orphan_node_gets_depth_zero(self, conn: sqlite3.Connection) -> None:
        """A node whose part_of parent is NOT in the nodes table is orphan-like."""
        _insert_node(conn, "root", kind="service", summary="Root")
        _insert_node(conn, "orphan", kind="domain", summary="Orphan")
        # orphan says part_of "ghost" — but ghost does not exist in nodes
        _insert_edge(conn, "orphan", "ghost", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        # orphan has a part_of parent but parent is not a root (not in all_ref_ids),
        # so BFS never reaches orphan → falls through to depth 0 → System
        assert by_id["orphan"].c4_level == "System"
        # boundary should still be "ghost" (the declared parent)
        assert by_id["orphan"].boundary == "ghost"

    def test_cycle_in_part_of_does_not_hang(self, conn: sqlite3.Connection) -> None:
        """Cycle in part_of edges: BFS should not hang and nodes get a level."""
        _insert_node(conn, "a", kind="domain", summary="A")
        _insert_node(conn, "b", kind="domain", summary="B")
        _insert_edge(conn, "a", "b", "part_of")
        _insert_edge(conn, "b", "a", "part_of")

        # Both nodes are children in part_of → no roots → both become orphans
        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        # Both should get depth 0 (System) as orphans
        assert by_id["a"].c4_level == "System"
        assert by_id["b"].c4_level == "System"


class TestPlantUMLComponentVariants:
    """Cover lines 451 (Component_Ext) and 453 (ComponentDb) in _node_macro."""

    def test_external_component_plantuml(self) -> None:
        nodes = [
            C4Node(
                ref_id="ext-lib",
                label="External Library",
                c4_level="Component",
                description="Third-party lib",
                boundary=None,
                is_external=True,
                is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'Component_Ext(ext_lib, "External Library", "", "Third-party lib")' in result

    def test_database_component_plantuml(self) -> None:
        nodes = [
            C4Node(
                ref_id="cache",
                label="Redis Cache",
                c4_level="Component",
                description="In-memory store",
                boundary=None,
                is_external=False,
                is_database=True,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'ComponentDb(cache, "Redis Cache", "", "In-memory store")' in result

    def test_external_component_takes_precedence_over_db_plantuml(self) -> None:
        """When both is_external and is_database, _Ext wins for Component too."""
        nodes = [
            C4Node(
                ref_id="ext-cache",
                label="External Cache",
                c4_level="Component",
                description="Remote cache",
                boundary=None,
                is_external=True,
                is_database=True,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert 'Component_Ext(ext_cache, "External Cache", "", "Remote cache")' in result


class TestMapToC4EdgeCases:
    """Additional edge cases for map_to_c4."""

    def test_node_with_none_summary_via_permissive_schema(self) -> None:
        """summary=NULL should fall back to ref_id as label (permissive schema)."""
        # Use a schema without NOT NULL on summary to test defensive code path
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript(
            """
            CREATE TABLE nodes (
                ref_id  TEXT PRIMARY KEY,
                kind    TEXT NOT NULL,
                summary TEXT,
                source  TEXT,
                extra   TEXT DEFAULT '{}'
            );
            CREATE TABLE edges (
                src_ref_id TEXT NOT NULL,
                dst_ref_id TEXT NOT NULL,
                kind       TEXT NOT NULL,
                extra      TEXT DEFAULT '{}',
                PRIMARY KEY (src_ref_id, dst_ref_id, kind)
            );
            """
        )
        sql = (
            "INSERT INTO nodes (ref_id, kind, summary, source, extra)"
            " VALUES (?, ?, NULL, NULL, '{}')"
        )
        db.execute(sql, ("nosummary", "domain"))
        db.commit()
        nodes, _ = map_to_c4(db)
        assert nodes[0].label == "nosummary"
        assert nodes[0].description == ""
        db.close()

    def test_node_with_null_extra(self, conn: sqlite3.Connection) -> None:
        """extra=NULL should not crash — treated as empty dict."""
        sql = (
            "INSERT INTO nodes (ref_id, kind, summary, source, extra)"
            " VALUES (?, ?, ?, NULL, NULL)"
        )
        conn.execute(sql, ("nullextra", "domain", "Node"))
        conn.commit()
        nodes, _ = map_to_c4(conn)
        assert nodes[0].c4_level == "System"
        assert nodes[0].is_external is False
        assert nodes[0].is_database is False

    def test_tags_non_list_ignored(self, conn: sqlite3.Connection) -> None:
        """If tags in extra is not a list (e.g. a string), treat as empty set."""
        _insert_node(
            conn,
            "badtags",
            kind="domain",
            summary="Bad tags",
            extra={"tags": "not-a-list"},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].is_external is False
        assert nodes[0].is_database is False

    def test_explicit_c4_level_empty_string_uses_heuristic(
        self, conn: sqlite3.Connection
    ) -> None:
        """Empty string c4_level in extra should fall back to heuristic."""
        _insert_node(
            conn,
            "emptyc4",
            kind="domain",
            summary="Empty c4",
            extra={"c4_level": ""},
        )
        nodes, _ = map_to_c4(conn)
        # Root node, depth 0 → System
        assert nodes[0].c4_level == "System"

    def test_explicit_c4_level_non_string_uses_heuristic(
        self, conn: sqlite3.Connection
    ) -> None:
        """Non-string c4_level (e.g. int) should fall back to heuristic."""
        _insert_node(
            conn,
            "intc4",
            kind="domain",
            summary="Int c4",
            extra={"c4_level": 42},
        )
        nodes, _ = map_to_c4(conn)
        assert nodes[0].c4_level == "System"

    def test_unknown_edge_kind_ignored(self, conn: sqlite3.Connection) -> None:
        """Edges with unknown kinds (not part_of/uses/depends_on) are ignored."""
        _insert_node(conn, "a", kind="service", summary="A")
        _insert_node(conn, "b", kind="service", summary="B")
        _insert_edge(conn, "a", "b", "imports")

        _, rels = map_to_c4(conn)
        assert rels == []

    def test_multiple_part_of_chains(self, conn: sqlite3.Connection) -> None:
        """Verify depth computation for multiple independent chains."""
        _insert_node(conn, "sys1", kind="service", summary="System 1")
        _insert_node(conn, "sys2", kind="service", summary="System 2")
        _insert_node(conn, "c1", kind="domain", summary="Container 1")
        _insert_node(conn, "c2", kind="domain", summary="Container 2")
        _insert_edge(conn, "c1", "sys1", "part_of")
        _insert_edge(conn, "c2", "sys2", "part_of")

        nodes, _ = map_to_c4(conn)
        by_id = {n.ref_id: n for n in nodes}
        assert by_id["sys1"].c4_level == "System"
        assert by_id["sys2"].c4_level == "System"
        assert by_id["c1"].c4_level == "Container"
        assert by_id["c2"].c4_level == "Container"

    def test_nodes_sorted_by_ref_id(self, conn: sqlite3.Connection) -> None:
        """C4 nodes should be returned sorted by ref_id."""
        _insert_node(conn, "zebra", kind="service", summary="Z")
        _insert_node(conn, "alpha", kind="service", summary="A")
        _insert_node(conn, "mid", kind="service", summary="M")

        nodes, _ = map_to_c4(conn)
        ref_ids = [n.ref_id for n in nodes]
        assert ref_ids == sorted(ref_ids)


class TestRenderMermaidEdgeCases:
    """Mermaid renderer edge cases."""

    def test_nested_boundary_with_grandchildren(self) -> None:
        """Container_Boundary renders grandchildren (Component under Container)."""
        nodes = [
            C4Node(
                ref_id="app", label="App", c4_level="System",
                description="Root", boundary=None,
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="svc", label="Service", c4_level="Container",
                description="A service", boundary="app",
                is_external=False, is_database=False,
            ),
            C4Node(
                ref_id="handler", label="Handler", c4_level="Component",
                description="Request handler", boundary="svc",
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_mermaid(nodes, [])
        assert "Container_Boundary(svc_boundary" in result
        assert "Component(handler" in result

    def test_orphan_boundary_parent_not_in_nodes(self) -> None:
        """Boundary parent that is not in the node list uses parent_id as label."""
        child = C4Node(
            ref_id="child", label="Child", c4_level="Container",
            description="Orphan child", boundary="ghost",
            is_external=False, is_database=False,
        )
        result = render_c4_mermaid([child], [])
        # ghost is not in nodes, so parent_label falls back to parent_id
        assert 'System_Boundary(ghost_boundary, "ghost")' in result

    def test_ends_with_newline(self) -> None:
        result = render_c4_mermaid([], [])
        assert result.endswith("\n")


class TestRenderPlantUMLEdgeCases:
    """PlantUML renderer edge cases."""

    def test_orphan_boundary_parent_not_in_nodes(self) -> None:
        """Boundary parent that is not in the node list uses parent_id as label."""
        child = C4Node(
            ref_id="child", label="Child", c4_level="Container",
            description="Orphan child", boundary="ghost",
            is_external=False, is_database=False,
        )
        result = render_c4_plantuml([child], [])
        assert 'System_Boundary(ghost_boundary, "ghost")' in result

    def test_no_relationships_no_empty_section(self) -> None:
        """With no rels, there should be no Rel() in output."""
        nodes = [
            C4Node(
                ref_id="solo", label="Solo", c4_level="System",
                description="Alone", boundary=None,
                is_external=False, is_database=False,
            ),
        ]
        result = render_c4_plantuml(nodes, [])
        assert "Rel(" not in result

    def test_nested_boundary_for_non_top_level_parent(self) -> None:
        """When boundary parent is also a child of another, it renders separately."""
        # parent "svc" has boundary="app", and "handler" has boundary="svc"
        # but "app" is NOT in the nodes list → svc is not top-level
        svc = C4Node(
            ref_id="svc", label="Service", c4_level="Container",
            description="A svc", boundary="app",
            is_external=False, is_database=False,
        )
        handler = C4Node(
            ref_id="handler", label="Handler", c4_level="Component",
            description="A handler", boundary="svc",
            is_external=False, is_database=False,
        )
        result = render_c4_plantuml([svc, handler], [])
        # svc is not top-level (has boundary="app"), so "svc" boundary for handler
        # renders as a separate boundary group
        assert 'System_Boundary(svc_boundary, "Service")' in result
        assert "Component(handler" in result


class TestFilterParametrized:
    """Parametrized tests across all levels."""

    @pytest.mark.parametrize(
        ("level", "expected_ids"),
        [
            ("context", {"beadloom", "ext-db"}),
            ("container", {"beadloom", "graph", "infra", "ext-db"}),
        ],
    )
    def test_filter_levels(
        self, level: str, expected_ids: set[str]
    ) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(nodes, rels, level=level)
        assert {n.ref_id for n in filtered} == expected_ids

    @pytest.mark.parametrize(
        ("scope", "expected_ids"),
        [
            ("graph", {"loader", "diff"}),
            ("infra", set()),
            ("beadloom", {"graph", "infra"}),
        ],
    )
    def test_component_scopes(
        self, scope: str, expected_ids: set[str]
    ) -> None:
        nodes, rels = _build_realistic_nodes()
        filtered, _ = filter_c4_nodes(
            nodes, rels, level="component", scope=scope
        )
        assert {n.ref_id for n in filtered} == expected_ids

    def test_component_scope_empty_string_raises(self) -> None:
        """Empty string for scope should raise ValueError."""
        nodes, rels = _build_realistic_nodes()
        with pytest.raises(ValueError, match="--level=component requires --scope"):
            filter_c4_nodes(nodes, rels, level="component", scope="")


class TestC4ElementNameParametrized:
    """Parametrized _c4_element_name tests covering all level x flag combos."""

    @pytest.mark.parametrize(
        ("c4_level", "is_external", "is_database", "expected"),
        [
            ("System", False, False, "System"),
            ("System", True, False, "System_Ext"),
            ("System", False, True, "System"),
            ("System", True, True, "System_Ext"),
            ("Container", False, False, "Container"),
            ("Container", True, False, "Container_Ext"),
            ("Container", False, True, "ContainerDb"),
            ("Container", True, True, "Container_Ext"),
            ("Component", False, False, "Component"),
            ("Component", True, False, "Component_Ext"),
            ("Component", False, True, "ComponentDb"),
            ("Component", True, True, "Component_Ext"),
        ],
    )
    def test_element_name(
        self,
        c4_level: str,
        is_external: bool,
        is_database: bool,
        expected: str,
    ) -> None:
        node = C4Node(
            ref_id="x", label="X", c4_level=c4_level,
            description="", boundary=None,
            is_external=is_external, is_database=is_database,
        )
        assert _c4_element_name(node) == expected


# ===========================================================================
# CLI integration tests for graph --format=c4 / c4-plantuml
# ===========================================================================


def _setup_c4_project(tmp_path: Path) -> Path:
    """Create a project with a graph suitable for C4 testing."""
    import yaml

    project = tmp_path / "c4proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "myapp", "kind": "service", "summary": "My Application"},
                    {"ref_id": "api", "kind": "domain", "summary": "API Service"},
                    {"ref_id": "db", "kind": "service", "summary": "Database",
                     "extra": {"tags": ["database"]}},
                    {"ref_id": "handler", "kind": "feature", "summary": "Request Handler"},
                ],
                "edges": [
                    {"src": "api", "dst": "myapp", "kind": "part_of"},
                    {"src": "handler", "dst": "api", "kind": "part_of"},
                    {"src": "api", "dst": "db", "kind": "uses"},
                ],
            }
        )
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    src_dir = project / "src"
    src_dir.mkdir()

    from beadloom.infrastructure.reindex import reindex

    reindex(project)
    return project


class TestCLIC4Format:
    """CLI integration tests: beadloom graph --format=c4."""

    def test_c4_mermaid_output(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "--format=c4", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "C4Container" in result.output

    def test_c4_plantuml_output(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["graph", "--format=c4-plantuml", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "@startuml" in result.output
        assert "@enduml" in result.output

    def test_c4_level_context(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["graph", "--format=c4", "--level=context", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert "C4Container" in result.output
        # At context level only System nodes shown — api (Container) should be filtered
        assert "Container(api" not in result.output

    def test_c4_level_container(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["graph", "--format=c4", "--level=container", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        # Component "handler" should be excluded at container level
        assert "handler" not in result.output

    def test_c4_level_component_with_scope(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "graph",
                "--format=c4",
                "--level=component",
                "--scope=api",
                "--project",
                str(project),
            ],
        )
        assert result.exit_code == 0, result.output
        # Should show handler (child of api)
        assert "handler" in result.output

    def test_c4_level_component_without_scope_errors(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["graph", "--format=c4", "--level=component", "--project", str(project)],
        )
        assert result.exit_code != 0

    def test_c4_level_component_unknown_scope_errors(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "graph",
                "--format=c4",
                "--level=component",
                "--scope=nonexistent",
                "--project",
                str(project),
            ],
        )
        assert result.exit_code != 0

    def test_c4_plantuml_level_context(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = _setup_c4_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "graph",
                "--format=c4-plantuml",
                "--level=context",
                "--project",
                str(project),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "@startuml" in result.output
        assert "@enduml" in result.output
