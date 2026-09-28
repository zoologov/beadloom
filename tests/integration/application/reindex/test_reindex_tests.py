"""The reindex records each node's bound tests in ``nodes.extra``.

The context bundle's and ``ctx``'s reading of them are under
``tests/integration/context_oracle/builder/`` and ``tests/unit/services/commands/``
(split by node, BDL-074 ``beadloom-2mj3.7``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
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

        # Test files laid out under the mirror of src/auth/ (BDL-074 C1): the
        # binding reads where a file lives, not what its name resembles.
        _write_file(
            project / "tests" / "unit" / "auth" / "test_service.py",
            (
                "from auth import service\n\n"
                "def test_login():\n    assert True\n\n"
                "def test_logout():\n    assert True\n"
            ),
        )
        _write_file(
            project / "tests" / "unit" / "auth" / "test_advanced.py",
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
        assert tests_info["test_files"] == [
            "tests/unit/auth/test_advanced.py",
            "tests/unit/auth/test_service.py",
        ]
        assert tests_info["test_count"] == 3
        assert tests_info["coverage_estimate"] == "medium"
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
            project / "tests" / "unit" / "auth" / "test_login.py",
            "def test_login():\n    assert True\n",
        )
        _write_file(
            project / "tests" / "integration" / "billing" / "test_invoice.py",
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
            assert len(extra["tests"]["test_files"]) == 1, extra["tests"]

        conn.close()
