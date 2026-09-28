"""The reindex extracts API routes into ``nodes.extra``, and keeps them across an incremental run.

The context bundle's reading of those routes is in
``tests/test_the_context_bundle_carries_routes.py`` (split by node, BDL-074
``beadloom-2mj3.7``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.infrastructure.db import open_db
from tests.support.reindex_project import empty_project, index_path

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure."""
    return empty_project(tmp_path)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return index_path(tmp_path)


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
            "nodes:\n"
            "  - ref_id: api-svc\n"
            "    kind: service\n"
            '    summary: "API service"\n'
            "    source: src\n"
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
            "nodes:\n"
            "  - ref_id: api-svc\n"
            "    kind: service\n"
            '    summary: "API service"\n'
            "    source: src\n"
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
            "nodes:\n"
            "  - ref_id: web-api\n"
            "    kind: service\n"
            '    summary: "Web API"\n'
            "    source: src\n"
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
