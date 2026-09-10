"""The room builder's refusals and its record, at the application level.

The behaviour is stated in `tests/acceptance/features/clean_room.feature`. What
is covered here is the set of named refusals a scenario would only restate — a
carried path that escapes the project, a directory named instead of a file, a
repository with no commit — and the record the rebuild guard reads. Each is a
branch an agent reaches by a plausible mistake, and each has to answer with its
own name rather than with a stack trace.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.waves import (
    REFUSAL_FILE_OUTSIDE,
    REFUSAL_NO_COMMIT,
    REFUSAL_NOT_A_FILE,
    REQUEST_KEY,
    ROOM_MARKER,
    RoomRequest,
    build_room,
    room_invocation,
    room_owner,
    room_path,
    room_request,
)

if TYPE_CHECKING:
    from pathlib import Path

BEAD = "beadloom-x.1"


def _repo(root: Path, *, commit: bool = True) -> Path:
    root.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "T"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)  # noqa: S607
        subprocess.run(
            ["git", "commit", "-q", "-m", "base"],  # noqa: S607
            cwd=root,
            check=True,
            capture_output=True,
        )
    return root


class TestTheCarriedPaths:
    def test_a_path_escaping_the_project_is_refused_by_name(self, tmp_path: Path) -> None:
        root = _repo(tmp_path / "project")
        (tmp_path / "elsewhere.txt").write_text("not ours\n", encoding="utf-8")

        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            carry=("../elsewhere.txt",),
        )

        assert build.refusal == REFUSAL_FILE_OUTSIDE
        assert not build.built
        assert not build.path.exists()

    def test_a_directory_is_refused_rather_than_copied_whole(self, tmp_path: Path) -> None:
        root = _repo(tmp_path / "project")

        build = build_room(
            bead_id=BEAD, project_root=root, parent=tmp_path / "rooms", carry=("src",)
        )

        assert build.refusal == REFUSAL_NOT_A_FILE
        # The reason is stated, because "name your files" is the instruction that
        # keeps a neighbour's work out of a room and a directory copy is how it
        # gets in.
        assert "neighbour" in build.detail


class TestTheCommitARoomIsBuiltFrom:
    def test_a_repository_with_no_commit_builds_no_room(self, tmp_path: Path) -> None:
        root = _repo(tmp_path / "project", commit=False)

        build = build_room(bead_id=BEAD, project_root=root, parent=tmp_path / "rooms")

        assert build.refusal == REFUSAL_NO_COMMIT
        assert build.commit is None
        assert not build.path.exists()

    def test_a_directory_that_is_not_a_repository_builds_no_room(
        self, tmp_path: Path
    ) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()

        build = build_room(bead_id=BEAD, project_root=plain, parent=tmp_path / "rooms")

        assert build.refusal == REFUSAL_NO_COMMIT


class TestTheRecordTheRebuildGuardReads:
    def test_every_way_of_not_being_a_room_answers_the_same(self, tmp_path: Path) -> None:
        # One answer, because they license one action: leave the directory alone.
        empty = tmp_path / "empty"
        empty.mkdir()
        assert room_owner(empty) is None

        broken = tmp_path / "broken"
        broken.mkdir()
        (broken / ROOM_MARKER).write_text("{ not json", encoding="utf-8")
        assert room_owner(broken) is None

        listed = tmp_path / "listed"
        listed.mkdir()
        (listed / ROOM_MARKER).write_text(json.dumps(["a"]), encoding="utf-8")
        assert room_owner(listed) is None

        anonymous = tmp_path / "anonymous"
        anonymous.mkdir()
        (anonymous / ROOM_MARKER).write_text(json.dumps({"bead": ""}), encoding="utf-8")
        assert room_owner(anonymous) is None

    def test_a_built_room_records_both_interpreters_and_its_carried_files(
        self, tmp_path: Path
    ) -> None:
        root = _repo(tmp_path / "project")
        (root / "src" / "thing.py").write_text("VALUE = 2\n", encoding="utf-8")

        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            carry=("src/thing.py",),
        )

        record = json.loads((build.path / ROOM_MARKER).read_text(encoding="utf-8"))
        assert record["bead"] == BEAD
        assert record["carried"] == ["src/thing.py"]
        assert record["commit"] == build.commit
        # Two interpreters, because they are not the same one: what the suite
        # will run under, and what built the room.
        assert record["interpreter"]["invocation"]
        assert record["interpreter"]["built_by"]["executable"]


class TestTheDerivedPath:
    def test_the_path_is_the_parent_plus_the_beads_own_room_name(
        self, tmp_path: Path
    ) -> None:
        assert room_path(tmp_path, BEAD) == tmp_path / f"room-{BEAD}"

    def test_the_invocation_names_the_rooms_sources_and_its_tests(
        self, tmp_path: Path
    ) -> None:
        room = tmp_path / "room-x"
        lines = room_invocation(room)

        assert all(f"PYTHONPATH={room / 'src'}" in line for line in lines)
        assert str(room / "tests") in lines[-1]


class TestAHalfBuiltRoomIsRemoved:
    def test_a_build_that_fails_partway_leaves_no_directory_behind(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A half-built room would be refused by the NEXT attempt, for a reason
        that has nothing to do with a neighbour — the rollback is what keeps the
        `already_exists` refusal meaning what it says.
        """
        from beadloom.application.waves import clean_room as module

        root = _repo(tmp_path / "project")

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("the disk said no")

        monkeypatch.setattr(module, "_write_marker", _boom)

        with pytest.raises(OSError, match="the disk said no"):
            build_room(bead_id=BEAD, project_root=root, parent=tmp_path / "rooms")

        assert not (tmp_path / "rooms" / f"room-{BEAD}").exists()


