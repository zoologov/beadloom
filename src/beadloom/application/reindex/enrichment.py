# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex node-extra enrichment: augment nodes.extra with derived data.

This module owns merging derived, source-scanned data into each node's
``extra`` JSON blob: API routes scoped to the files under the node's source, and
git activity. Each augmentation reads the current ``extra``, merges its key, and
writes it back. Routes are the one augmentation that also withdraws its key from
a node that no longer holds any, because a route scan covers the whole project on
every run. The other augmentations leave a node with no matching data untouched.

``extra["tests"]`` is not written here: since BDL-074 C1 it is rebuilt from the
test binding by :mod:`.test_index`, and the heuristic mapper no longer writes it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beadloom.application.reindex.models import _EXT_TO_LANG
from beadloom.infrastructure.node_source import NodeSource
from beadloom.infrastructure.repository import get_node_sources, get_part_of_containers

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _update_node_extra(
    conn: sqlite3.Connection,
    ref_id: str,
    key: str,
    value: object,
) -> None:
    """Merge a key/value into a node's ``extra`` JSON column.

    Reads the current ``extra`` JSON, sets ``extra[key] = value``, and
    writes it back.  Does nothing if *ref_id* does not exist.
    """
    row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    if row is None:
        return
    current: dict[str, object] = json.loads(row["extra"]) if row["extra"] else {}
    current[key] = value
    conn.execute(
        "UPDATE nodes SET extra = ? WHERE ref_id = ?",
        (json.dumps(current, ensure_ascii=False), ref_id),
    )


def _drop_node_extra_key(conn: sqlite3.Connection, ref_id: str, key: str) -> None:
    """Remove *key* from a node's ``extra`` JSON column, if it is there."""
    row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    if row is None or not row["extra"]:
        return
    current: dict[str, object] = json.loads(row["extra"])
    if current.pop(key, None) is None:
        return
    conn.execute(
        "UPDATE nodes SET extra = ? WHERE ref_id = ?",
        (json.dumps(current, ensure_ascii=False), ref_id),
    )


def _extract_and_store_routes(
    project_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Scan source files for API routes and store them in ``nodes.extra``.

    Extracts every route under the scan directories and stores, under each node's
    ``"routes"`` key, the routes whose file lies under the node's source. The store
    is the whole answer and not a merge: a node that holds no route now loses the
    key, so a route deleted from the code, or attributed under an earlier rule, does
    not survive an incremental reindex (BDL-069 `beadloom-rqma.4`). No empty array
    is stored.
    """
    all_routes = _scan_routes(project_root)

    # A route belongs to every node whose source its file lies under, by the one
    # rule `NodeSource` holds. A string prefix gave `src/ledger/` the routes of
    # `src/ledger_archive/`, and a root declaring `source: ''` every route there was.
    node_rows = conn.execute("SELECT ref_id, source FROM nodes").fetchall()
    for node_row in node_rows:
        under = NodeSource(node_row["source"])
        node_routes = [r for r in all_routes if under.holds(str(r.get("file", "")))]
        if node_routes:
            _update_node_extra(conn, node_row["ref_id"], "routes", node_routes)
        else:
            _drop_node_extra_key(conn, node_row["ref_id"], "routes")
    conn.commit()


def _scan_routes(project_root: Path) -> list[dict[str, object]]:
    """Every API route under the project's scan directories, with its relative file."""
    from beadloom.context_oracle.route_extractor import extract_routes
    from beadloom.infrastructure.scan_paths import resolve_scan_paths

    all_routes: list[dict[str, object]] = []

    scan_dirs = [project_root / d for d in resolve_scan_paths(project_root)]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for file_path in sorted(scan_dir.rglob("*")):
            if not file_path.is_file():
                continue
            lang = _EXT_TO_LANG.get(file_path.suffix)
            if lang is None:
                continue

            routes = extract_routes(file_path, lang)
            if not routes:
                continue

            rel_path = str(file_path.relative_to(project_root))
            for route in routes:
                all_routes.append(
                    {
                        "method": route.method,
                        "path": route.path,
                        "handler": route.handler,
                        "file": rel_path,
                        "line": route.line,
                        "framework": route.framework,
                    }
                )
    return all_routes


def _store_git_activity(
    conn: sqlite3.Connection,
    project_root: Path,
) -> None:
    """Analyze git activity and store results in ``nodes.extra["activity"]``.

    Builds a ``source_dirs`` mapping from nodes that have a ``source`` field and
    the ``part_of`` containers, so a box's activity rolls up its parts, runs
    ``analyze_git_activity``, and merges activity data into the existing
    ``extra`` JSON column for each matching node.

    ``analyze_git_activity`` is looked up on the package namespace at call time
    (``beadloom.application.reindex.analyze_git_activity``) so tests can patch
    it there.  Gracefully does nothing when git is unavailable
    (``analyze_git_activity`` returns an empty dict in that case).
    """
    from beadloom.application import reindex as _pkg

    source_dirs = get_node_sources(conn)
    if not source_dirs:
        return

    activities = _pkg.analyze_git_activity(
        project_root, source_dirs, get_part_of_containers(conn)
    )

    for ref_id, activity in activities.items():
        # Read existing extra.
        node_row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
        if node_row is None:
            continue

        extra_raw: str = node_row["extra"] if node_row["extra"] else "{}"
        extra: dict[str, Any] = json.loads(extra_raw)

        # Merge activity data.
        extra["activity"] = {
            "level": activity.activity_level,
            "lines_30d": activity.lines_30d,
            "lines_90d": activity.lines_90d,
            "commits_30d": activity.commits_30d,
            "commits_90d": activity.commits_90d,
            "last_commit": activity.last_commit_date,
            "top_contributors": activity.top_contributors,
        }

        conn.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps(extra, ensure_ascii=False), ref_id),
        )

    conn.commit()
