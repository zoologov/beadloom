"""The context bundle carries the tests the reindex recorded for its focus node.

Split out of ``tests/test_reindex_tests.py`` (BDL-074 ``beadloom-2mj3.7``); the
reindex's half is under ``tests/integration/application/reindex/``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.builder import build_context
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


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
