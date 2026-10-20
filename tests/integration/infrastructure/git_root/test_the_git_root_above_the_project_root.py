"""Where the git root stands against the project root, read from git (BDL-083 S2e, #325).

``beadloom-7pd6``. Real repositories, the real ``git``: a project root at the git root, one
below it, one in a linked worktree, one outside any repository, and one with no ``git`` on
``PATH``. Only the nested one answers with a root; every other answer is ``None``, and the
sentence every refusing surface prints names both paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure.git_root import NestedRoot, nested_root
from tests.support.committed_project import commit_project, git

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _repository(path: Path) -> Path:
    (path / "app").mkdir(parents=True)
    (path / "app" / "main.py").write_text("x = 1\n", encoding="utf-8")
    commit_project(path)
    return path


def test_a_project_root_at_the_git_root_is_not_nested(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")

    assert nested_root(repository) is None


def test_a_project_root_below_the_git_root_names_the_git_root(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")

    found = nested_root(repository / "app")

    assert found == NestedRoot(
        project_root=(repository / "app").resolve(), git_root=repository.resolve()
    )


def test_two_levels_below_the_git_root_names_the_same_git_root(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    deeper = repository / "app" / "frontend"
    deeper.mkdir()

    found = nested_root(deeper)

    assert found is not None
    assert found.git_root == repository.resolve()


def test_a_linked_worktree_at_its_own_root_is_not_nested(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    worktree = tmp_path / "worktree"
    git(repository, "worktree", "add", "-q", str(worktree))

    assert nested_root(worktree) is None
    assert nested_root(worktree / "app") is not None


def test_a_directory_outside_any_repository_is_not_nested(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()

    assert nested_root(plain) is None


def test_no_git_on_path_is_not_read_as_nested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path / "repository")
    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    assert nested_root(repository / "app") is None


def test_the_sentence_names_both_roots_and_the_rule(tmp_path: Path) -> None:
    found = NestedRoot(project_root=tmp_path / "repo" / "app", git_root=tmp_path / "repo")

    sentence = found.sentence()

    assert sentence.startswith("the git root is above the project root")
    assert str(tmp_path / "repo" / "app") in sentence
    assert f"git root {tmp_path / 'repo'}" in sentence
    assert "the project root must be the git root" in sentence
