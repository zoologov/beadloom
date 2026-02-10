"""Tests for `beadloom why` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project with graph and docs for why testing."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    # Graph.
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "PROJ-1", "kind": "feature", "summary": "Track filtering"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                    {"ref_id": "api-gw", "kind": "service", "summary": "API Gateway"},
                ],
                "edges": [
                    {"src": "PROJ-1", "dst": "routing", "kind": "part_of"},
                    {"src": "PROJ-1", "dst": "api-gw", "kind": "uses"},
                ],
            }
        )
    )

    # Docs.
    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    # Source.
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=PROJ-1\ndef list_tracks():\n    pass\n")

    # Reindex to populate DB.
    from beadloom.reindex import reindex

    reindex(project)
    return project


class TestCliWhy:
    def test_cli_why_basic(self, tmp_path: Path) -> None:
        """`beadloom why <ref>` outputs Rich format."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["why", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "PROJ-1" in result.output

    def test_cli_why_json(self, tmp_path: Path) -> None:
        """`beadloom why <ref> --json` outputs valid JSON."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["why", "PROJ-1", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["node"]["ref_id"] == "PROJ-1"
        assert "upstream" in data
        assert "downstream" in data
        assert "impact" in data

    def test_cli_why_depth(self, tmp_path: Path) -> None:
        """`beadloom why <ref> --depth 1` respects depth."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["why", "PROJ-1", "--depth", "1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["node"]["ref_id"] == "PROJ-1"

    def test_cli_why_not_found(self, tmp_path: Path) -> None:
        """Proper error message for nonexistent ref."""
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["why", "NONEXISTENT", "--project", str(project)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_cli_why_no_db(self, tmp_path: Path) -> None:
        """Error when database doesn't exist."""
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["why", "PROJ-1", "--project", str(project)])
        assert result.exit_code != 0
        assert "database not found" in result.output.lower() or "error" in result.output.lower()
