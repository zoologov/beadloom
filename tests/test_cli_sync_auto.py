"""Tests for `beadloom sync-update --auto` (LLM integration)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump({
            "nodes": [
                {
                    "ref_id": "F1",
                    "kind": "feature",
                    "summary": "Feature 1",
                    "docs": ["docs/spec.md"],
                },
            ],
        })
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Spec\n\nFeature spec.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text(
        "# beadloom:feature=F1\ndef handler():\n    pass\n"
    )

    from beadloom.reindex import reindex

    reindex(project)
    return project


class TestSyncUpdateAuto:
    def test_auto_without_config_errors(self, tmp_path: Path) -> None:
        """--auto should fail if no LLM config is present."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--auto", "--project", str(project)]
        )
        assert result.exit_code != 0
        assert "llm" in result.output.lower() or "config" in result.output.lower()

    def test_auto_with_config_but_no_key(self, tmp_path: Path) -> None:
        """--auto with LLM config but no API key should error gracefully."""
        project = _setup_project(tmp_path)
        config = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "api_key_env": "BEADLOOM_TEST_NO_SUCH_KEY",
            }
        }
        (project / ".beadloom" / "config.yml").write_text(
            yaml.dump(config), encoding="utf-8"
        )
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync-update", "F1", "--auto", "--project", str(project)]
        )
        # Should error about missing API key, not crash.
        assert result.exit_code != 0
        assert "api" in result.output.lower() or "key" in result.output.lower()
