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

    def test_nodes_kind_is_free_form(self, conn: sqlite3.Connection) -> None:
        """Node ``kind`` is paradigm-agnostic (BDL-038 U1): no DDD-only CHECK.

        An arbitrary FSD kind (``page``) is accepted; conventional vocabularies
        live in the lint preset, not the DB.
        """
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("test-node", "domain", "Test"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("fsd-node", "page", "Home"),
        )
        conn.commit()
        kinds = {
            r["ref_id"]: r["kind"]
            for r in conn.execute("SELECT ref_id, kind FROM nodes")
        }
        assert kinds == {"test-node": "domain", "fsd-node": "page"}

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

    def test_edges_kind_is_free_form(self, conn: sqlite3.Connection) -> None:
        """Edge ``kind`` is paradigm-agnostic (BDL-038 U1): no DDD-only CHECK.

        An arbitrary FSD-style edge kind (``renders``) is accepted; the
        (src,dst,kind,contract_key) identity + FK are still enforced.
        """
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
            ("b", "a", "renders"),
        )
        conn.commit()
        kinds = [r["kind"] for r in conn.execute("SELECT kind FROM edges")]
        assert kinds == ["renders"]

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


class TestTwoPhaseSyncMigration:
    """Tests for doc_hash_at_last_edit column migration (#70)."""

    def test_column_exists_after_fresh_schema(self, tmp_path: Path) -> None:
        """Fresh schema creation should include doc_hash_at_last_edit column."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        columns = {row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()}
        assert "doc_hash_at_last_edit" in columns
        c.close()

    def test_column_exists_after_migration(self, tmp_path: Path) -> None:
        """Existing DB without doc_hash_at_last_edit should gain it via migration."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        # Create a minimal sync_state without the new column.
        c.executescript(
            "CREATE TABLE IF NOT EXISTS nodes ("
            "  ref_id TEXT PRIMARY KEY,"
            "  kind TEXT NOT NULL,"
            "  summary TEXT DEFAULT ''"
            ");"
            "CREATE TABLE IF NOT EXISTS sync_state ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  doc_path TEXT NOT NULL,"
            "  code_path TEXT NOT NULL,"
            "  ref_id TEXT NOT NULL,"
            "  code_hash_at_sync TEXT NOT NULL,"
            "  doc_hash_at_sync TEXT NOT NULL,"
            "  synced_at TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'ok',"
            "  symbols_hash TEXT DEFAULT '',"
            "  UNIQUE(doc_path, code_path)"
            ");"
        )
        # Verify column is NOT there yet.
        columns_before = {
            row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()
        }
        assert "doc_hash_at_last_edit" not in columns_before

        # Run migration.
        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)

        columns_after = {
            row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()
        }
        assert "doc_hash_at_last_edit" in columns_after
        c.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        """Running migration twice should not raise an error."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        # Second call should be safe.
        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)
        columns = {row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()}
        assert "doc_hash_at_last_edit" in columns
        c.close()


class TestReferenceStateMigration:
    """BDL-057.6: ``reference_state`` is created on an old DB via the migration path."""

    def test_table_created_on_old_db(self, tmp_path: Path) -> None:
        """An old DB without ``reference_state`` gains it via ensure_schema_migrations."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        # Minimal pre-BDL-057 schema: a sync_state, no reference_state.
        c.executescript(
            "CREATE TABLE IF NOT EXISTS sync_state ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  doc_path TEXT NOT NULL,"
            "  code_path TEXT NOT NULL,"
            "  ref_id TEXT NOT NULL,"
            "  code_hash_at_sync TEXT NOT NULL,"
            "  doc_hash_at_sync TEXT NOT NULL,"
            "  synced_at TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'ok',"
            "  UNIQUE(doc_path, code_path)"
            ");"
        )
        from beadloom.infrastructure.db import _table_exists, ensure_schema_migrations

        assert not _table_exists(c, "reference_state")

        ensure_schema_migrations(c)

        assert _table_exists(c, "reference_state")
        # Columns match the canonical schema.
        cols = {row[1] for row in c.execute("PRAGMA table_info(reference_state)").fetchall()}
        assert {"doc_path", "watches", "aggregate_hash", "status"} <= cols
        c.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        """Running the migration twice on a DB that already has the table is safe."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        from beadloom.infrastructure.db import _table_exists, ensure_schema_migrations

        ensure_schema_migrations(c)
        ensure_schema_migrations(c)
        assert _table_exists(c, "reference_state")
        c.close()


class TestKindCheckDropMigration:
    """BDL-038 U1: legacy DDD-only ``kind`` CHECK is dropped on existing DBs."""

    def _legacy_db(self, tmp_path: Path) -> sqlite3.Connection:
        """Build a DB with the OLD restrictive ``kind`` CHECK + one DDD row each."""
        c = open_db(tmp_path / "legacy.db")
        c.executescript(
            "CREATE TABLE nodes ("
            "  ref_id TEXT PRIMARY KEY,"
            "  kind TEXT NOT NULL CHECK(kind IN "
            "    ('domain','feature','service','entity','adr')),"
            "  summary TEXT NOT NULL DEFAULT '',"
            "  source TEXT,"
            "  extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active'"
            ");"
            "CREATE TABLE edges ("
            "  src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  kind TEXT NOT NULL CHECK(kind IN "
            "    ('part_of','depends_on','uses','implements',"
            "     'touches_entity','touches_code','produces','consumes')),"
            "  extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active',"
            "  contract_key TEXT NOT NULL DEFAULT '',"
            "  PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)"
            ");"
        )
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES ('a', 'domain', 'A')"
        )
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES ('b', 'service', 'B')"
        )
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('b','a','part_of')"
        )
        c.commit()
        return c

    def test_legacy_check_rejects_fsd_kind_before_migration(
        self, tmp_path: Path
    ) -> None:
        c = self._legacy_db(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary) VALUES ('p','page','P')"
            )
        c.close()

    def test_migration_drops_check_and_preserves_rows(self, tmp_path: Path) -> None:
        from beadloom.infrastructure.db import ensure_schema_migrations

        c = self._legacy_db(tmp_path)
        ensure_schema_migrations(c)
        # Existing DDD rows survive verbatim.
        nodes = {
            r["ref_id"]: r["kind"]
            for r in c.execute("SELECT ref_id, kind FROM nodes")
        }
        assert nodes == {"a": "domain", "b": "service"}
        edges = [r["kind"] for r in c.execute("SELECT kind FROM edges")]
        assert edges == ["part_of"]
        # And FSD kinds are now accepted.
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('p','page','P')")
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('b','a','renders')"
        )
        c.commit()
        c.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        from beadloom.infrastructure.db import ensure_schema_migrations

        c = self._legacy_db(tmp_path)
        ensure_schema_migrations(c)
        ensure_schema_migrations(c)  # second run is a no-op
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('p','page','P')")
        c.commit()
        c.close()

    def test_fresh_schema_has_no_kind_check(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "fresh.db")
        create_schema(c)
        for table in ("nodes", "edges"):
            row = c.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            assert "CHECK(kindIN" not in "".join(str(row[0]).split())
        c.close()

    def test_default_value_is_empty_string(self, tmp_path: Path) -> None:
        """New column should default to empty string for backward compatibility."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES ('N1', 'feature', 'test')"
        )
        c.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at) "
            "VALUES ('d.md', 'c.py', 'N1', 'ch', 'dh', '2026-01-01')"
        )
        c.commit()
        row = c.execute("SELECT doc_hash_at_last_edit FROM sync_state").fetchone()
        assert row[0] == ""
        c.close()


