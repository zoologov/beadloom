"""Tests for symbol-level drift detection (BEAD-08)."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

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


def _insert_node(conn: sqlite3.Connection, ref_id: str = "F1") -> None:
    """Insert a graph node."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        (ref_id, "feature", f"Feature {ref_id}"),
    )
    conn.commit()


def _insert_symbol(
    conn: sqlite3.Connection,
    *,
    file_path: str = "src/api.py",
    symbol_name: str = "handler",
    kind: str = "function",
    ref_id: str = "F1",
    file_hash: str = "abc123",
) -> None:
    """Insert a code symbol annotated with a ref_id."""
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            file_path,
            symbol_name,
            kind,
            1,
            10,
            json.dumps({"domain": ref_id}),
            file_hash,
        ),
    )
    conn.commit()


def _insert_doc(
    conn: sqlite3.Connection,
    *,
    path: str = "spec.md",
    ref_id: str = "F1",
    doc_hash: str = "dochash1",
) -> None:
    """Insert a doc linked to a ref_id."""
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, "feature", ref_id, doc_hash),
    )
    conn.commit()


def _insert_sync_state(
    conn: sqlite3.Connection,
    *,
    doc_path: str = "spec.md",
    code_path: str = "src/api.py",
    ref_id: str = "F1",
    code_hash: str = "codehash1",
    doc_hash: str = "dochash1",
    symbols_hash: str = "",
) -> None:
    """Insert a sync_state row with optional symbols_hash."""
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status, symbols_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, code_hash, doc_hash, "2025-01-01", "ok", symbols_hash),
    )
    conn.commit()


class TestComputeSymbolsHash:
    """Tests for _compute_symbols_hash."""

    def test_consistent_hash_same_symbols(self, conn: sqlite3.Connection) -> None:
        """Same symbols produce the same hash."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        _insert_node(conn)
        _insert_symbol(conn, symbol_name="handler", kind="function", ref_id="F1")

        hash1 = _compute_symbols_hash(conn, "F1")
        hash2 = _compute_symbols_hash(conn, "F1")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_different_hash_when_symbols_change(self, conn: sqlite3.Connection) -> None:
        """Adding a symbol changes the hash."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        _insert_node(conn)
        _insert_symbol(conn, symbol_name="handler", kind="function", ref_id="F1")

        hash_before = _compute_symbols_hash(conn, "F1")

        # Add another symbol for the same ref_id.
        _insert_symbol(
            conn,
            file_path="src/utils.py",
            symbol_name="helper",
            kind="function",
            ref_id="F1",
        )

        hash_after = _compute_symbols_hash(conn, "F1")
        assert hash_before != hash_after

    def test_empty_string_for_unknown_ref_id(self, conn: sqlite3.Connection) -> None:
        """Unknown ref_id returns empty string."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        result = _compute_symbols_hash(conn, "NONEXISTENT")
        assert result == ""

    def test_hash_changes_when_symbol_kind_changes(self, conn: sqlite3.Connection) -> None:
        """Hash changes when symbol kind changes (e.g. function -> class)."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        _insert_node(conn)
        _insert_symbol(conn, symbol_name="Handler", kind="function", ref_id="F1")
        hash_function = _compute_symbols_hash(conn, "F1")

        # Delete the old symbol and insert with different kind.
        conn.execute("DELETE FROM code_symbols")
        conn.commit()
        _insert_symbol(conn, symbol_name="Handler", kind="class", ref_id="F1")
        hash_class = _compute_symbols_hash(conn, "F1")

        assert hash_function != hash_class


