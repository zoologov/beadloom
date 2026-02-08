"""Tests for `beadloom graph` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a project with a small graph."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump({
            "nodes": [
                {"ref_id": "FEAT-1", "kind": "feature", "summary": "Feature one"},
                {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                {"ref_id": "api-gw", "kind": "service", "summary": "API Gateway"},
            ],
            "edges": [
                {"src": "FEAT-1", "dst": "routing", "kind": "part_of"},
                {"src": "FEAT-1", "dst": "api-gw", "kind": "uses"},
            ],
        })
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    src_dir = project / "src"
    src_dir.mkdir()

    from beadloom.reindex import reindex

    reindex(project)
    return project


class TestGraphCommand:
    def test_mermaid_output_default(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "-->" in result.output

    def test_mermaid_with_ref_id(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "FEAT-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "FEAT-1" in result.output

    def test_json_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "nodes" in data
        assert "edges" in data

    def test_json_with_ref_id(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "FEAT-1", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        node_ids = {n["ref_id"] for n in data["nodes"]}
        assert "FEAT-1" in node_ids

    def test_depth_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["graph", "FEAT-1", "--depth", "1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_no_db(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "--project", str(project)])
        assert result.exit_code != 0

    def test_mermaid_contains_edges(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["graph", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Mermaid edges use --> syntax
        assert "-->" in result.output