class TestLifecycleExternalMigration:
    """BDL-038 G7/U4: the ``lifecycle`` CHECK is rebuilt to allow ``external``.

    SQLite cannot ALTER a CHECK in place, so the migration rebuilds ``nodes`` /
    ``edges``. The rebuild is additive (rows default ``active``, no loss),
    idempotent, and must NOT resurrect the dropped DDD-only ``kind`` CHECK
    (composes with ``_migrate_drop_kind_checks``).
    """

    def _v3_db(self, tmp_path: Path) -> sqlite3.Connection:
        """A SCHEMA_VERSION-3 DB: no kind CHECK, lifecycle CHECK without external."""
        c = open_db(tmp_path / "v3.db")
        c.executescript(
            "CREATE TABLE nodes ("
            "  ref_id TEXT PRIMARY KEY,"
            "  kind TEXT NOT NULL,"
            "  summary TEXT NOT NULL DEFAULT '',"
            "  source TEXT,"
            "  extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active'"
            "    CHECK(lifecycle IN ('active','planned','deprecated','dead'))"
            ");"
            "CREATE TABLE edges ("
            "  src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  kind TEXT NOT NULL,"
            "  extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active'"
            "    CHECK(lifecycle IN ('active','planned','deprecated','dead')),"
            "  contract_key TEXT NOT NULL DEFAULT '',"
            "  PRIMARY KEY (src_ref_id, dst_ref_id, kind, contract_key)"
            ");"
        )
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('a','domain','A')")
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('b','service','B')")
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('b','a','part_of')"
        )
        c.commit()
        return c

    def test_fresh_schema_lifecycle_allows_external(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "fresh.db")
        create_schema(c)
        for table, ddl in (
            ("nodes", "SELECT sql FROM sqlite_master WHERE name='nodes'"),
            ("edges", "SELECT sql FROM sqlite_master WHERE name='edges'"),
            ("foreign_edges", "SELECT sql FROM sqlite_master WHERE name='foreign_edges'"),
        ):
            sql = "".join(str(c.execute(ddl).fetchone()[0]).split())
            assert "'external'" in sql, f"{table} lifecycle CHECK missing external"
        # And an external row is actually accepted.
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('bridge','module','B','external')"
        )
        c.commit()
        c.close()

    def test_v3_db_legacy_check_rejects_external(self, tmp_path: Path) -> None:
        c = self._v3_db(tmp_path)
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
                "VALUES ('x','module','X','external')"
            )
        c.close()

    def test_migration_adds_external_and_preserves_rows(self, tmp_path: Path) -> None:
        from beadloom.infrastructure.db import ensure_schema_migrations

        c = self._v3_db(tmp_path)
        ensure_schema_migrations(c)
        # No data loss; rows default active.
        nodes = {
            r["ref_id"]: r["lifecycle"]
            for r in c.execute("SELECT ref_id, lifecycle FROM nodes")
        }
        assert nodes == {"a": "active", "b": "active"}
        edges = [r["lifecycle"] for r in c.execute("SELECT lifecycle FROM edges")]
        assert edges == ["active"]
        # external now accepted on both tables.
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('bridge','module','B','external')"
        )
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) "
            "VALUES ('a','bridge','depends_on','external')"
        )
        c.commit()
        c.close()

    def test_migration_keeps_kind_unconstrained(self, tmp_path: Path) -> None:
        """The lifecycle rebuild must NOT resurrect the dropped kind CHECK (BEAD-07)."""
        from beadloom.infrastructure.db import ensure_schema_migrations

        c = self._v3_db(tmp_path)
        ensure_schema_migrations(c)
        for table in ("nodes", "edges"):
            sql = "".join(
                str(
                    c.execute(
                        "SELECT sql FROM sqlite_master WHERE name=?", (table,)
                    ).fetchone()[0]
                ).split()
            )
            assert "CHECK(kindIN" not in sql
        # An arbitrary FSD kind is still accepted post-migration.
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('p','page','P')")
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a','p','renders')"
        )
        c.commit()
        c.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        from beadloom.infrastructure.db import ensure_schema_migrations

        c = self._v3_db(tmp_path)
        ensure_schema_migrations(c)
        ensure_schema_migrations(c)  # second run is a no-op
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary, lifecycle) "
            "VALUES ('bridge','module','B','external')"
        )
        c.commit()
        c.close()

    def test_schema_version_is_4(self) -> None:
        from beadloom.infrastructure.db import SCHEMA_VERSION

        assert SCHEMA_VERSION == "4"


