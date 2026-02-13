"""Tests for `beadloom status` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
    import yaml

    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                    {"ref_id": "F2", "kind": "feature", "summary": "Feature 2"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing"},
                ],
                "edges": [
                    {"src": "F1", "dst": "routing", "kind": "part_of"},
                    {"src": "F2", "dst": "routing", "kind": "part_of"},
                ],
            }
        )
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "f1.md").write_text("## Spec\n\nFeature 1 spec.\n")

    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "api.py").write_text("# beadloom:feature=F1\ndef handler():\n    pass\n")

    from beadloom.infrastructure.reindex import reindex

    reindex(project)
    return project


class TestStatusCommand:
    def test_status_output(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "node" in result.output.lower() or "total" in result.output.lower()

    def test_status_shows_counts(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
        # Should show node/edge/doc counts.
        assert "3" in result.output  # 3 nodes
        assert "2" in result.output  # 2 edges

    def test_status_no_db(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code != 0

    def test_status_empty_project(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / "docs").mkdir()
        (project / "src").mkdir()

        from beadloom.infrastructure.reindex import reindex

        reindex(project)
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--project", str(project)])
        assert result.exit_code == 0, result.output
