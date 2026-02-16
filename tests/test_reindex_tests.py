"""Tests for test mapping integration into reindex pipeline and context bundle."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.builder import build_context
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.reindex import reindex

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_file(path: Path, content: str = "") -> None:
    """Create parent dirs and write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal Beadloom project with graph, docs, and src dirs."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Integration: reindex stores test mapping in nodes.extra
# ---------------------------------------------------------------------------


class TestReindexTestMapping:
    """Integration tests: reindex discovers test files and stores mapping in nodes.extra."""

    def test_reindex_stores_tests_in_node_extra(self, tmp_path: Path) -> None:
        """Create a project with pytest test files, reindex, verify tests in nodes.extra."""
        project = _make_project(tmp_path)

        # Graph node with source pointing to src/auth
        _write_file(
            project / ".beadloom" / "_graph" / "domains.yml",
            (
                "nodes:\n"
                '  - ref_id: auth\n'
                '    kind: domain\n'
                '    summary: "Authentication module"\n'
                '    source: src/auth\n'
            ),
        )

        # Source file
        _write_file(
            project / "src" / "auth" / "service.py",
            "def login():\n    pass\n",
        )

        # conftest.py to mark pytest
        _write_file(project / "conftest.py", "import pytest\n")

        # Test files that map to "auth" node
        _write_file(
            project / "tests" / "test_auth.py",
            (
                "from auth import service\n\n"
                "def test_login():\n    assert True\n\n"
                "def test_logout():\n    assert True\n"
            ),
        )
        _write_file(
            project / "tests" / "test_auth_advanced.py",
            "def test_auth_token():\n    assert True\n",
        )

        result = reindex(project)
        assert result.nodes_loaded >= 1

        # Open DB and check nodes.extra for the "auth" node
        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT extra FROM nodes WHERE ref_id = ?", ("auth",)
        ).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])
        assert "tests" in extra

        tests_info = extra["tests"]
        assert tests_info["framework"] == "pytest"
        assert isinstance(tests_info["test_files"], list)
        assert len(tests_info["test_files"]) > 0
        assert isinstance(tests_info["test_count"], int)
        assert tests_info["test_count"] > 0
        assert tests_info["coverage_estimate"] in ("high", "medium", "low", "none")
        conn.close()

    def test_reindex_no_test_framework(self, tmp_path: Path) -> None:
        """When no test framework is detected, nodes.extra should have no tests key or empty."""
        project = _make_project(tmp_path)

        # Graph node with no test files at all
        _write_file(
            project / ".beadloom" / "_graph" / "domains.yml",
            (
                "nodes:\n"
                '  - ref_id: utils\n'
                '    kind: domain\n'
                '    summary: "Utility functions"\n'
                '    source: src/utils\n'
            ),
        )

        _write_file(
            project / "src" / "utils" / "helpers.py",
            "def helper():\n    pass\n",
        )

        result = reindex(project)
        assert result.nodes_loaded >= 1

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        row = conn.execute(
            "SELECT extra FROM nodes WHERE ref_id = ?", ("utils",)
        ).fetchone()
        assert row is not None
        extra = json.loads(row["extra"])

        # No test framework detected: either no "tests" key or tests show "none" framework
        if "tests" in extra:
            tests_info = extra["tests"]
            assert tests_info["test_count"] == 0
            assert tests_info["test_files"] == []
            assert tests_info["coverage_estimate"] == "none"
        conn.close()

    def test_reindex_multiple_nodes_with_tests(self, tmp_path: Path) -> None:
        """Multiple graph nodes each get their own test mapping."""
        project = _make_project(tmp_path)

        _write_file(
            project / ".beadloom" / "_graph" / "domains.yml",
            (
                "nodes:\n"
                '  - ref_id: auth\n'
                '    kind: domain\n'
                '    summary: "Auth"\n'
                '    source: src/auth\n'
                '  - ref_id: billing\n'
                '    kind: domain\n'
                '    summary: "Billing"\n'
                '    source: src/billing\n'
            ),
        )

        _write_file(project / "src" / "auth" / "login.py", "def login():\n    pass\n")
        _write_file(project / "src" / "billing" / "invoice.py", "def invoice():\n    pass\n")

        _write_file(project / "conftest.py", "import pytest\n")
        _write_file(
            project / "tests" / "test_auth.py",
            "def test_login():\n    assert True\n",
        )
        _write_file(
            project / "tests" / "test_billing.py",
            "def test_invoice():\n    assert True\n\ndef test_payment():\n    assert True\n",
        )

        reindex(project)

        db_path = project / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)

        for ref_id in ("auth", "billing"):
            row = conn.execute(
                "SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)
            ).fetchone()
            assert row is not None
            extra = json.loads(row["extra"])
            assert "tests" in extra, f"Node {ref_id} should have tests in extra"
            assert extra["tests"]["framework"] == "pytest"

        conn.close()


