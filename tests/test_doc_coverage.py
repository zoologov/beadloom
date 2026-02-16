"""Tests for check_doc_coverage — module-name mention detection in docs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import check_doc_coverage
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


class TestDocCoverageAllMentioned:
    """Doc mentions all module names from source directory -> empty result."""

    def test_all_modules_mentioned(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create source files
        (project / "src" / "mymodule" / "engine.py").write_text("def run(): pass\n")
        (project / "src" / "mymodule" / "builder.py").write_text("def build(): pass\n")

        # Create doc that mentions both module names
        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\nThis module has engine and builder components.\n"
        )

        results = check_doc_coverage(conn, project)
        assert results == []


class TestDocCoverageMissingModules:
    """Doc missing a module name -> detected with correct ref_id and missing list."""

    def test_missing_module_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create source files
        (project / "src" / "mymodule" / "engine.py").write_text("def run(): pass\n")
        (project / "src" / "mymodule" / "builder.py").write_text("def build(): pass\n")
        (project / "src" / "mymodule" / "parser.py").write_text("def parse(): pass\n")

        # Doc mentions engine and builder but NOT parser
        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\nThis has engine and builder.\n"
        )

        results = check_doc_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mymod"
        assert results[0]["doc_path"] == "mymodule.md"
        assert "parser" in results[0]["missing_modules"]

    def test_case_insensitive_match(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Module name matching should be case-insensitive."""
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "engine.py").write_text("x = 1\n")

        # Doc mentions "Engine" with capital E
        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\nThe Engine component handles logic.\n"
        )

        results = check_doc_coverage(conn, project)
        assert results == []

    def test_multiple_missing(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Multiple missing modules reported together."""
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "alpha.py").write_text("x = 1\n")
        (project / "src" / "mymodule" / "beta.py").write_text("y = 1\n")
        (project / "src" / "mymodule" / "gamma.py").write_text("z = 1\n")

        # Doc mentions none of them
        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\nGeneric description.\n"
        )

        results = check_doc_coverage(conn, project)
        assert len(results) == 1
        missing = results[0]["missing_modules"]
        assert "alpha" in missing
        assert "beta" in missing
        assert "gamma" in missing


class TestDocCoverageExclusions:
    """Excluded files (__init__.py, conftest.py, __main__.py) not checked."""

    def test_init_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Only excluded files on disk
        (project / "src" / "mymodule" / "__init__.py").write_text("")

        # Doc doesn't mention __init__ — should be fine
        (project / "docs" / "mymodule.md").write_text("# My Module\n\nOverview.\n")

        results = check_doc_coverage(conn, project)
        assert results == []

    def test_conftest_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "conftest.py").write_text("")
        (project / "docs" / "mymodule.md").write_text("# My Module\n\nOverview.\n")

        results = check_doc_coverage(conn, project)
        assert results == []

    def test_main_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__main__.py").write_text("")
        (project / "docs" / "mymodule.md").write_text("# My Module\n\nOverview.\n")

        results = check_doc_coverage(conn, project)
        assert results == []


class TestDocCoverageFileSource:
    """Node with file source (not dir, doesn't end in /) -> skipped."""

    def test_file_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/handler.py")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "docs" / "mymodule.md").write_text("# My Module\n\nNo modules mentioned.\n")

        results = check_doc_coverage(conn, project)
        assert results == []


class TestDocCoverageMissingDir:
    """Source directory doesn't exist on disk -> skipped gracefully."""

    def test_nonexistent_dir_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/nonexistent/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "docs" / "mymodule.md").write_text("# My Module\n\nOverview.\n")

        results = check_doc_coverage(conn, project)
        assert results == []


class TestDocCoverageNoNodes:
    """No nodes -> empty result."""

    def test_empty_db(self, conn: sqlite3.Connection, project: Path) -> None:
        results = check_doc_coverage(conn, project)
        assert results == []


class TestDocCoverageMissingDocFile:
    """Doc path in DB but file doesn't exist on disk -> skipped."""

    def test_missing_doc_file_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "engine.py").write_text("x = 1\n")
        # Don't create docs/mymodule.md

        results = check_doc_coverage(conn, project)
        assert results == []
