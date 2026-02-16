"""Sync engine: doc-code synchronization state management."""

# beadloom:domain=doc-sync

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


def _compute_symbols_hash(conn: sqlite3.Connection, ref_id: str) -> str:
    """Compute SHA-256 of sorted code_symbols for a *ref_id*.

    Returns an empty string when no symbols are annotated with the given
    ref_id, allowing callers to skip drift checks for unlinked nodes.
    """
    rows = conn.execute(
        "SELECT file_path, symbol_name, kind FROM code_symbols "
        "WHERE annotations LIKE ? ORDER BY file_path, symbol_name",
        (f'%"{ref_id}"%',),
    ).fetchall()
    if not rows:
        return ""
    data = "|".join(f"{r['file_path']}:{r['symbol_name']}:{r['kind']}" for r in rows)
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class SyncPair:
    """A doc-code pair linked through a shared ref_id."""

    ref_id: str
    doc_path: str
    code_path: str
    doc_hash: str
    code_hash: str


# beadloom:domain=doc-sync
def build_sync_state(conn: sqlite3.Connection) -> list[SyncPair]:
    """Build sync pairs from docs and code_symbols sharing a ref_id.

    For each ref_id that has both a doc and at least one code symbol,
    creates a SyncPair with current hashes.
    """
    # Find ref_ids that have linked docs.
    doc_rows = conn.execute(
        "SELECT ref_id, path, hash FROM docs WHERE ref_id IS NOT NULL"
    ).fetchall()

    if not doc_rows:
        return []

    pairs: list[SyncPair] = []

    for doc_row in doc_rows:
        ref_id = doc_row["ref_id"]
        doc_path = doc_row["path"]
        doc_hash = doc_row["hash"]

        # Find code symbols annotated with this ref_id.
        sym_rows = conn.execute("SELECT * FROM code_symbols").fetchall()
        seen_files: set[str] = set()

        for sym in sym_rows:
            annotations: dict[str, Any] = json.loads(sym["annotations"])
            for _key, val in annotations.items():
                if val == ref_id and sym["file_path"] not in seen_files:
                    seen_files.add(sym["file_path"])
                    pairs.append(
                        SyncPair(
                            ref_id=ref_id,
                            doc_path=doc_path,
                            code_path=sym["file_path"],
                            doc_hash=doc_hash,
                            code_hash=sym["file_hash"],
                        )
                    )
                    break

    return pairs


