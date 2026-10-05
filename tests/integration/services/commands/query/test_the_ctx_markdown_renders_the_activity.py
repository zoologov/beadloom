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
                    commits_30d=12,
                    commits_90d=120,
                    last_commit_date="2026-02-15",
                    top_contributors=["alice", "bob"],
                    activity_level="hot",
                    lines_30d=45,
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


def _markdown_with(project: Path, db_path: Path, level: str, lines: int) -> str:
    """Reindex with *level* and *lines* recorded for ``infra`` and render its ctx markdown."""
    write_two_nodes_with_sources(project)
    from beadloom.infrastructure.git_activity import GitActivity

    recorded = GitActivity(
        commits_30d=1,
        commits_90d=1,
        last_commit_date="2026-10-01",
        top_contributors=[],
        activity_level=level,
        lines_30d=lines,
    )
    with patch("beadloom.application.reindex.analyze_git_activity") as mock_activity:
        mock_activity.return_value = {"infra": recorded}
        reindex(project)

    from beadloom.context_oracle.builder import build_context
    from beadloom.services.cli import _format_markdown

    conn = open_db(db_path)
    bundle = build_context(conn, ["infra"])
    conn.close()
    return _format_markdown(bundle)


class TestCtxMarkdownSaysChangedLines:
    """BDL-078 F-activity: ctx words activity as the node card does."""

    def test_a_changed_node_shows_its_lines_and_level(self, project: Path, db_path: Path) -> None:
        md = _markdown_with(project, db_path, "warm", 340)
        assert "warm (340 lines changed in 30 days)" in md

    @pytest.mark.parametrize(
        ("level", "words"),
        [("quiet", "no change in 30 days"), ("dormant", "no change in 90 days")],
    )
    def test_no_change_is_said_in_words(
        self, project: Path, db_path: Path, level: str, words: str
    ) -> None:
        md = _markdown_with(project, db_path, level, 0)
        assert f"{level} ({words})" in md

    def test_every_level_has_its_mark(self, project: Path, db_path: Path) -> None:
        from beadloom.infrastructure.git_activity import ACTIVITY_LEVELS
        from beadloom.services.commands.query import ACTIVITY_MARKS

        assert set(ACTIVITY_MARKS) == set(ACTIVITY_LEVELS)
