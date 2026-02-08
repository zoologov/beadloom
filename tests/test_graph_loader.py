"""Tests for beadloom.graph_loader — YAML graph parsing and SQLite loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.db import create_schema, open_db
from beadloom.graph_loader import load_graph, parse_graph_file

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
            "nodes:\n"
            "  - ref_id: routing\n"
            "    kind: domain\n"
            '    summary: "Routing domain"\n'
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
            "nodes:\n"
            "  - ref_id: Track\n"
            "    kind: entity\n"
            '    summary: "Track record"\n'
        )
        result = parse_graph_file(yml)
        assert len(result.nodes) == 1
        assert result.edges == []


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
            "nodes:\n"
            "  - ref_id: dom1\n"
            "    kind: domain\n"
            '    summary: "D1"\n'
        )
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: svc1\n"
            "    kind: service\n"
            '    summary: "S1"\n'
        )
        result = load_graph(graph_dir, db)
        assert result.nodes_loaded == 2

    def test_duplicate_ref_id_error(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "a.yml").write_text(
            "nodes:\n"
            "  - ref_id: dup\n"
            "    kind: domain\n"
            '    summary: "First"\n'
        )
        (graph_dir / "b.yml").write_text(
            "nodes:\n"
            "  - ref_id: dup\n"
            "    kind: service\n"
            '    summary: "Second"\n'
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

    def test_edges_across_files(self, db: sqlite3.Connection, graph_dir: Path) -> None:
        (graph_dir / "domains.yml").write_text(
            "nodes:\n"
            "  - ref_id: dom\n"
            "    kind: domain\n"
            '    summary: "D"\n'
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
