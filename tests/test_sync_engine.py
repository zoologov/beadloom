"""Tests for beadloom.sync_engine — doc-code sync state management."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.db import create_schema, open_db
from beadloom.sync_engine import SyncPair, build_sync_state, check_sync

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


def _setup_linked_data(conn: sqlite3.Connection) -> None:
    """Insert a node with linked doc and code symbol sharing ref_id."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("F1", "feature", "Feature 1"),
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("spec.md", "feature", "F1", "dochash1"),
    )
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("src/api.py", "handler", "function", 1, 10, json.dumps({"feature": "F1"}), "codehash1"),
    )
    conn.commit()


class TestBuildSyncState:
    def test_creates_pairs(self, conn: sqlite3.Connection) -> None:
        _setup_linked_data(conn)
        pairs = build_sync_state(conn)
        assert len(pairs) >= 1
        pair = pairs[0]
        assert isinstance(pair, SyncPair)
        assert pair.ref_id == "F1"
        assert pair.doc_path == "spec.md"
        assert pair.code_path == "src/api.py"

    def test_empty_db(self, conn: sqlite3.Connection) -> None:
        pairs = build_sync_state(conn)
        assert pairs == []

    def test_no_code_for_ref(self, conn: sqlite3.Connection) -> None:
        """Node with doc but no code symbol — no sync pair."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("spec.md", "feature", "F1", "dochash1"),
        )
        conn.commit()
        pairs = build_sync_state(conn)
        assert pairs == []

    def test_multiple_code_files(self, conn: sqlite3.Connection) -> None:
        """Multiple code files for same ref_id → multiple pairs."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("spec.md", "feature", "F1", "dochash1"),
        )
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/a.py", "fn_a", "function", 1, 5, json.dumps({"feature": "F1"}), "hash_a"),
        )
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/b.py", "fn_b", "function", 1, 5, json.dumps({"feature": "F1"}), "hash_b"),
        )
        conn.commit()
        pairs = build_sync_state(conn)
        code_paths = {p.code_path for p in pairs}
        assert "src/a.py" in code_paths
        assert "src/b.py" in code_paths


class TestCheckSync:
    def test_all_ok(self, conn: sqlite3.Connection) -> None:
        _setup_linked_data(conn)
        pairs = build_sync_state(conn)
        # Populate sync_state with current hashes.
        for pair in pairs:
            conn.execute(
                "INSERT INTO sync_state "
                "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
                "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pair.doc_path, pair.code_path, pair.ref_id,
                 pair.code_hash, pair.doc_hash, "2025-01-01", "ok"),
            )
        conn.commit()
        results = check_sync(conn)
        assert all(r["status"] == "ok" for r in results)

    def test_stale_code(self, conn: sqlite3.Connection) -> None:
        _setup_linked_data(conn)
        # Insert sync_state with old code hash.
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1", "OLD_HASH", "dochash1", "2025-01-01", "ok"),
        )
        conn.commit()
        results = check_sync(conn)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1

    def test_stale_doc(self, conn: sqlite3.Connection) -> None:
        _setup_linked_data(conn)
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1", "codehash1", "OLD_DOC_HASH", "2025-01-01", "ok"),
        )
        conn.commit()
        results = check_sync(conn)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1

    def test_no_sync_state(self, conn: sqlite3.Connection) -> None:
        """If no sync_state entries, check_sync returns empty."""
        results = check_sync(conn)
        assert results == []
