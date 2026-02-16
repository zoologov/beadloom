"""Tests for check_source_coverage — untracked file detection via nodes.source dirs."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import check_source_coverage
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project directory with docs/ and src/ for coverage tests."""
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / "src" / "mymodule").mkdir(parents=True)
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


def _insert_node(
    conn: sqlite3.Connection,
    ref_id: str,
    source: str | None,
    *,
    kind: str = "domain",
    summary: str = "test node",
) -> None:
    """Insert a node with optional source field."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, summary, source),
    )
    conn.commit()


def _insert_doc(
    conn: sqlite3.Connection,
    path: str,
    ref_id: str,
    *,
    kind: str = "domain",
    doc_hash: str = "dochash",
) -> None:
    """Insert a doc entry linked to a ref_id."""
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, kind, ref_id, doc_hash),
    )
    conn.commit()


def _insert_sync_state(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    ref_id: str,
) -> None:
    """Insert a sync_state entry for a tracked code file."""
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, "hash1", "hash2", "2025-01-01", "ok"),
    )
    conn.commit()


def _insert_code_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    ref_id: str,
    *,
    symbol_name: str = "some_func",
    kind: str = "function",
) -> None:
    """Insert a code_symbol annotated with a given ref_id."""
    annotations = json.dumps({"domain": ref_id})
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, kind, 1, 10, annotations, "filehash"),
    )
    conn.commit()


class TestSourceCoverageAllTracked:
    """Node with source dir where all files are tracked -> empty result."""

    def test_all_files_tracked_via_sync_state(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via sync_state
        _insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_files_tracked_via_code_symbols(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via code_symbols (annotated with ref_id)
        _insert_code_symbol(conn, "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageUntracked:
    """Node with new untracked file -> detected."""

    def test_untracked_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create two files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "src" / "mymodule" / "new_feature.py").write_text("def new(): pass\n")

        # Only track handler.py
        _insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mymod"
        assert results[0]["doc_path"] == "mymodule.md"
        assert "src/mymodule/new_feature.py" in results[0]["untracked_files"]

    def test_untracked_file_relative_path(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Untracked files should be reported as relative paths."""
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "utils.py").write_text("X = 1\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        # Path should be relative, not absolute
        for path in results[0]["untracked_files"]:
            assert not path.startswith("/")


class TestSourceCoverageExclusions:
    """Exclusions work: __init__.py, conftest.py, __main__.py are ignored."""

    def test_init_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Only excluded files on disk
        (project / "src" / "mymodule" / "__init__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_conftest_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "conftest.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_main_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_exclusions_combined(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__init__.py").write_text("")
        (project / "src" / "mymodule" / "conftest.py").write_text("")
        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_excluded_files_ignored_but_real_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__init__.py").write_text("")
        (project / "src" / "mymodule" / "real_code.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/real_code.py" in results[0]["untracked_files"]
        # Excluded files should NOT appear
        untracked = results[0]["untracked_files"]
        assert all("__init__" not in f for f in untracked)


class TestSourceCoverageFileSource:
    """Node with file source (not dir, doesn't end in /) -> skipped."""

    def test_file_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Source points to a single file, not a directory
        _insert_node(conn, "mymod", "src/mymodule/handler.py")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "src" / "mymodule" / "untracked.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageNoNodes:
    """No nodes -> empty result."""

    def test_empty_db(self, conn: sqlite3.Connection, project: Path) -> None:
        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageMissingDir:
    """Source directory doesn't exist on disk -> skipped gracefully."""

    def test_nonexistent_dir_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/nonexistent/")
        _insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageMultipleNodes:
    """Multiple nodes with mixed results."""

    def test_mixed_results(self, conn: sqlite3.Connection, project: Path) -> None:
        # Node 1: all tracked (no gaps)
        _insert_node(conn, "mod-a", "src/mod_a/")
        _insert_doc(conn, "mod_a.md", "mod-a")
        (project / "src" / "mod_a").mkdir(parents=True)
        (project / "src" / "mod_a" / "tracked.py").write_text("x = 1\n")
        _insert_sync_state(conn, "mod_a.md", "src/mod_a/tracked.py", "mod-a")

        # Node 2: has untracked file
        _insert_node(conn, "mod-b", "src/mod_b/")
        _insert_doc(conn, "mod_b.md", "mod-b")
        (project / "src" / "mod_b").mkdir(parents=True)
        (project / "src" / "mod_b" / "tracked.py").write_text("y = 1\n")
        (project / "src" / "mod_b" / "untracked.py").write_text("z = 1\n")
        _insert_sync_state(conn, "mod_b.md", "src/mod_b/tracked.py", "mod-b")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mod-b"
        assert "src/mod_b/untracked.py" in results[0]["untracked_files"]

    def test_node_without_doc_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with source dir but no linked doc -> skipped."""
        _insert_node(conn, "mymod", "src/mymodule/")
        # No doc inserted for this node

        (project / "src" / "mymodule" / "code.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_node_with_null_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with NULL source -> skipped."""
        _insert_node(conn, "mymod", None)
        _insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []
