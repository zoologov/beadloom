"""Tests for doctor drift detection checks (BEAD-09)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doctor import (
    Severity,
    _check_stale_sync,
    _check_symbol_drift,
    run_checks,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


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
    status: str = "ok",
) -> None:
    """Insert a sync_state row with optional symbols_hash."""
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status, symbols_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, code_hash, doc_hash, "2025-01-01", status, symbols_hash),
    )
    conn.commit()


class TestCheckSymbolDrift:
    """Tests for _check_symbol_drift."""

    def test_ok_when_no_sync_state(self, conn: sqlite3.Connection) -> None:
        """Returns OK when sync_state is empty."""
        checks = _check_symbol_drift(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK
        assert checks[0].name == "symbol_drift"

    def test_ok_when_symbols_unchanged(self, conn: sqlite3.Connection) -> None:
        """Returns OK when symbols hash matches stored hash."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        _insert_node(conn)
        _insert_symbol(conn, symbol_name="handler", kind="function", ref_id="F1")
        _insert_doc(conn)

        # Store the current symbols hash.
        current_hash = _compute_symbols_hash(conn, "F1")
        _insert_sync_state(conn, symbols_hash=current_hash)

        checks = _check_symbol_drift(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK
        assert "No symbol drift" in checks[0].description

    def test_warning_when_symbols_changed(self, conn: sqlite3.Connection) -> None:
        """Returns WARNING when current symbols hash differs from stored."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        _insert_node(conn)
        _insert_symbol(conn, symbol_name="handler", kind="function", ref_id="F1")
        _insert_doc(conn)

        # Store the initial symbols hash.
        initial_hash = _compute_symbols_hash(conn, "F1")
        _insert_sync_state(conn, symbols_hash=initial_hash)

        # Now add a new symbol — hash will change.
        _insert_symbol(
            conn,
            file_path="src/utils.py",
            symbol_name="new_helper",
            kind="function",
            ref_id="F1",
            file_hash="newhash",
        )

        checks = _check_symbol_drift(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.WARNING
        assert "F1" in checks[0].description
        assert "spec.md" in checks[0].description

    def test_ok_when_sync_entries_have_empty_symbols_hash(self, conn: sqlite3.Connection) -> None:
        """Returns OK when sync entries exist but symbols_hash is empty."""
        _insert_node(conn)
        _insert_doc(conn)
        _insert_sync_state(conn, symbols_hash="")

        checks = _check_symbol_drift(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK

    def test_multiple_drifted_nodes(self, conn: sqlite3.Connection) -> None:
        """Returns multiple warnings for multiple drifted nodes."""
        from beadloom.doc_sync.engine import _compute_symbols_hash

        for ref_id in ("F1", "F2"):
            _insert_node(conn, ref_id=ref_id)
            _insert_symbol(
                conn,
                file_path=f"src/{ref_id.lower()}.py",
                symbol_name=f"func_{ref_id.lower()}",
                kind="function",
                ref_id=ref_id,
            )
            _insert_doc(conn, path=f"{ref_id.lower()}.md", ref_id=ref_id)

            stored_hash = _compute_symbols_hash(conn, ref_id)
            _insert_sync_state(
                conn,
                doc_path=f"{ref_id.lower()}.md",
                code_path=f"src/{ref_id.lower()}.py",
                ref_id=ref_id,
                symbols_hash=stored_hash,
            )

        # Add new symbols for both — causing drift.
        for ref_id in ("F1", "F2"):
            _insert_symbol(
                conn,
                file_path=f"src/{ref_id.lower()}_extra.py",
                symbol_name=f"extra_{ref_id.lower()}",
                kind="function",
                ref_id=ref_id,
                file_hash="extra",
            )

        checks = _check_symbol_drift(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        assert len(warnings) == 2
        descs = " ".join(c.description for c in warnings)
        assert "F1" in descs
        assert "F2" in descs

    def test_graceful_when_symbols_hash_column_missing(self, tmp_path: Path) -> None:
        """Returns OK gracefully when symbols_hash column is missing (old DB)."""
        import sqlite3

        db_path = tmp_path / "old.db"
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row

        # Create a minimal sync_state without symbols_hash column.
        c.executescript("""
            CREATE TABLE nodes (
                ref_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('domain','feature','service','entity','adr')),
                summary TEXT NOT NULL DEFAULT '',
                source TEXT,
                extra TEXT DEFAULT '{}'
            );
            CREATE TABLE sync_state (
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

        checks = _check_symbol_drift(c)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK
        assert "skipping" in checks[0].description.lower()
        c.close()


class TestCheckStaleSync:
    """Tests for _check_stale_sync."""

    def test_ok_when_no_stale_entries(self, conn: sqlite3.Connection) -> None:
        """Returns OK when no sync entries are stale."""
        checks = _check_stale_sync(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK
        assert checks[0].name == "stale_sync"

    def test_ok_when_all_entries_ok(self, conn: sqlite3.Connection) -> None:
        """Returns OK when all sync entries have status 'ok'."""
        _insert_node(conn)
        _insert_doc(conn)
        _insert_sync_state(conn, status="ok")

        checks = _check_stale_sync(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.OK

    def test_warning_for_stale_entries(self, conn: sqlite3.Connection) -> None:
        """Returns WARNING for each stale sync entry."""
        _insert_node(conn)
        _insert_doc(conn)
        _insert_sync_state(conn, status="stale")

        checks = _check_stale_sync(conn)
        assert len(checks) == 1
        assert checks[0].severity == Severity.WARNING
        assert "F1" in checks[0].description
        assert "spec.md" in checks[0].description
        assert "src/api.py" in checks[0].description

    def test_multiple_stale_entries(self, conn: sqlite3.Connection) -> None:
        """Returns one WARNING per stale entry."""
        for ref_id in ("F1", "F2"):
            _insert_node(conn, ref_id=ref_id)
            _insert_doc(conn, path=f"{ref_id.lower()}.md", ref_id=ref_id)
            _insert_sync_state(
                conn,
                doc_path=f"{ref_id.lower()}.md",
                code_path=f"src/{ref_id.lower()}.py",
                ref_id=ref_id,
                status="stale",
            )

        checks = _check_stale_sync(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        assert len(warnings) == 2


class TestRunChecksIncludesDriftChecks:
    """Integration: run_checks includes both drift checks."""

    def test_run_checks_includes_symbol_drift_and_stale_sync(
        self, conn: sqlite3.Connection
    ) -> None:
        """run_checks output includes symbol_drift and stale_sync check names."""
        checks = run_checks(conn)
        names = {c.name for c in checks}
        assert "symbol_drift" in names
        assert "stale_sync" in names

    def test_run_checks_drift_warning_surfaces(self, conn: sqlite3.Connection) -> None:
        """Drift warnings from new checks appear in run_checks output."""
        _insert_node(conn)
        _insert_doc(conn)
        _insert_sync_state(conn, status="stale")

        checks = run_checks(conn)
        stale_warnings = [
            c for c in checks if c.name == "stale_sync" and c.severity == Severity.WARNING
        ]
        assert len(stale_warnings) >= 1