class TestCheckSyncSymbolDrift:
    """Tests for symbol drift detection in check_sync."""

    def test_detects_symbol_drift(self, conn: sqlite3.Connection, project: Path) -> None:
        """check_sync detects stale when symbols changed but doc/code hashes same."""
        from beadloom.doc_sync.engine import _compute_symbols_hash, check_sync

        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"

        (project / "docs" / "spec.md").write_text(doc_content)
        (project / "src" / "api.py").write_text(code_content)

        _insert_node(conn)
        _insert_doc(conn, doc_hash=_file_hash(doc_content))
        _insert_symbol(conn, ref_id="F1", file_hash=_file_hash(code_content))

        # Compute initial symbols hash.
        initial_symbols_hash = _compute_symbols_hash(conn, "F1")
        assert initial_symbols_hash != ""

        # Insert sync_state with current file hashes and the initial symbols hash.
        _insert_sync_state(
            conn,
            code_hash=_file_hash(code_content),
            doc_hash=_file_hash(doc_content),
            symbols_hash=initial_symbols_hash,
        )

        # Now add a new symbol (simulating code change that added a new function).
        _insert_symbol(
            conn,
            file_path="src/utils.py",
            symbol_name="new_helper",
            kind="function",
            ref_id="F1",
            file_hash="newhash",
        )

        # File hashes on disk haven't changed, but symbols have.
        results = check_sync(conn, project_root=project)
        assert len(results) == 1
        assert results[0]["status"] == "stale"

    def test_ok_when_symbols_unchanged(self, conn: sqlite3.Connection, project: Path) -> None:
        """check_sync reports OK when symbols haven't changed."""
        from beadloom.doc_sync.engine import _compute_symbols_hash, check_sync

        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"

        (project / "docs" / "spec.md").write_text(doc_content)
        (project / "src" / "api.py").write_text(code_content)

        _insert_node(conn)
        _insert_doc(conn, doc_hash=_file_hash(doc_content))
        _insert_symbol(conn, ref_id="F1", file_hash=_file_hash(code_content))

        initial_symbols_hash = _compute_symbols_hash(conn, "F1")
        _insert_sync_state(
            conn,
            code_hash=_file_hash(code_content),
            doc_hash=_file_hash(doc_content),
            symbols_hash=initial_symbols_hash,
        )

        results = check_sync(conn, project_root=project)
        assert len(results) == 1
        assert results[0]["status"] == "ok"


class TestBuildInitialSyncStateSymbolsHash:
    """Test that _build_initial_sync_state stores symbols_hash."""

    def test_symbols_hash_stored(self, conn: sqlite3.Connection) -> None:
        """_build_initial_sync_state should populate symbols_hash."""
        from beadloom.doc_sync.engine import _compute_symbols_hash
        from beadloom.infrastructure.reindex import _build_initial_sync_state

        _insert_node(conn)
        _insert_doc(conn, doc_hash="dochash1")
        _insert_symbol(conn, ref_id="F1", file_hash="codehash1")

        _build_initial_sync_state(conn)

        row = conn.execute("SELECT symbols_hash FROM sync_state").fetchone()
        assert row is not None
        stored = row["symbols_hash"]
        expected = _compute_symbols_hash(conn, "F1")
        assert stored == expected
        assert stored != ""

    def test_preserved_symbols_hash(self, conn: sqlite3.Connection) -> None:
        """When preserved_symbols is provided, old hash is kept."""
        from beadloom.doc_sync.engine import _compute_symbols_hash
        from beadloom.infrastructure.reindex import _build_initial_sync_state

        _insert_node(conn)
        _insert_doc(conn, doc_hash="dochash1")
        _insert_symbol(conn, ref_id="F1", file_hash="codehash1")

        # Build initial state (baseline).
        _build_initial_sync_state(conn)
        baseline_hash = conn.execute("SELECT symbols_hash FROM sync_state").fetchone()[
            "symbols_hash"
        ]

        # Add a new symbol — changes the computed hash.
        _insert_symbol(
            conn,
            file_path="src/utils.py",
            symbol_name="new_helper",
            kind="function",
            ref_id="F1",
            file_hash="newhash",
        )
        new_computed = _compute_symbols_hash(conn, "F1")
        assert new_computed != baseline_hash

        # Rebuild sync_state with preserved hash.
        conn.execute("DELETE FROM sync_state")
        _build_initial_sync_state(conn, preserved_symbols={"F1": baseline_hash})

        stored = conn.execute("SELECT symbols_hash FROM sync_state").fetchone()["symbols_hash"]
        assert stored == baseline_hash  # Old hash preserved, not recomputed


