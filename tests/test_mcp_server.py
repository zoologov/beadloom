"""Tests for beadloom.services.mcp_server — MCP tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import open_db

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
        yaml.dump(
            {
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
            }
        )
    )

    docs_dir = proj / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    src_dir = proj / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=FEAT-1\ndef list_tracks():\n    pass\n")

    from beadloom.infrastructure.reindex import reindex

    reindex(proj)
    return proj


@pytest.fixture()
def db_conn(project: Path) -> sqlite3.Connection:
    db_path = project / ".beadloom" / "beadloom.db"
    return open_db(db_path)


class TestMcpToolHandlers:
    """Test MCP tool handler functions directly (without transport)."""

    def test_handle_get_context(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_context

        result = handle_get_context(db_conn, ref_id="FEAT-1")
        assert result["version"] == 2
        assert result["focus"]["ref_id"] == "FEAT-1"

    def test_handle_get_context_with_params(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_context

        result = handle_get_context(db_conn, ref_id="FEAT-1", depth=1, max_nodes=5, max_chunks=3)
        assert result["version"] == 2

    def test_handle_get_context_not_found(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_context

        with pytest.raises(LookupError, match="not found"):
            handle_get_context(db_conn, ref_id="NONEXISTENT")

    def test_handle_get_graph(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_graph

        result = handle_get_graph(db_conn, ref_id="FEAT-1")
        assert "nodes" in result
        assert "edges" in result
        node_ids = {n["ref_id"] for n in result["nodes"]}
        assert "FEAT-1" in node_ids

    def test_handle_get_graph_depth(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_graph

        result = handle_get_graph(db_conn, ref_id="FEAT-1", depth=1)
        assert "nodes" in result

    def test_handle_list_nodes(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_list_nodes

        result = handle_list_nodes(db_conn)
        assert len(result) >= 2
        assert any(n["ref_id"] == "FEAT-1" for n in result)

    def test_handle_list_nodes_filtered(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_list_nodes

        result = handle_list_nodes(db_conn, kind="domain")
        assert all(n["kind"] == "domain" for n in result)

    def test_handle_sync_check(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_sync_check

        result = handle_sync_check(db_conn)
        assert isinstance(result, list)

    def test_handle_sync_check_with_ref(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_sync_check

        result = handle_sync_check(db_conn, ref_id="FEAT-1")
        assert isinstance(result, list)

    def test_handle_get_status(self, db_conn: sqlite3.Connection) -> None:
        from beadloom.services.mcp_server import handle_get_status

        result = handle_get_status(db_conn)
        assert "nodes_count" in result
        assert "edges_count" in result
        assert "docs_count" in result

    def test_create_server(self, project: Path) -> None:
        from beadloom.services.mcp_server import create_server

        server = create_server(project)
        assert server is not None


class TestDispatchTool:
    """Test _dispatch_tool routing to correct handlers."""

    def test_dispatch_get_context(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"ref_id": "FEAT-1"}

        # Act
        result = _dispatch_tool(db_conn, "get_context", args)

        # Assert
        assert result["version"] == 2
        assert result["focus"]["ref_id"] == "FEAT-1"

    def test_dispatch_get_context_with_optional_args(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"ref_id": "FEAT-1", "depth": 1, "max_nodes": 5, "max_chunks": 3}

        # Act
        result = _dispatch_tool(db_conn, "get_context", args)

        # Assert
        assert result["version"] == 2
        assert result["focus"]["ref_id"] == "FEAT-1"

    def test_dispatch_get_graph(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"ref_id": "FEAT-1"}

        # Act
        result = _dispatch_tool(db_conn, "get_graph", args)

        # Assert
        assert "nodes" in result
        assert "edges" in result
        node_ids = {n["ref_id"] for n in result["nodes"]}
        assert "FEAT-1" in node_ids

    def test_dispatch_get_graph_with_depth(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"ref_id": "FEAT-1", "depth": 1}

        # Act
        result = _dispatch_tool(db_conn, "get_graph", args)

        # Assert
        assert "nodes" in result

    def test_dispatch_list_nodes(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args: dict[str, str] = {}

        # Act
        result = _dispatch_tool(db_conn, "list_nodes", args)

        # Assert
        assert len(result) >= 2
        assert any(n["ref_id"] == "FEAT-1" for n in result)

    def test_dispatch_list_nodes_with_kind(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"kind": "domain"}

        # Act
        result = _dispatch_tool(db_conn, "list_nodes", args)

        # Assert
        assert all(n["kind"] == "domain" for n in result)

    def test_dispatch_sync_check(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args: dict[str, str] = {}

        # Act
        result = _dispatch_tool(db_conn, "sync_check", args)

        # Assert
        assert isinstance(result, list)

    def test_dispatch_sync_check_with_ref_id(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args = {"ref_id": "FEAT-1"}

        # Act
        result = _dispatch_tool(db_conn, "sync_check", args)

        # Assert
        assert isinstance(result, list)

    def test_dispatch_get_status(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args: dict[str, str] = {}

        # Act
        result = _dispatch_tool(db_conn, "get_status", args)

        # Assert
        assert "nodes_count" in result
        assert "edges_count" in result
        assert "docs_count" in result

    def test_dispatch_unknown_tool(self, db_conn: sqlite3.Connection) -> None:
        # Arrange
        from beadloom.services.mcp_server import _dispatch_tool

        args: dict[str, str] = {}

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown tool: unknown"):
            _dispatch_tool(db_conn, "unknown", args)


class TestCacheIntegration:
    """Test L1 cache integration in MCP dispatch."""

    def test_first_call_returns_full_bundle(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        result = _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
        )
        assert result["version"] == 2
        assert result["focus"]["ref_id"] == "FEAT-1"

    def test_second_call_returns_cached_response(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        args = {"ref_id": "FEAT-1"}

        # First call — full bundle
        r1 = _dispatch_tool(
            db_conn,
            "get_context",
            args,
            project_root=project,
            cache=cache,
        )
        assert r1["version"] == 2

        # Second call — cached short response
        r2 = _dispatch_tool(
            db_conn,
            "get_context",
            args,
            project_root=project,
            cache=cache,
        )
        assert r2["cached"] is True
        assert r2["etag"].startswith("sha256:")
        assert "unchanged_since" in r2
        assert "hint" in r2

    def test_cache_invalidated_on_graph_change(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        import time

        from beadloom.context_oracle.cache import ContextCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        args = {"ref_id": "FEAT-1"}

        # Populate cache
        _dispatch_tool(
            db_conn,
            "get_context",
            args,
            project_root=project,
            cache=cache,
        )

        # Touch graph file
        time.sleep(0.05)
        graph_file = project / ".beadloom" / "_graph" / "graph.yml"
        graph_file.write_text(graph_file.read_text())

        # Should get full response (cache invalidated by mtime)
        r = _dispatch_tool(
            db_conn,
            "get_context",
            args,
            project_root=project,
            cache=cache,
        )
        assert r["version"] == 2
        assert "cached" not in r

    def test_graph_tool_cached(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        args = {"ref_id": "FEAT-1"}

        # First call — full result
        r1 = _dispatch_tool(
            db_conn,
            "get_graph",
            args,
            project_root=project,
            cache=cache,
        )
        assert "nodes" in r1

        # Second call — cached
        r2 = _dispatch_tool(
            db_conn,
            "get_graph",
            args,
            project_root=project,
            cache=cache,
        )
        assert r2["cached"] is True
        assert r2["etag"].startswith("sha256:")

    def test_no_cache_falls_back_to_full_bundle(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        # Without cache parameter — original behavior
        r = _dispatch_tool(db_conn, "get_context", {"ref_id": "FEAT-1"})
        assert r["version"] == 2
        assert "cached" not in r


class TestL2CacheIntegration:
    """Test L2 (SQLite) cache integration in MCP dispatch."""

    def test_l2_stores_on_first_call(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache, SqliteCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        l2 = SqliteCache(db_conn)
        result = _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )
        assert result["version"] == 2

        # L2 should have the entry now.
        l2_result = l2.get("FEAT-1:2:20:10")
        assert l2_result is not None

    def test_l2_hit_populates_l1(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache, SqliteCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        l2 = SqliteCache(db_conn)

        # First call fills both caches.
        _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )

        # Clear L1, keep L2.
        cache.clear()

        # Second call should hit L2 and return full bundle (not cached response).
        result = _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )
        assert result["version"] == 2
        assert "cached" not in result  # Full bundle, not short response.

        # Now L1 is populated, third call returns cached response.
        result3 = _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )
        assert result3["cached"] is True

    def test_l2_graph_tool_cached(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache, SqliteCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        l2 = SqliteCache(db_conn)

        _dispatch_tool(
            db_conn,
            "get_graph",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )

        # L2 should have graph entry.
        l2_result = l2.get("graph:FEAT-1:2")
        assert l2_result is not None

    def test_l2_invalidated_on_update_node(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.context_oracle.cache import ContextCache, SqliteCache
        from beadloom.services.mcp_server import _dispatch_tool

        cache = ContextCache()
        l2 = SqliteCache(db_conn)

        # Populate cache.
        _dispatch_tool(
            db_conn,
            "get_context",
            {"ref_id": "FEAT-1"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )
        assert l2.get("FEAT-1:2:20:10") is not None

        # update_node should invalidate L2.
        _dispatch_tool(
            db_conn,
            "update_node",
            {"ref_id": "FEAT-1", "summary": "New summary"},
            project_root=project,
            cache=cache,
            l2_cache=l2,
        )
        assert l2.get("FEAT-1:2:20:10") is None


class TestWriteTools:
    """Test MCP write tool handlers."""

    def test_update_node_summary(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_update_node

        result = handle_update_node(
            db_conn,
            project,
            ref_id="FEAT-1",
            summary="Updated summary",
        )
        assert result["updated"] is True

        # Verify SQLite updated.
        row = db_conn.execute("SELECT summary FROM nodes WHERE ref_id = ?", ("FEAT-1",)).fetchone()
        assert row["summary"] == "Updated summary"

        # Verify YAML updated.
        import yaml

        graph_file = project / ".beadloom" / "_graph" / "graph.yml"
        data = yaml.safe_load(graph_file.read_text())
        node = next(n for n in data["nodes"] if n["ref_id"] == "FEAT-1")
        assert node["summary"] == "Updated summary"

    def test_update_node_not_found(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_update_node

        with pytest.raises(LookupError, match="not found"):
            handle_update_node(
                db_conn,
                project,
                ref_id="NONEXISTENT",
                summary="x",
            )

    def test_mark_synced(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_mark_synced

        result = handle_mark_synced(db_conn, project, ref_id="FEAT-1")
        assert "pairs_synced" in result

    def test_search_by_keyword(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_search

        results = handle_search(db_conn, query="Track")
        assert len(results) >= 1
        assert any(r["ref_id"] == "FEAT-1" for r in results)

    def test_search_by_kind(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_search

        results = handle_search(db_conn, query="Routing", kind="domain")
        assert all(r["kind"] == "domain" for r in results)

    def test_search_no_results(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import handle_search

        results = handle_search(db_conn, query="zzzznonexistent")
        assert results == []

    def test_dispatch_update_node(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "update_node",
            {"ref_id": "FEAT-1", "summary": "Dispatch test"},
            project_root=project,
        )
        assert result["updated"] is True

    def test_dispatch_mark_synced(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "mark_synced",
            {"ref_id": "FEAT-1"},
            project_root=project,
        )
        assert "pairs_synced" in result

    def test_dispatch_search(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "search",
            {"query": "Track"},
        )
        assert isinstance(result, list)


class TestAutoReindex:
    """Test auto-reindex stale detection."""

    def test_is_index_stale_when_files_changed(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        import time

        from beadloom.services.mcp_server import _is_index_stale

        # Index is fresh right after reindex.
        assert _is_index_stale(project, db_conn) is False

        # Touch a graph file.
        time.sleep(0.05)
        graph_file = project / ".beadloom" / "_graph" / "graph.yml"
        graph_file.write_text(graph_file.read_text())

        assert _is_index_stale(project, db_conn) is True

    def test_ensure_fresh_index_triggers_reindex(
        self,
        project: Path,
    ) -> None:
        import time

        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import _ensure_fresh_index

        db_path = project / ".beadloom" / "beadloom.db"

        # Touch a doc file to make index stale.
        time.sleep(0.05)
        (project / "docs" / "spec.md").write_text("## Updated\n\nNew.\n")

        conn = open_db(db_path)
        reindexed = _ensure_fresh_index(project, conn)
        conn.close()

        assert reindexed is True

    def test_ensure_fresh_index_no_op_when_fresh(
        self,
        project: Path,
    ) -> None:
        from beadloom.infrastructure.db import open_db
        from beadloom.services.mcp_server import _ensure_fresh_index

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        reindexed = _ensure_fresh_index(project, conn)
        conn.close()

        assert reindexed is False


class TestGenerateDocsTool:
    """Tests for the generate_docs MCP tool."""

    def test_generate_docs_tool_listed(self) -> None:
        """Check that 'generate_docs' appears in the _TOOLS list."""
        from beadloom.services.mcp_server import _TOOLS

        tool_names = [t.name for t in _TOOLS]
        assert "generate_docs" in tool_names

    def test_generate_docs_all_nodes(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Calling generate_docs without ref_id returns all nodes."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "generate_docs",
            {},
            project_root=project,
        )

        assert "nodes" in result
        assert isinstance(result["nodes"], list)
        assert len(result["nodes"]) >= 2
        assert "instructions" in result
        assert "architecture" in result

    def test_generate_docs_single_ref_id(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Calling generate_docs with ref_id returns a single node."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "generate_docs",
            {"ref_id": "FEAT-1"},
            project_root=project,
        )

        assert "nodes" in result
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["ref_id"] == "FEAT-1"

    def test_generate_docs_response_format(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """Response is a dict with expected top-level keys and valid structure."""
        import json

        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "generate_docs",
            {},
            project_root=project,
        )

        # Result should be JSON-serialisable.
        text = json.dumps(result, ensure_ascii=False, indent=2)
        parsed = json.loads(text)
        assert "nodes" in parsed
        assert "architecture" in parsed
        assert "instructions" in parsed
        assert isinstance(parsed["instructions"], str)

    def test_generate_docs_requires_project_root(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        """generate_docs raises ValueError when project_root is None."""
        from beadloom.services.mcp_server import _dispatch_tool

        with pytest.raises(ValueError, match="generate_docs requires project_root"):
            _dispatch_tool(db_conn, "generate_docs", {})


class TestGetDebtReportTool:
    """Tests for the get_debt_report MCP tool (BEAD-05)."""

    def test_tool_listed(self) -> None:
        """get_debt_report appears in the _TOOLS list."""
        from beadloom.services.mcp_server import _TOOLS

        tool_names = [t.name for t in _TOOLS]
        assert "get_debt_report" in tool_names

    def test_tool_schema_has_trend_and_category(self) -> None:
        """Tool input schema declares trend (bool) and category (str) properties."""
        from beadloom.services.mcp_server import _TOOLS

        tool = next(t for t in _TOOLS if t.name == "get_debt_report")
        props = tool.inputSchema["properties"]
        assert "trend" in props
        assert props["trend"]["type"] == "boolean"
        assert "category" in props
        assert props["category"]["type"] == "string"

    def test_dispatch_returns_valid_json(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """get_debt_report returns a JSON-serializable dict with expected keys."""
        import json

        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "get_debt_report",
            {},
            project_root=project,
        )
        # Result should be JSON-serializable
        text = json.dumps(result, ensure_ascii=False, indent=2)
        parsed = json.loads(text)
        assert "debt_score" in parsed
        assert "severity" in parsed
        assert "categories" in parsed
        assert "top_offenders" in parsed
        assert isinstance(parsed["debt_score"], (int, float))
        assert isinstance(parsed["categories"], list)

    def test_dispatch_with_trend_false(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """With trend=False, trend key should be null."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "get_debt_report",
            {"trend": False},
            project_root=project,
        )
        assert "trend" in result
        # No snapshots exist, so trend is None regardless
        assert result["trend"] is None

    def test_dispatch_with_trend_true_no_snapshots(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """With trend=True but no snapshots, trend should be null."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "get_debt_report",
            {"trend": True},
            project_root=project,
        )
        assert result["trend"] is None

    def test_dispatch_with_category_filter(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """With category filter, only matching categories are returned."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "get_debt_report",
            {"category": "rule_violations"},
            project_root=project,
        )
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "rule_violations"

    def test_dispatch_with_unknown_category(
        self,
        project: Path,
        db_conn: sqlite3.Connection,
    ) -> None:
        """With an unknown category filter, no categories are returned."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(
            db_conn,
            "get_debt_report",
            {"category": "nonexistent"},
            project_root=project,
        )
        assert result["categories"] == []

    def test_dispatch_requires_project_root(
        self,
        db_conn: sqlite3.Connection,
    ) -> None:
        """get_debt_report raises ValueError when project_root is None."""
        from beadloom.services.mcp_server import _dispatch_tool

        with pytest.raises(ValueError, match="get_debt_report requires project_root"):
            _dispatch_tool(db_conn, "get_debt_report", {})
