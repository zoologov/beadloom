"""The context bundle carries the routes the reindex stored.

Split out of ``tests/test_reindex_routes.py`` (BDL-074): the reindex half is under
``tests/integration/application/reindex/``, and how ``ctx``'s markdown renders the
routes is under ``tests/integration/services/commands/query/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import reindex
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
# The context bundle
# ---------------------------------------------------------------------------


class TestContextBundleRoutes:
    """Routes appear in the context bundle."""

    def test_routes_in_context_bundle_json(
        self,
        project: Path,
        db_path: Path,
    ) -> None:
        """Context bundle JSON includes routes array."""
        from beadloom.context_oracle.builder import build_context

        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: api-svc\n"
            "    kind: service\n"
            '    summary: "API service"\n'
            "    source: src\n"
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
