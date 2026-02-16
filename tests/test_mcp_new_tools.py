"""Tests for new MCP tools — BEAD-05 (why) + BEAD-06 (diff) + BEAD-12 (lint).

Tests cover:
- why tool with valid ref_id (mock DB with nodes and edges)
- why tool with invalid ref_id
- why tool response structure
- diff tool with mock git state
- diff tool with default "HEAD~1"
- diff tool response structure
- lint tool listed in _TOOLS
- lint tool with no violations
- lint tool with violations (mock)
- lint severity filter (all, error, warn)
- lint response structure
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_with_graph(tmp_path: Path) -> Path:
    """Create a project with graph, docs, code and reindex."""
    import yaml

    proj = tmp_path / "proj"
    proj.mkdir()

    graph_dir = proj / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {
                        "ref_id": "FEAT-1",
                        "kind": "feature",
                        "summary": "Track filtering",
                        "docs": ["docs/spec.md"],
                    },
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                    {"ref_id": "api-svc", "kind": "service", "summary": "API service"},
                ],
                "edges": [
                    {"src": "FEAT-1", "dst": "routing", "kind": "part_of"},
                    {"src": "api-svc", "dst": "routing", "kind": "part_of"},
                ],
            }
        )
    )

    docs_dir = proj / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    src_dir = proj / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=FEAT-1\ndef list_tracks():\n    pass\n")

    from beadloom.infrastructure.reindex import reindex

    reindex(proj)
    return proj


@pytest.fixture()
def db_conn(project_with_graph: Path) -> sqlite3.Connection:
    db_path = project_with_graph / ".beadloom" / "beadloom.db"
    conn = open_db(db_path)
    yield conn  # type: ignore[misc]
    conn.close()


# ---------------------------------------------------------------------------
# Tests: MCP 'why' tool (BEAD-05)
# ---------------------------------------------------------------------------


class TestMcpWhyTool:
    """Tests for the MCP 'why' tool."""

    def test_why_tool_listed(self) -> None:
        """Check that 'why' appears in the _TOOLS list."""
        from beadloom.services.mcp_server import _TOOLS

        tool_names = [t.name for t in _TOOLS]
        assert "why" in tool_names

    def test_why_valid_ref_id(self, db_conn: sqlite3.Connection) -> None:
        """why tool returns upstream/downstream for a valid ref_id."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(db_conn, "why", {"ref_id": "routing"})
        assert result["ref_id"] == "routing"
        assert "upstream" in result
        assert "downstream" in result
        assert "impact_summary" in result

    def test_why_with_upstream_data(self, db_conn: sqlite3.Connection) -> None:
        """FEAT-1 has upstream dep to routing via part_of edge."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(db_conn, "why", {"ref_id": "FEAT-1"})
        assert result["ref_id"] == "FEAT-1"
        # FEAT-1 -> routing (part_of), so routing is upstream
        upstream_ids = [u["ref_id"] for u in result["upstream"]]
        assert "routing" in upstream_ids

    def test_why_with_downstream_data(self, db_conn: sqlite3.Connection) -> None:
        """routing has downstream dependents: FEAT-1 and api-svc."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(db_conn, "why", {"ref_id": "routing"})
        downstream_ids = [d["ref_id"] for d in result["downstream"]]
        assert "FEAT-1" in downstream_ids
        assert "api-svc" in downstream_ids

    def test_why_invalid_ref_id(self, db_conn: sqlite3.Connection) -> None:
        """why tool raises LookupError for unknown ref_id."""
        from beadloom.services.mcp_server import _dispatch_tool

        with pytest.raises(LookupError, match="not found"):
            _dispatch_tool(db_conn, "why", {"ref_id": "NONEXISTENT"})

    def test_why_response_structure(self, db_conn: sqlite3.Connection) -> None:
        """why response has expected JSON structure."""
        from beadloom.services.mcp_server import _dispatch_tool

        result = _dispatch_tool(db_conn, "why", {"ref_id": "routing"})

        # Top-level keys
        assert "ref_id" in result
        assert "upstream" in result
        assert "downstream" in result
        assert "impact_summary" in result

        # impact_summary should have metrics
        summary = result["impact_summary"]
        assert "downstream_direct" in summary
        assert "downstream_transitive" in summary
        assert "doc_coverage" in summary

    def test_why_node_with_no_edges(self, tmp_path: Path) -> None:
        """Node with no edges returns empty upstream/downstream."""
        db_path = tmp_path / "test_isolated.db"
        conn = open_db(db_path)
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("isolated", "domain", "Isolated node"),
        )
        conn.commit()

        from beadloom.services.mcp_server import handle_why

        result = handle_why(conn, ref_id="isolated")
        assert result["ref_id"] == "isolated"
        assert result["upstream"] == []
        assert result["downstream"] == []
        conn.close()


