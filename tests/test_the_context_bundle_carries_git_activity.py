"""The context bundle carries the git activity the reindex stored, and ctx renders it.

Split out of ``tests/test_reindex_activity.py`` (BDL-074 ``beadloom-2mj3.7``): the
reindex half is under ``tests/integration/application/reindex/``. This half reads
through ``build_context`` and, for two cases, ``ctx``'s markdown, so it spans two
nodes and stays unplaced until it is split again.
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
    """Integration: context bundle includes and renders activity."""

    def test_context_bundle_includes_activity(self, project: Path, db_path: Path) -> None:
        """build_context returns activity in the focus dict."""
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
                "api": GitActivity(
                    commits_30d=3,
                    commits_90d=10,
                    last_commit_date="2026-02-13",
                    top_contributors=["alice"],
                    activity_level="cold",
                ),
            }
            reindex(project)

        from beadloom.context_oracle.builder import build_context

        conn = open_db(db_path)
        bundle = build_context(conn, ["infra"])
        conn.close()

        # Focus should have activity
        assert "activity" in bundle["focus"]
        activity = bundle["focus"]["activity"]
        assert activity["level"] == "hot"
        assert activity["commits_30d"] == 45

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

    def test_context_json_includes_activity_object(self, project: Path, db_path: Path) -> None:
        """JSON output includes the full activity object."""
        write_two_nodes_with_sources(project)

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
            from beadloom.infrastructure.git_activity import GitActivity

            mock_activity.return_value = {
                "infra": GitActivity(
                    commits_30d=10,
                    commits_90d=30,
                    last_commit_date="2026-02-10",
                    top_contributors=["alice"],
                    activity_level="warm",
                ),
            }
            reindex(project)

        from beadloom.context_oracle.builder import build_context

        conn = open_db(db_path)
        bundle = build_context(conn, ["infra"])
        conn.close()

        # JSON output should include activity object
        focus = bundle["focus"]
        assert "activity" in focus
        assert focus["activity"]["level"] == "warm"
        assert focus["activity"]["commits_30d"] == 10
        assert focus["activity"]["commits_90d"] == 30
        assert focus["activity"]["last_commit"] == "2026-02-10"
        assert focus["activity"]["top_contributors"] == ["alice"]

    def test_context_bundle_no_activity_when_missing(self, project: Path, db_path: Path) -> None:
        """When no activity data, context bundle omits activity field."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: plain\n    kind: domain\n    summary: "Plain domain"\n'
        )

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
            mock_activity.return_value = {}
            reindex(project)

        from beadloom.context_oracle.builder import build_context

        conn = open_db(db_path)
        bundle = build_context(conn, ["plain"])
        conn.close()

        # No activity key in focus when no data
        assert "activity" not in bundle["focus"]
