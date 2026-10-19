"""Reading a ``.gitlab-ci.yml`` into the jobs it declares (BDL-083 S2a, RFC D6, BDL-UX #332).

The reader is the GitLab half of "where a project declares its legs". What it does not follow
-- an ``include:``, an ``extends:``, a ``parallel: matrix`` -- it names, because a pipeline read
in part and reported as read in full is the clean list this project refuses to hand back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gitlab_pipeline import (
    GITLAB_CI_FILE,
    load_gitlab_pipeline,
    python_of_image,
)

if TYPE_CHECKING:
    from pathlib import Path


def _pipeline(root: Path, body: str) -> Path:
    path = root / GITLAB_CI_FILE
    path.write_text(body, encoding="utf-8")
    return path


class TestJobsAreReadWithTheirImageAndCommands:
    def test_a_job_carries_its_image_and_every_command_in_order(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(
            tmp_path,
            "stages: [test]\n"
            "backend-tests:\n"
            "  stage: test\n"
            "  image: python:3.12-slim\n"
            "  before_script:\n"
            "    - pip install uv\n"
            "    - uv sync --frozen\n"
            "  script:\n"
            "    - uv run pytest tests\n"
            "  after_script: echo done\n",
        )

        # Act
        pipeline, failure = load_gitlab_pipeline(path)

        # Assert
        assert failure is None
        assert pipeline is not None
        (job,) = pipeline.jobs
        assert job.name == "backend-tests"
        assert job.image == "python:3.12-slim"
        assert job.commands == (
            "pip install uv",
            "uv sync --frozen",
            "uv run pytest tests",
            "echo done",
        )

    def test_reserved_keys_and_hidden_jobs_are_not_jobs(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(
            tmp_path,
            "stages: [test]\n"
            "variables: {A: b}\n"
            "workflow: {rules: [{when: always}]}\n"
            "cache: {paths: [.cache]}\n"
            ".template:\n"
            "  script: [echo hidden]\n"
            "lint:\n"
            "  image: node:22\n"
            "  script: [npm run lint]\n",
        )

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        assert [job.name for job in pipeline.jobs] == ["lint"]

    def test_a_job_inherits_the_default_image_and_before_script(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(
            tmp_path,
            "default:\n"
            "  image: {name: 'python:3.11', entrypoint: ['']}\n"
            "  before_script: [uv sync]\n"
            "tests:\n"
            "  script: [uv run pytest]\n"
            "own:\n"
            "  image: python:3.13\n"
            "  before_script: [pip install -e .]\n"
            "  script: [pytest]\n",
        )

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        jobs = {job.name: job for job in pipeline.jobs}
        assert jobs["tests"].image == "python:3.11"
        assert jobs["tests"].commands == ("uv sync", "uv run pytest")
        assert jobs["own"].image == "python:3.13"
        assert jobs["own"].commands == ("pip install -e .", "pytest")

    def test_a_top_level_image_is_the_default_when_default_names_none(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        path = _pipeline(tmp_path, "image: python:3.10\ntests:\n  script: [pytest]\n")

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        assert pipeline.jobs[0].image == "python:3.10"

    def test_a_job_with_no_image_anywhere_has_none(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(tmp_path, "tests:\n  script: [pytest]\n")

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        assert pipeline.jobs[0].image is None


class TestWhatTheReaderDoesNotFollowIsNamed:
    def test_an_include_is_a_pipeline_note(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(
            tmp_path,
            "include:\n  - local: ci/backend.yml\n"
            "tests:\n  image: python:3.12\n  script: [pytest]\n",
        )

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        assert len(pipeline.notes) == 1
        assert "include" in pipeline.notes[0]

    def test_extends_and_a_parallel_matrix_are_job_notes(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(
            tmp_path,
            ".base:\n  image: python:3.12\n"
            "tests:\n"
            "  extends: .base\n"
            "  parallel:\n"
            "    matrix:\n"
            "      - PY: ['3.11', '3.12']\n"
            "  script: [pytest]\n",
        )

        # Act
        pipeline, _ = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is not None
        notes = pipeline.jobs[0].notes
        assert any("extends" in note for note in notes)
        assert any("parallel" in note for note in notes)


class TestAPipelineThatCannotBeReadSaysWhy:
    def test_unparsable_yaml_is_a_failure(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(tmp_path, "tests: [unclosed\n")

        # Act
        pipeline, failure = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is None
        assert failure is not None
        assert "could not be parsed" in failure

    def test_a_document_that_is_not_a_mapping_is_a_failure(self, tmp_path: Path) -> None:
        # Arrange
        path = _pipeline(tmp_path, "- just\n- a list\n")

        # Act
        pipeline, failure = load_gitlab_pipeline(path)

        # Assert
        assert pipeline is None
        assert failure is not None
        assert "not a mapping" in failure


class TestThePythonAnImageNames:
    def test_the_official_image_tag_names_the_interpreter(self) -> None:
        assert python_of_image("python:3.12-slim") == "3.12"
        assert python_of_image("python:3.11") == "3.11"
        assert python_of_image("docker.io/library/python:3.10.14-bookworm") == "3.10"

    def test_an_image_that_names_no_minor_version_names_no_interpreter(self) -> None:
        assert python_of_image("python:3") is None
        assert python_of_image("python:latest") is None
        assert python_of_image("python") is None

    def test_another_image_names_no_interpreter(self) -> None:
        assert python_of_image("node:22-slim") is None
        assert python_of_image("ghcr.io/astral-sh/uv:python3.12-bookworm") is None
        assert python_of_image("$CI_REGISTRY_IMAGE/python:3.12") is None
