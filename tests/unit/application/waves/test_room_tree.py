"""What the working tree holds beyond HEAD, as a clean room reads it before it is built.

BDL-083 S2d (``beadloom-flrc``), RFC D6, BDL-UX #335. The scenarios in
``tests/acceptance/application/wave-plan/clean_room_carries_a_deletion.feature`` run the room
over the monorepo fixture. What is covered here is each kind of difference git can report
between the tree and HEAD, read one at a time, and the two answers the room needs about a
carried path before it decides to delete it: whether HEAD holds it, and as what.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from beadloom.application.waves.room_tree import (
    CHANGE_ADDED,
    CHANGE_DELETED,
    CHANGE_MODIFIED,
    CHANGE_UNTRACKED,
    HELD_AS_DIRECTORY,
    HELD_AS_FILE,
    TreeDifference,
    differences_not_carried,
    held_at_head,
    tree_differences,
)

if TYPE_CHECKING:
    from pathlib import Path

_TEXT = "utf-8"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _repository(root: Path) -> Path:
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "a.py").write_text("A = 1\n", encoding=_TEXT)
    (root / "pkg" / "b.py").write_text("B = 1\n", encoding=_TEXT)
    (root / "README.md").write_text("# p\n", encoding=_TEXT)
    (root / ".gitignore").write_text("*.db\n", encoding=_TEXT)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _changes(root: Path) -> dict[str, str]:
    differences = tree_differences(root)
    assert differences is not None
    return {difference.path: difference.change for difference in differences}


def test_a_clean_tree_differs_in_nothing(tmp_path: Path) -> None:
    assert tree_differences(_repository(tmp_path / "p")) == ()


def test_an_edit_is_a_modified_file(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    (root / "README.md").write_text("# changed\n", encoding=_TEXT)
    assert _changes(root) == {"README.md": CHANGE_MODIFIED}


def test_a_staged_edit_is_a_modified_file_too(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    (root / "README.md").write_text("# changed\n", encoding=_TEXT)
    _git(root, "add", "README.md")
    assert _changes(root) == {"README.md": CHANGE_MODIFIED}


def test_a_removed_file_is_deleted_staged_or_not(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    (root / "pkg" / "a.py").unlink()
    _git(root, "rm", "-q", "pkg/b.py")
    assert _changes(root) == {"pkg/a.py": CHANGE_DELETED, "pkg/b.py": CHANGE_DELETED}


def test_a_staged_rename_is_its_two_sides(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    _git(root, "mv", "pkg/a.py", "pkg/c.py")
    assert _changes(root) == {"pkg/a.py": CHANGE_DELETED, "pkg/c.py": CHANGE_ADDED}


def test_a_new_file_git_has_not_seen_is_untracked_and_an_ignored_one_is_not_listed(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path / "p")
    (root / "pkg" / "new.py").write_text("N = 1\n", encoding=_TEXT)
    (root / "index.db").write_bytes(b"\0")
    assert _changes(root) == {"pkg/new.py": CHANGE_UNTRACKED}


def test_a_path_with_a_space_is_read_whole(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    (root / "pkg" / "two words.py").write_text("W = 1\n", encoding=_TEXT)
    assert _changes(root) == {"pkg/two words.py": CHANGE_UNTRACKED}


def test_a_directory_git_does_not_hold_has_no_answer(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    assert tree_differences(tmp_path / "plain") is None


def test_head_holds_a_file_as_a_file_and_a_directory_as_a_directory(tmp_path: Path) -> None:
    root = _repository(tmp_path / "p")
    (root / "pkg" / "a.py").unlink()
    held = held_at_head(root, ("pkg/a.py", "pkg", "pkg/absent.py"))
    assert held == {"pkg/a.py": HELD_AS_FILE, "pkg": HELD_AS_DIRECTORY}


def test_head_holds_nothing_when_git_cannot_answer(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    assert held_at_head(tmp_path / "plain", ("a.py",)) == {}


def test_the_differences_left_out_are_the_ones_no_carried_path_names() -> None:
    differences = (
        TreeDifference("pkg/a.py", CHANGE_DELETED),
        TreeDifference("pkg/c.py", CHANGE_ADDED),
        TreeDifference("docs/x.md", CHANGE_MODIFIED),
    )
    left_out = differences_not_carried(differences, ("pkg/a.py", "pkg/c.py"))
    assert left_out == (TreeDifference("docs/x.md", CHANGE_MODIFIED),)
