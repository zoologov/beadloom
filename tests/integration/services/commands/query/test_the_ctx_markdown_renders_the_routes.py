"""``ctx``'s markdown renders the routes the context bundle carries.

Split out of ``tests/test_reindex_routes.py`` (BDL-074): the reindex half is under
``tests/integration/application/reindex/``, and the bundle's half under
``tests/integration/context_oracle/builder/``. The bundle is built here only as
the input the renderer reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from tests.support.reindex_project import empty_project, index_path

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure."""
    return empty_project(tmp_path)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return index_path(tmp_path)


class TestContextBundleRoutes:
    """Routes appear in ctx's markdown, and only when there are some."""

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
