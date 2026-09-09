"""The room's own interpreter, at the level a scenario would only restate.

The behaviour is stated in `tests/acceptance/features/room_environment.feature`,
which builds real environments over a real project. What is covered here is
everything that cannot be reached that way: the second installer, a create step
that fails, an environment read off a directory rather than off this process,
and the spellings of an install step this repository's own workflows do not use.

Each is a branch a room reaches on somebody else's machine, and a room that gets
one of them wrong reports a verdict taken under an interpreter nobody named,
which is BDL-UX #256 in one sentence.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application import rooms
from beadloom.application.rooms import (
    declared_extra_names,
    installed_extras,
    leg_installs,
)
from beadloom.application.waves import build_room, room_invocation
from beadloom.application.waves import clean_room as clean_room_module
from beadloom.application.waves.room_env import (
    INSTALLER_STDLIB,
    INSTALLER_UV,
    SOURCE_CALLER,
    SOURCE_LEGS,
    SOURCE_UNDERIVED,
    ExtrasChoice,
    build_environment,
    extras_a_room_installs,
    room_python,
    site_packages,
)

if TYPE_CHECKING:
    from pathlib import Path

BEAD = "beadloom-x.1"


def _pyproject(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(body, encoding="utf-8")
    return root


def _workflow(root: Path, name: str, body: str) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


def _job(name: str, run: str) -> str:
    return (
        f"name: w\non: [push]\njobs:\n  {name}:\n    runs-on: ubuntu-latest\n"
        f"    steps:\n      - run: {run}\n"
    )


class TestTheExtrasARoomInstalls:
    def test_the_caller_wins_over_every_leg(self, tmp_path: Path) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "ci.yml", _job("tests", "uv sync --extra dev --extra tui"))

        choice = extras_a_room_installs(root, ("watch",))

        assert choice.extras == ("watch",)
        assert choice.source == SOURCE_CALLER

    def test_an_empty_request_is_an_environment_and_not_an_absent_answer(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')

        choice = extras_a_room_installs(root, ())

        assert choice.extras == ()
        assert choice.label == "none"
        assert choice.source == SOURCE_CALLER

    def test_a_project_with_no_workflow_directory_derives_nothing(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')

        choice = extras_a_room_installs(root)

        assert choice.source == SOURCE_UNDERIVED
        assert choice.extras == ()
        assert "no leg" in choice.why

    def test_a_leg_that_installs_nothing_leaves_the_union_underived(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "ci.yml", _job("lint", "echo hello"))

        assert extras_a_room_installs(root).source == SOURCE_UNDERIVED

    def test_a_leg_installing_with_no_extras_declares_an_environment(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "ci.yml", _job("tests", "uv sync"))

        choice = extras_a_room_installs(root)

        assert choice.source == SOURCE_LEGS
        assert choice.extras == ()

    def test_all_extras_is_expanded_from_the_packaging(self, tmp_path: Path) -> None:
        root = _pyproject(
            tmp_path / "p",
            '[project]\nname = "thing"\n\n'
            "[project.optional-dependencies]\ndev = []\ntui = []\n",
        )
        _workflow(root, "ci.yml", _job("tests", "uv sync --all-extras"))

        assert extras_a_room_installs(root).extras == ("dev", "tui")

    def test_the_union_takes_every_leg_and_not_the_commonest(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "ci.yml", _job("site", "uv sync --extra dev"))
        _workflow(root, "b.yml", _job("more", "uv sync --extra dev"))
        _workflow(root, "c.yml", _job("tests", "uv sync --extra dev --extra tui"))

        # Two legs of three install `dev` alone. This repository's own shape:
        # four legs build a site or run a release gate and two run the suite,
        # so the commonest set is the one no verdict is taken under.
        assert extras_a_room_installs(root).extras == ("dev", "tui")


class TestTheExtrasAProjectDeclares:
    def test_the_table_may_be_the_last_one_in_the_file(self, tmp_path: Path) -> None:
        root = _pyproject(
            tmp_path / "p",
            '[project]\nname = "thing"\n\n'
            "[project.optional-dependencies]\ndev = []\nTUI = []\n",
        )

        assert declared_extra_names(root) == ("dev", "tui")

    def test_a_project_declaring_no_extras_answers_with_none(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')

        assert declared_extra_names(root) == ()

    def test_a_later_table_is_not_read_as_an_extra(self, tmp_path: Path) -> None:
        root = _pyproject(
            tmp_path / "p",
            '[project]\nname = "thing"\n\n'
            "[project.optional-dependencies]\ndev = []\n\n"
            '[tool.setuptools]\nwhere = ["src"]\n',
        )

        assert declared_extra_names(root) == ("dev",)

    def test_a_project_with_no_packaging_answers_with_none(
        self, tmp_path: Path
    ) -> None:
        assert declared_extra_names(tmp_path) == ()


class TestTheLegsThatInstall:
    def test_a_workflow_that_cannot_be_parsed_contributes_no_leg(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "broken.yml", "jobs: [this is not a mapping\n")
        _workflow(root, "ci.yml", _job("tests", "uv sync --extra dev"))

        installs = leg_installs(root)

        assert [leg.extras for leg in installs] == [("dev",)]

    def test_a_job_installing_through_a_local_action_names_no_extra(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(
            root,
            "ci.yml",
            "name: w\non: [push]\njobs:\n  gate:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: ./.github/actions/gate\n",
        )

        assert leg_installs(root) == ()

    def test_a_pip_install_of_this_project_is_a_leg(self, tmp_path: Path) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        _workflow(root, "ci.yml", _job("tests", "pip install -e '.[dev,tui]'"))

        assert [leg.extras for leg in leg_installs(root)] == [("dev", "tui")]


class TestTheExtrasOfAnotherEnvironment:
    """`installed_extras` must answer about the environment it is pointed at.

    A room builds an interpreter of its own, and reading THIS process's extras
    onto that room's record would state the extras of an environment no verdict
    was taken in. The metadata is files on disk, so it is read from a directory
    without importing anything that environment holds.
    """

    def _environment(self, tmp_path: Path, *distributions: tuple[str, str]) -> str:
        site = tmp_path / "site-packages"
        site.mkdir(parents=True)
        for name, metadata_text in distributions:
            info = site / f"{name}-1.0.dist-info"
            info.mkdir()
            (info / "METADATA").write_text(metadata_text, encoding="utf-8")
        return str(site)

    def test_the_extras_are_the_named_environments_and_not_this_process(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        site = self._environment(
            tmp_path,
            (
                "thing",
                "Metadata-Version: 2.1\nName: thing\nVersion: 1.0\n"
                "Provides-Extra: dev\nProvides-Extra: tui\n"
                'Requires-Dist: alpha; extra == "dev"\n'
                'Requires-Dist: beta; extra == "tui"\n',
            ),
            ("alpha", "Metadata-Version: 2.1\nName: alpha\nVersion: 1.0\n"),
        )

        found = installed_extras(root, search_path=(site,))

        assert found.resolved
        assert found.installed == ("dev",)
        assert [absent.extra for absent in found.absent] == ["tui"]

    def test_an_environment_without_the_project_is_unresolved_not_empty(
        self, tmp_path: Path
    ) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "thing"\n')
        site = self._environment(tmp_path)

        found = installed_extras(root, search_path=(site,))

        assert not found.resolved
        assert found.installed == ()

    def test_the_name_is_matched_canonically(self, tmp_path: Path) -> None:
        root = _pyproject(tmp_path / "p", '[project]\nname = "My_Thing"\n')
        site = self._environment(
            tmp_path,
            (
                "my_thing",
                "Metadata-Version: 2.1\nName: My-Thing\nVersion: 1.0\n"
                "Provides-Extra: dev\n"
                'Requires-Dist: alpha; extra == "dev"\n',
            ),
            ("alpha", "Metadata-Version: 2.1\nName: alpha\nVersion: 1.0\n"),
        )

        assert installed_extras(root, search_path=(site,)).installed == ("dev",)


class TestTheRoomsInterpreter:
    def test_a_room_without_one_answers_none_rather_than_a_path(
        self, tmp_path: Path
    ) -> None:
        assert room_python(tmp_path) is None
        assert site_packages(tmp_path) == ()

    def test_the_rooms_own_interpreter_precedes_the_projects(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "p"
        (project / ".venv" / "bin").mkdir(parents=True)
        (project / ".venv" / "bin" / "python").write_text("#!\n", encoding="utf-8")
        room = tmp_path / "room"
        (room / ".venv" / "bin").mkdir(parents=True)
        (room / ".venv" / "bin" / "python").write_text("#!\n", encoding="utf-8")

        lines = room_invocation(room, project_root=project)

        assert all(str(room / ".venv" / "bin" / "python") in line for line in lines)
        assert not any(str(project / ".venv") in line for line in lines)

    def test_the_projects_interpreter_is_named_when_the_room_holds_none(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "p"
        (project / ".venv" / "bin").mkdir(parents=True)
        (project / ".venv" / "bin" / "python").write_text("#!\n", encoding="utf-8")

        lines = room_invocation(tmp_path / "room", project_root=project)

        assert all(str(project / ".venv" / "bin" / "python") in line for line in lines)


class TestBuildingTheEnvironment:
    def test_an_underived_choice_builds_nothing_and_names_what_is_used_instead(
        self, tmp_path: Path
    ) -> None:
        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(why="no leg installs it"),
            otherwise="/somewhere/python",
        )

        assert not built.built
        assert built.python is None
        assert built.installer is None
        assert "/somewhere/python" in built.detail
        assert not (tmp_path / ".venv").exists()

    def test_a_create_step_that_fails_leaves_no_half_built_environment(
        self, tmp_path: Path
    ) -> None:
        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(extras=("dev",), source=SOURCE_CALLER, why="asked"),
            otherwise=str(tmp_path / "no-such-interpreter"),
        )

        assert not built.built
        assert built.python is None
        assert not (tmp_path / ".venv").exists()
        assert built.extras == ("dev",)

    def test_the_stdlib_installer_is_used_when_uv_is_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without ``uv`` the room still gets one, and says which tool built it.

        The two differ by about a factor of thirty in time — measured over this
        repository, 0.08 s plus 1.1 s against 1.84 s plus 39.6 s — so a report
        that does not name the installer hides a cost that decides whether a
        room is built at all.
        """
        monkeypatch.setattr(
            "beadloom.application.waves.room_env.shutil.which", lambda _: None
        )
        calls: list[list[str]] = []

        def _record(command: list[str], **_: Any) -> Any:
            calls.append(command)
            return subprocess.CompletedProcess(command, 1, "", "declined")

        monkeypatch.setattr(
            "beadloom.application.waves.room_env.subprocess.run", _record
        )

        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(extras=("dev",), source=SOURCE_CALLER, why="asked"),
            otherwise="/usr/bin/python3",
        )

        assert built.installer == INSTALLER_STDLIB
        assert calls == [["/usr/bin/python3", "-m", "venv", str(tmp_path / ".venv")]]
        assert "declined" in built.detail

    def test_uv_is_preferred_when_it_is_on_the_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "beadloom.application.waves.room_env.shutil.which", lambda _: "/bin/uv"
        )
        monkeypatch.setattr(
            "beadloom.application.waves.room_env.subprocess.run",
            lambda command, **_: subprocess.CompletedProcess(command, 1, "", "no"),
        )

        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(extras=("dev",), source=SOURCE_CALLER, why="asked"),
            otherwise="/usr/bin/python3",
        )

        assert built.installer == INSTALLER_UV


