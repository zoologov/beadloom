"""Tests for polish deep data: routes, activity, tests from nodes.extra."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.onboarding.doc_generator import (
    _load_extra_from_sqlite,
    format_polish_text,
    generate_polish_data,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_graph_yaml(tmp_path: Path, data: dict[str, Any]) -> None:
    """Write a graph YAML file so ``generate_polish_data`` can load it."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "services.yml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _create_sqlite_db(tmp_path: Path) -> Path:
    """Create a minimal beadloom.db with nodes table."""
    db_dir = tmp_path / ".beadloom"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "beadloom.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS nodes ("
        "  ref_id TEXT PRIMARY KEY,"
        "  kind TEXT NOT NULL,"
        "  summary TEXT NOT NULL DEFAULT '',"
        "  source TEXT,"
        "  extra TEXT DEFAULT '{}'"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS edges ("
        "  src_ref_id TEXT NOT NULL,"
        "  dst_ref_id TEXT NOT NULL,"
        "  kind TEXT NOT NULL,"
        "  extra TEXT DEFAULT '{}',"
        "  PRIMARY KEY (src_ref_id, dst_ref_id, kind)"
        ")"
    )
    conn.commit()
    conn.close()
    return db_path


def _insert_node_with_extra(
    db_path: Path,
    ref_id: str,
    kind: str,
    extra: dict[str, Any],
    summary: str = "",
    source: str = "",
) -> None:
    """Insert a single node with an extra JSON blob."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO nodes (ref_id, kind, summary, source, extra) "
        "VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, summary, source, json.dumps(extra, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def _default_graph() -> dict[str, Any]:
    """Minimal graph with root + one domain node."""
    return {
        "nodes": [
            {"ref_id": "myproject", "kind": "service", "source": "", "summary": "Root"},
            {
                "ref_id": "api-svc",
                "kind": "service",
                "summary": "API service",
                "source": "src/api/",
            },
        ],
        "edges": [
            {"src": "api-svc", "dst": "myproject", "kind": "part_of"},
        ],
    }


_SAMPLE_ROUTES: list[dict[str, Any]] = [
    {
        "method": "GET",
        "path": "/api/users",
        "handler": "get_users",
        "file": "src/api/routes.py",
        "line": 10,
        "framework": "fastapi",
    },
    {
        "method": "POST",
        "path": "/api/users",
        "handler": "create_user",
        "file": "src/api/routes.py",
        "line": 20,
        "framework": "fastapi",
    },
]

_SAMPLE_ACTIVITY: dict[str, Any] = {
    "level": "hot",
    "commits_30d": 45,
    "commits_90d": 120,
    "last_commit": "2026-02-15",
    "top_contributors": ["alice", "bob"],
}

_SAMPLE_TESTS: dict[str, Any] = {
    "framework": "pytest",
    "test_files": ["tests/test_api.py", "tests/test_routes.py", "tests/test_auth.py"],
    "test_count": 15,
    "coverage_estimate": "high",
}


# ---------------------------------------------------------------------------
# TestLoadExtraFromSqlite
# ---------------------------------------------------------------------------


class TestLoadExtraFromSqlite:
    """Tests for :func:`_load_extra_from_sqlite`."""

    def test_load_extra_from_sqlite_no_db(self, tmp_path: Path) -> None:
        """Returns empty dict when no database file exists."""
        result = _load_extra_from_sqlite(tmp_path)
        assert result == {}

    def test_load_extra_returns_parsed_dict(self, tmp_path: Path) -> None:
        """Returns parsed extra JSON keyed by ref_id."""
        db_path = _create_sqlite_db(tmp_path)
        extra = {"routes": _SAMPLE_ROUTES, "activity": _SAMPLE_ACTIVITY}
        _insert_node_with_extra(db_path, "api-svc", "service", extra)

        result = _load_extra_from_sqlite(tmp_path)
        assert "api-svc" in result
        assert result["api-svc"]["routes"] == _SAMPLE_ROUTES
        assert result["api-svc"]["activity"] == _SAMPLE_ACTIVITY

    def test_load_extra_skips_empty_extra(self, tmp_path: Path) -> None:
        """Nodes with empty or null extra are excluded."""
        db_path = _create_sqlite_db(tmp_path)
        # Insert a node with empty extra.
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) "
            "VALUES (?, ?, ?, ?, ?)",
            ("empty-node", "domain", "", "", ""),
        )
        conn.commit()
        conn.close()

        result = _load_extra_from_sqlite(tmp_path)
        assert "empty-node" not in result

    def test_load_extra_graceful_no_table(self, tmp_path: Path) -> None:
        """Returns empty dict when DB exists but nodes table is missing."""
        db_dir = tmp_path / ".beadloom"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "beadloom.db"
        conn = sqlite3.connect(str(db_path))
        # Create a dummy table instead of nodes.
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        result = _load_extra_from_sqlite(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# TestPolishDataDeepFields
# ---------------------------------------------------------------------------


class TestPolishDataDeepFields:
    """Tests that ``generate_polish_data`` includes routes, activity, tests."""

    def test_polish_data_includes_routes(self, tmp_path: Path) -> None:
        """Routes from nodes.extra appear in polish data."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        db_path = _create_sqlite_db(tmp_path)
        _insert_node_with_extra(
            db_path, "api-svc", "service", {"routes": _SAMPLE_ROUTES}
        )

        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert "routes" in node
        assert len(node["routes"]) == 2
        methods = {r["method"] for r in node["routes"]}
        assert "GET" in methods
        assert "POST" in methods

    def test_polish_data_includes_activity(self, tmp_path: Path) -> None:
        """Activity data from nodes.extra appears in polish data."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        db_path = _create_sqlite_db(tmp_path)
        _insert_node_with_extra(
            db_path, "api-svc", "service", {"activity": _SAMPLE_ACTIVITY}
        )

        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert "activity" in node
        assert node["activity"]["level"] == "hot"
        assert node["activity"]["commits_30d"] == 45

    def test_polish_data_includes_tests(self, tmp_path: Path) -> None:
        """Test mapping data from nodes.extra appears in polish data."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        db_path = _create_sqlite_db(tmp_path)
        _insert_node_with_extra(
            db_path, "api-svc", "service", {"tests": _SAMPLE_TESTS}
        )

        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert "tests" in node
        assert node["tests"]["framework"] == "pytest"
        assert node["tests"]["test_count"] == 15
        assert node["tests"]["coverage_estimate"] == "high"

    def test_polish_data_no_extra(self, tmp_path: Path) -> None:
        """Nodes without extra data still produce valid polish data."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        # No SQLite DB at all — no extras.
        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert node["ref_id"] == "api-svc"
        # These keys should not be present when there's no extra data.
        assert "routes" not in node
        assert "activity" not in node
        assert "tests" not in node

    def test_polish_data_partial_extra(self, tmp_path: Path) -> None:
        """Nodes with only some extra fields only get those fields."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        db_path = _create_sqlite_db(tmp_path)
        # Only routes, no activity or tests.
        _insert_node_with_extra(
            db_path, "api-svc", "service", {"routes": _SAMPLE_ROUTES}
        )

        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert "routes" in node
        assert "activity" not in node
        assert "tests" not in node

    def test_polish_data_all_extra_fields(self, tmp_path: Path) -> None:
        """All three extra fields appear when present."""
        graph_data = _default_graph()
        _write_graph_yaml(tmp_path, graph_data)

        db_path = _create_sqlite_db(tmp_path)
        _insert_node_with_extra(
            db_path,
            "api-svc",
            "service",
            {
                "routes": _SAMPLE_ROUTES,
                "activity": _SAMPLE_ACTIVITY,
                "tests": _SAMPLE_TESTS,
            },
        )

        result = generate_polish_data(tmp_path, ref_id="api-svc")
        node = result["nodes"][0]

        assert "routes" in node
        assert "activity" in node
        assert "tests" in node


