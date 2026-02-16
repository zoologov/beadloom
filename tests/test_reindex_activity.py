"""Tests for git activity integration in reindex pipeline and context bundle."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.reindex import reindex

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project structure with a graph node that has a source."""
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


def _setup_graph_with_source(project: Path) -> None:
    """Write a graph YAML with a node that has a source directory."""
    graph_dir = project / ".beadloom" / "_graph"
    (graph_dir / "domains.yml").write_text(
        "nodes:\n"
        "  - ref_id: infra\n"
        "    kind: domain\n"
        '    summary: "Infrastructure domain"\n'
        "    source: src/infra\n"
        "  - ref_id: api\n"
        "    kind: service\n"
        '    summary: "API service"\n'
        "    source: src/api\n"
    )


class TestReindexGitActivityIntegration:
    """Integration: reindex stores git activity in nodes.extra."""

    def test_activity_stored_in_nodes_extra(self, project: Path, db_path: Path) -> None:
        """After reindex with git activity, nodes.extra contains activity data."""
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
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

        conn = open_db(db_path)

        # Check infra node
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("infra",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "activity" in extra
        activity = extra["activity"]
        assert activity["level"] == "hot"
        assert activity["commits_30d"] == 45
        assert activity["commits_90d"] == 120
        assert activity["last_commit"] == "2026-02-15"
        assert activity["top_contributors"] == ["alice", "bob"]

        # Check api node
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("api",)).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "activity" in extra
        activity = extra["activity"]
        assert activity["level"] == "cold"
        assert activity["commits_30d"] == 3

        conn.close()

    def test_activity_preserves_existing_extra(self, project: Path, db_path: Path) -> None:
        """Activity data merges with existing extra fields (e.g., links)."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            "nodes:\n"
            "  - ref_id: infra\n"
            "    kind: domain\n"
            '    summary: "Infrastructure"\n'
            "    source: src/infra\n"
            "    links:\n"
            '      - label: "Docs"\n'
            '        url: "https://example.com"\n'
        )

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
            from beadloom.infrastructure.git_activity import GitActivity

            mock_activity.return_value = {
                "infra": GitActivity(
                    commits_30d=10,
                    commits_90d=30,
                    last_commit_date="2026-02-15",
                    top_contributors=["alice"],
                    activity_level="warm",
                ),
            }
            reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("infra",)).fetchone()
        extra = json.loads(row["extra"])
        # Activity should be present
        assert "activity" in extra
        assert extra["activity"]["level"] == "warm"
        # Original links should be preserved
        assert "links" in extra
        assert extra["links"][0]["url"] == "https://example.com"
        conn.close()

    def test_nodes_without_source_skip_activity(self, project: Path, db_path: Path) -> None:
        """Nodes without a source field should not get activity data."""
        graph_dir = project / ".beadloom" / "_graph"
        (graph_dir / "domains.yml").write_text(
            'nodes:\n  - ref_id: abstract\n    kind: domain\n    summary: "Abstract domain"\n'
        )

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
            mock_activity.return_value = {}
            reindex(project)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("abstract",)).fetchone()
        extra = json.loads(row["extra"])
        # No activity key when source is missing
        assert "activity" not in extra
        conn.close()


class TestReindexGitActivityGracefulDegradation:
    """Reindex gracefully handles missing git."""

    def test_no_git_skips_activity_silently(self, project: Path, db_path: Path) -> None:
        """When git is unavailable, reindex completes without errors."""
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
            mock_activity.return_value = {}
            result = reindex(project)

        # Reindex should complete without errors
        assert result.errors == [] or all("git" not in e.lower() for e in result.errors)

        conn = open_db(db_path)
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", ("infra",)).fetchone()
        extra = json.loads(row["extra"])
        # No activity key when git is unavailable
        assert "activity" not in extra
        conn.close()


class TestContextBundleActivity:
    """Integration: context bundle includes and renders activity."""

    def test_context_bundle_includes_activity(self, project: Path, db_path: Path) -> None:
        """build_context returns activity in the focus dict."""
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
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
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
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
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
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
        _setup_graph_with_source(project)

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
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

        with patch("beadloom.infrastructure.reindex.analyze_git_activity") as mock_activity:
            mock_activity.return_value = {}
            reindex(project)

        from beadloom.context_oracle.builder import build_context

        conn = open_db(db_path)
        bundle = build_context(conn, ["plain"])
        conn.close()

        # No activity key in focus when no data
        assert "activity" not in bundle["focus"]
