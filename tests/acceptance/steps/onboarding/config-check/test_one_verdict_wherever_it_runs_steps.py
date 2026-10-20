"""Steps for `onboarding/config-check/one_verdict_wherever_it_runs.feature`.

BDL-083 S2c (RFC D7, BDL-UX #334). The monorepo fixture is copied from the checkout
the package under test ships from, composed with the real ``setup-agentic-flow``
command and committed. ``config-check`` then runs in that checkout, in a real
``git worktree`` of HEAD and in a real clean room built by
:func:`~beadloom.application.waves.clean_room.build_room`, and each step reads the
exit code and the output of the real command.

The room is built with no interpreter of its own: the property under test is the
files the room holds, and ``config-check`` runs in-process here.

The module is named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner, Result
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves.clean_room import build_room
from beadloom.onboarding.project_name import PROJECT_HEADING_PREFIX, PROJECT_NAME_KEY
from beadloom.services.cli import main
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../onboarding/config-check/one_verdict_wherever_it_runs.feature")

#: The suffix a fixture file named like one of this repository's tests is stored under.
_STORED_SUFFIX = ".fixture"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"tmp": tmp_path, "declared": None, "runs": {}}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _config_check(root: Path) -> Result:
    return CliRunner().invoke(main, ["config-check", "--project", str(root)])


@given(parsers.parse('the monorepo fixture declaring the project name "{name}"'))
def _declaring(world: dict[str, Any], name: str) -> None:
    world["declared"] = name


@given(parsers.parse('the monorepo fixture composed and committed in a checkout named "{name}"'))
def _composed_and_committed(world: dict[str, Any], name: str) -> None:
    root: Path = world["tmp"] / name
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    for stored in sorted(root.rglob(f"*{_STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(_STORED_SUFFIX)))
    if world["declared"] is not None:
        config = root / ".beadloom" / "config.yml"
        text = config.read_text(encoding="utf-8")
        config.write_text(f"{PROJECT_NAME_KEY}: {world['declared']}\n{text}", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    composed = CliRunner().invoke(main, ["setup-agentic-flow", "--project", str(root)])
    assert composed.exit_code == 0, composed.output
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "the flow composed")
    world["checkout"] = root


@when("config-check runs in the checkout and in a worktree of HEAD")
def _in_a_worktree(world: dict[str, Any]) -> None:
    checkout: Path = world["checkout"]
    worktree: Path = world["tmp"] / "desk-worktree"
    _git(checkout, "worktree", "add", "-q", "--detach", str(worktree), "HEAD")
    world["runs"] = {"checkout": _config_check(checkout), "worktree": _config_check(worktree)}


@when(parsers.parse('config-check runs in the checkout and in the clean room of bead "{bead}"'))
def _in_a_room(world: dict[str, Any], bead: str) -> None:
    checkout: Path = world["checkout"]
    parent: Path = world["tmp"] / "rooms"
    parent.mkdir()
    built = build_room(bead_id=bead, project_root=checkout, parent=parent, environment=False)
    assert built.built, built
    assert built.path.name == f"room-{bead}"
    world["runs"] = {"checkout": _config_check(checkout), "room": _config_check(built.path)}


@then("both runs exit 0")
def _both_exit_0(world: dict[str, Any]) -> None:
    codes = {place: run.exit_code for place, run in world["runs"].items()}
    assert set(codes.values()) == {0}, {p: r.output for p, r in world["runs"].items()}


@then(
    parsers.parse(
        'both runs say they compared "{compared}" against its composition from "{source}"'
    )
)
def _both_name_the_files(world: dict[str, Any], compared: str, source: str) -> None:
    sentence = f"compared {compared} against its composition from {source}"
    for place, run in world["runs"].items():
        assert sentence in run.output, (place, run.output)


@then(
    parsers.parse(
        'both runs say the name "{name}" was read from "{source}" and is not compared'
    )
)
def _both_name_the_source(world: dict[str, Any], name: str, source: str) -> None:
    for place, run in world["runs"].items():
        assert f"'{name}' from {source}" in run.output, (place, run.output)
        assert "the heading's name is not compared" in run.output, (place, run.output)


@then(parsers.parse('the composed heading names the project "{name}"'))
def _the_heading(world: dict[str, Any], name: str) -> None:
    text = (world["checkout"] / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"{PROJECT_HEADING_PREFIX}{name}\n" in text
