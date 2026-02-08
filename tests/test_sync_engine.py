"""Tests for beadloom.sync_engine — doc-code sync state management."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.db import create_schema, open_db
from beadloom.sync_engine import SyncPair, build_sync_state, check_sync, mark_synced

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project directory with docs/ and src/ for sync tests."""
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / "src").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    db_path = project / ".beadloom" / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _setup_linked_data(
    conn: sqlite3.Connection,
    project: Path,
    doc_content: str = "# Spec\nFeature spec.\n",
    code_content: str = "# beadloom:feature=F1\ndef handler():\n    pass\n",
) -> None:
    """Insert a node with linked doc and code symbol sharing ref_id.

    Also creates actual files on disk for hash-based sync checking.
    """
    doc_hash = _file_hash(doc_content)
    code_hash = _file_hash(code_content)

    (project / "docs" / "spec.md").write_text(doc_content)
    (project / "src" / "api.py").write_text(code_content)

    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("F1", "feature", "Feature 1"),
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("spec.md", "feature", "F1", doc_hash),
    )
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("src/api.py", "handler", "function", 1, 10, json.dumps({"feature": "F1"}), code_hash),
    )
    conn.commit()


class TestBuildSyncState:
    def test_creates_pairs(self, conn: sqlite3.Connection, project: Path) -> None:
        _setup_linked_data(conn, project)
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
    def test_all_ok(self, conn: sqlite3.Connection, project: Path) -> None:
        _setup_linked_data(conn, project)
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
        results = check_sync(conn, project_root=project)
        assert all(r["status"] == "ok" for r in results)

    def test_stale_code(self, conn: sqlite3.Connection, project: Path) -> None:
        doc_content = "# Spec\nFeature spec.\n"
        _setup_linked_data(conn, project, doc_content=doc_content)
        # Insert sync_state with current doc hash but old code hash.
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1", "OLD_HASH",
             _file_hash(doc_content), "2025-01-01", "ok"),
        )
        conn.commit()
        results = check_sync(conn, project_root=project)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1

    def test_stale_doc(self, conn: sqlite3.Connection, project: Path) -> None:
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"
        _setup_linked_data(conn, project, code_content=code_content)
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "F1",
             _file_hash(code_content), "OLD_DOC_HASH", "2025-01-01", "ok"),
        )
        conn.commit()
        results = check_sync(conn, project_root=project)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1

    def test_no_sync_state(self, conn: sqlite3.Connection, project: Path) -> None:
        """If no sync_state entries, check_sync returns empty."""
        results = check_sync(conn, project_root=project)
        assert results == []


class TestMarkSynced:
    def test_updates_hashes_and_status(self, conn: sqlite3.Connection, project: Path) -> None:
        """mark_synced should update hashes and set status to 'ok'."""
        # Create files on disk.
        (project / "docs" / "spec.md").write_text("# Spec\n\nContent.\n")
        (project / "src" / "api.py").write_text("def handler():\n    pass\n")

        # Insert a node and stale sync_state.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES ('F1', 'feature', 'test')"
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
            "VALUES ('spec.md', 'src/api.py', 'F1', 'old_hash', 'old_hash', "
            "'2025-01-01', 'stale')"
        )
        conn.commit()

        mark_synced(conn, "spec.md", "src/api.py", project)

        row = conn.execute(
            "SELECT * FROM sync_state WHERE doc_path = 'spec.md'"
        ).fetchone()
        assert row["status"] == "ok"
        assert row["doc_hash_at_sync"] != "old_hash"
        assert row["code_hash_at_sync"] != "old_hash"
