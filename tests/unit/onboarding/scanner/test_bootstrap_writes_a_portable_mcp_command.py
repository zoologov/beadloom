"""`init --bootstrap` writes a command every clone can start (BDL-083 S2h, BDL-UX #356 e).

The second writer of the same defect `setup-mcp` had: measured on 9.0.0,
`init --bootstrap` wrote `shutil.which("beadloom")` into `.mcp.json` before
`setup-mcp` was ever run, so a committed config held one machine's absolute
path to the binary.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING

from beadloom.onboarding.scanner import MCP_SERVER_COMMAND, setup_mcp_auto

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_the_command_is_beadloom_on_path_not_an_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "somebody" / "bin"
    bin_dir.mkdir(parents=True)
    binary = bin_dir / "beadloom"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir))
    project = tmp_path / "proj"
    project.mkdir()

    assert setup_mcp_auto(project) == "claude-code"

    data = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
    assert data["mcpServers"]["beadloom"]["command"] == MCP_SERVER_COMMAND == "beadloom"
