"""Tests for beadloom.sync_engine — doc-code sync state management."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import (
    SyncPair,
    _compute_symbols_hash,
    build_sync_state,
    check_sync,
    mark_synced,
)
from beadloom.infrastructure.db import create_schema, open_db

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
                (
                    pair.doc_path,
                    pair.code_path,
                    pair.ref_id,
                    pair.code_hash,
                    pair.doc_hash,
                    "2025-01-01",
                    "ok",
                ),
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
            (
                "spec.md",
                "src/api.py",
                "F1",
                "OLD_HASH",
                _file_hash(doc_content),
                "2025-01-01",
                "ok",
            ),
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
            (
                "spec.md",
                "src/api.py",
                "F1",
                _file_hash(code_content),
                "OLD_DOC_HASH",
                "2025-01-01",
                "ok",
            ),
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
        conn.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('F1', 'feature', 'test')")
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
            "VALUES ('spec.md', 'src/api.py', 'F1', 'old_hash', 'old_hash', "
            "'2025-01-01', 'stale')"
        )
        conn.commit()

        mark_synced(conn, "spec.md", "src/api.py", project)

        row = conn.execute("SELECT * FROM sync_state WHERE doc_path = 'spec.md'").fetchone()
        assert row["status"] == "ok"
        assert row["doc_hash_at_sync"] != "old_hash"
        assert row["code_hash_at_sync"] != "old_hash"


class TestComputeSymbolsHash:
    """Tests for _compute_symbols_hash including file_path in hash."""

    def test_includes_file_path_in_hash(self, conn: sqlite3.Connection) -> None:
        """Hash changes when same symbol name is in a different file.

        Before the fix, _compute_symbols_hash only used symbol_name:kind,
        so moving a symbol to another file would not change the hash.
        After the fix, file_path is included, so the hash MUST change.
        """
        # Insert a symbol in file_a.py.
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/file_a.py", "handler", "function", 1, 10, json.dumps({"feature": "F1"}), "h1"),
        )
        conn.commit()

        hash_a = _compute_symbols_hash(conn, "F1")
        assert hash_a != "", "Expected non-empty hash for annotated symbol"

        # Delete the symbol from file_a and insert it in file_b.
        conn.execute("DELETE FROM code_symbols")
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/file_b.py", "handler", "function", 1, 10, json.dumps({"feature": "F1"}), "h2"),
        )
        conn.commit()

        hash_b = _compute_symbols_hash(conn, "F1")
        assert hash_b != "", "Expected non-empty hash for annotated symbol"

        # The hashes MUST differ because the file_path changed.
        assert hash_a != hash_b, (
            "Hash should change when symbol moves to a different file"
        )

    def test_empty_when_no_symbols(self, conn: sqlite3.Connection) -> None:
        """Returns empty string when no symbols exist for ref_id."""
        result = _compute_symbols_hash(conn, "nonexistent")
        assert result == ""


class TestCheckSyncIntegration:
    """Integration tests for check_sync with source and doc coverage checks."""

    def test_source_coverage_stale_with_hash_ok(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Source coverage gap should mark ref_id as stale even if hash is ok."""
        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"
        _setup_linked_data(conn, project, doc_content=doc_content, code_content=code_content)

        # Add node with directory source
        conn.execute(
            "UPDATE nodes SET source = 'src/' WHERE ref_id = 'F1'"
        )

        # Insert sync_state with correct hashes (hash check = ok)
        pairs = build_sync_state(conn)
        for pair in pairs:
            conn.execute(
                "INSERT INTO sync_state "
                "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
                "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pair.doc_path,
                    pair.code_path,
                    pair.ref_id,
                    pair.code_hash,
                    pair.doc_hash,
                    "2025-01-01",
                    "ok",
                ),
            )
        conn.commit()

        # Add an untracked file to the source directory
        (project / "src" / "new_module.py").write_text("def new(): pass\n")

        results = check_sync(conn, project_root=project)

        # Find the result for F1
        f1_results = [r for r in results if r["ref_id"] == "F1"]
        assert len(f1_results) >= 1

        # At least one result should be stale due to untracked files
        stale = [r for r in f1_results if r["status"] == "stale"]
        assert len(stale) >= 1

        # Check reason field exists
        stale_with_reason = [r for r in stale if r.get("reason") == "untracked_files"]
        assert len(stale_with_reason) >= 1

    def test_doc_coverage_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Doc coverage gap should mark ref_id as stale."""
        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"
        _setup_linked_data(conn, project, doc_content=doc_content, code_content=code_content)

        # Add node with directory source
        conn.execute(
            "UPDATE nodes SET source = 'src/' WHERE ref_id = 'F1'"
        )

        # Insert sync_state with correct hashes (hash check = ok)
        pairs = build_sync_state(conn)
        for pair in pairs:
            conn.execute(
                "INSERT INTO sync_state "
                "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
                "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pair.doc_path,
                    pair.code_path,
                    pair.ref_id,
                    pair.code_hash,
                    pair.doc_hash,
                    "2025-01-01",
                    "ok",
                ),
            )
        conn.commit()

        # Add a new file that doc doesn't mention
        (project / "src" / "unmention.py").write_text("def x(): pass\n")
        # Track it via code_symbols so source coverage is ok
        _setup_code_symbol(conn, "src/unmention.py", "F1")

        results = check_sync(conn, project_root=project)

        # Should have a stale result for missing doc module coverage
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1

        stale_doc_cov = [r for r in stale if r.get("reason") == "missing_modules"]
        assert len(stale_doc_cov) >= 1

    def test_all_checks_ok(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """When all checks pass, result should show ok with reason=ok."""
        doc_content = "# Spec\nFeature spec about api.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"
        _setup_linked_data(conn, project, doc_content=doc_content, code_content=code_content)

        # Insert sync_state with correct hashes
        pairs = build_sync_state(conn)
        for pair in pairs:
            conn.execute(
                "INSERT INTO sync_state "
                "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
                "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pair.doc_path,
                    pair.code_path,
                    pair.ref_id,
                    pair.code_hash,
                    pair.doc_hash,
                    "2025-01-01",
                    "ok",
                ),
            )
        conn.commit()

        results = check_sync(conn, project_root=project)
        assert all(r["status"] == "ok" for r in results)
        # Every result should have a reason field
        assert all("reason" in r for r in results)

    def test_hash_stale_keeps_reason(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Hash-based stale should report reason=hash_changed."""
        doc_content = "# Spec\nFeature spec.\n"
        _setup_linked_data(conn, project, doc_content=doc_content)
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "spec.md",
                "src/api.py",
                "F1",
                "OLD_HASH",
                _file_hash(doc_content),
                "2025-01-01",
                "ok",
            ),
        )
        conn.commit()
        results = check_sync(conn, project_root=project)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) >= 1
        assert stale[0].get("reason") == "hash_changed"


def _setup_code_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    ref_id: str,
    *,
    symbol_name: str = "some_func",
) -> None:
    """Insert a code_symbol annotated with a given ref_id."""
    annotations = json.dumps({"feature": ref_id})
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, annotations, "filehash"),
    )
    conn.commit()
