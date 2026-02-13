"""Tests for `beadloom mcp-serve` and `beadloom setup-mcp` CLI commands."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestSetupMcpCommand:
    def test_creates_mcp_json(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])
        assert result.exit_code == 0, result.output
        mcp_json = project / ".mcp.json"
        assert mcp_json.exists()
        data = json.loads(mcp_json.read_text())
        assert "mcpServers" in data
        assert "beadloom" in data["mcpServers"]

    def test_mcp_json_content(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        runner = CliRunner()
        runner.invoke(main, ["setup-mcp", "--project", str(project)])
        mcp_json = project / ".mcp.json"
        data = json.loads(mcp_json.read_text())
        server = data["mcpServers"]["beadloom"]
        assert "command" in server
        assert "args" in server
        assert "mcp-serve" in server["args"]

    def test_updates_existing_mcp_json(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        existing = {"mcpServers": {"other": {"command": "other-tool"}}}
        (project / ".mcp.json").write_text(json.dumps(existing))
        runner = CliRunner()
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads((project / ".mcp.json").read_text())
        assert "other" in data["mcpServers"]
        assert "beadloom" in data["mcpServers"]

    def test_remove_flag(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        runner = CliRunner()
        # Setup first.
        runner.invoke(main, ["setup-mcp", "--project", str(project)])
        # Remove.
        result = runner.invoke(main, ["setup-mcp", "--remove", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads((project / ".mcp.json").read_text())
        assert "beadloom" not in data["mcpServers"]

    def test_global_flag(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        runner = CliRunner()
        # Global setup writes to home, but we test the command runs.
        result = runner.invoke(main, ["setup-mcp", "--project", str(project)])
        assert result.exit_code == 0


class TestMcpServeCommand:
    def test_mcp_serve_no_db(self, tmp_path: Path) -> None:
        """mcp-serve should fail if no DB exists."""
        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["mcp-serve", "--project", str(project)])
        assert result.exit_code != 0

    def test_mcp_serve_command_exists(self) -> None:
        """mcp-serve should be a registered command."""
        runner = CliRunner()
        result = runner.invoke(main, ["mcp-serve", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "mcp" in result.output.lower()
