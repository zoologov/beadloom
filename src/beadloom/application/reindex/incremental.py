# beadloom:domain=application
# beadloom:feature=reindex
"""Incremental reindex orchestration: process only changed files.

This module owns the :func:`incremental_reindex` use case — the fast path that
diffs the file index, falls back to a full reindex on first run / parser-change
/ graph-YAML change, and otherwise re-indexes only the changed/added/deleted
docs and code files, rebuilds sync state from preserved baselines, and
backfills live-DB totals. It composes the cohesive helpers in this package; it
holds the change-driven sequence, not the mechanics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from beadloom.application.reindex.change_detection import (
    _compute_parser_fingerprint,
    _diff_files,
    _get_stored_file_index,
    _get_stored_parser_fingerprint,
    _graph_yaml_changed,
    _scan_project_files,
    _update_file_index,
)
from beadloom.application.reindex.enrichment import _extract_and_store_routes
from beadloom.application.reindex.full import _beadloom_version, reindex
from beadloom.application.reindex.indexing import (
    _build_doc_ref_map,
    _index_single_code_file,
    _index_single_doc,
    _resolve_docs_dir,
)
from beadloom.application.reindex.models import ReindexResult, _SyncPairSnapshot
from beadloom.application.reindex.sync_state import _build_initial_sync_state
from beadloom.infrastructure.db import create_schema, open_db, set_meta
from beadloom.infrastructure.health import take_snapshot

if TYPE_CHECKING:
    from pathlib import Path


def incremental_reindex(
    project_root: Path,
    *,
    docs_dir: Path | None = None,
) -> ReindexResult:
    """Incremental reindex: only process changed files.

    Falls back to full reindex when:
    - ``file_index`` is empty (first run after upgrade)
    - Any graph YAML file changed (safest: full reload)

    Parameters
    ----------
    project_root:
        Root of the project.
    docs_dir:
        Optional explicit docs directory.

    Returns
    -------
    ReindexResult
        Summary with counts for re-indexed items.
    """
    result = ReindexResult()

    db_path = project_root / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db_path)
    create_schema(conn)

    if docs_dir is None:
        docs_dir = _resolve_docs_dir(project_root)

    # Scan current files on disk.
    current_files = _scan_project_files(project_root, docs_dir)

    # Read stored hashes from previous run.
    stored_files = _get_stored_file_index(conn)

    if not stored_files:
        # First run — fall back to full reindex.
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    # Check if parser availability changed (e.g. new tree-sitter grammar installed).
    current_fingerprint = _compute_parser_fingerprint()
    stored_fingerprint = _get_stored_parser_fingerprint(conn)
    if stored_fingerprint is not None and current_fingerprint != stored_fingerprint:
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    # Belt-and-suspenders: always check graph YAML files directly.
    # This catches changes even if file_index got out of sync with the DB
    # (e.g. interrupted reindex, partial writes, or upgrade edge cases).
    graph_affected = _graph_yaml_changed(current_files, stored_files)
    if graph_affected:
        conn.close()
        return reindex(project_root, docs_dir=docs_dir)

    changed, added, deleted = _diff_files(current_files, stored_files)

    if not changed and not added and not deleted:
        # Nothing changed — just update timestamp.
        now = datetime.now(tz=timezone.utc).isoformat()
        set_meta(conn, "last_reindex_at", now)
        take_snapshot(conn)
        conn.close()
        result.nothing_changed = True
        return result

    # --- Only docs / code changed — true incremental path ---

    docs_dir_rel = docs_dir.relative_to(project_root)

    # Known ref_ids for edge creation.
    seen_ref_ids: set[str] = {
        row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()
    }

    # Doc → ref_id mapping (from graph YAML).
    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir():
        ref_map, doc_ref_warns = _build_doc_ref_map(
            graph_dir,
            project_root,
            docs_dir,
        )
        result.warnings.extend(doc_ref_warns)
    else:
        ref_map = {}

    # Snapshot symbols_hash and two-phase data BEFORE deleting/re-indexing
    # files so we can preserve baselines for drift detection.
    old_symbols: dict[str, str] = {}
    old_pairs: dict[tuple[str, str], _SyncPairSnapshot] = {}
    for row in conn.execute("SELECT * FROM sync_state").fetchall():
        if row["symbols_hash"]:
            old_symbols[row["ref_id"]] = row["symbols_hash"]
        # sqlite3.Row `in` checks values not keys; use .keys()
        has_edit_col = "doc_hash_at_last_edit" in row.keys()  # noqa: SIM118
        edit_hash: str = row["doc_hash_at_last_edit"] if has_edit_col else ""
        if edit_hash:
            old_pairs[(row["doc_path"], row["code_path"])] = _SyncPairSnapshot(
                doc_hash_at_last_edit=edit_hash,
                code_hash_at_sync=row["code_hash_at_sync"],
            )

    # Process deleted files.
    for path in deleted:
        kind = stored_files[path][1]
        if kind == "doc":
            doc_rel = str(type(docs_dir_rel)(path).relative_to(docs_dir_rel))
            conn.execute(
                "DELETE FROM sync_state WHERE doc_path = ?",
                (doc_rel,),
            )
            conn.execute("DELETE FROM docs WHERE path = ?", (doc_rel,))
        elif kind == "code":
            conn.execute(
                "DELETE FROM code_symbols WHERE file_path = ?",
                (path,),
            )
            conn.execute(
                "DELETE FROM sync_state WHERE code_path = ?",
                (path,),
            )

    # Process changed files (delete old data, re-index).
    for path in changed:
        kind = current_files[path][1]
        if kind == "doc":
            doc_rel = str(type(docs_dir_rel)(path).relative_to(docs_dir_rel))
            conn.execute("DELETE FROM docs WHERE path = ?", (doc_rel,))
            conn.execute(
                "DELETE FROM sync_state WHERE doc_path = ?",
                (doc_rel,),
            )
            abs_path = project_root / path
            d, c = _index_single_doc(conn, abs_path, docs_dir, ref_map)
            result.docs_indexed += d
            result.chunks_indexed += c
        elif kind == "code":
            conn.execute(
                "DELETE FROM code_symbols WHERE file_path = ?",
                (path,),
            )
            conn.execute(
                "DELETE FROM sync_state WHERE code_path = ?",
                (path,),
            )
            abs_path = project_root / path
            result.symbols_indexed += _index_single_code_file(
                conn,
                abs_path,
                project_root,
                seen_ref_ids,
            )

    # Process added files.
    for path in added:
        kind = current_files[path][1]
        if kind == "doc":
            abs_path = project_root / path
            d, c = _index_single_doc(conn, abs_path, docs_dir, ref_map)
            result.docs_indexed += d
            result.chunks_indexed += c
        elif kind == "code":
            abs_path = project_root / path
            result.symbols_indexed += _index_single_code_file(
                conn,
                abs_path,
                project_root,
                seen_ref_ids,
            )

    # Re-extract routes after code changes and update nodes.extra.
    _extract_and_store_routes(project_root, conn)

    # Rebuild sync_state (cheap full rebuild) using preserved baselines.
    conn.execute("DELETE FROM sync_state")
    _build_initial_sync_state(
        conn,
        preserved_symbols=old_symbols or None,
        preserved_pairs=old_pairs or None,
    )

    # Re-baseline reference-doc surface hashes, preserving existing baselines
    # (BDL-057 Layer 2; advisory). Unlike sync_state this is NOT deleted first —
    # build_reference_state preserves the prior aggregate_hash so accrued surface
    # drift survives a routine incremental reindex.
    from beadloom.doc_sync.engine import build_reference_state

    build_reference_state(conn, project_root)

    # Rebuild FTS5 search index.
    from beadloom.context_oracle.search import populate_search_index

    populate_search_index(conn)

    # Clear persistent bundle cache (conservative invalidation).
    conn.execute("DELETE FROM bundle_cache")
    conn.commit()

    # Update file_index.
    _update_file_index(conn, current_files, changed, added, deleted)

    # Update meta.
    now = datetime.now(tz=timezone.utc).isoformat()
    set_meta(conn, "last_reindex_at", now)
    set_meta(conn, "beadloom_version", _beadloom_version())

    # Health snapshot.
    take_snapshot(conn)

    # #88: the incremental path never touches the graph (nodes/edges), so the
    # ReindexResult defaults of 0 would make the CLI print "Nodes: 0" on an
    # intact index. Populate the true live-DB totals (mirroring the
    # nothing_changed branch handled in services/cli.py).
    result.nodes_loaded = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    result.edges_loaded = conn.execute("SELECT count(*) FROM edges").fetchone()[0]

    # #112: symbols_indexed accumulated only the per-run delta (re-indexed
    # changed/added code files), so a docs-only incremental run reported
    # "Symbols: 0" even on an intact index. Mirror the #88 nodes/edges
    # backfill: report the true live-DB symbol total.
    result.symbols_indexed = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]

    conn.close()
    return result
