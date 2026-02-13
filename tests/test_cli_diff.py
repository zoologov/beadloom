"""Tests for `beadloom diff` CLI command."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_GIT_ENV,
    )


def _setup_git_project(tmp_path: Path) -> Path:
    """Create a git repo with initial graph YAML committed."""
    project = tmp_path / "proj"
    project.mkdir()

    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)

    yaml_content = yaml.dump(
        {
            "nodes": [
                {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                {"ref_id": "user-service", "kind": "service", "summary": "User management"},
            ],
            "edges": [
                {"src": "auth-login", "dst": "user-service", "kind": "uses"},
            ],
        }
    )
    (graph_dir / "test.yml").write_text(yaml_content)

    _git(project, "init")
    _git(project, "add", ".")
    _git(project, "commit", "-m", "initial")

    return project


class TestCliDiffBasic:
    def test_cli_diff_basic(self, tmp_path: Path) -> None:
        """beadloom diff works with default HEAD."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "No graph changes" in result.output


class TestCliDiffSince:
    def test_cli_diff_since(self, tmp_path: Path) -> None:
        """beadloom diff --since=HEAD works."""
        project = _setup_git_project(tmp_path)

        # Make a second commit with changes
        graph_dir = project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                    {"ref_id": "new-svc", "kind": "service", "summary": "New service"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)
        _git(project, "add", ".")
        _git(project, "commit", "-m", "add new-svc")

        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--since", "HEAD~1", "--project", str(project)])
        # exit code 1 = changes detected
        assert result.exit_code == 1, result.output
        assert "new-svc" in result.output


class TestCliDiffJson:
    def test_cli_diff_json(self, tmp_path: Path) -> None:
        """beadloom diff --json outputs valid JSON."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "since_ref" in data
        assert "nodes" in data
        assert "edges" in data
        assert data["has_changes"] is False


class TestCliDiffExitCodes:
    def test_cli_diff_exit_code_no_changes(self, tmp_path: Path) -> None:
        """Exit code 0 when no changes."""
        project = _setup_git_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--project", str(project)])
        assert result.exit_code == 0

    def test_cli_diff_exit_code_with_changes(self, tmp_path: Path) -> None:
        """Exit code 1 when changes detected."""
        project = _setup_git_project(tmp_path)

        # Add a node on disk (uncommitted change)
        graph_dir = project / ".beadloom" / "_graph"
        yaml_content = yaml.dump(
            {
                "nodes": [
                    {"ref_id": "auth-login", "kind": "feature", "summary": "User authentication"},
                    {"ref_id": "user-service", "kind": "service", "summary": "User management"},
                    {"ref_id": "extra", "kind": "feature", "summary": "Extra feature"},
                ],
                "edges": [
                    {"src": "auth-login", "dst": "user-service", "kind": "uses"},
                ],
            }
        )
        (graph_dir / "test.yml").write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--project", str(project)])
        assert result.exit_code == 1


class TestCliDiffNoGraphDir:
    def test_cli_diff_no_graph_dir(self, tmp_path: Path) -> None:
        """Error when .beadloom/_graph/ doesn't exist."""
        project = tmp_path / "empty"
        project.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--project", str(project)])
        assert result.exit_code == 1
        assert "graph directory not found" in result.output
