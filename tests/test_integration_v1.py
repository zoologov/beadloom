# beadloom:domain=linter
"""Integration tests for v1.0 release — self-lint, version, graph completeness."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from beadloom import __version__
from beadloom.services.cli import main

# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestVersion:
    """Verify version is 1.1.0."""

    def test_version_string(self) -> None:
        assert __version__ == "1.1.0"

    def test_cli_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "1.1.0" in result.output


class TestGraphCompleteness:
    """Verify the knowledge graph has the DDD domain structure."""

    def test_graph_has_domain_nodes(self) -> None:
        graph_path = _PROJECT_ROOT / ".beadloom" / "_graph" / "services.yml"
        data = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        ref_ids = {n["ref_id"] for n in data["nodes"]}
        # All 5 DDD domains must be present
        for domain in ("context-oracle", "doc-sync", "graph", "onboarding", "infrastructure"):
            assert domain in ref_ids, f"Missing domain: {domain}"
        # Rule engine feature (was "linter" domain)
        assert "rule-engine" in ref_ids

    def test_graph_domain_edges(self) -> None:
        graph_path = _PROJECT_ROOT / ".beadloom" / "_graph" / "services.yml"
        data = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        edges = data["edges"]
        # graph domain part_of beadloom
        assert any(
            e["src"] == "graph" and e["dst"] == "beadloom" and e["kind"] == "part_of"
            for e in edges
        )
        # cli uses graph
        assert any(
            e["src"] == "cli" and e["dst"] == "graph" and e["kind"] == "uses" for e in edges
        )

    def test_rules_yml_exists(self) -> None:
        rules_path = _PROJECT_ROOT / ".beadloom" / "_graph" / "rules.yml"
        assert rules_path.is_file()
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert len(data["rules"]) >= 1


class TestSelfLint:
    """Run beadloom lint on its own codebase."""

    def test_self_lint_clean(self) -> None:
        """Self-lint should produce 0 violations."""
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--project", str(_PROJECT_ROOT), "--format", "json"])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["summary"]["violations_count"] == 0
        assert parsed["summary"]["rules_evaluated"] >= 1

    def test_self_lint_strict(self) -> None:
        """Self-lint with --strict should also exit 0 (no violations)."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["lint", "--project", str(_PROJECT_ROOT), "--strict", "--format", "json"],
        )
        assert result.exit_code == 0, result.output
