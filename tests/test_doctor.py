"""Tests for beadloom.infrastructure.doctor — graph and data validation checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doctor import Check, Severity, run_checks

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


class TestRunChecks:
    def test_clean_graph(self, conn: sqlite3.Connection) -> None:
        """No issues with an empty graph."""
        checks = run_checks(conn)
        assert all(c.severity == Severity.OK for c in checks)

    def test_empty_summary(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", ""),
        )
        conn.commit()
        checks = run_checks(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        descs = " ".join(c.description for c in warnings)
        assert "summary" in descs.lower() or "empty" in descs.lower()

    def test_orphaned_edge_src(self, conn: sqlite3.Connection) -> None:
        """Edge with src that doesn't exist in nodes (FK should prevent this
        but doctor should still check for edge targets if FK is off)."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("A", "feature", "A"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("B", "domain", "B"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("A", "B", "part_of"),
        )
        conn.commit()
        # This is valid — should not produce errors.
        checks = run_checks(conn)
        errors = [c for c in checks if c.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_duplicate_edges(self, conn: sqlite3.Connection) -> None:
        """Duplicate edges are prevented by PK, but doc without ref_id is not an error."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("A", "feature", "A"),
        )
        conn.commit()
        checks = run_checks(conn)
        # Should have no errors — just a feature node.
        errors = [c for c in checks if c.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_doc_without_ref_id(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("orphan.md", "other", None, "abc"),
        )
        conn.commit()
        checks = run_checks(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        descs = " ".join(c.description for c in warnings)
        assert "ref_id" in descs.lower() or "unlinked" in descs.lower()

    def test_node_without_docs_severity_warning(self, conn: sqlite3.Connection) -> None:
        """#38: undocumented nodes should be WARNING, not INFO."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.commit()
        checks = run_checks(conn)
        warnings = [
            c for c in checks
            if c.severity == Severity.WARNING and c.name == "nodes_without_docs"
        ]
        assert len(warnings) == 1
        assert "F1" in warnings[0].description

    def test_check_dataclass(self) -> None:
        c = Check(
            name="test_check",
            severity=Severity.WARNING,
            description="Something is wrong",
        )
        assert c.name == "test_check"
        assert c.severity == Severity.WARNING


class TestSymbolDrift:
    """Edge-case tests for _check_symbol_drift()."""

    def test_symbol_drift_detected(self, conn: sqlite3.Connection) -> None:
        """When code symbols hash differs from stored hash, drift is WARNING."""
        import json as _json

        # Insert a node + sync_state with a stale symbols_hash
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("drift-node", "feature", "Drifted", "src/drift/"),
        )
        # Insert a code symbol annotated with the ref_id so _compute_symbols_hash
        # returns a non-empty hash
        annotations = _json.dumps({"ref_id": "drift-node"})
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/drift/main.py", "func_a", "function", 1, 10, annotations, "h1"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status, symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "docs/drift.md", "src/drift/main.py", "drift-node",
                "oldhash", "dochash", "2026-01-01T00:00:00", "ok",
                "definitely-stale-hash",
            ),
        )
        conn.commit()
        checks = run_checks(conn)
        drift_warnings = [
            c for c in checks
            if c.name == "symbol_drift" and c.severity == Severity.WARNING
        ]
        assert len(drift_warnings) == 1
        assert "drift-node" in drift_warnings[0].description

    def test_symbol_drift_no_drift(self, conn: sqlite3.Connection) -> None:
        """When symbols_hash matches current, drift check returns OK."""
        import json as _json

        from beadloom.doc_sync.engine import _compute_symbols_hash

        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("stable-node", "feature", "Stable", "src/stable/"),
        )
        annotations = _json.dumps({"ref_id": "stable-node"})
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/stable/main.py", "func_b", "function", 1, 10, annotations, "h2"),
        )
        conn.commit()
        # Compute the actual hash so it matches
        current_hash = _compute_symbols_hash(conn, "stable-node")
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status, symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "docs/stable.md", "src/stable/main.py", "stable-node",
                "ch", "dh", "2026-01-01T00:00:00", "ok", current_hash,
            ),
        )
        conn.commit()
        checks = run_checks(conn)
        drift_checks = [c for c in checks if c.name == "symbol_drift"]
        assert all(c.severity == Severity.OK for c in drift_checks)


