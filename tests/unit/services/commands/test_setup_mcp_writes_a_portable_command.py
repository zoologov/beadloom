"""`setup-mcp` writes a command every clone can start (BDL-083 S2h, RFC D13, BDL-UX #356 e).

Measured on 9.0.0: `setup-mcp` wrote `shutil.which("beadloom")`, so the committed
`.cursor/mcp.json` held one machine's absolute path to the binary and the MCP
server could not start from it on a teammate's machine. The composed
instructions already assume `beadloom` on PATH; the generated file now says the
same, whatever PATH holds on the machine that wrote it.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _path_with_beadloom(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "somebody" / "bin"
    bin_dir.mkdir(parents=True)
    binary = bin_dir / "beadloom"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def _path_without_beadloom(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "empty-bin"
    bin_dir.mkdir()
    return bin_dir


def _setup_mcp(tmp_path: Path, tool: str) -> tuple[dict[str, object], str]:
    project = tmp_path / "proj"
    project.mkdir(exist_ok=True)
    result = CliRunner().invoke(main, ["setup-mcp", "--tool", tool, "--project", str(project)])
    assert result.exit_code == 0, result.output
    relpath = ".mcp.json" if tool == "claude-code" else ".cursor/mcp.json"
    data = json.loads((project / relpath).read_text(encoding="utf-8"))
    server: dict[str, object] = data["mcpServers"]["beadloom"]
    return server, result.output


@pytest.mark.parametrize("tool", ["claude-code", "cursor"])
def test_the_command_is_beadloom_on_path_not_an_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    monkeypatch.setenv("PATH", str(_path_with_beadloom(tmp_path)))
    server, _ = _setup_mcp(tmp_path, tool)
    assert server["command"] == "beadloom"
    assert server["args"] == ["mcp-serve"]


def test_the_file_is_the_same_bytes_with_and_without_beadloom_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setenv("PATH", str(_path_with_beadloom(tmp_path)))
    with_binary, _ = _setup_mcp(first, "cursor")
    monkeypatch.setenv("PATH", str(_path_without_beadloom(tmp_path)))
    without_binary, _ = _setup_mcp(second, "cursor")
    assert with_binary == without_binary


def test_a_path_without_beadloom_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(_path_without_beadloom(tmp_path)))
    server, output = _setup_mcp(tmp_path, "cursor")
    assert server["command"] == "beadloom"
    assert "`beadloom` is not on PATH" in output