class TestTheRequestARoomRecords:
    """What a rebuild reads back, and what it does when the record cannot say.

    The behaviour is stated in `clean_room_rebuild.feature`. Covered here is the
    record itself: the shapes a marker can take that a scenario would only
    restate, and the room built by a version that did not record a request.
    """

    def test_the_request_is_recorded_apart_from_what_the_build_did(
        self, tmp_path: Path
    ) -> None:
        # A room given no environment records no extras CHOICE at all, so the
        # pinned set survives only because the request is recorded separately.
        root = _repo(tmp_path / "project")

        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            carry=("src/thing.py",),
            extras=("dev",),
            environment=False,
        )

        record = json.loads((build.path / ROOM_MARKER).read_text(encoding="utf-8"))
        assert record[REQUEST_KEY] == {
            "carry": ["src/thing.py"],
            "extras": ["dev"],
            "environment": False,
        }
        assert record["environment"]["asked"] == []

    def test_extras_nobody_named_are_recorded_as_named_by_nobody(
        self, tmp_path: Path
    ) -> None:
        # `null` and `[]` are two requests: derive them, and install none. A
        # rebuild reuses the second and re-derives the first, so recording one
        # for the other would pin a set nobody named.
        root = _repo(tmp_path / "project")

        derived = build_room(
            bead_id=BEAD, project_root=root, parent=tmp_path / "derived"
        )
        pinned = build_room(
            bead_id=BEAD, project_root=root, parent=tmp_path / "pinned", extras=()
        )

        assert room_request(derived.path) is not None
        assert room_request(derived.path).extras is None  # type: ignore[union-attr]
        assert room_request(pinned.path).extras == ()  # type: ignore[union-attr]

    def test_a_room_recorded_before_requests_were_rebuilds_from_its_carried_list(
        self, tmp_path: Path
    ) -> None:
        """The alternative is a rebuild that silently carries nothing, which is
        the failure the reuse exists to prevent arriving by another door."""
        root = _repo(tmp_path / "project")
        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            carry=("src/thing.py",),
        )
        record = json.loads((build.path / ROOM_MARKER).read_text(encoding="utf-8"))
        del record[REQUEST_KEY]
        (build.path / ROOM_MARKER).write_text(json.dumps(record), encoding="utf-8")
        (root / "src" / "thing.py").write_text("VALUE = 9\n", encoding="utf-8")

        again = build_room(
            bead_id=BEAD, project_root=root, parent=tmp_path / "rooms", rebuild=True
        )

        assert again.built, again.detail
        assert again.carried == ("src/thing.py",)
        assert again.reused == ("carry",)
        assert (again.path / "src" / "thing.py").read_text(encoding="utf-8") == "VALUE = 9\n"

    def test_a_record_that_cannot_state_a_request_states_an_empty_one(
        self, tmp_path: Path
    ) -> None:
        # A marker is a file on disk another tool may have written. A shape this
        # reader cannot use must leave the room deletable and rebuildable, with
        # a request the caller states, rather than raise out of the rebuild.
        room = tmp_path / "room"
        room.mkdir()
        (room / ROOM_MARKER).write_text(
            json.dumps({"bead": BEAD, REQUEST_KEY: {"carry": "src/thing.py"}}),
            encoding="utf-8",
        )

        assert room_request(room) == RoomRequest(carry=(), extras=None, environment=True)
        assert room_request(tmp_path / "absent") is None