def _file_hash(path: Path) -> str | None:
    """Compute SHA-256 hash of a file, or None if file doesn't exist."""
    if not path.is_file():
        return None
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def check_sync(
    conn: sqlite3.Connection,
    project_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Check sync_state entries against actual file hashes on disk.

    Reads files directly from disk to detect changes since last sync,
    independent of whether reindex has been run.  Also runs source
    coverage and doc coverage checks to catch untracked files and
    missing module mentions.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    project_root:
        Project root directory. If None, inferred from DB path.

    Returns list of dicts with doc_path, code_path, ref_id, status,
    reason, and optional details.
    """
    sync_rows = conn.execute("SELECT * FROM sync_state").fetchall()
    if not sync_rows:
        return []

    # Infer project root from database path if not provided.
    if project_root is None:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        project_root = Path(db_path).parent.parent  # .beadloom/beadloom.db → project

    results: list[dict[str, Any]] = []

    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        stored_code_hash = row["code_hash_at_sync"]
        stored_doc_hash = row["doc_hash_at_sync"]

        # Hash actual files on disk.
        current_doc_hash = _file_hash(project_root / "docs" / doc_path)
        current_code_hash = _file_hash(project_root / code_path)

        status = "ok"
        reason = "ok"
        if current_code_hash and current_code_hash != stored_code_hash:
            status = "stale"
            reason = "hash_changed"
        if current_doc_hash and current_doc_hash != stored_doc_hash:
            status = "stale"
            reason = "hash_changed"

        # Symbol-level drift detection.
        stored_symbols_hash = row["symbols_hash"] if "symbols_hash" in row.keys() else ""  # noqa: SIM118 - sqlite3.Row `in` checks values, not keys
        if stored_symbols_hash:
            current_symbols_hash = _compute_symbols_hash(conn, ref_id)
            if current_symbols_hash != stored_symbols_hash and status == "ok":
                # Code symbols changed but doc hash is same -> semantic drift.
                status = "stale"
                reason = "symbols_changed"

        # Update status in DB.
        conn.execute(
            "UPDATE sync_state SET status = ? WHERE doc_path = ? AND code_path = ?",
            (status, doc_path, code_path),
        )

        results.append(
            {
                "doc_path": doc_path,
                "code_path": code_path,
                "ref_id": ref_id,
                "status": status,
                "reason": reason,
            }
        )

    conn.commit()

    # --- Phase 2: Source coverage checks ---
    source_gaps = check_source_coverage(conn, project_root)

    # Build a lookup of ref_ids already in results and their indices.
    ref_id_indices: dict[str, list[int]] = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in source_gaps:
        gap_ref_id: str = gap["ref_id"]
        gap_doc_path: str = gap["doc_path"]
        untracked: list[str] = gap["untracked_files"]
        details = ", ".join(Path(f).name for f in untracked)

        if gap_ref_id in ref_id_indices:
            # Update existing results: if any are "ok", change to "stale"
            for idx in ref_id_indices[gap_ref_id]:
                if results[idx]["status"] == "ok":
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "untracked_files"
                    results[idx]["details"] = details
                    # Update DB status
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            # Add new result for ref_id not yet in sync_state
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "untracked_files",
                    "details": details,
                }
            )

    # --- Phase 3: Doc coverage checks ---
    doc_gaps = check_doc_coverage(conn, project_root)
    # Rebuild index since source coverage may have added entries.
    ref_id_indices = {}
    for i, r in enumerate(results):
        ref_id_indices.setdefault(r["ref_id"], []).append(i)

    for gap in doc_gaps:
        gap_ref_id = gap["ref_id"]
        gap_doc_path = gap["doc_path"]
        missing: list[str] = gap["missing_modules"]
        details = ", ".join(missing)

        if gap_ref_id in ref_id_indices:
            for idx in ref_id_indices[gap_ref_id]:
                if results[idx]["status"] == "ok":
                    results[idx]["status"] = "stale"
                    results[idx]["reason"] = "missing_modules"
                    results[idx]["details"] = details
                    conn.execute(
                        "UPDATE sync_state SET status = 'stale' "
                        "WHERE doc_path = ? AND code_path = ?",
                        (results[idx]["doc_path"], results[idx]["code_path"]),
                    )
        else:
            results.append(
                {
                    "doc_path": gap_doc_path,
                    "code_path": "",
                    "ref_id": gap_ref_id,
                    "status": "stale",
                    "reason": "missing_modules",
                    "details": details,
                }
            )

    conn.commit()
    return results


def mark_synced(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    project_root: Path,
) -> None:
    """Recompute hashes for a doc-code pair and mark as synced.

    Also updates ``symbols_hash`` to the current value so that future
    :func:`check_sync` calls use this as the new baseline for symbol drift
    detection.
    """
    doc_hash = _file_hash(project_root / "docs" / doc_path)
    code_hash = _file_hash(project_root / code_path)

    # Look up ref_id for this pair to recompute symbols_hash.
    row = conn.execute(
        "SELECT ref_id FROM sync_state WHERE doc_path = ? AND code_path = ?",
        (doc_path, code_path),
    ).fetchone()
    symbols_hash = _compute_symbols_hash(conn, row["ref_id"]) if row else ""

    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
        "symbols_hash = ?, synced_at = ?, status = 'ok' "
        "WHERE doc_path = ? AND code_path = ?",
        (doc_hash, code_hash, symbols_hash, now, doc_path, code_path),
    )
    conn.commit()


def mark_synced_by_ref(
    conn: sqlite3.Connection,
    ref_id: str,
    project_root: Path,
) -> int:
    """Mark all doc-code pairs for *ref_id* as synced.

    Recomputes current file hashes and ``symbols_hash``, establishing a new
    baseline for symbol drift detection.
    Returns the number of rows updated.
    """
    rows = conn.execute(
        "SELECT doc_path, code_path FROM sync_state WHERE ref_id = ?",
        (ref_id,),
    ).fetchall()

    if not rows:
        return 0

    symbols_hash = _compute_symbols_hash(conn, ref_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    count = 0
    for row in rows:
        doc_hash = _file_hash(project_root / "docs" / row["doc_path"])
        code_hash = _file_hash(project_root / row["code_path"])
        conn.execute(
            "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
            "symbols_hash = ?, synced_at = ?, status = 'ok' "
            "WHERE doc_path = ? AND code_path = ?",
            (doc_hash, code_hash, symbols_hash, now, row["doc_path"], row["code_path"]),
        )
        count += 1

    conn.commit()
    return count


# Excluded filenames — boilerplate, not doc-worthy
_COVERAGE_EXCLUDE = frozenset({"__init__.py", "conftest.py", "__main__.py"})


def check_source_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if all source files in a node's directory are tracked in sync_state.

    For each node with a ``source`` field ending in ``/`` (a directory),
    compares actual Python files on disk against code_paths tracked in
    sync_state for that ref_id.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``untracked_files``
    for nodes that have gaps.
    """
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve directory on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Find doc_path for this ref_id (from sync_state first, then docs table)
        doc_row = conn.execute(
            "SELECT doc_path FROM sync_state WHERE ref_id = ? LIMIT 1",
            (ref_id,),
        ).fetchone()

        if doc_row is None:
            # Fallback to docs table
            doc_row = conn.execute(
                "SELECT path AS doc_path FROM docs WHERE ref_id = ? LIMIT 1",
                (ref_id,),
            ).fetchone()

        if doc_row is None:
            # No linked doc — skip, nothing to mark stale
            continue

        doc_path: str = doc_row["doc_path"]

        # 4. List *.py files on disk (non-recursive), excluding boilerplate
        disk_files: set[str] = set()
        for py_file in source_dir.glob("*.py"):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue
            relative = str(py_file.relative_to(project_root))
            disk_files.add(relative)

        if not disk_files:
            continue

        # 5. Collect tracked code_paths from sync_state for this ref_id
        tracked: set[str] = set()
        sync_rows = conn.execute(
            "SELECT code_path FROM sync_state WHERE ref_id = ?",
            (ref_id,),
        ).fetchall()
        for row in sync_rows:
            tracked.add(row["code_path"])

        # 5b. Also include files tracked under child nodes (part_of this ref_id)
        child_rows = conn.execute(
            "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'part_of'",
            (ref_id,),
        ).fetchall()
        child_ref_ids = [r["src_ref_id"] for r in child_rows]

        for child_id in child_ref_ids:
            child_sync = conn.execute(
                "SELECT code_path FROM sync_state WHERE ref_id = ?",
                (child_id,),
            ).fetchall()
            for r in child_sync:
                tracked.add(r["code_path"])

        # 6. Also collect file_paths from code_symbols annotated with this ref_id
        #    OR any child ref_id
        all_ref_ids = [ref_id, *child_ref_ids]
        for rid in all_ref_ids:
            sym_rows = conn.execute(
                "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
                (f'%"{rid}"%',),
            ).fetchall()
            for row in sym_rows:
                tracked.add(row["file_path"])

        # 7. Find untracked files
        untracked = sorted(disk_files - tracked)

        # 8. Report if gaps exist
        if untracked:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "untracked_files": untracked,
                }
            )

    return results