class TestLifecycleColumnMigration:
    """Tests for the additive ``lifecycle`` column on nodes and edges (BEAD-02)."""

    def test_columns_exist_after_fresh_schema(self, tmp_path: Path) -> None:
        """Fresh schema creation should include lifecycle on nodes and edges."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        node_cols = {row[1] for row in c.execute("PRAGMA table_info(nodes)").fetchall()}
        edge_cols = {row[1] for row in c.execute("PRAGMA table_info(edges)").fetchall()}
        assert "lifecycle" in node_cols
        assert "lifecycle" in edge_cols
        c.close()

    def test_columns_added_via_migration(self, tmp_path: Path) -> None:
        """An existing DB without lifecycle columns should gain them via migration."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        # Old-style schema: nodes/edges without a lifecycle column.
        c.executescript(
            "CREATE TABLE IF NOT EXISTS nodes ("
            "  ref_id TEXT PRIMARY KEY,"
            "  kind TEXT NOT NULL,"
            "  summary TEXT NOT NULL DEFAULT '',"
            "  source TEXT,"
            "  extra TEXT DEFAULT '{}'"
            ");"
            "CREATE TABLE IF NOT EXISTS edges ("
            "  src_ref_id TEXT NOT NULL,"
            "  dst_ref_id TEXT NOT NULL,"
            "  kind TEXT NOT NULL,"
            "  extra TEXT DEFAULT '{}',"
            "  PRIMARY KEY (src_ref_id, dst_ref_id, kind)"
            ");"
            "CREATE TABLE IF NOT EXISTS sync_state ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  doc_path TEXT NOT NULL,"
            "  code_path TEXT NOT NULL,"
            "  ref_id TEXT NOT NULL,"
            "  code_hash_at_sync TEXT NOT NULL,"
            "  doc_hash_at_sync TEXT NOT NULL,"
            "  synced_at TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'ok',"
            "  UNIQUE(doc_path, code_path)"
            ");"
        )
        assert "lifecycle" not in {
            row[1] for row in c.execute("PRAGMA table_info(nodes)").fetchall()
        }

        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)

        assert "lifecycle" in {
            row[1] for row in c.execute("PRAGMA table_info(nodes)").fetchall()
        }
        assert "lifecycle" in {
            row[1] for row in c.execute("PRAGMA table_info(edges)").fetchall()
        }
        c.close()

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        """Running the migration twice must not raise (additive, idempotent)."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)
        assert "lifecycle" in {
            row[1] for row in c.execute("PRAGMA table_info(nodes)").fetchall()
        }
        c.close()

    def test_default_lifecycle_is_active(self, tmp_path: Path) -> None:
        """Rows inserted without an explicit lifecycle default to 'active'."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('N1', 'feature', 't')")
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('N2', 'feature', 't')")
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('N1', 'N2', 'depends_on')"
        )
        c.commit()
        node_row = c.execute("SELECT lifecycle FROM nodes WHERE ref_id = 'N1'").fetchone()
        edge_row = c.execute("SELECT lifecycle FROM edges").fetchone()
        assert node_row[0] == "active"
        assert edge_row[0] == "active"
        c.close()


