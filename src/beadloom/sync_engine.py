"""Sync engine: doc-code synchronization state management."""

from __future__ import annotations

import json
from dataclasses import dataclass
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


def check_sync(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Check sync_state entries against current doc and code hashes.

    Compares stored hashes with current hashes from docs and code_symbols.
    Returns list of dicts with doc_path, code_path, ref_id, status.
    """
    sync_rows = conn.execute("SELECT * FROM sync_state").fetchall()
    if not sync_rows:
        return []

    results: list[dict[str, str]] = []

    for row in sync_rows:
        doc_path = row["doc_path"]
        code_path = row["code_path"]
        ref_id = row["ref_id"]
        stored_code_hash = row["code_hash_at_sync"]
        stored_doc_hash = row["doc_hash_at_sync"]

        # Get current hashes.
        doc_row = conn.execute(
            "SELECT hash FROM docs WHERE path = ?", (doc_path,)
        ).fetchone()
        current_doc_hash = doc_row["hash"] if doc_row else None

        sym_row = conn.execute(
            "SELECT file_hash FROM code_symbols WHERE file_path = ? LIMIT 1",
            (code_path,),
        ).fetchone()
        current_code_hash = sym_row["file_hash"] if sym_row else None

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
