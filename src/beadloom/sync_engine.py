"""Sync engine: doc-code synchronization state management."""

# beadloom:domain=doc-sync

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


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
                    pairs.append(SyncPair(
                        ref_id=ref_id,
                        doc_path=doc_path,
                        code_path=sym["file_path"],
                        doc_hash=doc_hash,
                        code_hash=sym["file_hash"],
                    ))
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
) -> list[dict[str, str]]:
    """Check sync_state entries against actual file hashes on disk.

    Reads files directly from disk to detect changes since last sync,
    independent of whether reindex has been run.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    project_root:
        Project root directory. If None, inferred from DB path.

    Returns list of dicts with doc_path, code_path, ref_id, status.
    """
    sync_rows = conn.execute("SELECT * FROM sync_state").fetchall()
    if not sync_rows:
        return []

    # Infer project root from database path if not provided.
    if project_root is None:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        project_root = Path(db_path).parent.parent  # .beadloom/beadloom.db → project

    results: list[dict[str, str]] = []

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
        if current_code_hash and current_code_hash != stored_code_hash:
            status = "stale"
        if current_doc_hash and current_doc_hash != stored_doc_hash:
            status = "stale"

        # Update status in DB.
        conn.execute(
            "UPDATE sync_state SET status = ? WHERE doc_path = ? AND code_path = ?",
            (status, doc_path, code_path),
        )

        results.append({
            "doc_path": doc_path,
            "code_path": code_path,
            "ref_id": ref_id,
            "status": status,
        })

    conn.commit()
    return results


def mark_synced(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    project_root: Path,
) -> None:
    """Recompute hashes for a doc-code pair and mark as synced."""
    doc_hash = _file_hash(project_root / "docs" / doc_path)
    code_hash = _file_hash(project_root / code_path)

    now = datetime.now(tz=timezone.utc).isoformat()
    conn.execute(
        "UPDATE sync_state SET doc_hash_at_sync = ?, code_hash_at_sync = ?, "
        "synced_at = ?, status = 'ok' WHERE doc_path = ? AND code_path = ?",
        (doc_hash, code_hash, now, doc_path, code_path),
    )
    conn.commit()