# ---------------------------------------------------------------------------
# Integration: context bundle includes tests line
# ---------------------------------------------------------------------------


class TestContextBundleTests:
    """Integration tests: context bundle includes test mapping info."""

    @pytest.fixture()
    def conn(self, tmp_path: Path) -> sqlite3.Connection:
        """Create DB with schema."""
        db_path = tmp_path / "test.db"
        c = open_db(db_path)
        create_schema(c)
        return c

    def _insert_node_with_tests(
        self,
        conn: sqlite3.Connection,
        ref_id: str,
        kind: str,
        summary: str,
        tests_info: dict[str, object] | None = None,
    ) -> None:
        """Insert a node with optional test info in extra."""
        extra: dict[str, object] = {}
        if tests_info is not None:
            extra["tests"] = tests_info
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, json.dumps(extra, ensure_ascii=False)),
        )
        conn.commit()

    def test_context_bundle_includes_tests_in_json(self, conn: sqlite3.Connection) -> None:
        """JSON context bundle should include tests object."""
        tests_info = {
            "framework": "pytest",
            "test_files": ["tests/test_auth.py", "tests/test_auth_service.py"],
            "test_count": 15,
            "coverage_estimate": "high",
        }
        self._insert_node_with_tests(conn, "auth", "domain", "Auth module", tests_info)

        # Set meta for build_context
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_reindex_at", "2026-01-01T00:00:00"),
        )
        conn.commit()

        bundle = build_context(conn, ["auth"], depth=0, max_nodes=5, max_chunks=5)
        assert "tests" in bundle
        assert bundle["tests"]["framework"] == "pytest"
        assert bundle["tests"]["test_count"] == 15
        assert len(bundle["tests"]["test_files"]) == 2
        assert bundle["tests"]["coverage_estimate"] == "high"

    def test_context_bundle_no_tests(self, conn: sqlite3.Connection) -> None:
        """When node has no tests info, bundle should have tests=None or empty."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("utils", "domain", "Utilities"),
        )
        conn.commit()
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_reindex_at", "2026-01-01T00:00:00"),
        )
        conn.commit()

        bundle = build_context(conn, ["utils"], depth=0, max_nodes=5, max_chunks=5)
        # Should have tests key but it should be None
        assert "tests" in bundle
        assert bundle["tests"] is None


# ---------------------------------------------------------------------------
# Markdown rendering of tests line
# ---------------------------------------------------------------------------


class TestMarkdownTestsLine:
    """Test that _format_markdown renders the Tests: line correctly."""

    def test_format_markdown_includes_tests_line(self) -> None:
        """Markdown output should contain a Tests: line when tests are present."""
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "version": 2,
            "focus": {"ref_id": "auth", "kind": "domain", "summary": "Auth module"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [],
            "code_symbols": [],
            "sync_status": {"stale_docs": [], "last_reindex": None},
            "constraints": [],
            "warning": None,
            "tests": {
                "framework": "pytest",
                "test_files": [
                    "tests/test_auth.py",
                    "tests/test_auth_service.py",
                    "tests/test_auth_utils.py",
                ],
                "test_count": 15,
                "coverage_estimate": "high",
            },
        }
        md = _format_markdown(bundle)
        assert "Tests:" in md
        assert "pytest" in md
        assert "15 tests" in md
        assert "3 files" in md
        assert "high coverage" in md

    def test_format_markdown_no_tests(self) -> None:
        """Markdown output should not have Tests: line when tests is None."""
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "version": 2,
            "focus": {"ref_id": "auth", "kind": "domain", "summary": "Auth module"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [],
            "code_symbols": [],
            "sync_status": {"stale_docs": [], "last_reindex": None},
            "constraints": [],
            "warning": None,
            "tests": None,
        }
        md = _format_markdown(bundle)
        assert "Tests:" not in md