class TestContractEdgeKinds:
    """Edge ``kind`` CHECK accepts contract kinds produces/consumes (#101)."""

    def _two_nodes(self, c: sqlite3.Connection) -> None:
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('a', 'service', 'A')")
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('b', 'feature', 'B')")
        c.commit()

    def test_produces_kind_accepted(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a', 'b', 'produces')"
        )
        c.commit()
        row = c.execute("SELECT kind FROM edges").fetchone()
        assert row[0] == "produces"
        c.close()

    def test_consumes_kind_accepted(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a', 'b', 'consumes')"
        )
        c.commit()
        row = c.execute("SELECT kind FROM edges").fetchone()
        assert row[0] == "consumes"
        c.close()

    def test_arbitrary_kind_accepted(self, tmp_path: Path) -> None:
        """Edge ``kind`` is free-form (BDL-038 U1): a non-preset kind is kept."""
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a', 'b', 'renders')"
        )
        c.commit()
        row = c.execute("SELECT kind FROM edges").fetchone()
        assert row[0] == "renders"
        c.close()

    def test_old_db_migrates_to_allow_produces(self, tmp_path: Path) -> None:
        """An existing DB with the old kind CHECK gains produces/consumes."""
        c = open_db(tmp_path / "t.db")
        c.executescript(
            "CREATE TABLE nodes ("
            "  ref_id TEXT PRIMARY KEY, kind TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',"
            "  source TEXT, extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active'"
            ");"
            "CREATE TABLE edges ("
            "  src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,"
            "  kind TEXT NOT NULL CHECK(kind IN "
            "    ('part_of','depends_on','uses','implements','touches_entity','touches_code')),"
            "  extra TEXT DEFAULT '{}',"
            "  lifecycle TEXT NOT NULL DEFAULT 'active',"
            "  PRIMARY KEY (src_ref_id, dst_ref_id, kind)"
            ");"
        )
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('a', 'service', 'A')")
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('b', 'feature', 'B')")
        c.execute("INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a', 'b', 'uses')")
        c.commit()

        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)

        # Pre-existing rows preserved.
        assert c.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 1
        # produces now accepted.
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('a', 'b', 'produces')"
        )
        c.commit()
        kinds = {r[0] for r in c.execute("SELECT kind FROM edges").fetchall()}
        assert kinds == {"uses", "produces"}
        c.close()


