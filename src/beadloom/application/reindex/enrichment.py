# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex node-extra enrichment: augment nodes.extra with derived data.

This module owns merging derived, source-scanned data into each node's
``extra`` JSON blob: test mappings (framework + counts), API routes scoped to
the node's source prefix, and git activity. Each augmentation reads the current
``extra``, merges its key, and writes it back; nodes with no matching data are
left untouched.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beadloom.application.reindex.models import _EXT_TO_LANG

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _store_test_mappings(
    project_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Run test mapper and merge results into ``nodes.extra["tests"]``.

    Builds a ``source_dirs`` dict from nodes that have a non-null ``source``
    field, calls :func:`~beadloom.context_oracle.test_mapper.map_tests`, and
    updates each node's ``extra`` JSON blob with the test mapping data.
    """
    from beadloom.context_oracle.test_mapper import aggregate_parent_tests, map_tests

    # Build source_dirs: {ref_id: source_path} for nodes with a source field.
    rows = conn.execute("SELECT ref_id, source FROM nodes WHERE source IS NOT NULL").fetchall()
    source_dirs: dict[str, str] = {row["ref_id"]: row["source"] for row in rows}

    if not source_dirs:
        return

    mappings = map_tests(project_root, source_dirs)

    # Build parent->children hierarchy from part_of edges for aggregation.
    parent_children: dict[str, list[str]] = {}
    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'part_of'"
    ).fetchall()
    for edge_row in edge_rows:
        child_id = edge_row["src_ref_id"]
        parent_id = edge_row["dst_ref_id"]
        if parent_id not in parent_children:
            parent_children[parent_id] = []
        parent_children[parent_id].append(child_id)

    # Aggregate child test counts up to parent (domain) nodes.
    mappings = aggregate_parent_tests(mappings, parent_children)

    for ref_id, mapping in mappings.items():
        # Read existing extra JSON.
        row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
        if row is None:
            continue

        extra: dict[str, object] = json.loads(row["extra"]) if row["extra"] else {}
        extra["tests"] = {
            "framework": mapping.framework,
            "test_files": mapping.test_files,
            "test_count": mapping.test_count,
            "coverage_estimate": mapping.coverage_estimate,
        }
        conn.execute(
            "UPDATE nodes SET extra = ? WHERE ref_id = ?",
            (json.dumps(extra, ensure_ascii=False), ref_id),
        )

    conn.commit()


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


def _extract_and_store_routes(
    project_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Scan source files for API routes and store them in ``nodes.extra``.

    Iterates over all known scan directories, extracts routes via
    :func:`~beadloom.context_oracle.route_extractor.extract_routes`, and
    aggregates them.  When routes are found, stores them under the
    ``"routes"`` key in each node's ``extra`` JSON column.

    Files without routes are skipped (no empty arrays stored).
    """
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

    if not all_routes:
        return

    # Scope routes to nodes whose source path covers the route's file.
    # Build node source paths mapping.
    node_rows = conn.execute("SELECT ref_id, source FROM nodes").fetchall()
    for node_row in node_rows:
        ref_id: str = node_row["ref_id"]
        source: str | None = node_row["source"]
        if source is None:
            continue

        # Normalise source to a directory prefix for matching.
        # e.g. "src/beadloom/context_oracle" matches "src/beadloom/context_oracle/builder.py"
        source_prefix = source.rstrip("/")

        node_routes = [r for r in all_routes if str(r.get("file", "")).startswith(source_prefix)]
        if node_routes:
            _update_node_extra(conn, ref_id, "routes", node_routes)
    conn.commit()


def _store_git_activity(
    conn: sqlite3.Connection,
    project_root: Path,
) -> None:
    """Analyze git activity and store results in ``nodes.extra["activity"]``.

    Builds a ``source_dirs`` mapping from nodes that have a ``source`` field,
    runs ``analyze_git_activity``, and merges activity data into the existing
    ``extra`` JSON column for each matching node.

    ``analyze_git_activity`` is looked up on the package namespace at call time
    (``beadloom.application.reindex.analyze_git_activity``) so tests can patch
    it there.  Gracefully does nothing when git is unavailable
    (``analyze_git_activity`` returns an empty dict in that case).
    """
    from beadloom.application import reindex as _pkg

    # Build ref_id -> source_path mapping from nodes with source field.
    rows = conn.execute("SELECT ref_id, source FROM nodes WHERE source IS NOT NULL").fetchall()
    source_dirs: dict[str, str] = {}
    for row in rows:
        src: str = row["source"]
        if src.strip():
            source_dirs[row["ref_id"]] = src

    if not source_dirs:
        return

    activities = _pkg.analyze_git_activity(project_root, source_dirs)

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