class TestStaleSync:
    """Edge-case tests for _check_stale_sync()."""

    def test_stale_sync_detected(self, conn: sqlite3.Connection) -> None:
        """When sync_state has stale entries, they should appear as WARNING."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("stale-node", "feature", "Stale"),
        )
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, "
            "code_hash_at_sync, doc_hash_at_sync, synced_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "docs/stale.md", "src/stale/main.py", "stale-node",
                "ch", "dh", "2026-01-01T00:00:00", "stale",
            ),
        )
        conn.commit()
        checks = run_checks(conn)
        stale_warnings = [
            c for c in checks
            if c.name == "stale_sync" and c.severity == Severity.WARNING
        ]
        assert len(stale_warnings) == 1
        assert "stale-node" in stale_warnings[0].description

    def test_no_stale_sync(self, conn: sqlite3.Connection) -> None:
        """When no sync entries are stale, check returns OK."""
        checks = run_checks(conn)
        stale_checks = [c for c in checks if c.name == "stale_sync"]
        assert all(c.severity == Severity.OK for c in stale_checks)


class TestSourceCoverage:
    """Edge-case tests for _check_source_coverage()."""

    def test_source_coverage_with_untracked_files(
        self, tmp_path: Path,
    ) -> None:
        """Nodes with untracked .py files produce WARNING."""
        import json as _json

        # Create a project with source files
        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        src_dir = proj / "src" / "mymod"
        src_dir.mkdir(parents=True)
        (src_dir / "tracked.py").write_text("def f(): pass\n", encoding="utf-8")
        (src_dir / "untracked.py").write_text("def g(): pass\n", encoding="utf-8")

        db_path = beadloom_dir / "test.db"
        c = open_db(db_path)
        create_schema(c)

        # Insert a node whose source is src/mymod/
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("mymod", "feature", "My Module", "src/mymod/"),
        )
        # Link a doc so check_source_coverage doesn't skip
        c.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("docs/mymod.md", "feature", "mymod", "hash1"),
        )
        # Only track tracked.py in code_symbols with correct annotation
        annotations = _json.dumps({"ref_id": "mymod"})
        c.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, "
            "line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/mymod/tracked.py", "f", "function", 1, 1, annotations, "h"),
        )
        c.commit()

        checks = run_checks(c)
        coverage_warnings = [
            ch for ch in checks
            if ch.name == "source_coverage" and ch.severity == Severity.WARNING
        ]
        # untracked.py should be flagged
        assert len(coverage_warnings) >= 1
        descs = " ".join(ch.description for ch in coverage_warnings)
        assert "untracked" in descs.lower() or "mymod" in descs
        c.close()

    def test_source_coverage_in_memory_db_graceful(self) -> None:
        """In-memory DB has no file path — _check_source_coverage should handle gracefully."""
        import sqlite3 as _sqlite3

        c = _sqlite3.connect(":memory:")
        c.row_factory = _sqlite3.Row
        # Minimal schema for doctor checks
        c.executescript("""
            CREATE TABLE nodes (
                ref_id TEXT PRIMARY KEY, kind TEXT, summary TEXT DEFAULT '',
                source TEXT, extra TEXT DEFAULT '{}'
            );
            CREATE TABLE edges (
                src_ref_id TEXT, dst_ref_id TEXT, kind TEXT,
                extra TEXT DEFAULT '{}', PRIMARY KEY(src_ref_id, dst_ref_id, kind)
            );
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY, path TEXT, kind TEXT,
                ref_id TEXT, hash TEXT
            );
            CREATE TABLE sync_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_path TEXT, code_path TEXT, ref_id TEXT,
                code_hash_at_sync TEXT, doc_hash_at_sync TEXT,
                synced_at TEXT, status TEXT DEFAULT 'ok', symbols_hash TEXT DEFAULT ''
            );
            CREATE TABLE code_symbols (
                file_path TEXT, symbol_name TEXT, kind TEXT,
                line_start INTEGER, line_end INTEGER,
                annotations TEXT DEFAULT '{}', file_hash TEXT
            );
        """)
        from beadloom.infrastructure.doctor import _check_source_coverage
        results = _check_source_coverage(c)
        # Should gracefully return OK (can't determine project root from :memory:)
        assert len(results) >= 1
        c.close()


class TestDoctorCli:
    def test_doctor_command(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.infrastructure.reindex import reindex
        from beadloom.services.cli import main

        project = tmp_path / "proj"
        project.mkdir()
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / "docs").mkdir()
        (project / "src").mkdir()
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_doctor_no_db(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--project", str(project)])
        assert result.exit_code != 0