# ---------------------------------------------------------------------------
# TestFormatPolishTextDeepFields
# ---------------------------------------------------------------------------


class TestFormatPolishTextDeepFields:
    """Tests that ``format_polish_text`` renders routes, activity, tests."""

    def test_format_polish_text_routes(self) -> None:
        """Routes table is rendered in the text output."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "api-svc",
                    "kind": "service",
                    "summary": "API service",
                    "source": "src/api/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": None,
                    "doc_status": "missing",
                    "routes": _SAMPLE_ROUTES,
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "Routes:" in text
        assert "GET" in text
        assert "/api/users" in text
        assert "get_users" in text
        assert "POST" in text
        assert "create_user" in text
        assert "(fastapi)" in text

    def test_format_polish_text_activity(self) -> None:
        """Activity line is rendered in the text output."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "api-svc",
                    "kind": "service",
                    "summary": "API service",
                    "source": "src/api/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": None,
                    "doc_status": "missing",
                    "activity": _SAMPLE_ACTIVITY,
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "Activity: hot" in text
        assert "45 commits/30d" in text
        assert "last: 2026-02-15" in text

    def test_format_polish_text_tests(self) -> None:
        """Tests line is rendered in the text output."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "api-svc",
                    "kind": "service",
                    "summary": "API service",
                    "source": "src/api/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": None,
                    "doc_status": "missing",
                    "tests": _SAMPLE_TESTS,
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "Tests: pytest" in text
        assert "15 tests in 3 files" in text
        assert "coverage: high" in text

    def test_format_polish_text_no_deep_data(self) -> None:
        """No routes/activity/tests sections when data is absent."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "plain-node",
                    "kind": "domain",
                    "summary": "Plain node",
                    "source": "src/plain/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": None,
                    "doc_status": "missing",
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        assert "Routes:" not in text
        assert "Activity:" not in text
        assert "Tests:" not in text

    def test_format_polish_text_all_deep_data(self) -> None:
        """All three deep data sections rendered together."""
        data: dict[str, Any] = {
            "nodes": [
                {
                    "ref_id": "api-svc",
                    "kind": "service",
                    "summary": "API service",
                    "source": "src/api/",
                    "symbols": [],
                    "depends_on": [],
                    "used_by": [],
                    "doc_path": None,
                    "doc_status": "missing",
                    "routes": _SAMPLE_ROUTES,
                    "activity": _SAMPLE_ACTIVITY,
                    "tests": _SAMPLE_TESTS,
                },
            ],
            "architecture": {"project_name": "testproject"},
            "instructions": "Enrich the docs.",
        }
        text = format_polish_text(data)

        # All three sections present.
        assert "Routes:" in text
        assert "Activity:" in text
        assert "Tests:" in text

        # Verify ordering: Routes before Activity before Tests before Doc.
        routes_idx = text.index("Routes:")
        activity_idx = text.index("Activity:")
        tests_idx = text.index("Tests:")
        doc_idx = text.index("Doc:")
        assert routes_idx < activity_idx < tests_idx < doc_idx
