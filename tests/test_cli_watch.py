"""Tests for `beadloom watch` CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCliWatchNoWatchfiles:
    def test_cli_watch_no_watchfiles(self, tmp_path: Path) -> None:
        """Graceful error when watchfiles is not installed."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)

        runner = CliRunner()

        # Simulate ImportError when CLI tries to import beadloom.infrastructure.watcher
        with patch.dict("sys.modules", {"beadloom.infrastructure.watcher": None}):
            result = runner.invoke(main, ["watch", "--project", str(tmp_path)])
            assert result.exit_code != 0
            assert "watchfiles" in result.output or "Error" in result.output


class TestCliWatchHelp:
    def test_cli_watch_help(self) -> None:
        """`beadloom watch --help` works and shows usage."""
        runner = CliRunner()
        result = runner.invoke(main, ["watch", "--help"])
        assert result.exit_code == 0
        assert "Watch files and auto-reindex" in result.output
        assert "--debounce" in result.output
        assert "--project" in result.output


class TestCliWatchNoGraphDir:
    def test_cli_watch_no_graph_dir(self, tmp_path: Path) -> None:
        """Error when .beadloom/_graph/ doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(main, ["watch", "--project", str(tmp_path)])
        assert result.exit_code != 0
        assert "graph directory not found" in result.output
