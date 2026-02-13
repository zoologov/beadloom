"""Tests for beadloom.db — SQLite schema and connection management."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, get_meta, open_db, set_meta

if TYPE_CHECKING:
    from pathlib import Path


class TestOpenDb:
    """Tests for open_db() connection factory."""

    def test_creates_db_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)
        conn = open_db(db_path)
        conn.close()
        assert db_path.exists()

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = open_db(db_path)
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result is not None
        assert result[0] == "wal"
        conn.close()

    def test_foreign_keys_enabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = open_db(db_path)
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result is not None
        assert result[0] == 1
        conn.close()

    def test_foreign_keys_per_connection(self, tmp_path: Path) -> None:
        """Each new connection must re-enable foreign_keys."""
        db_path = tmp_path / "test.db"
        conn1 = open_db(db_path)
        conn1.close()
        conn2 = open_db(db_path)
        result = conn2.execute("PRAGMA foreign_keys").fetchone()
        assert result is not None
        assert result[0] == 1
        conn2.close()

    def test_returns_row_factory(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = open_db(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestCreateSchema:
    """Tests for create_schema() — all tables, constraints, indexes."""

    @pytest.fixture()
    def conn(self, tmp_path: Path) -> sqlite3.Connection:
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        return c

    def test_all_tables_exist(self, conn: sqlite3.Connection) -> None:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        expected = {"nodes", "edges", "docs", "chunks", "code_symbols", "sync_state", "meta"}
        assert expected.issubset(tables)

    def test_nodes_check_kind(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("test-node", "domain", "Test"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                ("bad-node", "invalid_kind", "Test"),
            )

    def test_nodes_ref_id_unique(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("dup", "domain", "First"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                ("dup", "feature", "Second"),
            )

    def test_edges_check_kind(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("a", "domain", "A"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("b", "service", "B"),
        )
        conn.commit()
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("b", "a", "part_of"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                ("b", "a", "bad_kind"),
            )

    def test_edges_cascade_on_node_delete(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("src", "domain", "Source"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("dst", "service", "Dest"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("src", "dst", "part_of"),
        )
        conn.commit()
        conn.execute("DELETE FROM nodes WHERE ref_id = ?", ("src",))
        conn.commit()
        edges = conn.execute("SELECT * FROM edges").fetchall()
        assert len(edges) == 0

    def test_edges_fk_enforcement(self, conn: sqlite3.Connection) -> None:
        """Edges must reference existing nodes."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
                ("nonexistent", "also_nonexistent", "part_of"),
            )

    def test_docs_check_kind(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO docs (path, kind, hash) VALUES (?, ?, ?)",
            ("docs/test.md", "feature", "abc123"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO docs (path, kind, hash) VALUES (?, ?, ?)",
                ("docs/bad.md", "invalid_kind", "abc123"),
            )

    def test_docs_ref_id_set_null_on_node_delete(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("n1", "feature", "Feature"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("docs/f.md", "feature", "n1", "hash1"),
        )
        conn.commit()
        conn.execute("DELETE FROM nodes WHERE ref_id = ?", ("n1",))
        conn.commit()
        row = conn.execute("SELECT ref_id FROM docs WHERE path = ?", ("docs/f.md",)).fetchone()
        assert row is not None
        assert row[0] is None  # SET NULL, not CASCADE

    def test_chunks_cascade_on_doc_delete(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO docs (path, kind, hash) VALUES (?, ?, ?)",
            ("docs/x.md", "other", "h1"),
        )
        doc_id = conn.execute("SELECT id FROM docs WHERE path = ?", ("docs/x.md",)).fetchone()[0]
        conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, content) VALUES (?, ?, ?)",
            (doc_id, 0, "chunk text"),
        )
        conn.commit()
        conn.execute("DELETE FROM docs WHERE id = ?", (doc_id,))
        conn.commit()
        chunks = conn.execute("SELECT * FROM chunks").fetchall()
        assert len(chunks) == 0

    def test_chunks_node_ref_id_set_null(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("cn", "domain", "D"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, hash) VALUES (?, ?, ?)",
            ("docs/c.md", "domain", "h"),
        )
        doc_id = conn.execute("SELECT id FROM docs").fetchone()[0]
        conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, content, node_ref_id) VALUES (?, ?, ?, ?)",
            (doc_id, 0, "text", "cn"),
        )
        conn.commit()
        conn.execute("DELETE FROM nodes WHERE ref_id = ?", ("cn",))
        conn.commit()
        row = conn.execute("SELECT node_ref_id FROM chunks").fetchone()
        assert row is not None
        assert row[0] is None

    def test_code_symbols_check_kind(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, "
            "file_hash) VALUES (?, ?, ?, ?, ?, ?)",
            ("src/a.py", "foo", "function", 1, 10, "hash"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, "
                "file_hash) VALUES (?, ?, ?, ?, ?, ?)",
                ("src/b.py", "bar", "invalid_kind", 1, 5, "hash"),
            )

    def test_sync_state_check_status(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("ss", "feature", "F"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
            "doc_hash_at_sync, synced_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("d.md", "c.py", "ss", "h1", "h2", "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
                "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("d2.md", "c2.py", "ss", "h1", "h2", "2026-01-01T00:00:00Z", "bad_status"),
            )

    def test_sync_state_unique_doc_code_pair(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("u", "feature", "F"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
            "doc_hash_at_sync, synced_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("d.md", "c.py", "u", "h1", "h2", "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
                "doc_hash_at_sync, synced_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("d.md", "c.py", "u", "h3", "h4", "2026-01-02T00:00:00Z"),
            )

    def test_indexes_exist(self, conn: sqlite3.Connection) -> None:
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            ).fetchall()
        }
        expected = {
            "idx_nodes_kind",
            "idx_edges_src",
            "idx_edges_dst",
            "idx_docs_ref",
            "idx_chunks_doc",
            "idx_chunks_node",
            "idx_symbols_file",
            "idx_sync_status",
            "idx_sync_ref",
        }
        assert expected.issubset(indexes)

    def test_idempotent_schema_creation(self, conn: sqlite3.Connection) -> None:
        """create_schema should be safe to call multiple times."""
        create_schema(conn)  # second call
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert len(tables) > 0


class TestMeta:
    """Tests for get_meta() / set_meta()."""

    @pytest.fixture()
    def conn(self, tmp_path: Path) -> sqlite3.Connection:
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        return c

    def test_set_and_get(self, conn: sqlite3.Connection) -> None:
        set_meta(conn, "test_key", "test_value")
        assert get_meta(conn, "test_key") == "test_value"

    def test_get_missing_returns_none(self, conn: sqlite3.Connection) -> None:
        assert get_meta(conn, "nonexistent") is None

    def test_get_missing_with_default(self, conn: sqlite3.Connection) -> None:
        assert get_meta(conn, "nonexistent", "default") == "default"

    def test_set_overwrites(self, conn: sqlite3.Connection) -> None:
        set_meta(conn, "k", "v1")
        set_meta(conn, "k", "v2")
        assert get_meta(conn, "k") == "v2"
