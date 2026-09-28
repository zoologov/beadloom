"""The context bundle carries the routes the reindex stored, and ctx renders them.

Split out of ``tests/test_reindex_routes.py`` (BDL-074 ``beadloom-2mj3.7``): the
reindex half is under ``tests/integration/application/reindex/``. This half reads
through ``build_context`` and ``ctx``'s markdown, so it spans two nodes and stays
unplaced until it is split again.
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
        assert "/api/login" in md
        assert "POST" in md
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
