"""``ctx``'s markdown renders the git activity the context bundle carries.

Split out of ``tests/test_reindex_activity.py`` (BDL-074): the reindex half is
under ``tests/integration/application/reindex/``, and the bundle's half under
``tests/integration/context_oracle/builder/``. The bundle is built here only as
the input the renderer reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from tests.support.reindex_project import (
    empty_project,
    index_path,
    write_two_nodes_with_sources,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure with a graph node that has a source."""
    return empty_project(tmp_path)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return index_path(tmp_path)


class TestContextBundleActivity:
    """Integration: ctx's markdown renders the activity."""

    def test_context_markdown_shows_activity_line(self, project: Path, db_path: Path) -> None:
        """_format_markdown renders activity as a human-readable line."""
        write_two_nodes_with_sources(project)

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
            from beadloom.infrastructure.git_activity import GitActivity

            mock_activity.return_value = {
                "infra": GitActivity(
                    commits_30d=45,
                    commits_90d=120,
                    last_commit_date="2026-02-15",
                    top_contributors=["alice", "bob"],
                    activity_level="hot",
                ),
            }
            reindex(project)

        from beadloom.context_oracle.builder import build_context
        from beadloom.services.cli import _format_markdown

        conn = open_db(db_path)
        bundle = build_context(conn, ["infra"])
        conn.close()

        md = _format_markdown(bundle)
        assert "Activity:" in md
        assert "hot" in md
        assert "45" in md

    def test_context_markdown_dormant_activity(self, project: Path, db_path: Path) -> None:
        """Dormant activity renders with ice emoji."""
        write_two_nodes_with_sources(project)

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
            from beadloom.infrastructure.git_activity import GitActivity

            mock_activity.return_value = {
                "infra": GitActivity(
                    commits_30d=0,
                    commits_90d=0,
                    last_commit_date="",
                    top_contributors=[],
                    activity_level="dormant",
                ),
            }
            reindex(project)

        from beadloom.context_oracle.builder import build_context
        from beadloom.services.cli import _format_markdown

        conn = open_db(db_path)
        bundle = build_context(conn, ["infra"])
        conn.close()

        md = _format_markdown(bundle)
        assert "Activity:" in md
        assert "dormant" in md