class TestIncrementalReindexPreservesSymbolDrift:
    """E2E: incremental reindex preserves old symbols_hash for drift detection."""

    def test_incremental_reindex_detects_symbol_drift(self, project: Path) -> None:
        """After adding a function and reindexing, sync-check should detect stale."""
        import yaml

        from beadloom.doc_sync.engine import check_sync
        from beadloom.infrastructure.db import open_db
        from beadloom.infrastructure.reindex import incremental_reindex
        from beadloom.infrastructure.reindex import reindex as full_reindex

        # Set up minimal project structure.
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "config.yml").write_text("scan_paths: [src]\n")

        # Graph with one feature node linked to a doc.
        graph_data = {
            "nodes": [
                {
                    "ref_id": "F1",
                    "kind": "feature",
                    "summary": "Test feature",
                    "source": "src/",
                    "docs": ["docs/spec.md"],
                }
            ],
            "edges": [],
        }
        (graph_dir / "services.yml").write_text(yaml.dump(graph_data))

        # Doc file.
        (project / "docs").mkdir(exist_ok=True)
        (project / "docs" / "spec.md").write_text("# F1 Spec\nInitial content for api module.\n")

        # Code file with one function.
        (project / "src").mkdir(exist_ok=True)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    pass\n"
        )

        # Step 1: Full reindex — establishes baseline.
        full_reindex(project)

        # Verify baseline is ok.
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)
        assert all(r["status"] == "ok" for r in results)

        baseline_hash = conn.execute(
            "SELECT symbols_hash FROM sync_state WHERE ref_id = 'F1'"
        ).fetchone()["symbols_hash"]
        assert baseline_hash != ""
        conn.close()

        # Step 2: Add a new function to the code file.
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    pass\n\n"
            "# beadloom:feature=F1\ndef new_helper():\n    return 42\n"
        )

        # Step 3: Incremental reindex — should preserve old symbols_hash.
        incremental_reindex(project)

        # Step 4: check_sync should detect symbol drift.
        conn = open_db(db_path)
        results = check_sync(conn, project_root=project)
        stale = [r for r in results if r["status"] == "stale"]
        assert len(stale) > 0, "Expected stale status due to symbol drift"
        assert stale[0]["ref_id"] == "F1"
        conn.close()

    def test_mark_synced_resets_symbol_baseline(self, project: Path) -> None:
        """After mark_synced_by_ref, symbol drift is no longer detected."""
        import yaml

        from beadloom.doc_sync.engine import check_sync, mark_synced_by_ref
        from beadloom.infrastructure.db import open_db
        from beadloom.infrastructure.reindex import incremental_reindex
        from beadloom.infrastructure.reindex import reindex as full_reindex

        # Set up project.
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "config.yml").write_text("scan_paths: [src]\n")

        graph_data = {
            "nodes": [
                {
                    "ref_id": "F1",
                    "kind": "feature",
                    "summary": "Test feature",
                    "source": "src/",
                    "docs": ["docs/spec.md"],
                }
            ],
            "edges": [],
        }
        (graph_dir / "services.yml").write_text(yaml.dump(graph_data))
        (project / "docs").mkdir(exist_ok=True)
        (project / "docs" / "spec.md").write_text("# F1 Spec\nContent about the api module.\n")
        (project / "src").mkdir(exist_ok=True)
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    pass\n"
        )

        # Full reindex baseline.
        full_reindex(project)

        # Add new function and incremental reindex.
        (project / "src" / "api.py").write_text(
            "# beadloom:feature=F1\ndef handler():\n    pass\n\n"
            "# beadloom:feature=F1\ndef new_helper():\n    return 42\n"
        )
        incremental_reindex(project)

        # Now mark as synced (user updated the doc).
        (project / "docs" / "spec.md").write_text(
            "# F1 Spec\nUpdated api: now includes new_helper.\n"
        )
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        mark_synced_by_ref(conn, "F1", project)

        # After marking synced, sync-check should be ok.
        results = check_sync(conn, project_root=project)
        assert all(r["status"] == "ok" for r in results)
        conn.close()