def check_doc_coverage(
    conn: sqlite3.Connection,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Check if documentation mentions module names from the node's source directory.

    For each node with a directory-based ``source``, lists Python file stems
    (without .py) and checks if the linked doc content contains each name.

    Returns list of dicts with ``ref_id``, ``doc_path``, ``missing_modules``
    for nodes where the doc is missing module mentions.
    """
    # 1. Query nodes with directory-based source (ending in /)
    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()

    if not node_rows:
        return []

    results: list[dict[str, Any]] = []

    for node in node_rows:
        ref_id: str = node["ref_id"]
        source: str = node["source"]

        # 2. Resolve source dir on disk
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        # 3. Get the doc path from docs table for this ref_id
        doc_row = conn.execute(
            "SELECT path FROM docs WHERE ref_id = ? LIMIT 1",
            (ref_id,),
        ).fetchone()

        if doc_row is None:
            continue

        doc_path: str = doc_row["path"]

        # 4. Read the doc file content from disk
        doc_file = project_root / "docs" / doc_path
        if not doc_file.is_file():
            continue

        doc_content = doc_file.read_text(encoding="utf-8")

        # 5. List *.py files on disk (non-recursive), excluding boilerplate
        missing_modules: list[str] = []
        for py_file in sorted(source_dir.glob("*.py")):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue

            # 6. Get stem and check if it appears as a word in doc content
            stem = py_file.stem
            pattern = re.compile(rf"\b{re.escape(stem)}\b", re.IGNORECASE)
            if not pattern.search(doc_content):
                missing_modules.append(stem)

        # 7-8. If any missing, add to results
        if missing_modules:
            results.append(
                {
                    "ref_id": ref_id,
                    "doc_path": doc_path,
                    "missing_modules": missing_modules,
                }
            )

    return results
