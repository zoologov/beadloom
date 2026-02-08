"""Tests for `beadloom ctx` CLI command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project with graph, docs, and code for ctx testing."""
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    # Graph.
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features.yml").write_text(
        yaml.dump({
            "nodes": [
                {"ref_id": "PROJ-1", "kind": "feature", "summary": "Track filtering"},
                {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
            ],
            "edges": [
                {"src": "PROJ-1", "dst": "routing", "kind": "part_of"},
            ],
        })
    )

    # Docs.
    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "spec.md").write_text("## Specification\n\nTrack filtering rules.\n")

    # Source.
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text(
        "# beadloom:feature=PROJ-1\n" "def list_tracks():\n    pass\n"
    )

    # Reindex to populate DB.
    from beadloom.reindex import reindex

    reindex(project)
    return project


class TestCtxCommand:
    def test_ctx_json_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["version"] == 1
        assert data["focus"]["ref_id"] == "PROJ-1"

    def test_ctx_markdown_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Should contain focus node info.
        assert "PROJ-1" in result.output

    def test_ctx_multiple_ref_ids(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "routing", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        node_ids = {n["ref_id"] for n in data["graph"]["nodes"]}
        assert "PROJ-1" in node_ids
        assert "routing" in node_ids

    def test_ctx_depth_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--depth", "1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["version"] == 1

    def test_ctx_max_nodes_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--max-nodes", "5", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_ctx_max_chunks_flag(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--max-chunks", "3", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_ctx_not_found(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "NONEXISTENT", "--project", str(project)])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_ctx_no_db(self, tmp_path: Path) -> None:
        """Running ctx without reindex should produce an error."""
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code != 0

    def test_ctx_markdown_flag_explicit(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["ctx", "PROJ-1", "--markdown", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert "PROJ-1" in result.output
