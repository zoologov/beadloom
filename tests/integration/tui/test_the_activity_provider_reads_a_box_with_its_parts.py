"""The TUI's activity reads a box with its parts, as the node card does.

BDL-078 F-activity (`beadloom-lw56`). The dashboard and the portal show one
activity: a box whose parts changed is not shown idle because its own files
stood still.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from beadloom.tui.data_providers import ActivityDataProvider
from tests.support.reindex_project import index_path
from tests.support.squash_merged_repo import (
    PARSER_LINES,
    build_squash_merged_project,
    exclude_from_activity,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_a_box_shows_the_lines_of_its_parts(tmp_path: Path) -> None:
    root = build_squash_merged_project(tmp_path / "repo").root
    reindex(root)

    conn = open_db(index_path(root))
    try:
        provider = ActivityDataProvider(conn=conn, project_root=root)
        provider.refresh()
        activity = provider.get_activity()
    finally:
        conn.close()

    assert activity["core"].lines_30d == PARSER_LINES
    # BDL-078 `beadloom-btkd.1`: a box is ranked among boxes; "app" outranks it.
    assert activity["core"].activity_level == "cool"


def test_the_dashboard_leaves_out_the_files_the_project_excludes(tmp_path: Path) -> None:
    # BDL-078 `beadloom-btkd.1`: the dashboard reads the project's `activity:` block,
    # as the reindex does, so the two show one activity.
    root = build_squash_merged_project(tmp_path / "repo").root
    exclude_from_activity(root, "src/app/config/*")
    reindex(root)

    conn = open_db(index_path(root))
    try:
        provider = ActivityDataProvider(conn=conn, project_root=root)
        provider.refresh()
        activity = provider.get_activity()
    finally:
        conn.close()

    assert activity["config"].activity_level == "dormant"
