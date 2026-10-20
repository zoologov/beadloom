"""``config-check`` on a project whose second tool reads fewer layers (BDL-UX #356 a, RFC D13).

The adopter's teammate ran the flow on Cursor, and Cursor read the five role files and a
17-line pointer: no core, no project layer, no commands. On 9.0.0 ``config-check`` exited 0
over that project, because it compared no layer across the tools a flow declares. Measured
on the monorepo fixture composed by 9.0.0 for both tools: 9.0.0 exits 0, this release exits 1
with "`cursor` lacks 8 layer(s) `claude` reads".

The project is composed through ``setup-agentic-flow`` and judged through ``config-check``,
both by their command lines, so the file collects against 9.0.0 and fails there on the exit
code it asserts. Removing the Cursor rules gives the layout 9.0.0 wrote, less its pointer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner, Result

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _composed_for_both_tools(tmp_path: Path) -> Path:
    root = tmp_path / "acme"
    (root / ".beadloom").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    composed = CliRunner().invoke(
        main,
        ["setup-agentic-flow", "--tool", "claude", "--tool", "cursor", "--project", str(root)],
    )
    assert composed.exit_code == 0, composed.output
    return root


def _without_the_cursor_rules(root: Path) -> Path:
    for rule in (root / ".cursor" / "rules").iterdir():
        if rule.is_file():
            rule.unlink()
    return root


def _config_check(root: Path) -> Result:
    return CliRunner().invoke(main, ["config-check", "--project", str(root)])


def test_a_project_composed_for_both_tools_passes(tmp_path: Path) -> None:
    root = _composed_for_both_tools(tmp_path)

    result = _config_check(root)

    assert result.exit_code == 0, result.output


def test_cursor_reading_fewer_layers_than_claude_exits_1(tmp_path: Path) -> None:
    root = _without_the_cursor_rules(_composed_for_both_tools(tmp_path))

    result = _config_check(root)

    assert result.exit_code == 1, result.output


def test_the_verdict_names_the_tool_and_the_tool_whose_layers_it_lacks(tmp_path: Path) -> None:
    root = _without_the_cursor_rules(_composed_for_both_tools(tmp_path))

    result = _config_check(root)

    assert "`cursor` lacks" in result.output
    assert "layer(s) `claude` reads" in result.output
