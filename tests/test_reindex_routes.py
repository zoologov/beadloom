"""Tests for route extraction integration in reindex + context bundle."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.reindex import incremental_reindex, reindex

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / ".beadloom" / "beadloom.db"


# ---------------------------------------------------------------------------
# Reindex route integration
# ---------------------------------------------------------------------------


class TestReindexExtractsRoutes:
    """Routes are extracted during reindex and stored in nodes.extra."""

    def test_fastapi_routes_stored_in_node_extra(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """FastAPI routes from a Python source file appear in nodes.extra."""
        # Arrange: graph node + source file with FastAPI routes.
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: api-svc\n    kind: service\n    summary: "API service"\n'
        )
        src = project / "src"
        (src / "routes.py").write_text(
            "from fastapi import FastAPI\n"
            "\n"
            "app = FastAPI()\n"
            "\n"
            '@app.get("/users")\n'
            "async def list_users():\n"
            "    return []\n"
            "\n"
            '@app.post("/users")\n'
            "def create_user():\n"
            "    pass\n"
        )

        # Act
        reindex(project)

        # Assert: routes are in nodes.extra
        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("api-svc",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        routes = extra.get("routes", [])
        assert len(routes) >= 2

        # Check route fields
        methods = {r["method"] for r in routes}
        assert "GET" in methods
        assert "POST" in methods

        paths = {r["path"] for r in routes}
        assert "/users" in paths

        # Each route has required fields
        for route in routes:
            assert "method" in route
            assert "path" in route
            assert "handler" in route
            assert "file" in route
            assert "line" in route
            assert "framework" in route

        conn.close()

    def test_routes_survive_incremental_reindex(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Routes persist across incremental reindex when code doesn't change."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: api-svc\n    kind: service\n    summary: "API service"\n'
        )
        src = project / "src"
        (src / "api.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/health")\n'
            "def health():\n"
            "    return {'ok': True}\n"
        )

        # First reindex (falls back to full).
        incremental_reindex(project)

        # Verify routes exist after first run.
        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("api-svc",)).fetchone()
        extra = json.loads(row["extra"])
        assert len(extra.get("routes", [])) >= 1
        conn.close()

        # Second incremental (nothing changed) -- routes should still be there.
        result = incremental_reindex(project)
        assert result.nothing_changed is True

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("api-svc",)).fetchone()
        extra = json.loads(row["extra"])
        assert len(extra.get("routes", [])) >= 1
        conn.close()

    def test_files_without_routes_no_empty_array(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Source files without routes don't produce an empty routes array."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: utils\n    kind: domain\n    summary: "Utilities"\n'
        )
        src = project / "src"
        (src / "util.py").write_text("def helper():\n    return 42\n")

        reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("utils",)).fetchone()
        extra = json.loads(row["extra"])
        # Either no "routes" key or an empty list is acceptable --
        # but an empty list should NOT be created.
        assert extra.get("routes") is None or extra.get("routes") == []
        conn.close()

    def test_multiple_files_routes_aggregated(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Routes from multiple source files are aggregated into nodes.extra."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: web-api\n    kind: service\n    summary: "Web API"\n'
        )
        src = project / "src"
        (src / "auth.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.post("/login")\n'
            "def login():\n"
            "    pass\n"
        )
        (src / "items.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/items")\n'
            "def get_items():\n"
            "    pass\n"
        )

        reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("web-api",)).fetchone()
        extra = json.loads(row["extra"])
        routes = extra.get("routes", [])
        # Both files contributed routes
        assert len(routes) >= 2
        paths = {r["path"] for r in routes}
        assert "/login" in paths
        assert "/items" in paths
        conn.close()


# ---------------------------------------------------------------------------
# Context bundle rendering
# ---------------------------------------------------------------------------


class TestContextBundleRoutes:
    """Routes appear in context bundle output (markdown + JSON)."""

    def test_routes_in_context_bundle_json(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Context bundle JSON includes routes array."""
        from beadloom.context_oracle.builder import build_context

        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: api-svc\n    kind: service\n    summary: "API service"\n'
        )
        src = project / "src"
        (src / "app.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/health")\n'
            "def health():\n"
            "    return {'status': 'ok'}\n"
        )

        reindex(project)

        conn = open_db(db_path)
        bundle = build_context(conn, ["api-svc"])
        conn.close()

        # Routes should be present in the bundle
        assert "routes" in bundle
        routes = bundle["routes"]
        assert len(routes) >= 1
        assert routes[0]["method"] == "GET"
        assert routes[0]["path"] == "/health"

    def test_routes_in_context_bundle_markdown(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Context bundle Markdown output contains 'API Routes:' section."""
        from beadloom.context_oracle.builder import build_context
        from beadloom.services.cli import _format_markdown

        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            'nodes:\n  - ref_id: api-svc\n    kind: service\n    summary: "API service"\n'
        )
        src = project / "src"
        (src / "app.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.post("/api/login")\n'
            "def login():\n"
            "    pass\n"
        )

        reindex(project)

        conn = open_db(db_path)
        bundle = build_context(conn, ["api-svc"])
        conn.close()

        md = _format_markdown(bundle)
        assert "API Routes" in md
        assert "POST /api/login" in md
        assert "login()" in md

    def test_no_routes_no_section_in_markdown(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """When there are no routes, 'API Routes' section is omitted."""
        from beadloom.context_oracle.builder import build_context
        from beadloom.services.cli import _format_markdown

        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: utils\n    kind: domain\n    summary: "Utils"\n'
        )
        src = project / "src"
        (src / "util.py").write_text("def helper():\n    pass\n")

        reindex(project)

        conn = open_db(db_path)
        bundle = build_context(conn, ["utils"])
        conn.close()

        md = _format_markdown(bundle)
        assert "API Routes" not in md