class TestContractEdgeDiscriminator:
    """Multiple contracts on one (src,dst,kind) survive (#102)."""

    def _two_nodes(self, c: sqlite3.Connection) -> None:
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('p', 'service', 'P')")
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('q', 'feature', 'Q')")
        c.commit()

    def test_contract_key_column_exists(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        cols = {row[1] for row in c.execute("PRAGMA table_info(edges)").fetchall()}
        assert "contract_key" in cols
        c.close()

    def test_two_contracts_same_pair_both_survive(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
            "VALUES ('p', 'q', 'produces', 'msg-a')"
        )
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
            "VALUES ('p', 'q', 'produces', 'msg-b')"
        )
        c.commit()
        assert c.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 2
        c.close()

    def test_duplicate_full_key_still_rejected(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
            "VALUES ('p', 'q', 'produces', 'msg-a')"
        )
        c.commit()
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
                "VALUES ('p', 'q', 'produces', 'msg-a')"
            )
        c.close()

    def test_contract_key_defaults_empty(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        self._two_nodes(c)
        c.execute("INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES ('p', 'q', 'uses')")
        c.commit()
        row = c.execute("SELECT contract_key FROM edges").fetchone()
        assert row[0] == ""
        c.close()


class TestForeignEdgesTable:
    """The ``foreign_edges`` table persists cross-repo @repo: edges (#100)."""

    def test_table_exists(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        names = {
            row[0]
            for row in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "foreign_edges" in names
        c.close()

    def test_accepts_foreign_dst(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        create_schema(c)
        c.execute("INSERT INTO nodes (ref_id, kind, summary) VALUES ('local', 'service', 'L')")
        c.commit()
        c.execute(
            "INSERT INTO foreign_edges (src_ref_id, dst_ref_id, kind, extra, lifecycle) "
            "VALUES ('local', '@other:x', 'depends_on', '{}', 'active')"
        )
        c.commit()
        row = c.execute("SELECT dst_ref_id FROM foreign_edges").fetchone()
        assert row[0] == "@other:x"
        c.close()

    def test_old_db_gains_foreign_edges_via_migration(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "t.db")
        c.executescript(
            "CREATE TABLE nodes (ref_id TEXT PRIMARY KEY, kind TEXT NOT NULL,"
            "  summary TEXT NOT NULL DEFAULT '');"
        )
        from beadloom.infrastructure.db import ensure_schema_migrations

        ensure_schema_migrations(c)
        names = {
            row[0]
            for row in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "foreign_edges" in names
        c.close()
