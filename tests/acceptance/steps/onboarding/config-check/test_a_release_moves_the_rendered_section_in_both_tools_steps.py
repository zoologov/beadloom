"""Steps for `onboarding/config-check/a_release_moves_the_rendered_section_in_both_tools.feature`.

BDL-083 S2R pass 1 Major 1 (RFC D13). The project is composed with the real
``setup-agentic-flow`` command, released by rewriting its ``pyproject.toml`` the
way a release does, and then read through the real ``setup-rules --refresh`` and
``config-check`` commands: their exit codes, their output and the files they leave.

The module is named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.onboarding.tool_reach import cursor_core_rule_relpath, rule_body
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios(
    "../../../onboarding/config-check/a_release_moves_the_rendered_section_in_both_tools.feature"
)


def _manifest(version: str, *dependencies: str) -> str:
    listed = ", ".join(f'"{name}"' for name in dependencies)
    return f'[project]\nname = "acme"\nversion = "{version}"\ndependencies = [{listed}]\n'


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path / "acme"}


@given(parsers.parse('a project composed for "{first}" and "{second}" at version "{version}"'))
def _composed(world: dict[str, Any], first: str, second: str, version: str) -> None:
    root: Path = world["root"]
    root.mkdir()
    (root / "pyproject.toml").write_text(_manifest(version, "click"), encoding="utf-8")
    args = ["setup-agentic-flow", "--project", str(root), "--stack", "python"]
    args += ["--tool", first, "--tool", second]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    clean = CliRunner().invoke(main, ["config-check", "--project", str(root)])
    assert clean.exit_code == 0, clean.output


@when(parsers.parse('the project is released as version "{version}" with a new dependency'))
def _released(world: dict[str, Any], version: str) -> None:
    manifest = world["root"] / "pyproject.toml"
    manifest.write_text(_manifest(version, "click", "rich"), encoding="utf-8")


@when("setup-rules --refresh runs")
def _refresh(world: dict[str, Any]) -> None:
    args = ["setup-rules", "--refresh", "--project", str(world["root"])]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output


@when("config-check runs")
def _config_check(world: dict[str, Any]) -> None:
    world["check"] = CliRunner().invoke(main, ["config-check", "--project", str(world["root"])])


@then(parsers.parse("config-check exits {code:d}"))
def _exit_code(world: dict[str, Any], code: int) -> None:
    assert world["check"].exit_code == code, world["check"].output


@then(parsers.parse('"{relpath}" is reported with "{reason}"'))
def _reported(world: dict[str, Any], relpath: str, reason: str) -> None:
    assert f"- {relpath}: {reason}\n" in world["check"].output, world["check"].output


@then(parsers.parse('no finding blames "{cause}"'))
def _not_blamed(world: dict[str, Any], cause: str) -> None:
    assert cause not in world["check"].output, world["check"].output


@then("the body of the Cursor core rule is byte-identical to the Claude CLAUDE.md")
def _one_text(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    claude_md = (root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    rule = (root / cursor_core_rule_relpath()).read_text(encoding="utf-8")
    assert rule_body(rule) == claude_md


@then(parsers.parse('the Claude CLAUDE.md states version "{version}"'))
def _states_version(world: dict[str, Any], version: str) -> None:
    claude_md = (world["root"] / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"- **Current version:** {version}\n" in claude_md
