"""Step implementations for the room-environment suite (BDL-068 S6, BDL-UX #256).

Every step runs the real builder against a real git repository in ``tmp_path``
and, where the scenario is about an environment, builds a real one. Nothing is
stubbed: the defect the scenarios describe is that a room's verdict was decided
by an interpreter nobody had looked at, and a scenario that passes against a
double proves the double.

The fixture project's extras deliberately require nothing. What is under test is
which extras the room asks for and whether the interpreter it produces imports
the project from inside the room, and a requirement would add a network fetch to
every scenario without adding an observation to any of them.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.rooms import installed_extras
from beadloom.application.waves import ROOM_MARKER, build_room
from beadloom.application.waves.room_env import SOURCE_CALLER, SOURCE_LEGS

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/room_environment.feature")

_PYPROJECT = """\
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "thing"
version = "0.1.0"

[project.optional-dependencies]
dev = []
tui = []
watch = []

[tool.setuptools.packages.find]
where = ["src"]
"""

_BROKEN_PYPROJECT = """\
[build-system]
requires = []
build-backend = "no_such_backend.build"

[project]
name = "thing"
version = "0.1.0"
"""


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path / "project", "parent": tmp_path / "rooms", "build": None}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _project(world: dict[str, Any], *, pyproject: str = _PYPROJECT) -> Path:
    root: Path = world["root"]
    (root / "src" / "thing").mkdir(parents=True)
    (root / "src" / "thing" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def _commit(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    world["parent"].mkdir(parents=True)


def _workflow(root: Path, name: str, jobs: dict[str, str]) -> None:
    body = ["name: w", "on: [push]", "jobs:"]
    for job, install in jobs.items():
        body += [f"  {job}:", "    runs-on: ubuntu-latest", "    steps:"]
        body += [f"      - run: {install}"]
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("\n".join(body) + "\n", encoding="utf-8")


@given(parsers.parse('a project at a commit whose legs install "{first}" and "{second}"'))
def _legs_installing_two_extras(world: dict[str, Any], first: str, second: str) -> None:
    root = _project(world)
    install = f"uv sync --extra {first} --extra {second}"
    _workflow(root, "ci.yml", {"tests": install, "types": install})
    _commit(world)


@given(parsers.parse('one further leg that installs only "{extra}"'))
def _one_further_leg(world: dict[str, Any], extra: str) -> None:
    root: Path = world["root"]
    _workflow(root, "site.yml", {"site": f"uv sync --extra {extra}"})
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "one more leg")


@given("a project at a commit that declares no legs")
def _no_legs(world: dict[str, Any]) -> None:
    _project(world)
    _commit(world)


@given("a project at a commit whose legs install an extra it does not declare")
def _packaging_that_cannot_be_installed(world: dict[str, Any]) -> None:
    root = _project(world, pyproject=_BROKEN_PYPROJECT)
    _workflow(root, "ci.yml", {"tests": "uv sync --extra dev"})
    _commit(world)


@when(parsers.parse('bead "{bead}" builds its clean room'))
def _builds_its_room(world: dict[str, Any], bead: str) -> None:
    world["build"] = build_room(
        bead_id=bead, project_root=world["root"], parent=world["parent"]
    )


@when(parsers.parse('bead "{bead}" builds its clean room installing "{extras}"'))
def _builds_its_room_installing(world: dict[str, Any], bead: str, extras: str) -> None:
    world["build"] = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        extras=tuple(part for part in extras.split(",") if part),
    )


@then("the room is built")
def _the_room_is_built(world: dict[str, Any]) -> None:
    assert world["build"].built, world["build"].detail


@then("the room holds an interpreter of its own")
def _the_room_holds_an_interpreter(world: dict[str, Any]) -> None:
    environment = world["build"].environment
    assert environment.built, environment.detail
    assert environment.python is not None
    assert environment.python.is_relative_to(world["build"].path)
    assert environment.python.exists()


@then("that interpreter imports the project from inside the room")
def _the_interpreter_imports_from_the_room(world: dict[str, Any]) -> None:
    python = world["build"].environment.python
    result = subprocess.run(  # noqa: S603
        [str(python), "-c", "import thing; print(thing.__file__)"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    assert result.stdout.strip().startswith(str(world["build"].path))


@then("the invocation names the room's own interpreter")
def _the_invocation_names_the_rooms_interpreter(world: dict[str, Any]) -> None:
    """What the command prints and what the room records must be one answer.

    They were two: the record kept naming the project's interpreter while the
    printed invocation named the room's, which is a record that disagrees with
    the run that wrote it about the one fact this bead is here for.
    """
    python = str(world["build"].environment.python)
    assert all(python in line for line in world["build"].invocation)
    assert _marker(world)["interpreter"]["invocation"] == python


@then("the room records the extras of that interpreter rather than of this process")
def _the_record_states_the_rooms_own_extras(world: dict[str, Any]) -> None:
    """The distinction BDL-UX #236 was filed about, taken one interpreter over.

    This process holds no distribution named ``thing`` and the room's own
    interpreter does, so a record read off the wrong one is unresolved where the
    right one is resolved. Without this the two answers are indistinguishable,
    because a fixture project is absent from the process that builds it.
    """
    assert not installed_extras(world["root"]).resolved
    recorded = _marker(world)["interpreter"]["extras"]
    assert recorded["resolved"] is True
    assert recorded["distribution"] == "thing"
    assert world["build"].extras is not None


@then(parsers.parse('the room installed the extras "{label}"'))
def _the_room_installed(world: dict[str, Any], label: str) -> None:
    environment = world["build"].environment
    assert environment.built, environment.detail
    assert environment.label == label


@then("the room records that the choice came from the project's own legs")
def _the_choice_came_from_the_legs(world: dict[str, Any]) -> None:
    assert world["build"].environment.source == SOURCE_LEGS
    assert _marker(world)["environment"]["source"] == SOURCE_LEGS


@then("the room records that the choice was named by the caller")
def _the_choice_came_from_the_caller(world: dict[str, Any]) -> None:
    assert world["build"].environment.source == SOURCE_CALLER
    assert _marker(world)["environment"]["source"] == SOURCE_CALLER


@then("the room holds no interpreter of its own")
def _the_room_holds_no_interpreter(world: dict[str, Any]) -> None:
    environment = world["build"].environment
    assert not environment.built
    assert environment.python is None


@then("the room says which environment its verdict is taken under instead")
def _the_room_says_what_it_uses_instead(world: dict[str, Any]) -> None:
    detail = world["build"].environment.detail
    assert "no leg" in detail
    assert world["build"].invocation[0].split()[1] in detail


@then("the room reports why the environment was not built")
def _the_room_reports_the_failure(world: dict[str, Any]) -> None:
    detail = world["build"].environment.detail
    assert "no_such_backend" in detail or "backend" in detail
    assert _marker(world)["environment"]["built"] is False


def _marker(world: dict[str, Any]) -> dict[str, Any]:
    text = (world["build"].path / ROOM_MARKER).read_text(encoding="utf-8")
    record = json.loads(text)
    assert isinstance(record, dict)
    return record
