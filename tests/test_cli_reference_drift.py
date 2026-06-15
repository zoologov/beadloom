"""CLI-level tests for BDL-057 Layer 2 reference surface-drift.

Exercises `beadloom sync-check` (warning, exit 0, JSON `references`) and
`beadloom sync-update <doc> --yes` (clears the warning) end-to-end, and asserts
the symbol-pair output is not masked by the additive reference reporting.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _build_project(tmp_path: Path, *, watches: str = "graph") -> Path:
    """A project whose architecture.md watches a surface; fully reindexed."""
    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "graph.yml").write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                ],
            }
        )
    )

    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text(
        f"<!-- beadloom:watches={watches} -->\n# Architecture\nOverview prose.\n"
    )

    from beadloom.application.reindex import reindex

    reindex(project)
    return project


def _mutate_graph(project: Path) -> None:
    """Add a node to the graph YAML and reindex (incremental) -> surface drift."""
    graph_file = project / ".beadloom" / "_graph" / "graph.yml"
    graph_file.write_text(
        yaml.dump(
            {
                "nodes": [
                    {"ref_id": "F1", "kind": "feature", "summary": "Feature 1"},
                    {"ref_id": "F2", "kind": "feature", "summary": "Feature 2"},
                ],
            }
        )
    )
    from beadloom.application.reindex import incremental_reindex

    incremental_reindex(project)


def test_sync_check_clean_no_drift(tmp_path: Path) -> None:
    project = _build_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["sync-check", "--project", str(project)])
    assert result.exit_code == 0
    assert "surface drift" not in result.output


def test_sync_check_warns_on_drift_but_exit_zero(tmp_path: Path) -> None:
    project = _build_project(tmp_path)
    _mutate_graph(project)
    runner = CliRunner()
    result = runner.invoke(main, ["sync-check", "--project", str(project)])
    # Surface drift is advisory: warning shown, exit code stays 0.
    assert result.exit_code == 0
    assert "surface drift" in result.output
    assert "docs/architecture.md" in result.output


def test_sync_check_json_reports_reference_drift(tmp_path: Path) -> None:
    project = _build_project(tmp_path)
    _mutate_graph(project)
    runner = CliRunner()
    result = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["summary"]["surface_drift"] == 1
    refs = data["references"]
    assert len(refs) == 1
    assert refs[0]["doc_path"] == "docs/architecture.md"
    assert refs[0]["status"] == "surface_drift"
    assert refs[0]["reason"] == "surface_drift"
    assert refs[0]["severity"] == "warning"
    # Symbol-pair `pairs` array is still present and unmasked.
    assert "pairs" in data


def test_sync_update_clears_surface_drift(tmp_path: Path) -> None:
    project = _build_project(tmp_path)
    _mutate_graph(project)
    runner = CliRunner()

    update = runner.invoke(
        main,
        ["sync-update", "docs/architecture.md", "--yes", "--project", str(project)],
    )
    assert update.exit_code == 0
    assert "reference doc" in update.output.lower()

    after = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
    data = json.loads(after.output)
    assert data["summary"]["surface_drift"] == 0
    assert data["references"][0]["status"] == "ok"


def test_sync_update_all_clears_surface_drift(tmp_path: Path) -> None:
    project = _build_project(tmp_path)
    _mutate_graph(project)
    runner = CliRunner()
    update = runner.invoke(
        main, ["sync-update", "--all", "--yes", "--project", str(project)]
    )
    assert update.exit_code == 0

    after = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
    data = json.loads(after.output)
    assert data["summary"]["surface_drift"] == 0


def test_no_reference_docs_is_noop(tmp_path: Path) -> None:
    project = _build_project(tmp_path, watches="")  # no annotation written
    # Overwrite the doc without any annotation.
    (project / "docs" / "architecture.md").write_text("# Architecture\nPlain.\n")
    from beadloom.application.reindex import reindex

    reindex(project)
    runner = CliRunner()
    result = runner.invoke(main, ["sync-check", "--json", "--project", str(project)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["references"] == []
    assert data["summary"]["surface_drift"] == 0
