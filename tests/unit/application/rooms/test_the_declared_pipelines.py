"""The pipeline files a room census reads are declared, never guessed (BDL-083 S2F1, RFC D6).

D6 as amended on 2026-10-19 by the owner's ruling: S2a read ``.github/workflows`` first and
set ``.gitlab-ci.yml`` aside whenever both were in the tree, a choice of forge the census made
on the project's behalf. ``.beadloom/config.yml`` now carries ``rooms.pipelines``, a list of
``github`` and/or ``gitlab``. Unset, every pipeline file present is read; set, the named ones
only, a present file the key leaves out is set aside naming the key, and a name with no file
in the tree is a named line rather than an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.pipeline_sources import pipeline_sources

if TYPE_CHECKING:
    from pathlib import Path


def _gitlab(root: Path) -> None:
    (root / ".gitlab-ci.yml").write_text(
        "t:\n  image: python:3.12\n  script: [pytest]\n", encoding="utf-8"
    )


def _github(root: Path) -> None:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ci.yml").write_text("jobs: {}\n", encoding="utf-8")


def _declare(root: Path, body: str) -> None:
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(body, encoding="utf-8")


class TestWithNoDeclarationEveryFilePresentIsRead:
    def test_both_files_are_read_and_nothing_is_set_aside(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert [path.name for path in sources.workflows] == ["ci.yml"]
        assert sources.gitlab == tmp_path / ".gitlab-ci.yml"
        assert sources.notes == ()

    def test_a_config_without_the_key_reads_both(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "scan_paths:\n- src\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.gitlab is not None
        assert sources.workflows

    def test_no_pipeline_is_no_source(self, tmp_path: Path) -> None:
        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert not sources.declared
        assert sources.notes == ()


class TestTheKeyNamesTheFilesRead:
    def test_github_sets_the_gitlab_file_aside_naming_the_key(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: [github]\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.gitlab is None
        assert [path.name for path in sources.workflows] == ["ci.yml"]
        (note,) = sources.set_aside
        assert note.source == ".gitlab-ci.yml"
        assert "`rooms.pipelines`" in note.why

    def test_gitlab_sets_the_workflows_aside_naming_the_key(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: [gitlab]\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows == ()
        assert sources.gitlab is not None
        (note,) = sources.set_aside
        assert note.source == ".github/workflows"
        assert "`rooms.pipelines`" in note.why

    def test_a_named_pipeline_with_no_file_is_a_named_line(self, tmp_path: Path) -> None:
        # Arrange
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: [github, gitlab]\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows
        assert sources.set_aside == ()
        (note,) = sources.missing
        assert note.source == ".gitlab-ci.yml"
        assert "`rooms.pipelines` names `gitlab`" in note.why

    def test_an_empty_list_reads_nothing_and_sets_every_file_aside(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: []\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert not sources.declared
        assert {note.source for note in sources.set_aside} == {
            ".gitlab-ci.yml",
            ".github/workflows",
        }


class TestAnUnusableDeclarationIsNamed:
    def test_a_name_outside_the_vocabulary_is_refused_and_the_rest_kept(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: [github, jenkins]\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows
        assert sources.gitlab is None
        (refused,) = sources.refused
        assert "rooms.pipelines[1]" in refused.why
        assert "`jenkins`" in refused.why

    def test_a_scalar_is_refused_and_every_file_present_is_read(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _github(tmp_path)
        _declare(tmp_path, "rooms:\n  pipelines: github\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.workflows
        assert sources.gitlab is not None
        (refused,) = sources.refused
        assert "not a list" in refused.why

    def test_a_key_the_block_does_not_read_is_refused(self, tmp_path: Path) -> None:
        # Arrange
        _gitlab(tmp_path)
        _declare(tmp_path, "rooms:\n  pipeline: [github]\n")

        # Act
        sources = pipeline_sources(tmp_path)

        # Assert
        assert sources.gitlab is not None
        (refused,) = sources.refused
        assert "`pipeline:`" in refused.why
