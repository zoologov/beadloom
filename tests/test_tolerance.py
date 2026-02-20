"""Tests for the tolerance system (BEAD-05).

Verifies configurable per-fact tolerance in compare_facts():
- Default tolerances (exact for versions, +/-5% for test_count, +/-10% for growing metrics)
- Config overrides
- Tolerance stored in AuditFinding
- CLI display of tolerance
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.doc_sync.audit import (
    DEFAULT_TOLERANCES,
    Fact,
    compare_facts,
)
from beadloom.doc_sync.scanner import Mention

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Default tolerance constants
# ---------------------------------------------------------------------------


class TestDefaultTolerances:
    """Tests for DEFAULT_TOLERANCES constant."""

    def test_version_exact(self) -> None:
        """Version tolerance should be 0.0 (exact match)."""
        assert DEFAULT_TOLERANCES["version"] == 0.0

    def test_node_count_10pct(self) -> None:
        """node_count tolerance should be 10%."""
        assert DEFAULT_TOLERANCES["node_count"] == 0.10

    def test_edge_count_10pct(self) -> None:
        """edge_count tolerance should be 10%."""
        assert DEFAULT_TOLERANCES["edge_count"] == 0.10

    def test_test_count_5pct(self) -> None:
        """test_count tolerance should be 5%."""
        assert DEFAULT_TOLERANCES["test_count"] == 0.05


# ---------------------------------------------------------------------------
# Tolerance application in compare_facts
# ---------------------------------------------------------------------------


class TestToleranceApplication:
    """Tests for tolerance-aware comparison logic."""

    def test_default_tolerances_exact_version(self, tmp_path: Path) -> None:
        """Version with tolerance=0.0 requires exact match."""
        facts = {
            "version": Fact(name="version", value="2.0.0", source="pyproject.toml"),
        }
        mentions = [
            Mention(
                fact_name="version",
                value="2.0.1",
                file=tmp_path / "README.md",
                line=1,
                context="v2.0.1",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "stale"
        assert result.findings[0].tolerance == 0.0

    def test_default_tolerances_test_count_within(self, tmp_path: Path) -> None:
        """test_count 1657 vs 1720 actual, within 5% -> fresh.

        Lower = 1720 * 0.95 = 1634, Upper = 1720 * 1.05 = 1806.
        1657 is in [1634, 1806] -> fresh.
        """
        facts = {
            "test_count": Fact(name="test_count", value=1720, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=1657,
                file=tmp_path / "README.md",
                line=10,
                context="1657 tests",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "fresh"
        assert result.findings[0].tolerance == 0.05

    def test_default_tolerances_test_count_outside(self, tmp_path: Path) -> None:
        """test_count 1500 vs 1720 actual, outside 5% -> stale.

        Lower = 1720 * 0.95 = 1634. 1500 < 1634 -> stale.
        """
        facts = {
            "test_count": Fact(name="test_count", value=1720, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=1500,
                file=tmp_path / "README.md",
                line=10,
                context="1500 tests",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "stale"
        assert result.findings[0].tolerance == 0.05

    def test_default_tolerances_node_count_within_10pct(self, tmp_path: Path) -> None:
        """node_count 30 vs 32 actual, within 10% -> fresh.

        Lower = 32 * 0.90 = 28.8, Upper = 32 * 1.10 = 35.2.
        30 is in [28.8, 35.2] -> fresh.
        """
        facts = {
            "node_count": Fact(name="node_count", value=32, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="node_count",
                value=30,
                file=tmp_path / "README.md",
                line=5,
                context="30 nodes",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "fresh"
        assert result.findings[0].tolerance == 0.10

    def test_default_tolerances_node_count_outside(self, tmp_path: Path) -> None:
        """node_count 20 vs 32 actual, outside 10% -> stale.

        Lower = 32 * 0.90 = 28.8. 20 < 28.8 -> stale.
        """
        facts = {
            "node_count": Fact(name="node_count", value=32, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="node_count",
                value=20,
                file=tmp_path / "README.md",
                line=5,
                context="20 nodes",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "stale"
        assert result.findings[0].tolerance == 0.10

    def test_config_override_tolerance(self, tmp_path: Path) -> None:
        """User sets test_count to 0.10, verify wider tolerance applied.

        test_count 1500 vs 1720 actual.
        Default 5%: Lower = 1634 -> stale.
        Override 10%: Lower = 1548 -> 1500 < 1548 -> still stale.

        Use a case that flips: 1600 vs 1720.
        Default 5%: Lower = 1634 -> stale.
        Override 10%: Lower = 1548 -> 1600 >= 1548 -> fresh.
        """
        facts = {
            "test_count": Fact(name="test_count", value=1720, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=1600,
                file=tmp_path / "README.md",
                line=10,
                context="1600 tests",
            ),
        ]
        # Without override: default 5% -> 1634 lower bound -> 1600 < 1634 -> stale
        result_default = compare_facts(facts, mentions)
        assert result_default.findings[0].status == "stale"
        assert result_default.findings[0].tolerance == 0.05

        # With override: 10% -> 1548 lower bound -> 1600 >= 1548 -> fresh
        result_override = compare_facts(facts, mentions, tolerances={"test_count": 0.10})
        assert result_override.findings[0].status == "fresh"
        assert result_override.findings[0].tolerance == 0.10

    def test_tolerance_stored_in_finding(self, tmp_path: Path) -> None:
        """AuditFinding.tolerance has the correct applied value."""
        facts = {
            "node_count": Fact(name="node_count", value=32, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="node_count",
                value=32,
                file=tmp_path / "README.md",
                line=5,
                context="32 nodes",
            ),
        ]
        result = compare_facts(facts, mentions)
        # Default tolerance for node_count is 0.10
        assert result.findings[0].tolerance == 0.10

    def test_tolerance_zero_means_exact(self, tmp_path: Path) -> None:
        """tolerance=0.0 requires exact match."""
        facts = {
            "mcp_tool_count": Fact(name="mcp_tool_count", value=14, source="MCP server"),
        }
        mentions = [
            Mention(
                fact_name="mcp_tool_count",
                value=13,
                file=tmp_path / "README.md",
                line=42,
                context="13 MCP tools",
            ),
        ]
        result = compare_facts(facts, mentions)
        # mcp_tool_count has default tolerance 0.0 -> exact -> stale
        assert result.findings[0].status == "stale"
        assert result.findings[0].tolerance == 0.0

    def test_tolerance_with_zero_actual(self, tmp_path: Path) -> None:
        """actual=0, mentioned=0 -> fresh (avoid division by zero)."""
        facts = {
            "test_count": Fact(name="test_count", value=0, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=0,
                file=tmp_path / "README.md",
                line=10,
                context="0 tests",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "fresh"

    def test_tolerance_with_zero_actual_nonzero_mentioned(self, tmp_path: Path) -> None:
        """actual=0, mentioned=5 -> stale (even with tolerance)."""
        facts = {
            "test_count": Fact(name="test_count", value=0, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=5,
                file=tmp_path / "README.md",
                line=10,
                context="5 tests",
            ),
        ]
        result = compare_facts(facts, mentions)
        assert result.findings[0].status == "stale"


# ---------------------------------------------------------------------------
# CLI output with tolerance
# ---------------------------------------------------------------------------


class TestCliToleranceOutput:
    """Tests for tolerance display in CLI output."""

    @staticmethod
    def _setup_project(tmp_path: Path) -> Path:
        """Create a project with a node_count mention within tolerance."""
        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )
        # README with node count that is within 10% tolerance of actual
        (proj / "README.md").write_text(
            "# Demo\n\nDemo v3.0.0 is the current release.\n\n"
            "The project has 30 nodes in the architecture graph.\n",
            encoding="utf-8",
        )

        from beadloom.infrastructure.db import create_schema, open_db

        db_path = beadloom_dir / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)

        # Insert 32 nodes so 30 (mentioned) is within 10% tolerance
        for i in range(32):
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source, extra) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"node-{i}", "feature", f"Node {i}", f"src/n{i}.py", "{}"),
            )
        conn.commit()
        conn.close()

        return proj

    def test_cli_shows_tolerance_in_output(self, tmp_path: Path) -> None:
        """Rich output should show tolerance percentage for fresh findings."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "audit", "--project", str(proj)])

        assert result.exit_code == 0, result.output
        # The node_count=30 vs actual=32 should be fresh with tolerance
        # and the output should include the tolerance indicator
        has_tolerance = (
            "tolerance" in result.output.lower()
            or "\u00b15%" in result.output
            or "\u00b110%" in result.output
        )
        assert has_tolerance

    def test_cli_json_includes_tolerance(self, tmp_path: Path) -> None:
        """JSON output should include tolerance field in findings."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        proj = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["docs", "audit", "--json", "--project", str(proj)]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Check that fresh items include tolerance field
        for item in data["fresh"]:
            assert "tolerance" in item


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


class TestConfigIntegration:
    """Tests for tolerance loading from config.yml."""

    @staticmethod
    def _setup_project_with_config(tmp_path: Path, tolerances: dict[str, float]) -> Path:
        """Create a project with config.yml tolerance overrides."""
        import yaml

        proj = tmp_path / "proj"
        proj.mkdir()
        beadloom_dir = proj / ".beadloom"
        beadloom_dir.mkdir()
        (proj / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "3.0.0"\n',
            encoding="utf-8",
        )

        # Write config.yml with tolerance overrides
        config_data = {
            "languages": [".py"],
            "scan_paths": ["src"],
            "docs_audit": {
                "tolerances": tolerances,
            },
        }
        (beadloom_dir / "config.yml").write_text(
            yaml.dump(config_data, default_flow_style=False),
            encoding="utf-8",
        )

        (proj / "README.md").write_text(
            "# Demo\n\nDemo v3.0.0 is the current release.\n\n"
            "We run 1600 tests in our CI pipeline.\n",
            encoding="utf-8",
        )

        from beadloom.infrastructure.db import create_schema, open_db

        db_path = beadloom_dir / "beadloom.db"
        conn = open_db(db_path)
        create_schema(conn)

        # Insert a node with test_count=1720
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) "
            "VALUES (?, ?, ?, ?, ?)",
            ("test-node", "feature", "Test", "src/test.py",
             json.dumps({"tests": {"test_count": 1720, "framework": "pytest"}})),
        )
        conn.commit()
        conn.close()

        return proj

    def test_run_audit_loads_tolerances_from_config(self, tmp_path: Path) -> None:
        """run_audit should load tolerances from config.yml and apply them."""
        from beadloom.doc_sync.audit import run_audit
        from beadloom.infrastructure.db import open_db

        # With default 5% tolerance: 1600 vs 1720 -> stale (lower=1634)
        # With config 10% tolerance: 1600 vs 1720 -> fresh (lower=1548)
        proj = self._setup_project_with_config(tmp_path, {"test_count": 0.10})

        db_path = proj / ".beadloom" / "beadloom.db"
        conn = open_db(db_path)
        try:
            result = run_audit(proj, conn)
        finally:
            conn.close()

        test_findings = [
            f for f in result.findings if f.mention.fact_name == "test_count"
        ]
        assert len(test_findings) >= 1
        # With 10% tolerance, 1600 vs 1720 should be fresh
        assert test_findings[0].status == "fresh"
        assert test_findings[0].tolerance == 0.10


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestToleranceEdgeCases:
    """Edge cases for the tolerance system."""

    def test_large_tolerance_100pct_everything_fresh(self, tmp_path: Path) -> None:
        """tolerance=1.0 (100%) means everything is within range."""
        facts = {
            "node_count": Fact(name="node_count", value=100, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="node_count",
                value=5,
                file=tmp_path / "README.md",
                line=1,
                context="5 nodes",
            ),
        ]
        # 100% tolerance: lower=0, upper=200 -> 5 is in range -> fresh
        result = compare_facts(facts, mentions, tolerances={"node_count": 1.0})
        assert result.findings[0].status == "fresh"
        assert result.findings[0].tolerance == 1.0

    def test_large_tolerance_mentioned_far_above(self, tmp_path: Path) -> None:
        """tolerance=1.0 with mentioned value 2x actual -> within range."""
        facts = {
            "test_count": Fact(name="test_count", value=100, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=200,
                file=tmp_path / "README.md",
                line=1,
                context="200 tests",
            ),
        ]
        # 100% tolerance: lower=0, upper=200 -> 200 is in range -> fresh
        result = compare_facts(facts, mentions, tolerances={"test_count": 1.0})
        assert result.findings[0].status == "fresh"

    def test_large_tolerance_mentioned_above_upper(self, tmp_path: Path) -> None:
        """tolerance=1.0 with mentioned value 3x actual -> outside."""
        facts = {
            "test_count": Fact(name="test_count", value=100, source="graph DB"),
        }
        mentions = [
            Mention(
                fact_name="test_count",
                value=201,
                file=tmp_path / "README.md",
                line=1,
                context="201 tests",
            ),
        ]
        # 100% tolerance: upper=200 -> 201 > 200 -> stale
        result = compare_facts(facts, mentions, tolerances={"test_count": 1.0})
        assert result.findings[0].status == "stale"
