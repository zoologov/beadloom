"""CLI-level tests for `beadloom clean-room` (BDL-068 S6, BDL-UX #235 / #243).

What is exercised here is the COMMAND: the path it derives, the exit code it
returns and the two shapes it prints. The build itself is covered by the
acceptance scenarios in `tests/acceptance/features/clean_room.feature`, and the
tracker arrives through a double — a double proves the double's contract, and
what these tests are about is what the command does with the answer.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner

from beadloom.application.waves import ROOM_MARKER, room_for
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

BEAD = "beadloom-x.1"


def _project(tmp_path: Path) -> Path:
    """A git repository with one commit — the only thing a room needs."""
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "T"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)  # noqa: S607
    subprocess.run(
        ["git", "commit", "-q", "-m", "base"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )
    return root


class _FakeBd:
    """bead id -> status, or an absent bead the tracker answers ``1`` for."""

    def __init__(self, statuses: dict[str, str]) -> None:
        self.statuses = statuses

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        bead = args[1]
        if bead not in self.statuses:
            return BdResult(returncode=1, stdout="", stderr=f"no such issue: {bead}")
        record = {"id": bead, "title": f"[{bead}] work", "status": self.statuses[bead]}
        return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")


@pytest.fixture()
def bd(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _install(statuses: dict[str, str]) -> None:
        monkeypatch.setattr(
            "beadloom.services.bd_seam.run_bd", _FakeBd(statuses), raising=True
        )

    return _install


def _run(root: Path, at: Path, *extra: str) -> Any:
    """Invoke the command over a project that declares no leg, and no interpreter.

    ``--no-environment`` is passed because none of the cases below is about the
    room's interpreter: they are about who the room belongs to and how many
    times it may be built. Without it every one of them would build a real venv
    it never looks at, and would report the finding a room without one carries.
    The environment's own cases live in
    ``tests/acceptance/features/room_environment.feature`` and in
    ``tests/test_room_environment.py``.
    """
    return CliRunner().invoke(
        main,
        [
            "clean-room",
            BEAD,
            "--project",
            str(root),
            "--at",
            str(at),
            "--no-environment",
            *extra,
        ],
    )


class TestBuilding:
    def test_a_claimed_bead_gets_a_room_named_after_it_at_exit_zero(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        room = tmp_path / "rooms" / room_for(BEAD)
        assert result.exit_code == 0, result.output
        assert room.is_dir()
        assert (room / "src" / "thing.py").exists()
        assert (room / ROOM_MARKER).exists()
        assert str(room) in result.output

    def test_the_invocation_it_hands_back_points_at_the_rooms_own_sources(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        room = tmp_path / "rooms" / room_for(BEAD)
        assert f"PYTHONPATH={room / 'src'}" in result.output
        assert "import beadloom" in result.output

    def test_a_carried_file_is_the_working_trees_copy(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        (root / "src" / "thing.py").write_text("VALUE = 2\n", encoding="utf-8")
        result = _run(root, tmp_path / "rooms", "--carry", "src/thing.py")

        room = tmp_path / "rooms" / room_for(BEAD)
        assert result.exit_code == 0, result.output
        assert (room / "src" / "thing.py").read_text(encoding="utf-8") == "VALUE = 2\n"

    def test_the_room_states_that_it_answers_for_its_own_files_only(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        assert "combined tree" in result.output
        assert ".git" in result.output


class TestRefusing:
    def test_a_second_build_is_refused_and_names_the_remedy(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        assert _run(root, tmp_path / "rooms").exit_code == 0
        marker = (tmp_path / "rooms" / room_for(BEAD) / ROOM_MARKER).read_text(
            encoding="utf-8"
        )

        result = _run(root, tmp_path / "rooms")

        assert result.exit_code == 2
        assert "already_exists" in result.output
        assert "--rebuild" in result.output
        # The refused run changed nothing about the room it declined to enter.
        assert (tmp_path / "rooms" / room_for(BEAD) / ROOM_MARKER).read_text(
            encoding="utf-8"
        ) == marker

    def test_a_rebuild_replaces_the_room_rather_than_refreshing_it(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        assert _run(root, tmp_path / "rooms").exit_code == 0
        room = tmp_path / "rooms" / room_for(BEAD)
        (room / "stale.txt").write_text("from the first build\n", encoding="utf-8")

        result = _run(root, tmp_path / "rooms", "--rebuild")

        assert result.exit_code == 0, result.output
        assert not (room / "stale.txt").exists()
        assert (room / ROOM_MARKER).exists()

    def test_a_bead_the_tracker_does_not_have_builds_nothing(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({})
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        assert result.exit_code == 2
        assert "unknown_bead" in result.output
        assert not (tmp_path / "rooms" / room_for(BEAD)).exists()

    def test_a_room_under_the_project_is_refused(self, tmp_path: Path, bd: Any) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        result = _run(root, root / "scratch")

        assert result.exit_code == 2
        assert "inside_the_project" in result.output


class TestTheClaim:
    def test_a_bead_nobody_claimed_still_gets_a_room_and_a_finding(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "open"})
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        assert result.exit_code == 1
        assert (tmp_path / "rooms" / room_for(BEAD)).is_dir()
        assert "open" in result.output

    def test_a_tracker_that_cannot_answer_is_a_finding_and_not_a_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.services.bd_seam import BdUnavailableError

        def _no_bd(args: list[str], *, cwd: str | None = None) -> Any:
            raise BdUnavailableError("bd not found")

        monkeypatch.setattr("beadloom.services.bd_seam.run_bd", _no_bd, raising=True)
        root = _project(tmp_path)
        result = _run(root, tmp_path / "rooms")

        assert result.exit_code == 1
        assert (tmp_path / "rooms" / room_for(BEAD)).is_dir()
        assert "FINDING" in result.output


class TestBothShapes:
    def test_json_and_the_human_shape_agree_on_the_room_and_the_verdict(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        human = _run(root, tmp_path / "rooms")
        structured = _run(root, tmp_path / "rooms-json", "--json")

        payload = json.loads(structured.stdout)
        assert payload["built"] is True
        assert payload["bead"] == BEAD
        assert payload["room"] == str(tmp_path / "rooms-json" / room_for(BEAD))
        assert payload["refusal"] is None
        assert payload["exit_code"] == human.exit_code == structured.exit_code

    def test_a_refusal_carries_the_derived_path_in_both_shapes(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        assert _run(root, tmp_path / "rooms").exit_code == 0
        structured = _run(root, tmp_path / "rooms", "--json")

        payload = json.loads(structured.stdout)
        assert payload["built"] is False
        assert payload["refusal"] == "already_exists"
        assert payload["room"] == str(tmp_path / "rooms" / room_for(BEAD))
        assert payload["exit_code"] == structured.exit_code == 2


class TestTheInterpreterTheInvocationNames:
    """Found by using the command on its own bead, which is the only way to find it.

    The first version named ``sys.executable`` — the interpreter the CLI process
    happens to run under. Installed as a uv tool, that is
    ``~/.local/share/uv/tools/beadloom/bin/python3``, which has neither pytest nor
    the project's dev dependencies, so the invocation the command handed back
    could not be run. What the suite runs under is the project's own environment.
    """

    def test_the_projects_own_environment_is_named_when_it_has_one(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.waves import room_invocation

        root = _project(tmp_path)
        interpreter = root / ".venv" / "bin" / "python"
        interpreter.parent.mkdir(parents=True)
        interpreter.write_text("#!/bin/sh\n", encoding="utf-8")

        lines = room_invocation(tmp_path / "room", project_root=root)

        assert all(str(interpreter) in line for line in lines)

    def test_a_project_with_no_environment_falls_back_to_this_interpreter(
        self, tmp_path: Path
    ) -> None:
        import sys

        from beadloom.application.waves import room_invocation

        root = _project(tmp_path)
        lines = room_invocation(tmp_path / "room", project_root=root)

        assert all(sys.executable in line for line in lines)


class TestATrackerAnswerNobodyCanRead:
    """An unreadable answer is the tracker failing, not the bead being absent.

    Both cases below build the room and cost exit 1. Refusing instead would make
    the command unusable behind any `bd` whose output shape changed, and the room
    itself does not depend on the answer.
    """

    def _bd_answering(self, monkeypatch: pytest.MonkeyPatch, stdout: str) -> None:
        from beadloom.services.bd_seam import BdResult

        def _answer(args: list[str], *, cwd: str | None = None) -> Any:
            return BdResult(returncode=0, stdout=stdout, stderr="")

        monkeypatch.setattr("beadloom.services.bd_seam.run_bd", _answer, raising=True)

    def test_an_answer_that_is_not_json_is_a_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bd_answering(monkeypatch, "not json at all")
        result = _run(_project(tmp_path), tmp_path / "rooms")

        assert result.exit_code == 1
        assert "not JSON" in result.output
        assert (tmp_path / "rooms" / room_for(BEAD)).is_dir()

    def test_an_answer_that_is_not_a_bead_record_is_a_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bd_answering(monkeypatch, json.dumps("a string"))
        result = _run(_project(tmp_path), tmp_path / "rooms")

        assert result.exit_code == 1
        assert "not a bead record" in result.output
        assert (tmp_path / "rooms" / room_for(BEAD)).is_dir()


class TestTheEnvironmentTheRoomIsGiven:
    """The exit codes and the shapes a room's own interpreter is reported in.

    No case here builds a real environment. Some decline it with
    `--no-environment`; the rest name a project with no packaging at all, so the
    install step fails in about 0.2 s and the room reports the failure — which
    is the case being checked, since what a caller ASKED for has to reach the
    record whether or not the ask succeeded. What the command DOES about a real
    environment is stated in
    `tests/acceptance/features/room_environment.feature`, over real ones.
    """

    def _raw(self, root: Path, at: Path, *extra: str) -> Any:
        return CliRunner().invoke(
            main,
            ["clean-room", BEAD, "--project", str(root), "--at", str(at), *extra],
        )

    def test_a_room_without_an_interpreter_is_a_finding_and_not_a_refusal(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)

        result = self._raw(root, tmp_path / "rooms")

        assert result.exit_code == 1, result.output
        assert (tmp_path / "rooms" / room_for(BEAD)).is_dir()
        assert "holds no interpreter of its own" in result.output

    def test_a_caller_who_declines_one_is_not_told_they_are_missing_it(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)

        result = self._raw(root, tmp_path / "rooms", "--no-environment")

        assert result.exit_code == 0, result.output
        assert "holds no interpreter of its own" not in result.output
        assert "the caller declined one" in result.output

    def test_the_extras_the_caller_names_reach_the_record(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)

        result = self._raw(
            root, tmp_path / "rooms", "--extras", "dev, tui", "--json"
        )

        payload = json.loads(result.stdout)
        assert payload["environment"]["asked"] == ["dev", "tui"]
        assert payload["environment"]["source"] == "caller"

    def test_an_empty_extras_request_is_an_environment_and_not_an_absent_one(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)

        result = self._raw(root, tmp_path / "rooms", "--extras", "", "--json")

        payload = json.loads(result.stdout)
        assert payload["environment"]["asked"] == []
        assert payload["environment"]["source"] == "caller"

    def test_both_shapes_carry_the_same_environment_verdict(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)

        human = self._raw(root, tmp_path / "rooms", "--no-environment")
        machine = self._raw(
            root, tmp_path / "rooms2", "--no-environment", "--json"
        )

        payload = json.loads(machine.stdout)
        assert payload["environment"]["built"] is False
        assert payload["environment"]["detail"] in human.output
        assert payload["exit_code"] == human.exit_code


class TestTheListARebuildDoesNotAskFor:
    """`--rebuild` re-copies the files the room recorded, and says it did.

    Measured by `beadloom-0mdo.37` while using the command on its own bead: 16
    `--carry` flags entered twice. The retyping costs seconds; what it buys is
    the wrong path being the cheaper one, which is BDL-UX #243 waiting to happen
    again. The property under test is that the LIST is reused and the CONTENT is
    not — a room whose files came from the previous room is #243 itself.
    """

    def test_a_rebuild_re_copies_the_recorded_files_from_the_working_tree(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        (root / "src" / "thing.py").write_text("VALUE = 2\n", encoding="utf-8")
        assert _run(root, tmp_path / "rooms", "--carry", "src/thing.py").exit_code == 0
        (root / "src" / "thing.py").write_text("VALUE = 3\n", encoding="utf-8")

        result = _run(root, tmp_path / "rooms", "--rebuild")

        assert result.exit_code == 0, result.output
        room = tmp_path / "rooms" / room_for(BEAD)
        assert (room / "src" / "thing.py").read_text(encoding="utf-8") == "VALUE = 3\n"
        assert "src/thing.py" in result.output
        assert "carry" in result.output

    def test_both_shapes_name_what_was_taken_from_the_replaced_room(
        self, tmp_path: Path, bd: Any
    ) -> None:
        # A caller who did not type a list has to be able to see that one was
        # used, or the room's contents are a fact with no stated source.
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        assert _run(root, tmp_path / "rooms", "--carry", "src/thing.py").exit_code == 0

        human = _run(root, tmp_path / "rooms", "--rebuild")
        structured = _run(root, tmp_path / "rooms", "--rebuild", "--json")

        assert human.exit_code == 0, human.output
        assert structured.exit_code == 0, structured.output
        data = json.loads(structured.stdout)
        assert data["reused"] == ["carry"]
        assert data["carried"] == ["src/thing.py"]
        assert "taken from the record of the room this replaced" in human.output

    def test_a_carry_named_beside_a_rebuild_replaces_the_recorded_one(
        self, tmp_path: Path, bd: Any
    ) -> None:
        bd({BEAD: "in_progress"})
        root = _project(tmp_path)
        (root / "other.txt").write_text("mine too\n", encoding="utf-8")
        assert _run(root, tmp_path / "rooms", "--carry", "src/thing.py").exit_code == 0

        result = _run(root, tmp_path / "rooms", "--rebuild", "--carry", "other.txt", "--json")

        data = json.loads(result.stdout)
        assert data["carried"] == ["other.txt"]
        assert data["reused"] == []
