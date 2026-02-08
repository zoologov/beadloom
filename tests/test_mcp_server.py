"""Tests for beadloom.mcp_server — MCP tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.db import open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project with graph, docs, code and reindex."""
    import yaml

    proj = tmp_path / "proj"
    proj.mkdir()

    graph_dir = proj / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump({
            "nodes": [
                {
                    "ref_id": "FEAT-1",
                    "kind": "feature",
                    "summary": "Track filtering",
                    "docs": ["docs/spec.md"],
                },
                {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
            ],
            "edges": [
                {"src": "FEAT-1", "dst": "routing", "kind": "part_of"},
            ],
        })
    )

    docs_dir = proj / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    src_dir = proj / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text(
        "# beadloom:feature=FEAT-1\ndef list_tracks():\n    pass\n"
    )

    from beadloom.reindex import reindex

    reindex(proj)
    return proj


@pytest.fixture()
def db_conn(project: Path) -> sqlite3.Connection:
    db_path = project / ".beadloom" / "beadloom.db"
    return open_db(db_path)


class TestMcpToolHandlers:
    """Test MCP tool handler functions directly (without transport)."""

    def test_handle_get_context(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_context

        result = handle_get_context(db_conn, ref_id="FEAT-1")
        assert result["version"] == 1
        assert result["focus"]["ref_id"] == "FEAT-1"

    def test_handle_get_context_with_params(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_context

        result = handle_get_context(db_conn, ref_id="FEAT-1", depth=1, max_nodes=5, max_chunks=3)
        assert result["version"] == 1

    def test_handle_get_context_not_found(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_context

        with pytest.raises(LookupError, match="not found"):
            handle_get_context(db_conn, ref_id="NONEXISTENT")

    def test_handle_get_graph(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_graph

        result = handle_get_graph(db_conn, ref_id="FEAT-1")
        assert "nodes" in result
        assert "edges" in result
        node_ids = {n["ref_id"] for n in result["nodes"]}
        assert "FEAT-1" in node_ids

    def test_handle_get_graph_depth(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_graph

        result = handle_get_graph(db_conn, ref_id="FEAT-1", depth=1)
        assert "nodes" in result

    def test_handle_list_nodes(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_list_nodes

        result = handle_list_nodes(db_conn)
        assert len(result) >= 2
        assert any(n["ref_id"] == "FEAT-1" for n in result)

    def test_handle_list_nodes_filtered(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_list_nodes

        result = handle_list_nodes(db_conn, kind="domain")
        assert all(n["kind"] == "domain" for n in result)

    def test_handle_sync_check(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_sync_check

        result = handle_sync_check(db_conn)
        assert isinstance(result, list)

    def test_handle_sync_check_with_ref(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_sync_check

        result = handle_sync_check(db_conn, ref_id="FEAT-1")
        assert isinstance(result, list)

    def test_handle_get_status(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.mcp_server import handle_get_status

        result = handle_get_status(db_conn)
        assert "nodes_count" in result
        assert "edges_count" in result
        assert "docs_count" in result

    def test_create_server(self, project: Path) -> None:
        from beadloom.mcp_server import create_server

        server = create_server(project)
        assert server is not None
