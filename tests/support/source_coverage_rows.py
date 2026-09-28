"""Rows a source-coverage test writes into an index, and the pre-N1 check it compares with."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def insert_node(
    conn: sqlite3.Connection,
    ref_id: str,
    source: str | None,
    *,
    kind: str = "domain",
    summary: str = "test node",
) -> None:
    """Insert a node with optional source field."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, summary, source),
    )
    conn.commit()


def insert_doc(
    conn: sqlite3.Connection,
    path: str,
    ref_id: str,
    *,
    kind: str = "domain",
    doc_hash: str = "dochash",
) -> None:
    """Insert a doc entry linked to a ref_id."""
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, kind, ref_id, doc_hash),
    )
    conn.commit()


def insert_sync_state(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    ref_id: str,
) -> None:
    """Insert a sync_state entry for a tracked code file."""
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, "hash1", "hash2", "2025-01-01", "ok"),
    )
    conn.commit()


def insert_code_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    ref_id: str,
    *,
    symbol_name: str = "some_func",
    kind: str = "function",
) -> None:
    """Insert a code_symbol annotated with a given ref_id."""
    annotations = json.dumps({"domain": ref_id})
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, kind, 1, 10, annotations, "filehash"),
    )
    conn.commit()


def insert_edge(
    conn: sqlite3.Connection,
    src_ref_id: str,
    dst_ref_id: str,
    kind: str = "part_of",
) -> None:
    """Insert an edge between two nodes."""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src_ref_id, dst_ref_id, kind),
    )
    conn.commit()


def legacy_check_source_coverage(
    conn: sqlite3.Connection, project_root: Path
) -> list[dict[str, object]]:
    """The pre-refactor per-node algorithm, frozen as the golden oracle.

    Mirrors the original ~5N-query implementation (per-node sync/docs lookup,
    per-node sync_state + edges + child sync_state, per-ref_id
    ``annotations LIKE '%"ref_id"%'``). The refactored set-based version MUST
    return structurally-identical results to this for any fixture.
    """
    from beadloom.doc_sync.engine import (
        _COVERAGE_EXCLUDE,
        _file_annotation_ref_ids,
        _tracked_paths_from_doc,
    )

    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()
    if not node_rows:
        return []

    results: list[dict[str, object]] = []
    for node in node_rows:
        ref_id = node["ref_id"]
        source = node["source"]
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        doc_row = conn.execute(
            "SELECT doc_path FROM sync_state WHERE ref_id = ? LIMIT 1", (ref_id,)
        ).fetchone()
        if doc_row is None:
            doc_row = conn.execute(
                "SELECT path AS doc_path FROM docs WHERE ref_id = ? LIMIT 1",
                (ref_id,),
            ).fetchone()
        if doc_row is None:
            continue
        doc_path = doc_row["doc_path"]

        disk_files: set[str] = set()
        for py_file in source_dir.glob("*.py"):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue
            disk_files.add(str(py_file.relative_to(project_root)))
        if not disk_files:
            continue

        tracked: set[str] = set()
        for r in conn.execute(
            "SELECT code_path FROM sync_state WHERE ref_id = ?", (ref_id,)
        ).fetchall():
            tracked.add(r["code_path"])

        child_rows = conn.execute(
            "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'part_of'",
            (ref_id,),
        ).fetchall()
        child_ref_ids = [r["src_ref_id"] for r in child_rows]
        for child_id in child_ref_ids:
            for r in conn.execute(
                "SELECT code_path FROM sync_state WHERE ref_id = ?", (child_id,)
            ).fetchall():
                tracked.add(r["code_path"])

        all_ref_ids = [ref_id, *child_ref_ids]
        for rid in all_ref_ids:
            for r in conn.execute(
                "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
                (f'%"{rid}"%',),
            ).fetchall():
                tracked.add(r["file_path"])

        owned_ref_ids = set(all_ref_ids)
        tracked |= _tracked_paths_from_doc(project_root / "docs" / doc_path, project_root)
        for disk_file in disk_files:
            if disk_file in tracked:
                continue
            if _file_annotation_ref_ids(project_root / disk_file) & owned_ref_ids:
                tracked.add(disk_file)

        untracked = sorted(disk_files - tracked)
        if untracked:
            results.append({"ref_id": ref_id, "doc_path": doc_path, "untracked_files": untracked})
    return results
