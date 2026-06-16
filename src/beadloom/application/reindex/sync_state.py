# beadloom:domain=application
# beadloom:feature=reindex
"""Reindex sync-state baselining: snapshot and rebuild the sync_state table.

This module owns the two-phase doc-code sync baselines across a reindex: it
snapshots the prior ``sync_state`` (symbols hashes + per-pair edit/code hashes)
before the table is dropped, then rebuilds ``sync_state`` afterwards, preserving
those baselines so :func:`~beadloom.doc_sync.engine.check_sync` can still detect
symbol drift and code drift relative to the last doc edit.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from beadloom.application.reindex.models import _is_missing_table_error, _SyncPairSnapshot


def _snapshot_sync_baselines(
    conn: sqlite3.Connection,
) -> tuple[dict[str, str], dict[tuple[str, str], _SyncPairSnapshot]]:
    """Snapshot sync_state data before table drop.

    Returns
    -------
    tuple[dict[str, str], dict[tuple[str, str], _SyncPairSnapshot]]
        ``(symbols_by_ref, pair_snapshots)`` where:
        - *symbols_by_ref* maps ``ref_id -> symbols_hash`` for symbol drift detection
        - *pair_snapshots* maps ``(doc_path, code_path) -> _SyncPairSnapshot``
          preserving two-phase sync data across reindex
    """
    try:
        rows = conn.execute(
            "SELECT ref_id, symbols_hash, doc_path, code_path, "
            "doc_hash_at_last_edit, code_hash_at_sync FROM sync_state"
        ).fetchall()
    except sqlite3.OperationalError as exc:  # sync_state may not exist on first run
        if _is_missing_table_error(exc):
            return {}, {}
        raise

    symbols: dict[str, str] = {}
    pairs: dict[tuple[str, str], _SyncPairSnapshot] = {}
    for row in rows:
        sym_hash: str = row["symbols_hash"] or ""
        if sym_hash:
            symbols[row["ref_id"]] = sym_hash
        # sqlite3.Row `in` checks values not keys; use .keys()
        has_edit_col = "doc_hash_at_last_edit" in row.keys()  # noqa: SIM118
        edit_hash: str = row["doc_hash_at_last_edit"] if has_edit_col else ""
        if edit_hash:
            pairs[(row["doc_path"], row["code_path"])] = _SyncPairSnapshot(
                doc_hash_at_last_edit=edit_hash,
                code_hash_at_sync=row["code_hash_at_sync"],
            )
    return symbols, pairs


def _build_initial_sync_state(
    conn: sqlite3.Connection,
    *,
    preserved_symbols: dict[str, str] | None = None,
    preserved_pairs: dict[tuple[str, str], _SyncPairSnapshot] | None = None,
) -> None:
    """Populate sync_state table from docs and code_symbols with shared ref_ids.

    Parameters
    ----------
    preserved_symbols:
        Optional mapping of ``ref_id → symbols_hash`` from a previous sync
        state.  When provided, the old hash is kept so that
        :func:`~beadloom.doc_sync.engine.check_sync` can detect symbol drift
        (new/removed public symbols since the last time docs were marked
        synced).  When *None* (default), a fresh hash is computed — used on
        first full reindex to establish a baseline.
    preserved_pairs:
        Optional mapping of ``(doc_path, code_path) → _SyncPairSnapshot``
        from a previous sync state.  When provided, ``doc_hash_at_last_edit``
        is preserved across reindex so that two-phase sync detection can
        identify docs that haven't been updated since code changed.
        If the doc hasn't been edited since the last known edit, the old
        ``code_hash_at_sync`` baseline is also preserved (not reset to
        current) so that :func:`~beadloom.doc_sync.engine.check_sync` can
        detect code drift relative to the last doc edit.
    """
    from beadloom.doc_sync.engine import _compute_symbols_hash, build_sync_state

    now = datetime.now(tz=timezone.utc).isoformat()
    pairs = build_sync_state(conn)
    for pair in pairs:
        pair_key = (pair.doc_path, pair.code_path)
        snapshot = (preserved_pairs or {}).get(pair_key)

        # Two-phase sync: if doc_hash_at_last_edit is set and doc hasn't
        # been edited since, preserve the old code_hash_at_sync baseline
        # so check_sync can detect code drift since last doc edit.
        if (
            snapshot is not None
            and snapshot.doc_hash_at_last_edit
            and snapshot.doc_hash_at_last_edit == pair.doc_hash
        ):
            # Doc unchanged since last edit — keep old code baseline.
            effective_code_hash = snapshot.code_hash_at_sync
        else:
            effective_code_hash = pair.code_hash

        conn.execute(
            "INSERT OR IGNORE INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, 'ok')",
            (pair.doc_path, pair.code_path, pair.ref_id, effective_code_hash, pair.doc_hash, now),
        )
        # Preserve old symbols hash to detect drift, or compute fresh baseline.
        if preserved_symbols is not None and pair.ref_id in preserved_symbols:
            symbols_hash = preserved_symbols[pair.ref_id]
        else:
            symbols_hash = _compute_symbols_hash(conn, pair.ref_id)

        # Preserve doc_hash_at_last_edit from previous state.
        doc_hash_at_last_edit = snapshot.doc_hash_at_last_edit if snapshot else ""

        conn.execute(
            "UPDATE sync_state SET symbols_hash = ?, doc_hash_at_last_edit = ? "
            "WHERE doc_path = ? AND code_path = ?",
            (symbols_hash, doc_hash_at_last_edit, pair.doc_path, pair.code_path),
        )
    conn.commit()
