"""Step implementations for `features/scaffold_edit_policy.feature` (BDL-068 S6).

Thin by design: every step runs the real ``setup-agentic-flow`` command over a
real project directory and then reads the bytes on disk. Nothing here inspects
``preserve`` or the flow manifest, because the property under test is what an
adopter's file looks like after the command they were told to run, and an
assertion about the mechanism would pass over a mechanism that stopped being
wired to the command.

The role names come from the composer's own population, so a role a later
release adds is covered without a second list; the module is named ``test_*``
so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner, Result
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/scaffold_edit_policy.feature")

#: The two lines a team appends to a shipped protocol — the only copy of an
#: intent, which is what makes recomposing over them data loss.
_HAND_EDIT = "\n## OUR TEAM RULE\n\nEvery pull request needs two reviewers.\n"

#: One file of each kind the command writes, keyed by the name a scenario uses.
_ARTIFACT_PATHS: dict[str, str] = {
    "dev": ".claude/agents/dev.md",
    "review": ".claude/agents/review.md",
    "coordinator": ".claude/commands/coordinator.md",
    "CLAUDE.md": ".claude/CLAUDE.md",
}

#: One file per artifact kind, for the scenario that checks all three at once.
_ONE_PER_KIND: tuple[str, ...] = ("dev", "coordinator", "CLAUDE.md")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    root = tmp_path / "acme"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return {"root": root, "edited": {}}


def _run(world: dict[str, Any], *args: str) -> Result:
    result = CliRunner().invoke(
        main, ["setup-agentic-flow", "--project", str(world["root"]), *args]
    )
    assert result.exit_code == 0, result.output
    world["output"] = result.output
    return result


def _path(world: dict[str, Any], name: str) -> Path:
    return world["root"] / _ARTIFACT_PATHS[name]


def _edit(world: dict[str, Any], name: str) -> None:
    path = _path(world, name)
    path.write_text(path.read_text(encoding="utf-8") + _HAND_EDIT, encoding="utf-8")
    world["edited"][name] = path.read_text(encoding="utf-8")


@given("a project that has been scaffolded once")
def _scaffolded(world: dict[str, Any]) -> None:
    _run(world)


@given(parsers.parse('"{name}" has been edited by hand'))
def _edited(world: dict[str, Any], name: str) -> None:
    _edit(world, name)


@given("one file of every artifact kind has been edited by hand")
def _edited_everywhere(world: dict[str, Any]) -> None:
    for name in _ONE_PER_KIND:
        _edit(world, name)


@when("the scaffold is re-run with no flags")
def _rerun(world: dict[str, Any]) -> None:
    _run(world)


@when("the scaffold is re-run with --force")
def _rerun_forced(world: dict[str, Any]) -> None:
    _run(world, "--force")


@when("the agent-config check runs")
def _check_runs(world: dict[str, Any]) -> None:
    """Read the promise off the command an adopter runs, not off a drift object.

    The sentence under test is one a human reads in a terminal, and reading it
    from ``check_config_drift`` would let the command stop printing it while the
    scenario stayed green.
    """
    result = CliRunner().invoke(
        main, ["config-check", "--project", str(world["root"])]
    )
    world["unwritable"] = [
        relpath
        for relpath in _ARTIFACT_PATHS.values()
        for line in result.output.splitlines()
        if relpath in line and "NOT be rewritten" in line
    ]
    assert world["unwritable"], result.output


@then(parsers.parse('the hand edit in "{name}" is still on disk'))
def _edit_survived(world: dict[str, Any], name: str) -> None:
    assert _path(world, name).read_text(encoding="utf-8") == world["edited"][name]


@then(parsers.parse('the hand edit in "{name}" is gone'))
def _edit_gone(world: dict[str, Any], name: str) -> None:
    assert _path(world, name).read_text(encoding="utf-8") != world["edited"][name]


@then("every hand edit is still on disk")
def _every_edit_survived(world: dict[str, Any]) -> None:
    survived = {
        name: _path(world, name).read_text(encoding="utf-8") == body
        for name, body in world["edited"].items()
    }
    assert all(survived.values()), survived


@then(parsers.parse('the output names "{relpath}" as left alone'))
def _named_left_alone(world: dict[str, Any], relpath: str) -> None:
    assert f"Skipped {relpath}" in world["output"], world["output"]


@then(parsers.parse('the output names "{relpath}" as where the edit belongs'))
def _named_overlay(world: dict[str, Any], relpath: str) -> None:
    assert relpath in world["output"], world["output"]


@then(parsers.parse('the output does not claim to have written "{relpath}"'))
def _not_claimed_written(world: dict[str, Any], relpath: str) -> None:
    claims = [
        line
        for line in world["output"].splitlines()
        if line.startswith("Wrote ") and relpath in line
    ]
    assert not claims, claims


@then(parsers.parse('the output names "{relpath}" as written'))
def _claimed_written(world: dict[str, Any], relpath: str) -> None:
    assert f"Wrote {relpath}" in world["output"], world["output"]


@then(parsers.parse('"{name}" was recomposed'))
def _recomposed(world: dict[str, Any], name: str) -> None:
    from beadloom.onboarding.flow_config import load_flow_config
    from beadloom.onboarding.role_composer import compose_all_roles

    composed = compose_all_roles(load_flow_config(world["root"]), world["root"])
    assert _path(world, name).read_text(encoding="utf-8") == composed[name]


@then("nothing is reported as left alone")
def _nothing_left_alone(world: dict[str, Any]) -> None:
    assert "Left alone" not in world["output"], world["output"]
    assert "Skipped .claude/" not in world["output"], world["output"]


@then("the file the check said would not be rewritten was not rewritten")
def _check_promise_kept(world: dict[str, Any]) -> None:
    rewritten = [
        relpath
        for relpath in world["unwritable"]
        for name, known in _ARTIFACT_PATHS.items()
        if known == relpath
        and name in world["edited"]
        and _path(world, name).read_text(encoding="utf-8") != world["edited"][name]
    ]
    assert not rewritten, rewritten


@then("every adapter --fix declines is one the scaffold left alone")
def _same_declines(world: dict[str, Any]) -> None:
    from beadloom.onboarding.config_sync import declined_adapter_rewrites

    declined = declined_adapter_rewrites(world["root"])
    assert declined, "--fix declined no adapter, so the two cannot be compared"
    for entry in declined:
        assert f"Skipped {entry.file}" in world["output"], world["output"]


@then(parsers.parse('the output names no path under "{prefix}" for CLAUDE.md'))
def _no_bogus_command_path(world: dict[str, Any], prefix: str) -> None:
    bogus = [
        line
        for line in world["output"].splitlines()
        if prefix in line and "CLAUDE.md" in line
    ]
    assert not bogus, bogus