# ---------------------------------------------------------------------------
# Tests: MCP 'diff' tool (BEAD-06)
# ---------------------------------------------------------------------------


class TestMcpDiffTool:
    """Tests for the MCP 'diff' tool."""

    def test_diff_tool_listed(self) -> None:
        """Check that 'diff' appears in the _TOOLS list."""
        from beadloom.services.mcp_server import _TOOLS

        tool_names = [t.name for t in _TOOLS]
        assert "diff" in tool_names

    def test_diff_response_structure(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """diff tool returns expected JSON structure."""
        # Mock compute_diff to return a known result
        from beadloom.graph.diff import EdgeChange, GraphDiff, NodeChange
        from beadloom.services.mcp_server import _dispatch_tool

        mock_diff = GraphDiff(
            since_ref="HEAD~1",
            nodes=(NodeChange(ref_id="new-feat", kind="feature", change_type="added"),),
            edges=(
                EdgeChange(src="new-feat", dst="routing", kind="part_of", change_type="added"),
            ),
        )

        with patch("beadloom.services.mcp_server.compute_diff", return_value=mock_diff):
            result = _dispatch_tool(
                db_conn,
                "diff",
                {},
                project_root=project_with_graph,
            )

        assert "since" in result
        assert "added_nodes" in result
        assert "removed_nodes" in result
        assert "changed_nodes" in result
        assert "added_edges" in result
        assert "removed_edges" in result

    def test_diff_with_default_since(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """diff tool uses HEAD~1 as default when 'since' is not provided."""
        from beadloom.graph.diff import GraphDiff
        from beadloom.services.mcp_server import _dispatch_tool

        mock_diff = GraphDiff(since_ref="HEAD~1", nodes=(), edges=())

        with patch("beadloom.services.mcp_server.compute_diff", return_value=mock_diff) as mock_fn:
            result = _dispatch_tool(
                db_conn,
                "diff",
                {},
                project_root=project_with_graph,
            )
            mock_fn.assert_called_once_with(project_with_graph, since="HEAD~1")

        assert result["since"] == "HEAD~1"

    def test_diff_with_custom_since(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """diff tool passes custom 'since' arg to compute_diff."""
        from beadloom.graph.diff import GraphDiff
        from beadloom.services.mcp_server import _dispatch_tool

        mock_diff = GraphDiff(since_ref="main", nodes=(), edges=())

        with patch("beadloom.services.mcp_server.compute_diff", return_value=mock_diff) as mock_fn:
            result = _dispatch_tool(
                db_conn,
                "diff",
                {"since": "main"},
                project_root=project_with_graph,
            )
            mock_fn.assert_called_once_with(project_with_graph, since="main")

        assert result["since"] == "main"

    def test_diff_no_changes(self, project_with_graph: Path, db_conn: sqlite3.Connection) -> None:
        """diff tool with no changes returns empty lists."""
        from beadloom.graph.diff import GraphDiff
        from beadloom.services.mcp_server import _dispatch_tool

        mock_diff = GraphDiff(since_ref="HEAD~1", nodes=(), edges=())

        with patch("beadloom.services.mcp_server.compute_diff", return_value=mock_diff):
            result = _dispatch_tool(
                db_conn,
                "diff",
                {},
                project_root=project_with_graph,
            )

        assert result["added_nodes"] == []
        assert result["removed_nodes"] == []
        assert result["changed_nodes"] == []
        assert result["added_edges"] == []
        assert result["removed_edges"] == []

    def test_diff_with_changes(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """diff tool correctly categorizes node/edge changes."""
        from beadloom.graph.diff import EdgeChange, GraphDiff, NodeChange
        from beadloom.services.mcp_server import _dispatch_tool

        mock_diff = GraphDiff(
            since_ref="HEAD~1",
            nodes=(
                NodeChange(ref_id="new-feat", kind="feature", change_type="added"),
                NodeChange(ref_id="old-feat", kind="feature", change_type="removed"),
                NodeChange(
                    ref_id="mod-feat",
                    kind="feature",
                    change_type="changed",
                    old_summary="Old",
                    new_summary="New",
                ),
            ),
            edges=(
                EdgeChange(src="new-feat", dst="routing", kind="part_of", change_type="added"),
                EdgeChange(src="old-feat", dst="routing", kind="part_of", change_type="removed"),
            ),
        )

        with patch("beadloom.services.mcp_server.compute_diff", return_value=mock_diff):
            result = _dispatch_tool(
                db_conn,
                "diff",
                {},
                project_root=project_with_graph,
            )

        assert len(result["added_nodes"]) == 1
        assert result["added_nodes"][0]["ref_id"] == "new-feat"
        assert len(result["removed_nodes"]) == 1
        assert result["removed_nodes"][0]["ref_id"] == "old-feat"
        assert len(result["changed_nodes"]) == 1
        assert result["changed_nodes"][0]["ref_id"] == "mod-feat"
        assert len(result["added_edges"]) == 1
        assert len(result["removed_edges"]) == 1

    def test_diff_requires_project_root(self, db_conn: sqlite3.Connection) -> None:
        """diff tool raises ValueError when project_root is None."""
        from beadloom.services.mcp_server import _dispatch_tool

        with pytest.raises(ValueError, match="diff requires project_root"):
            _dispatch_tool(db_conn, "diff", {})


# ---------------------------------------------------------------------------
# Tests: MCP 'lint' tool (BEAD-12)
# ---------------------------------------------------------------------------


class TestMcpLintTool:
    """Tests for the MCP 'lint' tool."""

    def test_lint_tool_listed(self) -> None:
        """Check that 'lint' appears in the _TOOLS list."""
        from beadloom.services.mcp_server import _TOOLS

        tool_names = [t.name for t in _TOOLS]
        assert "lint" in tool_names

    def test_lint_tool_schema(self) -> None:
        """Verify lint tool has correct inputSchema with severity enum."""
        from beadloom.services.mcp_server import _TOOLS

        lint_tool = next(t for t in _TOOLS if t.name == "lint")
        props = lint_tool.inputSchema["properties"]
        assert "severity" in props
        assert props["severity"]["enum"] == ["all", "error", "warn"]

    def test_lint_no_violations(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint tool returns empty violations when no rules are violated."""
        from beadloom.graph.linter import LintResult
        from beadloom.services.mcp_server import _dispatch_tool

        mock_result = LintResult(
            violations=[],
            rules_evaluated=3,
            files_scanned=10,
            imports_resolved=5,
            elapsed_ms=42.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {},
                project_root=project_with_graph,
            )

        assert result["violations"] == []
        assert result["summary"]["errors"] == 0
        assert result["summary"]["warnings"] == 0
        assert result["summary"]["rules_evaluated"] == 3

    def test_lint_with_violations(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint tool returns violations from linter."""
        from beadloom.graph.linter import LintResult
        from beadloom.graph.rule_engine import Violation
        from beadloom.services.mcp_server import _dispatch_tool

        violations = [
            Violation(
                rule_name="no-cross-domain",
                rule_description="No cross-domain imports",
                rule_type="deny",
                severity="error",
                file_path="src/billing/invoice.py",
                line_number=12,
                from_ref_id="billing",
                to_ref_id="auth",
                message="Import from 'billing' to 'auth' violates deny rule",
            ),
            Violation(
                rule_name="domain-needs-parent",
                rule_description="Domains must have part_of edge",
                rule_type="require",
                severity="warn",
                file_path=None,
                line_number=None,
                from_ref_id="orphan",
                to_ref_id=None,
                message="Node 'orphan' has no part_of edge",
            ),
        ]
        mock_result = LintResult(
            violations=violations,
            rules_evaluated=4,
            files_scanned=15,
            imports_resolved=8,
            elapsed_ms=55.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {},
                project_root=project_with_graph,
            )

        assert len(result["violations"]) == 2
        assert result["summary"]["errors"] == 1
        assert result["summary"]["warnings"] == 1
        assert result["summary"]["rules_evaluated"] == 4

    def test_lint_severity_filter_error(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint tool with severity=error returns only error violations."""
        from beadloom.graph.linter import LintResult
        from beadloom.graph.rule_engine import Violation
        from beadloom.services.mcp_server import _dispatch_tool

        violations = [
            Violation(
                rule_name="no-cross-domain",
                rule_description="No cross-domain imports",
                rule_type="deny",
                severity="error",
                file_path="src/a.py",
                line_number=1,
                from_ref_id="a",
                to_ref_id="b",
                message="error violation",
            ),
            Violation(
                rule_name="soft-rule",
                rule_description="Soft warning",
                rule_type="require",
                severity="warn",
                file_path=None,
                line_number=None,
                from_ref_id="c",
                to_ref_id=None,
                message="warning violation",
            ),
        ]
        mock_result = LintResult(
            violations=violations,
            rules_evaluated=2,
            files_scanned=5,
            imports_resolved=3,
            elapsed_ms=10.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {"severity": "error"},
                project_root=project_with_graph,
            )

        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == "error"
        assert result["summary"]["errors"] == 1
        assert result["summary"]["warnings"] == 0

    def test_lint_severity_filter_warn(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint tool with severity=warn returns only warn violations."""
        from beadloom.graph.linter import LintResult
        from beadloom.graph.rule_engine import Violation
        from beadloom.services.mcp_server import _dispatch_tool

        violations = [
            Violation(
                rule_name="no-cross-domain",
                rule_description="No cross-domain imports",
                rule_type="deny",
                severity="error",
                file_path="src/a.py",
                line_number=1,
                from_ref_id="a",
                to_ref_id="b",
                message="error violation",
            ),
            Violation(
                rule_name="soft-rule",
                rule_description="Soft warning",
                rule_type="require",
                severity="warn",
                file_path=None,
                line_number=None,
                from_ref_id="c",
                to_ref_id=None,
                message="warning violation",
            ),
        ]
        mock_result = LintResult(
            violations=violations,
            rules_evaluated=2,
            files_scanned=5,
            imports_resolved=3,
            elapsed_ms=10.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {"severity": "warn"},
                project_root=project_with_graph,
            )

        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == "warn"
        assert result["summary"]["errors"] == 0
        assert result["summary"]["warnings"] == 1

    def test_lint_severity_filter_all(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint tool with severity=all returns all violations (same as default)."""
        from beadloom.graph.linter import LintResult
        from beadloom.graph.rule_engine import Violation
        from beadloom.services.mcp_server import _dispatch_tool

        violations = [
            Violation(
                rule_name="rule-a",
                rule_description="Rule A",
                rule_type="deny",
                severity="error",
                file_path="src/a.py",
                line_number=1,
                from_ref_id="a",
                to_ref_id="b",
                message="error",
            ),
            Violation(
                rule_name="rule-b",
                rule_description="Rule B",
                rule_type="require",
                severity="warn",
                file_path=None,
                line_number=None,
                from_ref_id="c",
                to_ref_id=None,
                message="warn",
            ),
        ]
        mock_result = LintResult(
            violations=violations,
            rules_evaluated=2,
            files_scanned=5,
            imports_resolved=3,
            elapsed_ms=10.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {"severity": "all"},
                project_root=project_with_graph,
            )

        assert len(result["violations"]) == 2
        assert result["summary"]["errors"] == 1
        assert result["summary"]["warnings"] == 1

    def test_lint_response_structure(
        self, project_with_graph: Path, db_conn: sqlite3.Connection
    ) -> None:
        """lint response has expected JSON structure with violations and summary."""
        from beadloom.graph.linter import LintResult
        from beadloom.graph.rule_engine import Violation
        from beadloom.services.mcp_server import _dispatch_tool

        violations = [
            Violation(
                rule_name="test-rule",
                rule_description="Test rule description",
                rule_type="deny",
                severity="error",
                file_path="src/test.py",
                line_number=42,
                from_ref_id="src-node",
                to_ref_id="dst-node",
                message="Test violation message",
            ),
        ]
        mock_result = LintResult(
            violations=violations,
            rules_evaluated=3,
            files_scanned=10,
            imports_resolved=5,
            elapsed_ms=99.0,
        )

        with patch("beadloom.services.mcp_server.lint", return_value=mock_result):
            result = _dispatch_tool(
                db_conn,
                "lint",
                {},
                project_root=project_with_graph,
            )

        # Top-level keys
        assert "violations" in result
        assert "summary" in result

        # Violation structure
        v = result["violations"][0]
        assert v["rule"] == "test-rule"
        assert v["severity"] == "error"
        assert v["rule_type"] == "deny"
        assert v["file_path"] == "src/test.py"
        assert v["line_number"] == 42
        assert v["from_ref_id"] == "src-node"
        assert v["to_ref_id"] == "dst-node"
        assert v["message"] == "Test violation message"

        # Summary structure
        s = result["summary"]
        assert s["errors"] == 1
        assert s["warnings"] == 0
        assert s["rules_evaluated"] == 3

    def test_lint_requires_project_root(self, db_conn: sqlite3.Connection) -> None:
        """lint tool raises ValueError when project_root is None."""
        from beadloom.services.mcp_server import _dispatch_tool

        with pytest.raises(ValueError, match="lint requires project_root"):
            _dispatch_tool(db_conn, "lint", {})
