"""The room census reads a GitLab pipeline and a nested Python project (BDL-083 S2a, RFC D6).

BDL-UX #332, measured on 9.0.0 over the monorepo fixture: `rooms` read `<root>/pyproject.toml`
and `.github/workflows` only, so a project with `backend/pyproject.toml` and `.gitlab-ci.yml`
declared 0 rooms and `ci` printed `0 of 0 declared room(s)`. Each room now names the file
and job it came from, and a project whose pipeline the census cannot read says so in one
reason rather than in a count of zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.rooms import derive_declared_rooms, pipeline_sources, take_census

if TYPE_CHECKING:
    from pathlib import Path

_BACKEND_JOB = (
    "backend-tests:\n"
    "  image: python:3.12-slim\n"
    "  before_script: [pip install uv, uv sync --frozen]\n"
    "  script: [uv run pytest tests]\n"
)


def _gitlab(root: Path, body: str) -> None:
    (root / ".gitlab-ci.yml").write_text(body, encoding="utf-8")


def _github(root: Path, body: str) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ci.yml").write_text(body, encoding="utf-8")


def _backend(root: Path) -> None:
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "scan_paths:\n- backend/src\n", encoding="utf-8"
    )
    (root / "backend" / "src").mkdir(parents=True)
    (root / "backend" / "pyproject.toml").write_text(
        '[project]\nname = "desk-backend"\nrequires-python = ">=3.12"\n', encoding="utf-8"
    )


class TestAGitlabJobIsARoom:
    def test_a_job_on_a_python_image_is_a_room_naming_its_source(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, _BACKEND_JOB)

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        (room,) = declared.rooms
        assert room.source == ".gitlab-ci.yml: backend-tests"
        assert dict(room.dimensions) == {"image": "python:3.12-slim", "python": "3.12"}

    def test_a_job_on_another_image_is_a_room_without_a_python(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, "lint:\n  image: node:22-slim\n  script: [npm ci]\n")

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        (room,) = declared.rooms
        assert dict(room.dimensions) == {"image": "node:22-slim"}

    def test_a_job_with_no_image_is_unresolved_and_no_room(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, "tests:\n  script: [pytest]\n")

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        assert declared.rooms == ()
        assert any(
            entry.source == ".gitlab-ci.yml: tests" and "image" in entry.why
            for entry in declared.unresolved
        )

    def test_what_the_reader_did_not_follow_is_unresolved(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(
            tmp_path,
            "include: [{local: ci/more.yml}]\n"
            "tests:\n  image: python:3.12\n  extends: .base\n  script: [pytest]\n",
        )

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        sources = {entry.source for entry in declared.unresolved}
        assert ".gitlab-ci.yml" in sources
        assert ".gitlab-ci.yml: tests" in sources

    def test_with_both_hosts_and_no_declaration_both_sets_of_legs_are_read(
        self, tmp_path: Path
    ) -> None:
        # Arrange: S2a read GitHub first and set this file aside; the owner's ruling of
        # 2026-10-19 (RFC D6, S2F1) withdrew that ordering -- which pipeline is read is
        # declared under `rooms.pipelines`, and with no key every file present is read.
        _gitlab(tmp_path, _BACKEND_JOB)
        _github(tmp_path, "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n")

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        assert [room.source for room in declared.rooms] == [
            ".github/workflows/ci.yml: build",
            ".gitlab-ci.yml: backend-tests",
        ]
        assert not [entry for entry in declared.unresolved if entry.source == ".gitlab-ci.yml"]

    def test_a_declaration_of_github_sets_the_gitlab_file_aside_naming_the_key(
        self, tmp_path: Path
    ) -> None:
        # Arrange: a project on one forge that keeps a mirror pipeline for the other, as
        # this repository does, and says so in its config.
        _gitlab(tmp_path, _BACKEND_JOB)
        _github(tmp_path, "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n")
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "rooms:\n  pipelines: [github]\n", encoding="utf-8"
        )

        # Act
        declared = derive_declared_rooms(tmp_path)

        # Assert
        assert [room.source for room in declared.rooms] == [".github/workflows/ci.yml: build"]
        set_aside = [entry for entry in declared.unresolved if entry.source == ".gitlab-ci.yml"]
        assert len(set_aside) == 1
        assert "not read" in set_aside[0].why
        assert "`rooms.pipelines`" in set_aside[0].why

    def test_a_declared_pipeline_with_no_file_is_not_derived_with_the_key_named(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        _github(tmp_path, "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n")
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "rooms:\n  pipelines: [gitlab]\n", encoding="utf-8"
        )

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.not_derived is not None
        assert "`rooms.pipelines` names `gitlab`" in census.not_derived
        assert "no `.github/workflows/*.yml` and no" not in census.not_derived

    def test_a_run_outside_the_image_does_not_enter_it_and_says_why(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, _BACKEND_JOB)

        # Act
        census = take_census(tmp_path)

        # Assert
        (comparison,) = census.comparisons
        assert not comparison.entered
        assert "image" in comparison.why


class TestAPipelineTheCensusCannotReadIsNamed:
    def test_no_pipeline_at_all_is_not_derived_with_both_files_named(self, tmp_path: Path) -> None:
        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.not_derived is not None
        assert census.not_derived.startswith("no readable pipeline")
        assert ".github/workflows" in census.not_derived
        assert ".gitlab-ci.yml" in census.not_derived

    def test_a_pipeline_of_another_host_is_named(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / "Jenkinsfile").write_text("pipeline {}\n", encoding="utf-8")

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.not_derived is not None
        assert "Jenkinsfile" in census.not_derived

    def test_an_unreadable_gitlab_pipeline_is_not_derived_and_unresolved(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        _gitlab(tmp_path, "tests: [unclosed\n")

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.not_derived is not None
        assert any(entry.source == ".gitlab-ci.yml" for entry in census.unresolved)

    def test_a_census_with_a_room_is_derived(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, _BACKEND_JOB)

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.not_derived is None


class TestThePackagingComesFromTheProjectFound:
    def test_the_floor_is_read_from_the_nested_project(self, tmp_path: Path) -> None:
        # Arrange
        _backend(tmp_path)
        _gitlab(tmp_path, _BACKEND_JOB)

        # Act
        census = take_census(tmp_path)

        # Assert
        assert census.floor == ">=3.12"
        sources = {entry.source for entry in census.unresolved}
        assert "backend/pyproject.toml" in sources
        assert "pyproject.toml" not in sources


class TestThePipelineSourcesAreChosenOnce:
    def test_only_a_gitlab_pipeline_is_read_as_gitlab(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path, _BACKEND_JOB)

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows == ()
        assert sources.gitlab == tmp_path / ".gitlab-ci.yml"
        assert sources.set_aside == ()

    def test_with_no_declaration_both_hosts_are_read(self, tmp_path: Path) -> None:
        # Arrange: the GitHub-first ordering S2a shipped is withdrawn (RFC D6, 2026-10-19).
        _gitlab(tmp_path, _BACKEND_JOB)
        _github(tmp_path, "jobs: {}\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert [path.name for path in sources.workflows] == ["ci.yml"]
        assert sources.gitlab == tmp_path / ".gitlab-ci.yml"
        assert sources.set_aside == ()

    def test_no_pipeline_is_no_source(self, tmp_path: Path) -> None:
        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows == ()
        assert sources.gitlab is None
        assert not sources.declared
