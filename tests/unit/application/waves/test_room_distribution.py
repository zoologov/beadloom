"""The Python project a clean room measures, how it is installed, and the hint it prints.

BDL-083 S2b (``beadloom-cptm``), RFC D6, BDL-UX #333 and #311. The scenarios in
``tests/acceptance/application/wave-plan/clean_room_of_a_monorepo.feature`` build a real
environment from the monorepo fixture's lock. What is covered here is what they cannot reach
cheaply: which project owns the carried files when several could, the install command each
arrangement produces without running it, and the hint a room prints for a layout it did not
build an environment for.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from beadloom.application.rooms import leg_installs
from beadloom.application.waves import room_invocation
from beadloom.application.waves.room_distribution import (
    ROOT_DIRECTORY,
    RoomDistribution,
    owning_distribution,
)
from beadloom.application.waves.room_env import (
    SOURCE_LEGS,
    ExtrasChoice,
    build_environment,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_PACKAGING = '[project]\nname = "{name}"\nversion = "0.1.0"\n'


def _python_project(directory: Path, name: str, *, locked: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pyproject.toml").write_text(_PACKAGING.format(name=name), encoding="utf-8")
    if locked:
        (directory / "uv.lock").write_text("version = 1\n", encoding="utf-8")


def _scan_paths(root: Path, *paths: str) -> None:
    """Declare *paths* as the project's scan paths, where Python projects are looked for."""
    (root / ".beadloom").mkdir()
    listed = "".join(f"  - {path}\n" for path in paths)
    (root / ".beadloom" / "config.yml").write_text(f"scan_paths:\n{listed}", encoding="utf-8")


def _file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("VALUE = 1\n", encoding="utf-8")


class TestTheProjectThatOwnsTheCarriedFiles:
    def test_a_carried_file_under_a_nested_project_chooses_that_project(
        self, tmp_path: Path
    ) -> None:
        _python_project(tmp_path / "backend", "backend", locked=True)
        _file(tmp_path / "backend" / "src" / "digest" / "sections.py")
        _scan_paths(tmp_path, "backend/src")

        found = owning_distribution(tmp_path, ("backend/src/digest/sections.py",))

        assert found.directory == "backend"
        assert found.packaging == "backend/pyproject.toml"
        assert found.lock == "backend/uv.lock"

    def test_the_deepest_project_owns_a_file_two_projects_enclose(self, tmp_path: Path) -> None:
        _python_project(tmp_path, "root")
        _python_project(tmp_path / "backend", "backend")
        _scan_paths(tmp_path, "backend")

        found = owning_distribution(tmp_path, ("backend/app.py",))

        assert found.directory == "backend"

    def test_files_in_two_projects_choose_the_one_owning_more_and_name_the_other(
        self, tmp_path: Path
    ) -> None:
        _python_project(tmp_path / "api", "api")
        _python_project(tmp_path / "worker", "worker")
        _scan_paths(tmp_path, "api", "worker")

        found = owning_distribution(tmp_path, ("worker/a.py", "worker/b.py", "api/c.py"))

        assert found.directory == "worker"
        assert any("api/pyproject.toml" in note for note in found.notes), found.notes

    def test_no_carried_file_falls_back_to_the_project_the_census_reads(
        self, tmp_path: Path
    ) -> None:
        _python_project(tmp_path, "root", locked=True)

        found = owning_distribution(tmp_path, ())

        assert found.directory == ROOT_DIRECTORY
        assert found.lock == "uv.lock"

    def test_a_project_without_a_lock_names_none(self, tmp_path: Path) -> None:
        _python_project(tmp_path / "backend", "backend")
        _scan_paths(tmp_path, "backend")

        assert owning_distribution(tmp_path, ("backend/x.py",)).lock is None


def _recording(monkeypatch: pytest.MonkeyPatch, *, uv: bool = True) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "beadloom.application.waves.room_env.shutil.which",
        lambda _: "/bin/uv" if uv else None,
    )

    def _run(command: list[str], **kwargs: Any) -> Any:
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 1, "", "stopped by the test")

    monkeypatch.setattr("beadloom.application.waves.room_env.subprocess.run", _run)
    return calls


_BACKEND = RoomDistribution(
    directory="backend",
    packaging="backend/pyproject.toml",
    lock="backend/uv.lock",
    why="it owns 1 of the 1 carried file(s)",
)