class TestWhatABuiltRoomRecords:
    def _repo(self, root: Path) -> Path:
        root.mkdir(parents=True)
        (root / "src").mkdir()
        (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "thing"\n', encoding="utf-8"
        )
        for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "t@example.invalid"],
            ["config", "user.name", "T"],
            ["add", "-A"],
            ["commit", "-q", "-m", "base"],
        ):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
        return root

    def test_a_caller_who_declines_one_is_told_so_rather_than_warned(
        self, tmp_path: Path
    ) -> None:
        root = self._repo(tmp_path / "p")

        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            environment=False,
        )

        assert build.built
        assert build.environment is not None
        assert not build.environment.built
        assert "declined" in build.environment.detail

    def test_the_marker_states_the_environment_and_not_only_the_files(
        self, tmp_path: Path
    ) -> None:
        root = self._repo(tmp_path / "p")

        build = build_room(
            bead_id=BEAD,
            project_root=root,
            parent=tmp_path / "rooms",
            environment=False,
        )

        record = clean_room_module.json.loads(
            (build.path / clean_room_module.ROOM_MARKER).read_text(encoding="utf-8")
        )
        assert record["environment"]["built"] is False
        assert record["environment"]["source"] == SOURCE_UNDERIVED
        assert record["environment"]["installer"] is None
        assert record["environment"]["python"] is None


@pytest.fixture(autouse=True)
def _clear_caches() -> Any:
    """Both caches are per-interpreter facts, and these tests name interpreters."""
    rooms._declared_requirements.cache_clear()
    rooms._installed_distributions.cache_clear()
    yield
    rooms._declared_requirements.cache_clear()
    rooms._installed_distributions.cache_clear()
