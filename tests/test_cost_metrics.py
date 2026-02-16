"""Tests for context cost metrics — estimate_tokens and status command metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.context_oracle.builder import estimate_tokens
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# estimate_tokens unit tests
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_short_string(self) -> None:
        # 12 chars / 4 = 3
        assert estimate_tokens("Hello World!") == 3

    def test_known_length(self) -> None:
        # 100 chars / 4 = 25
        text = "a" * 100
        assert estimate_tokens(text) == 25

    def test_rough_approximation(self) -> None:
        # Typical prose: ~4 chars per token is a rough estimate
        text = "The quick brown fox jumps over the lazy dog."
        result = estimate_tokens(text)
        assert result == len(text) // 4

    def test_large_text(self) -> None:
        text = "x" * 10000
        assert estimate_tokens(text) == 2500

    def test_unicode_text(self) -> None:
        # Unicode characters still count by char length
        text = "Hello" * 20  # 100 chars
        assert estimate_tokens(text) == 25


# ---------------------------------------------------------------------------
# Status command with Context Metrics section
# ---------------------------------------------------------------------------


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project structure with indexed data."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "AUTH", "kind": "domain", "summary": "Authentication domain"},
                    {"ref_id": "CORE", "kind": "domain", "summary": "Core domain"},
                    {
                        "ref_id": "login",
                        "kind": "feature",
                        "summary": "Login feature",
                        "docs": ["docs/login.md"],
                    },
                ],
                "edges": [
                    {"src": "login", "dst": "AUTH", "kind": "part_of"},
                    {"src": "AUTH", "dst": "CORE", "kind": "depends_on"},
                ],
            }
        )
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "login.md").write_text("## Spec\n\nLogin specification.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "auth.py").write_text("# beadloom:domain=AUTH\ndef login():\n    pass\n")

    from beadloom.infrastructure.reindex import reindex

    reindex(project)
    return project


class TestStatusContextMetrics:
    def test_status_shows_context_metrics(self, tmp_path: Path) -> None:
        """Status output includes Context Metrics section."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "Context Metrics" in result.output

    def test_status_shows_avg_bundle(self, tmp_path: Path) -> None:
        """Status output includes average bundle size."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "Avg bundle" in result.output
        assert "tokens" in result.output

    def test_status_shows_largest_bundle(self, tmp_path: Path) -> None:
        """Status output includes largest bundle info."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "Largest bundle" in result.output

    def test_status_shows_total_indexed(self, tmp_path: Path) -> None:
        """Status output includes total indexed symbols."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "Total indexed" in result.output
        assert "symbols" in result.output.lower()

    def test_status_json_includes_context_metrics(self, tmp_path: Path) -> None:
        """JSON status output includes context_metrics field."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output

        import json

        data = json.loads(result.output)
        assert "context_metrics" in data
        metrics = data["context_metrics"]
        assert "avg_bundle_tokens" in metrics
        assert "largest_bundle_tokens" in metrics
        assert "largest_bundle_ref_id" in metrics
        assert "total_symbols" in metrics

    def test_status_json_metrics_types(self, tmp_path: Path) -> None:
        """JSON metrics have correct types."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output

        import json

        data = json.loads(result.output)
        metrics = data["context_metrics"]
        assert isinstance(metrics["avg_bundle_tokens"], int)
        assert isinstance(metrics["largest_bundle_tokens"], int)
        assert isinstance(metrics["largest_bundle_ref_id"], str)
        assert isinstance(metrics["total_symbols"], int)