class TestTheInstallACommandOfTheLock:
    def test_a_locked_project_is_synced_frozen_from_its_own_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _recording(monkeypatch)

        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(extras=("dev", "tui"), source=SOURCE_LEGS, why="legs"),
            otherwise="/usr/bin/python3",
            distribution=_BACKEND,
        )

        assert calls[0]["command"] == [
            "uv",
            "sync",
            "--frozen",
            "--extra",
            "dev",
            "--extra",
            "tui",
        ]
        assert calls[0]["cwd"] == tmp_path / "backend"
        assert calls[0]["env"]["UV_PROJECT_ENVIRONMENT"] == str(tmp_path / "backend" / ".venv")
        assert "VIRTUAL_ENV" not in calls[0]["env"]
        assert built.lock == "backend/uv.lock"
        assert "uv sync --frozen" in built.resolution

    def test_the_trees_own_interpreter_is_kept_when_the_caller_names_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _recording(monkeypatch)

        build_environment(
            room=tmp_path,
            choice=ExtrasChoice(source=SOURCE_LEGS, why="legs"),
            otherwise="/tree/backend/.venv/bin/python",
            distribution=_BACKEND,
            interpreter="/tree/backend/.venv/bin/python",
        )

        assert calls[0]["command"][-2:] == ["--python", "/tree/backend/.venv/bin/python"]

    def test_a_project_without_a_lock_is_resolved_afresh_and_says_so(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _recording(monkeypatch)
        unlocked = RoomDistribution(
            directory="backend", packaging="backend/pyproject.toml", lock=None, why="w"
        )

        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(source=SOURCE_LEGS, why="legs"),
            otherwise="/usr/bin/python3",
            distribution=unlocked,
        )

        assert calls[0]["command"][:2] == ["uv", "venv"]
        assert calls[0]["cwd"] == tmp_path / "backend"
        assert built.lock is None
        assert "outside any lock" in built.resolution
        assert "backend/pyproject.toml" in built.resolution

    def test_a_lock_without_uv_is_resolved_afresh_and_names_why(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _recording(monkeypatch, uv=False)

        built = build_environment(
            room=tmp_path,
            choice=ExtrasChoice(source=SOURCE_LEGS, why="legs"),
            otherwise="/usr/bin/python3",
            distribution=_BACKEND,
        )

        assert calls[0]["command"][1:3] == ["-m", "venv"]
        assert built.lock is None
        assert "uv is not on PATH" in built.resolution
        assert "backend/uv.lock" in built.resolution


class TestTheHintIsDerivedFromTheProject:
    def _room(self, room: Path) -> None:
        backend = room / "backend"
        backend.mkdir(parents=True)
        (backend / "pyproject.toml").write_text(
            '[project]\nname = "b"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
            'pythonpath = ["src"]\n',
            encoding="utf-8",
        )
        _file(backend / "src" / "digest" / "__init__.py")
        (backend / "tests").mkdir()
        (backend / ".venv" / "bin").mkdir(parents=True)
        (backend / ".venv" / "bin" / "python").write_text("#!\n", encoding="utf-8")

    def test_the_hint_names_the_projects_sources_package_tests_and_interpreter(
        self, tmp_path: Path
    ) -> None:
        room = tmp_path / "room"
        self._room(room)

        lines = room_invocation(room, distribution=_BACKEND)

        python = str(room / "backend" / ".venv" / "bin" / "python")
        assert all(python in line for line in lines)
        assert all(f"PYTHONPATH={room / 'backend' / 'src'}" in line for line in lines)
        assert "import digest" in lines[0]
        assert lines[-1].endswith(f"-m pytest {room / 'backend' / 'tests'}")
        assert not any("beadloom" in line for line in lines)

    def test_a_project_declaring_no_test_paths_runs_pytest_over_its_directory(
        self, tmp_path: Path
    ) -> None:
        room = tmp_path / "room"
        _python_project(room, "flat")
        _file(room / "flat_pkg" / "__init__.py")

        lines = room_invocation(room)

        assert lines[-1].endswith(f"-m pytest {room}")
        assert f"PYTHONPATH={room} " in lines[-1]
        assert "import flat_pkg" in lines[0]

    def test_a_project_with_no_importable_package_prints_the_suite_line_only(
        self, tmp_path: Path
    ) -> None:
        room = tmp_path / "room"
        _python_project(room, "empty")

        lines = room_invocation(room)

        assert len(lines) == 1
        assert "-m pytest" in lines[0]


class TestTheLegsAPipelineDeclares:
    def test_a_gitlab_job_that_syncs_is_a_leg_when_gitlab_is_the_pipeline(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".gitlab-ci.yml").write_text(
            "backend-tests:\n  image: python:3.12-slim\n  script:\n"
            "    - cd backend\n    - uv sync --frozen --extra dev\n",
            encoding="utf-8",
        )

        legs = leg_installs(tmp_path)

        assert [(leg.source, leg.extras) for leg in legs] == [
            (".gitlab-ci.yml: backend-tests", ("dev",))
        ]

    def test_a_gitlab_pipeline_beside_github_workflows_is_set_aside(self, tmp_path: Path) -> None:
        (tmp_path / ".gitlab-ci.yml").write_text(
            "t:\n  image: python:3.12\n  script:\n    - uv sync --extra gl\n",
            encoding="utf-8",
        )
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text(
            "on: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - run: uv sync --extra gh\n",
            encoding="utf-8",
        )

        assert [leg.extras for leg in leg_installs(tmp_path)] == [("gh",)]
