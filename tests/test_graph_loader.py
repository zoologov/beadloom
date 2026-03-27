"""Tests for beadloom.graph_loader — YAML graph parsing and SQLite loading."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.loader import GraphParseError, load_graph, parse_graph_file
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    conn = open_db(tmp_path / "test.db")
    create_schema(conn)
    return conn


@pytest.fixture()
def graph_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".beadloom" / "_graph"
    d.mkdir(parents=True)
    return d


# --- parse_graph_file ---


class TestParseGraphFile:
    def test_parse_nodes(self, graph_dir: Path) -> None:
        yml = graph_dir / "domains.yml"
        yml.write_text(
            'nodes:\n  - ref_id: routing\n    kind: domain\n    summary: "Routing domain"\n'
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 1
        assert result.nodes[0]["ref_id"] == "routing"
        assert result.nodes[0]["kind"] == "domain"

    def test_parse_edges(self, graph_dir: Path) -> None:
        yml = graph_dir / "features.yml"
        yml.write_text(
            "nodes:\n"
            "  - ref_id: PROJ-1\n"
            "    kind: feature\n"
            '    summary: "Feature"\n'
            "edges:\n"
            "  - src: PROJ-1\n"
            "    dst: routing\n"
            "    kind: part_of\n"
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert result.edges[0]["src"] == "PROJ-1"
        assert result.edges[0]["dst"] == "routing"

    def test_parse_docs_field(self, graph_dir: Path) -> None:
        yml = graph_dir / "features.yml"
        yml.write_text(
            "nodes:\n"
            "  - ref_id: PROJ-1\n"
            "    kind: feature\n"
            '    summary: "F"\n'
            "    docs:\n"
            "      - docs/spec.md\n"
            "      - docs/api.md\n"
        )
        result = parse_graph_file(yml)
        assert result.nodes[0]["docs"] == ["docs/spec.md", "docs/api.md"]

    def test_parse_extra_fields(self, graph_dir: Path) -> None:
        yml = graph_dir / "services.yml"
        yml.write_text(
            "nodes:\n"
            "  - ref_id: api-gw\n"
            "    kind: service\n"
            '    summary: "API Gateway"\n'
            "    source: src/api/\n"
            "    confidence: high\n"
        )
        result = parse_graph_file(yml)
        node = result.nodes[0]
        assert node["source"] == "src/api/"
        assert node.get("confidence") == "high"

    def test_empty_file(self, graph_dir: Path) -> None:
        yml = graph_dir / "empty.yml"
        yml.write_text("")
        result = parse_graph_file(yml)
        assert result.nodes == []
        assert result.edges == []

    def test_nodes_only_no_edges(self, graph_dir: Path) -> None:
        yml = graph_dir / "entities.yml"
        yml.write_text(
            'nodes:\n  - ref_id: Track\n    kind: entity\n    summary: "Track record"\n'
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 1
        assert result.edges == []

    def test_parse_flow_style_edges(self, graph_dir: Path) -> None:
        """Flow-style (inline) mapping edges are valid YAML; parse identically (#86)."""
        yml = graph_dir / "services.yml"
        yml.write_text(
            "nodes:\n"
            "  - ref_id: houses\n"
            "    kind: service\n"
            '    summary: "Houses"\n'
            "  - ref_id: core\n"
            "    kind: service\n"
            '    summary: "Core"\n'
            "edges:\n"
            "  - { src: houses, dst: core, kind: depends_on }\n"
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.edges[0]["src"] == "houses"
        assert result.edges[0]["dst"] == "core"
        assert result.edges[0]["kind"] == "depends_on"

    def test_parse_flow_style_nodes(self, graph_dir: Path) -> None:
        """Flow-style mapping nodes are valid YAML; parse identically (#86)."""
        yml = graph_dir / "services.yml"
        yml.write_text(
            "nodes:\n"
            "  - { ref_id: houses, kind: service, summary: Houses }\n"
            "  - { ref_id: core, kind: service, summary: Core }\n"
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 2
        assert result.nodes[0]["ref_id"] == "houses"
        assert result.nodes[1]["ref_id"] == "core"

    def test_tab_indented_yaml_raises_clear_error(self, graph_dir: Path) -> None:
        """Tab characters are invalid YAML indentation; raise a clear, line-referenced
        error instead of silently returning 0 nodes (#86)."""
        yml = graph_dir / "services.yml"
        # Tabs after the list dash are a common manual-editing footgun that makes
        # PyYAML raise -- which previously bubbled up as a silent reindex failure.
        yml.write_text("nodes:\n\t- ref_id: houses\n\t  kind: service\n")
        with pytest.raises(GraphParseError) as exc_info:
            parse_graph_file(yml)
        msg = str(exc_info.value)
        assert "services.yml" in msg
        assert "line" in msg.lower()


# --- load_graph ---


class TestLoadGraph:
    def test_loads_nodes_into_db(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "domains.yml").write_text(
            "nodes:\n"
            "  - ref_id: routing\n"
            "    kind: domain\n"
            '    summary: "Routing"\n'
            "  - ref_id: billing\n"
            "    kind: domain\n"
            '    summary: "Billing"\n'
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 2
        rows = db.execute("SELECT ref_id, kind, summary FROM nodes ORDER BY ref_id").fetchall()
        assert len(rows) == 2
        assert rows[0]["ref_id"] == "billing"
        assert rows[1]["ref_id"] == "routing"

    def test_loads_edges_into_db(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "all.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc\n"
            "    kind: service\n"
            '    summary: "S"\n'
            "  - ref_id: dom\n"
            "    kind: domain\n"
            '    summary: "D"\n'
            "edges:\n"
            "  - src: svc\n"
            "    dst: dom\n"
            "    kind: part_of\n"
        )
        result = load_graph(graph_dir, db)
        assert result.edges_loaded == 1
        row = db.execute("SELECT * FROM edges").fetchone()
        assert row["src_ref_id"] == "svc"
        assert row["dst_ref_id"] == "dom"
        assert row["kind"] == "part_of"

    def test_extra_fields_stored_as_json(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "s.yml").write_text(
            "nodes:\n"
            "  - ref_id: api\n"
            "    kind: service\n"
            '    summary: "API"\n'
            "    source: src/api/\n"
            "    confidence: high\n"
            "    team: backend\n"
        )
        load_graph(graph_dir, db)
        import json

        row = db.execute("SELECT source, extra FROM nodes WHERE ref_id = ?", ("api",)).fetchone()
        assert row["source"] == "src/api/"
        extra = json.loads(row["extra"])
        assert extra["confidence"] == "high"
        assert extra["team"] == "backend"

    def test_multiple_yml_files(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: dom1\n    kind: domain\n    summary: "D1"\n'
        )
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: svc1\n    kind: service\n    summary: "S1"\n'
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 2

    def test_duplicate_ref_id_error(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "a.yml").write_text(
            'nodes:\n  - ref_id: dup\n    kind: domain\n    summary: "First"\n'
        )
        (graph_dir / "b.yml").write_text(
            'nodes:\n  - ref_id: dup\n    kind: service\n    summary: "Second"\n'
        )
        result = load_graph(graph_dir, db)
        assert len(result.errors) > 0
        assert any("dup" in e for e in result.errors)

    def test_broken_edge_warning(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: feat1\n"
            "    kind: feature\n"
            '    summary: "F"\n'
            "edges:\n"
            "  - src: feat1\n"
            "    dst: nonexistent\n"
            "    kind: part_of\n"
        )
        result = load_graph(graph_dir, db)
        assert len(result.warnings) > 0
        assert any("nonexistent" in w for w in result.warnings)
        assert result.edges_loaded == 0

    def test_empty_graph_dir(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 0
        assert result.edges_loaded == 0
        assert result.errors == []

    def test_no_yml_files(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "readme.txt").write_text("not a yml file")
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 0

    def test_node_with_docs_creates_doc_refs(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """Node docs field should NOT create docs table entries during graph load.

        Doc indexing is a separate concern (BEAD-04). Graph loader only loads
        nodes and edges.
        """
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: feat\n"
            "    kind: feature\n"
            '    summary: "F"\n'
            "    docs:\n"
            "      - docs/spec.md\n"
        )
        load_graph(graph_dir, db)
        # docs field is stored in extra, actual doc indexing is BEAD-04
        docs_count = db.execute("SELECT count(*) FROM docs").fetchone()[0]
        assert docs_count == 0

    def test_flow_style_edges_loaded(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        """Flow-style edges load into the DB identically to block style (#86)."""
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - { ref_id: houses, kind: service, summary: Houses }\n"
            "  - { ref_id: core, kind: service, summary: Core }\n"
            "edges:\n"
            "  - { src: houses, dst: core, kind: depends_on }\n"
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 2
        assert result.edges_loaded == 1
        row = db.execute("SELECT * FROM edges").fetchone()
        assert row["src_ref_id"] == "houses"
        assert row["dst_ref_id"] == "core"

    def test_edges_across_files(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: dom\n    kind: domain\n    summary: "D"\n'
        )
        (graph_dir / "features.yml").write_text(
            "nodes:\n"
            "  - ref_id: feat\n"
            "    kind: feature\n"
            '    summary: "F"\n'
            "edges:\n"
            "  - src: feat\n"
            "    dst: dom\n"
            "    kind: part_of\n"
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 2
        assert result.edges_loaded == 1
        assert result.warnings == []


class TestLoadGraphFederation:
    """Cross-repo node identity (@repo:ref_id) at load time (BDL-037 BEAD-01)."""

    def test_foreign_dst_recorded_not_dangling(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """A foreign target (@repo:id) is a foreign edge, NOT a dangling warning."""
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n'
            "edges:\n"
            "  - src: plans\n"
            "    dst: '@integration-service:queue'\n"
            "    kind: depends_on\n"
        )
        result = load_graph(graph_dir, db)
        # Not a dangling/broken-edge warning.
        assert not any("queue" in w for w in result.warnings)
        # Surfaced as a foreign edge instead.
        assert len(result.foreign_edges) == 1
        fe = result.foreign_edges[0]
        assert fe.src == "plans"
        assert fe.dst == "@integration-service:queue"
        assert fe.kind == "depends_on"
        # Foreign edges are not inserted into the local edges table.
        assert result.edges_loaded == 0
        assert db.execute("SELECT count(*) FROM edges").fetchone()[0] == 0

    def test_foreign_src_recorded(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n'
            "edges:\n"
            "  - src: '@core-monolith:orders'\n"
            "    dst: plans\n"
            "    kind: depends_on\n"
        )
        result = load_graph(graph_dir, db)
        assert len(result.foreign_edges) == 1
        assert result.foreign_edges[0].src == "@core-monolith:orders"
        assert result.edges_loaded == 0

    def test_malformed_foreign_src_is_error(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n'
            "edges:\n"
            "  - src: '@:x'\n"
            "    dst: plans\n"
            "    kind: depends_on\n"
        )
        result = load_graph(graph_dir, db)
        assert any("@:x" in e for e in result.errors)
        assert result.edges_loaded == 0
        assert result.foreign_edges == []

    def test_malformed_foreign_dst_is_error(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n'
            "edges:\n"
            "  - src: plans\n"
            "    dst: '@repo:'\n"
            "    kind: depends_on\n"
        )
        result = load_graph(graph_dir, db)
        assert any("@repo:" in e for e in result.errors)
        assert result.edges_loaded == 0

    def test_local_edges_unchanged_no_foreign(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """No regression: a purely local graph yields zero foreign edges."""
        (graph_dir / "all.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc\n"
            "    kind: service\n"
            '    summary: "S"\n'
            "  - ref_id: dom\n"
            "    kind: domain\n"
            '    summary: "D"\n'
            "edges:\n"
            "  - src: svc\n"
            "    dst: dom\n"
            "    kind: part_of\n"
        )
        result = load_graph(graph_dir, db)
        assert result.edges_loaded == 1
        assert result.foreign_edges == []
        assert result.warnings == []

    def test_foreign_edge_persisted_to_foreign_edges_table(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """A declared @repo: edge is persisted so export can surface it (#100)."""
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: plans\n"
            "    kind: feature\n"
            '    summary: "Plans"\n'
            "edges:\n"
            "  - src: plans\n"
            "    dst: '@integration-service:queue'\n"
            "    kind: depends_on\n"
            "    lifecycle: planned\n"
        )
        load_graph(graph_dir, db)
        rows = db.execute(
            "SELECT src_ref_id, dst_ref_id, kind, lifecycle FROM foreign_edges"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["src_ref_id"] == "plans"
        assert rows[0]["dst_ref_id"] == "@integration-service:queue"
        assert rows[0]["kind"] == "depends_on"
        assert rows[0]["lifecycle"] == "planned"

    def test_foreign_edge_carries_contract_extra(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """A cross-repo contract edge keeps its contract payload in extra."""
        (graph_dir / "f.yml").write_text(
            "nodes:\n"
            "  - ref_id: producer\n"
            "    kind: service\n"
            '    summary: "P"\n'
            "edges:\n"
            "  - src: producer\n"
            "    dst: '@other:queue'\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: m1\n"
            "      direction: produces\n"
        )
        load_graph(graph_dir, db)
        row = db.execute("SELECT extra, kind FROM foreign_edges").fetchone()
        assert row["kind"] == "produces"
        extra = json.loads(row["extra"])
        assert extra["contract"]["message_type"] == "m1"


class TestLoadGraphContractEdges:
    """Contract edges with produces/consumes kinds + per-message identity."""

    def test_produces_edge_loaded_into_db(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """A local produces edge persists through the real DB path (#101)."""
        (graph_dir / "c.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc\n"
            "    kind: service\n"
            '    summary: "S"\n'
            "  - ref_id: q\n"
            "    kind: feature\n"
            '    summary: "Q"\n'
            "edges:\n"
            "  - src: svc\n"
            "    dst: q\n"
            "    kind: produces\n"
        )
        result = load_graph(graph_dir, db)
        assert result.edges_loaded == 1
        assert result.warnings == []
        row = db.execute("SELECT kind FROM edges").fetchone()
        assert row["kind"] == "produces"

    def test_two_contracts_same_pair_both_loaded(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """Two AMQP contracts on one node pair both survive (#102)."""
        (graph_dir / "c.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc\n"
            "    kind: service\n"
            '    summary: "S"\n'
            "  - ref_id: q\n"
            "    kind: feature\n"
            '    summary: "Q"\n'
            "edges:\n"
            "  - src: svc\n"
            "    dst: q\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: msg_a\n"
            "  - src: svc\n"
            "    dst: q\n"
            "    kind: produces\n"
            "    contract:\n"
            "      protocol: amqp\n"
            "      message_type: msg_b\n"
        )
        result = load_graph(graph_dir, db)
        assert result.edges_loaded == 2
        assert result.warnings == []
        keys = {
            r["contract_key"]
            for r in db.execute("SELECT contract_key FROM edges").fetchall()
        }
        assert keys == {"msg_a", "msg_b"}


# --- lifecycle field (BEAD-02) ---


class TestNodeLifecycle:
    def test_node_lifecycle_loaded(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "n.yml").write_text(
            "nodes:\n"
            "  - ref_id: legacy\n"
            "    kind: domain\n"
            '    summary: "Old domain"\n'
            "    lifecycle: deprecated\n"
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 1
        row = db.execute("SELECT lifecycle FROM nodes WHERE ref_id = 'legacy'").fetchone()
        assert row[0] == "deprecated"

    def test_node_lifecycle_defaults_active(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """No regression: a node without lifecycle defaults to 'active'."""
        (graph_dir / "n.yml").write_text(
            "nodes:\n  - ref_id: routing\n    kind: domain\n    summary: \"R\"\n"
        )
        load_graph(graph_dir, db)
        row = db.execute("SELECT lifecycle FROM nodes WHERE ref_id = 'routing'").fetchone()
        assert row[0] == "active"

    def test_node_lifecycle_not_in_extra(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        """lifecycle is a first-class column, not dumped into extra JSON."""
        import json

        (graph_dir / "n.yml").write_text(
            "nodes:\n"
            "  - ref_id: routing\n"
            "    kind: domain\n"
            '    summary: "R"\n'
            "    lifecycle: planned\n"
        )
        load_graph(graph_dir, db)
        row = db.execute("SELECT extra FROM nodes WHERE ref_id = 'routing'").fetchone()
        extra = json.loads(row[0])
        assert "lifecycle" not in extra

    def test_invalid_node_lifecycle_recorded(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        (graph_dir / "n.yml").write_text(
            "nodes:\n"
            "  - ref_id: routing\n"
            "    kind: domain\n"
            '    summary: "R"\n'
            "    lifecycle: bogus\n"
        )
        result = load_graph(graph_dir, db)
        assert any("bogus" in e for e in result.errors)
        # Node still loaded with safe default.
        row = db.execute("SELECT lifecycle FROM nodes WHERE ref_id = 'routing'").fetchone()
        assert row[0] == "active"


class TestEdgeLifecycle:
    def test_edge_lifecycle_loaded(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "g.yml").write_text(
            "nodes:\n"
            "  - ref_id: a\n    kind: domain\n    summary: A\n"
            "  - ref_id: b\n    kind: domain\n    summary: B\n"
            "edges:\n"
            "  - src: a\n    dst: b\n    kind: depends_on\n    lifecycle: planned\n"
        )
        result = load_graph(graph_dir, db)
        assert result.edges_loaded == 1
        row = db.execute("SELECT lifecycle FROM edges WHERE src_ref_id = 'a'").fetchone()
        assert row[0] == "planned"

    def test_edge_lifecycle_defaults_active(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        (graph_dir / "g.yml").write_text(
            "nodes:\n"
            "  - ref_id: a\n    kind: domain\n    summary: A\n"
            "  - ref_id: b\n    kind: domain\n    summary: B\n"
            "edges:\n"
            "  - src: a\n    dst: b\n    kind: depends_on\n"
        )
        load_graph(graph_dir, db)
        row = db.execute("SELECT lifecycle FROM edges WHERE src_ref_id = 'a'").fetchone()
        assert row[0] == "active"

    def test_edge_lifecycle_not_in_extra(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        import json

        (graph_dir / "g.yml").write_text(
            "nodes:\n"
            "  - ref_id: a\n    kind: domain\n    summary: A\n"
            "  - ref_id: b\n    kind: domain\n    summary: B\n"
            "edges:\n"
            "  - src: a\n    dst: b\n    kind: depends_on\n    lifecycle: deprecated\n"
        )
        load_graph(graph_dir, db)
        row = db.execute("SELECT extra FROM edges WHERE src_ref_id = 'a'").fetchone()
        extra = json.loads(row[0])
        assert "lifecycle" not in extra

    def test_invalid_edge_lifecycle_recorded(
        self, db: sqlite3.Connection, graph_dir: Path
    ) -> None:
        (graph_dir / "g.yml").write_text(
            "nodes:\n"
            "  - ref_id: a\n    kind: domain\n    summary: A\n"
            "  - ref_id: b\n    kind: domain\n    summary: B\n"
            "edges:\n"
            "  - src: a\n    dst: b\n    kind: depends_on\n    lifecycle: nope\n"
        )
        result = load_graph(graph_dir, db)
        assert any("nope" in m for m in result.warnings + result.errors)
        row = db.execute("SELECT lifecycle FROM edges WHERE src_ref_id = 'a'").fetchone()
        assert row[0] == "active"
