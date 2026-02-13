"""Tests for beadloom docs CLI commands (generate + polish)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def _setup_graph(tmp_path: Path) -> None:
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    data = {
        "nodes": [
            {"ref_id": "myproj", "kind": "service", "summary": "Root: myproj", "source": ""},
            {
                "ref_id": "auth",
                "kind": "domain",
                "summary": "Domain: auth (3 files)",
                "source": "src/auth/",
            },
            {
                "ref_id": "auth-api",
                "kind": "feature",
                "summary": "Feature: api (1 file)",
                "source": "src/auth/api/",
            },
        ],
        "edges": [
            {"src": "auth", "dst": "myproj", "kind": "part_of"},
            {"src": "auth-api", "dst": "auth", "kind": "part_of"},
        ],
    }
    (graph_dir / "services.yml").write_text(
        yaml.dump(data, default_flow_style=False),
        encoding="utf-8",
    )


class TestDocsGenerate:
    """Tests for ``beadloom docs generate``."""

    def test_docs_generate_creates_files(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Created" in result.output
        assert (tmp_path / "docs" / "architecture.md").exists()

    def test_docs_generate_skips_existing(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "architecture.md").write_text("existing content", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "skipped" in result.output

    def test_docs_generate_no_graph(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])

        # Graceful: exits 0 even with no graph YAML.
        # architecture.md is always created (with empty tables).
        assert result.exit_code == 0, result.output
        assert "Created" in result.output

    def test_docs_generate_idempotent(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        runner = CliRunner()

        # First run: creates files.
        result1 = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])
        assert result1.exit_code == 0, result1.output
        assert "Created" in result1.output

        # Second run: all files already exist.
        result2 = runner.invoke(main, ["docs", "generate", "--project", str(tmp_path)])
        assert result2.exit_code == 0, result2.output
        assert "Created 0 files" in result2.output
        assert "skipped" in result2.output


class TestDocsPolish:
    """Tests for ``beadloom docs polish``."""

    def test_docs_polish_text_format(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["docs", "polish", "--project", str(tmp_path)])

        assert result.exit_code == 0, result.output
        # Default format is text — outputs the instructions string.
        assert "enriching documentation" in result.output

    def test_docs_polish_json_format(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["docs", "polish", "--format", "json", "--project", str(tmp_path)]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "nodes" in data
        assert "architecture" in data
        assert "instructions" in data

    def test_docs_polish_single_ref_id(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        _setup_graph(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["docs", "polish", "--format", "json", "--ref-id", "auth", "--project", str(tmp_path)],
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["ref_id"] == "auth"

    def test_docs_polish_no_graph(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main, ["docs", "polish", "--format", "json", "--project", str(tmp_path)]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["nodes"] == []
