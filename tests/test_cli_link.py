"""Tests for `beadloom link` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import _detect_link_label, main

if TYPE_CHECKING:
    from pathlib import Path


def _setup_project(tmp_path: Path) -> Path:
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
                ],
            }
        )
    )
    return project


class TestDetectLinkLabel:
    def test_github_issue(self) -> None:
        assert _detect_link_label("https://github.com/org/repo/issues/42") == "github"

    def test_github_pr(self) -> None:
        assert _detect_link_label("https://github.com/org/repo/pull/99") == "github-pr"

    def test_jira_atlassian(self) -> None:
        assert _detect_link_label("https://company.atlassian.net/browse/AUTH-42") == "jira"

    def test_jira_self_hosted(self) -> None:
        assert _detect_link_label("https://jira.company.com/browse/AUTH-42") == "jira"

    def test_linear(self) -> None:
        assert _detect_link_label("https://linear.app/team/issue/ENG-123") == "linear"

    def test_unknown(self) -> None:
        assert _detect_link_label("https://example.com/something") == "link"


class TestLinkCommand:
    def test_add_link(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "F1", "https://github.com/org/repo/issues/42", "--project", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        assert "github" in result.output

        # Verify YAML was updated.
        graph_file = project / ".beadloom" / "_graph" / "graph.yml"
        data = yaml.safe_load(graph_file.read_text())
        node = data["nodes"][0]
        assert "links" in node
        assert node["links"][0]["url"] == "https://github.com/org/repo/issues/42"

    def test_add_link_with_label(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "link",
                "F1",
                "https://example.com/ticket/1",
                "--label",
                "custom",
                "--project",
                str(project),
            ],
        )
        assert result.exit_code == 0
        assert "custom" in result.output

    def test_list_links_empty(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["link", "F1", "--project", str(project)])
        assert result.exit_code == 0
        assert "No links" in result.output

    def test_list_links(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        # Add a link first.
        runner.invoke(
            main,
            ["link", "F1", "https://github.com/org/repo/issues/42", "--project", str(project)],
        )
        # List.
        result = runner.invoke(main, ["link", "F1", "--project", str(project)])
        assert result.exit_code == 0
        assert "github" in result.output
        assert "issues/42" in result.output

    def test_remove_link(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        url = "https://github.com/org/repo/issues/42"
        # Add.
        runner.invoke(main, ["link", "F1", url, "--project", str(project)])
        # Remove.
        result = runner.invoke(main, ["link", "F1", "--remove", url, "--project", str(project)])
        assert result.exit_code == 0
        assert "Removed" in result.output

        # Verify YAML was updated.
        graph_file = project / ".beadloom" / "_graph" / "graph.yml"
        data = yaml.safe_load(graph_file.read_text())
        node = data["nodes"][0]
        assert "links" not in node

    def test_duplicate_link(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        url = "https://github.com/org/repo/issues/42"
        runner.invoke(main, ["link", "F1", url, "--project", str(project)])
        result = runner.invoke(main, ["link", "F1", url, "--project", str(project)])
        assert "already exists" in result.output

    def test_remove_nonexistent_link(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "F1", "--remove", "https://nope.com", "--project", str(project)],
        )
        assert "not found" in result.output

    def test_node_not_found(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "NONEXISTENT", "https://example.com", "--project", str(project)],
        )
        assert result.exit_code != 0

    def test_no_graph_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["link", "F1", "https://example.com", "--project", str(project)],
        )
        assert result.exit_code != 0
