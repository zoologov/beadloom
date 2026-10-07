"""The debt report's dormant count: no change in 90 days, a box read with its parts.

BDL-078 F-activity (`beadloom-lw56`). ``dormant`` keeps its meaning — no change
in 90 days — and is decided by the same activity the node card shows, so a box
whose parts changed is not dormant because its own files stood still.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.debt_report.collect import _count_dormant
from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from tests.support.reindex_project import index_path
from tests.support.squash_merged_repo import build_squash_merged_project, exclude_from_activity

if TYPE_CHECKING:
    from pathlib import Path


def test_only_a_node_with_no_change_in_90_days_is_dormant(tmp_path: Path) -> None:
    root = build_squash_merged_project(tmp_path / "repo").root
    reindex(root)

    conn = open_db(index_path(root))
    try:
        count, refs = _count_dormant(conn, root)
    finally:
        conn.close()

    # "app" and "core" have no change of their own in 90 days; their parts do.
    assert (count, refs) == (1, ["legacy"])


def test_a_change_only_to_a_file_the_project_excludes_leaves_a_node_dormant(
    tmp_path: Path,
) -> None:
    # BDL-078 `beadloom-btkd.1`: "config"'s only change in 90 days is to a file
    # the project declares generated, so it counts as none.
    root = build_squash_merged_project(tmp_path / "repo").root
    exclude_from_activity(root, "src/app/config/*")
    reindex(root)

    conn = open_db(index_path(root))
    try:
        count, refs = _count_dormant(conn, root)
    finally:
        conn.close()

    assert (count, sorted(refs)) == (2, ["config", "legacy"])
