"""The reindex stores each node's git activity in ``nodes.extra``, and skips it without git.

The context bundle's reading of that activity is under
``tests/integration/context_oracle/builder/`` and ``ctx``'s rendering of it under
``tests/integration/services/commands/query/`` (split by node, BDL-074).
"""

from __future__ import annotations

import json
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


class TestReindexGitActivityIntegration:
    """Integration: reindex stores git activity in nodes.extra."""

    def test_activity_stored_in_nodes_extra(self, project: Path, db_path: Path) -> None:
        """After reindex with git activity, nodes.extra contains activity data."""
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

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
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

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
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
        write_two_nodes_with_sources(project)

        with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
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
