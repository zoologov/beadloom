"""Step implementations for `features/room_extras.feature` (BDL-068 S6, #236).

Thin by design: each step writes a real declaration on disk and runs the real
`beadloom rooms` command, or builds a real room with the real builder. Nothing
is doubled, because the defect is a property of the environment the run is in,
and a double of the environment proves the double.

The project written on disk names THIS project's own distribution, so the
derivation reads the metadata the running interpreter actually holds. The
alternative — fabricating a distribution — would test the seam and not the
answer, and the answer is the whole finding.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import ROOM_MARKER, build_room
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/room_extras.feature")

#: The distribution this suite's own interpreter holds, so the derivation reads
#: real metadata rather than a fixture's idea of it.
_OWN_DISTRIBUTION = "beadloom"

#: A name no index resolves. Not a typo of a real one: a near-miss would be
#: found by a resolver that falls back to a prefix search, and this step is
#: about the answer "this interpreter does not hold it" and nothing else.
_ABSENT_DISTRIBUTION = "beadloom-no-such-distribution-x9"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _write_packaging(world: dict[str, Any], name: str) -> None:
    (world["root"] / "pyproject.toml").write_text(
        "[project]\n"
        f'name = "{name}"\n'
        'requires-python = ">=3.10"\n'
        "classifiers = [\n"
        '  "Programming Language :: Python :: 3.13",\n'
        "]\n",
        encoding="utf-8",
    )


def _rooms(world: dict[str, Any], *extra: str) -> str:
    outcome = CliRunner().invoke(main, ["rooms", "--project", str(world["root"]), *extra])
    assert outcome.exit_code == 0, outcome.stdout + outcome.stderr
    return outcome.stdout


@given("a project whose packaging is this project's own")
def _packaging_is_our_own(world: dict[str, Any]) -> None:
    _write_packaging(world, _OWN_DISTRIBUTION)


@given("a project whose packaging names a distribution this interpreter does not hold")
def _packaging_names_an_absent_distribution(world: dict[str, Any]) -> None:
    _write_packaging(world, _ABSENT_DISTRIBUTION)


@given(parsers.parse('a workflow job that installs the project with the "{extra}" extra'))
def _a_job_installing_one_extra(world: dict[str, Any], extra: str) -> None:
    workflows = world["root"] / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "name: CI\n"
        "on: [push]\n"
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Install dependencies\n"
        f"        run: uv sync --extra {extra}\n",
        encoding="utf-8",
    )
    world["declared_extra"] = extra


@given("a bead whose room has been built")
def _a_room_has_been_built(world: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{_OWN_DISTRIBUTION}"\n', encoding="utf-8"
    )
    for args in (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "t@example.invalid"),
        ("config", "user.name", "T"),
        ("add", "-A"),
        ("commit", "-q", "-m", "base"),
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
    build = build_room(
        bead_id="beadloom-0mdo.38", project_root=root, parent=tmp_path / "rooms"
    )
    assert build.built, build.detail
    world["build"] = build


@when("the rooms are reported")
def _the_rooms_are_reported(world: dict[str, Any]) -> None:
    world["report"] = _rooms(world)
    world["payload"] = json.loads(_rooms(world, "--json"))


@when("the extras axis is asked for")
def _the_extras_axis(world: dict[str, Any]) -> None:
    world["axis"] = _rooms(world, "--dimension", "extras")


@when("the room's record is read")
def _the_record_is_read(world: dict[str, Any]) -> None:
    world["record"] = json.loads(
        (world["build"].path / ROOM_MARKER).read_text(encoding="utf-8")
    )


@then("the room this run is in names an extras dimension")
def _the_current_room_names_extras(world: dict[str, Any]) -> None:
    assert "extras" in world["payload"]["current"], world["payload"]["current"]


@then("that leg is reported as not entered")
def _the_leg_is_not_entered(world: dict[str, Any]) -> None:
    declared = world["payload"]["declared"]
    assert declared, world["report"]
    assert all(not room["entered"] for room in declared), world["report"]


@then("the reason names the extras that differ")
def _the_reason_names_the_extras(world: dict[str, Any]) -> None:
    reasons = [room["why"] for room in world["payload"]["declared"]]
    assert any("extras" in reason for reason in reasons), reasons
    assert any(world["declared_extra"] in reason for reason in reasons), reasons


@then("the extras that leg installs are printed")
def _the_axis_prints_the_extras(world: dict[str, Any]) -> None:
    values = [line for line in world["axis"].splitlines() if line.strip()]
    assert values, world["axis"]
    assert any(world["declared_extra"] in value for value in values), values


@then("no room carries an extras dimension")
def _no_room_carries_extras(world: dict[str, Any]) -> None:
    assert "extras" not in world["payload"]["current"], world["payload"]["current"]
    for room in world["payload"]["declared"]:
        assert "extras" not in room["dimensions"], room


@then("the report says the extras could not be resolved")
def _the_report_says_unresolved(world: dict[str, Any]) -> None:
    reasons = [entry["why"] for entry in world["payload"]["unresolved"]]
    assert any("extra" in reason for reason in reasons), reasons
    assert any(_ABSENT_DISTRIBUTION in reason for reason in reasons), reasons


@then("it names the extras the invocation's interpreter has")
def _the_record_names_the_extras(world: dict[str, Any]) -> None:
    interpreter = world["record"]["interpreter"]
    assert "extras" in interpreter, interpreter
    assert "label" in interpreter["extras"], interpreter["extras"]
