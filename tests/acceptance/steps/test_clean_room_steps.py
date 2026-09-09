"""Step implementations for the clean-room suite (BDL-068 S6, BDL-UX #235/#243).

Thin by design: every step runs the real builder against a real git repository
in ``tmp_path``. Nothing is mocked, because the two defects the scenarios
describe are both properties of the filesystem the room is built on — one room
directory reached by two beads, and one room directory entered twice.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import build_room, room_for

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/clean_room.feature")
scenarios("../features/clean_room_rebuild.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path / "project", "parent": tmp_path / "rooms", "builds": {}}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


@given("a project at a commit")
def _a_project_at_a_commit(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    (root / "src").mkdir(parents=True)
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'p'\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    world["parent"].mkdir(parents=True)


@given(parsers.parse('the working tree changes "{path}"'))
def _the_working_tree_changes(world: dict[str, Any], path: str) -> None:
    (world["root"] / path).write_text("VALUE = 2\n", encoding="utf-8")


@given(parsers.parse('bead "{bead}" has built its clean room holding its own file "{name}"'))
def _a_room_already_built(world: dict[str, Any], bead: str, name: str) -> None:
    build = build_room(
        bead_id=bead, project_root=world["root"], parent=world["parent"]
    )
    assert build.built, build.detail
    (build.path / name).write_text("a neighbour's work\n", encoding="utf-8")
    world["builds"][bead] = build


@given(parsers.parse('a directory named "{name}" that no room build created'))
def _a_directory_nobody_built(world: dict[str, Any], name: str) -> None:
    (world["parent"] / name).mkdir()


@given(parsers.parse('a directory named "{name}" recorded as the room of bead "{owner}"'))
def _a_directory_owned_by_another_bead(
    world: dict[str, Any], name: str, owner: str
) -> None:
    from beadloom.application.waves import ROOM_MARKER

    room = world["parent"] / name
    room.mkdir()
    (room / ROOM_MARKER).write_text(json.dumps({"bead": owner}), encoding="utf-8")


@when(parsers.parse('bead "{bead}" builds its clean room'))
def _builds_its_room(world: dict[str, Any], bead: str) -> None:
    world["last"] = build_room(
        bead_id=bead, project_root=world["root"], parent=world["parent"]
    )


@when(parsers.parse('bead "{bead}" builds its clean room again'))
def _builds_its_room_again(world: dict[str, Any], bead: str) -> None:
    _builds_its_room(world, bead)


@when(parsers.parse('bead "{bead}" builds its clean room carrying "{path}"'))
def _builds_its_room_carrying(world: dict[str, Any], bead: str, path: str) -> None:
    world["last"] = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        carry=(path,),
    )


@when(parsers.parse('bead "{bead}" builds its clean room under the project itself'))
def _builds_inside_the_project(world: dict[str, Any], bead: str) -> None:
    world["last"] = build_room(
        bead_id=bead, project_root=world["root"], parent=world["root"] / "scratch"
    )


@when(parsers.parse('bead "{bead}" rebuilds its clean room'))
def _rebuilds_its_room(world: dict[str, Any], bead: str) -> None:
    world["last"] = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        rebuild=True,
    )


@then("the room is built")
def _the_room_is_built(world: dict[str, Any]) -> None:
    assert world["last"].built, world["last"].detail
    assert world["last"].path.is_dir()


@then("no room is built")
def _no_room_is_built(world: dict[str, Any]) -> None:
    assert not world["last"].built
    assert world["last"].refusal is not None


@then(parsers.parse('the refusal is reported as "{reason}"'))
def _the_refusal_is(world: dict[str, Any], reason: str) -> None:
    assert world["last"].refusal == reason, world["last"].detail


@then(parsers.parse('the room\'s directory is named "{name}"'))
def _the_room_is_named(world: dict[str, Any], name: str) -> None:
    assert world["last"].path.name == name


@then("the two beads' rooms are different directories")
def _rooms_differ(world: dict[str, Any]) -> None:
    others = {build.path for build in world["builds"].values()}
    assert world["last"].path not in others
    assert len(others) == 1


@then(parsers.parse('the room does not hold "{name}"'))
def _the_room_does_not_hold(world: dict[str, Any], name: str) -> None:
    assert not (world["last"].path / name).exists()


@then(parsers.parse('the room still holds "{name}"'))
def _the_room_still_holds(world: dict[str, Any], name: str) -> None:
    existing = next(iter(world["builds"].values()))
    assert (existing.path / name).exists()


@then(parsers.parse('the room records that it belongs to "{bead}"'))
def _the_room_records_its_owner(world: dict[str, Any], bead: str) -> None:
    from beadloom.application.waves import room_owner

    assert room_owner(world["last"].path) == bead
    assert world["last"].path.name == room_for(bead)


@then("the room records the commit it was built from")
def _the_room_records_its_commit(world: dict[str, Any]) -> None:
    commit = world["last"].commit
    assert commit is not None
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=world["root"],
        check=True,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
    ).stdout.strip()
    assert commit == head


@then(parsers.parse('the room holds the working tree\'s "{path}"'))
def _the_room_holds_the_changed_file(world: dict[str, Any], path: str) -> None:
    assert world["last"].carried == (path,)
    room_text = (world["last"].path / path).read_text(encoding="utf-8")
    assert room_text == (world["root"] / path).read_text(encoding="utf-8")


@then("the invocation sets PYTHONPATH to the room's own sources")
def _the_invocation_sets_pythonpath(world: dict[str, Any]) -> None:
    room = world["last"].path
    assert any(f"PYTHONPATH={room / 'src'}" in line for line in world["last"].invocation)


@then("the invocation prints where beadloom was imported from")
def _the_invocation_checks_the_import(world: dict[str, Any]) -> None:
    assert any("import beadloom" in line for line in world["last"].invocation)


@given(parsers.parse('the working tree changes "{path}" again'))
def _the_working_tree_changes_again(world: dict[str, Any], path: str) -> None:
    """A second, distinct edit — the content a reused LIST must be re-read from."""
    (world["root"] / path).write_text("VALUE = 3\n", encoding="utf-8")


@given(parsers.parse('the working tree no longer holds "{path}"'))
def _the_working_tree_no_longer_holds(world: dict[str, Any], path: str) -> None:
    (world["root"] / path).unlink()


@given(parsers.parse('bead "{bead}" has built its clean room carrying "{path}"'))
def _a_room_already_built_carrying(world: dict[str, Any], bead: str, path: str) -> None:
    build = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        carry=(path,),
    )
    assert build.built, build.detail
    world["builds"][bead] = build


@given(parsers.parse('bead "{bead}" has built its clean room with no environment'))
def _a_room_already_built_without_an_environment(world: dict[str, Any], bead: str) -> None:
    build = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        environment=False,
    )
    assert build.built, build.detail
    world["builds"][bead] = build


@given(
    parsers.parse(
        'bead "{bead}" has built its clean room with extras "{extras}" and no environment'
    )
)
def _a_room_already_built_with_extras(world: dict[str, Any], bead: str, extras: str) -> None:
    build = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        extras=tuple(extras.split(",")),
        environment=False,
    )
    assert build.built, build.detail
    world["builds"][bead] = build


@when(parsers.parse('bead "{bead}" rebuilds its clean room naming no files'))
def _rebuilds_naming_no_files(world: dict[str, Any], bead: str) -> None:
    _rebuilds_its_room(world, bead)


@when(parsers.parse('bead "{bead}" rebuilds its clean room carrying "{path}"'))
def _rebuilds_carrying(world: dict[str, Any], bead: str, path: str) -> None:
    world["last"] = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        carry=(path,),
        rebuild=True,
    )


@when(
    parsers.parse(
        'bead "{bead}" rebuilds its clean room with no environment and naming no files'
    )
)
def _rebuilds_without_an_environment(world: dict[str, Any], bead: str) -> None:
    world["last"] = build_room(
        bead_id=bead,
        project_root=world["root"],
        parent=world["parent"],
        rebuild=True,
        environment=False,
    )


@then(parsers.parse('the rebuild reused "{part}"'))
def _the_rebuild_reused(world: dict[str, Any], part: str) -> None:
    assert part in world["last"].reused, world["last"].reused


@then("the rebuild reused nothing")
def _the_rebuild_reused_nothing(world: dict[str, Any]) -> None:
    assert world["last"].reused == ()


@then(parsers.parse('the room carried only "{path}"'))
def _the_room_carried_only(world: dict[str, Any], path: str) -> None:
    assert world["last"].carried == (path,)


@then(parsers.parse('the room records the extras request "{extras}"'))
def _the_room_records_the_extras_request(world: dict[str, Any], extras: str) -> None:
    assert _request_of(world["last"].path)["extras"] == extras.split(",")


@then("the room records that an environment was asked for")
def _the_room_records_an_environment_request(world: dict[str, Any]) -> None:
    assert _request_of(world["last"].path)["environment"] is True


def _request_of(room: Path) -> dict[str, Any]:
    """The request half of the room's own record, read as a reader would."""
    from beadloom.application.waves import ROOM_MARKER

    record = json.loads((room / ROOM_MARKER).read_text(encoding="utf-8"))
    asked = record["request"]
    assert isinstance(asked, dict)
    return asked