class TestMarkSyncedUpdatesSymbolsHash:
    """Test that mark_synced and mark_synced_by_ref update symbols_hash."""

    def test_mark_synced_updates_symbols_hash(
        self,
        conn: sqlite3.Connection,
        project: Path,
    ) -> None:
        """mark_synced should update symbols_hash to current value."""
        from beadloom.doc_sync.engine import _compute_symbols_hash, mark_synced

        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"

        (project / "docs" / "spec.md").write_text(doc_content)
        (project / "src" / "api.py").write_text(code_content)

        _insert_node(conn)
        _insert_doc(conn, doc_hash=_file_hash(doc_content))
        _insert_symbol(conn, ref_id="F1", file_hash=_file_hash(code_content))

        # Set up sync_state with old symbols_hash.
        _insert_sync_state(
            conn,
            code_hash=_file_hash(code_content),
            doc_hash=_file_hash(doc_content),
            symbols_hash="old_hash_placeholder",
        )

        # Mark synced — should update symbols_hash.
        mark_synced(conn, "spec.md", "src/api.py", project)

        row = conn.execute("SELECT symbols_hash FROM sync_state").fetchone()
        expected = _compute_symbols_hash(conn, "F1")
        assert row["symbols_hash"] == expected
        assert row["symbols_hash"] != "old_hash_placeholder"

    def test_mark_synced_by_ref_updates_symbols_hash(
        self,
        conn: sqlite3.Connection,
        project: Path,
    ) -> None:
        """mark_synced_by_ref should update symbols_hash to current value."""
        from beadloom.doc_sync.engine import _compute_symbols_hash, mark_synced_by_ref

        doc_content = "# Spec\nFeature spec.\n"
        code_content = "# beadloom:feature=F1\ndef handler():\n    pass\n"

        (project / "docs" / "spec.md").write_text(doc_content)
        (project / "src" / "api.py").write_text(code_content)

        _insert_node(conn)
        _insert_doc(conn, doc_hash=_file_hash(doc_content))
        _insert_symbol(conn, ref_id="F1", file_hash=_file_hash(code_content))

        _insert_sync_state(
            conn,
            code_hash=_file_hash(code_content),
            doc_hash=_file_hash(doc_content),
            symbols_hash="old_hash_placeholder",
        )

        count = mark_synced_by_ref(conn, "F1", project)
        assert count == 1

        row = conn.execute("SELECT symbols_hash FROM sync_state").fetchone()
        expected = _compute_symbols_hash(conn, "F1")
        assert row["symbols_hash"] == expected


class TestEnsureSchemaMigrations:
    """Test ensure_schema_migrations adds column if missing."""

    def test_adds_column_if_missing(self, project: Path) -> None:
        """ensure_schema_migrations should add symbols_hash column."""
        from beadloom.infrastructure.db import ensure_schema_migrations, open_db

        db_path = project / ".beadloom" / "migration_test.db"
        c = open_db(db_path)

        # Create a sync_state table WITHOUT symbols_hash (simulating old schema).
        c.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                ref_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('domain','feature','service','entity','adr')),
                summary TEXT NOT NULL DEFAULT '',
                source TEXT,
                extra TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_path TEXT NOT NULL,
                code_path TEXT NOT NULL,
                ref_id TEXT NOT NULL REFERENCES nodes(ref_id),
                code_hash_at_sync TEXT NOT NULL,
                doc_hash_at_sync TEXT NOT NULL,
                synced_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ok' CHECK(status IN ('ok','stale')),
                UNIQUE(doc_path, code_path)
            );
        """)

        # Verify column does not exist.
        columns = {row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()}
        assert "symbols_hash" not in columns

        # Run migration.
        ensure_schema_migrations(c)

        # Verify column now exists.
        columns = {row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()}
        assert "symbols_hash" in columns

        c.close()

    def test_idempotent(self, project: Path) -> None:
        """Running ensure_schema_migrations twice should not error."""
        from beadloom.infrastructure.db import ensure_schema_migrations, open_db

        db_path = project / ".beadloom" / "idempotent_test.db"
        c = open_db(db_path)
        create_schema(c)

        # Already has the column from create_schema.
        ensure_schema_migrations(c)
        ensure_schema_migrations(c)  # Second call should be harmless.

        columns = {row[1] for row in c.execute("PRAGMA table_info(sync_state)").fetchall()}
        assert "symbols_hash" in columns
        c.close()
