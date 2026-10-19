"""The commits a branch holds against a ref, each with its message and the paths it changed.

BDL-083 S1c (``beadloom-b23f``; RFC D3). The Gate's ownership report attributes a finding
to the bead whose commits changed its files, so git has to be asked which commits those
are. :mod:`beadloom.doc_sync.git_baseline` is the one reader of git in this domain, and
``None`` stays its answer for "git could not say", never "no commits".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.git_baseline import commits_since
from tests.support.committed_project import commit_project, git

if TYPE_CHECKING:
    from pathlib import Path

_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("A = 1\n", encoding="utf-8")
    (root / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
    commit_project(root)
    git(root, "branch", "-M", "main")
    git(root, "switch", "-q", "-c", "features/X")
    return root


def _commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, *_IDENTITY, "commit", "-q", "-m", message)


def test_each_commit_since_the_ref_carries_its_message_and_paths(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "src" / "a.py").write_text("A = 2\n", encoding="utf-8")
    _commit(root, "first (bd-1)\n\nwith a body")
    (root / "src" / "b.py").unlink()
    (root / "src" / "c.py").write_text("C = 1\n", encoding="utf-8")
    _commit(root, "second (bd-2)")

    commits = commits_since(root, "main")

    assert commits is not None
    assert [c.message.splitlines()[0] for c in commits] == ["second (bd-2)", "first (bd-1)"]
    assert commits[0].paths == frozenset({"src/b.py", "src/c.py"})
    assert commits[1].paths == frozenset({"src/a.py"})
    assert "with a body" in commits[1].message


def test_a_rename_counts_both_of_its_paths(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    git(root, "mv", "src/a.py", "src/renamed.py")
    _commit(root, "rename")

    commits = commits_since(root, "main")

    assert commits is not None
    assert commits[0].paths == frozenset({"src/a.py", "src/renamed.py"})


def test_a_branch_with_no_commit_of_its_own_holds_none(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    assert commits_since(root, "main") == ()


def test_an_unknown_ref_is_none_not_an_empty_branch(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    assert commits_since(root, "no-such-branch") is None


def test_outside_a_repository_git_cannot_say(tmp_path: Path) -> None:
    assert commits_since(tmp_path, "main") is None


def test_paths_are_relative_to_a_project_below_the_git_root(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "sub").mkdir()
    (root / "sub" / "x.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "a.py").write_text("A = 3\n", encoding="utf-8")
    _commit(root, "both")

    commits = commits_since(root / "sub", "main")

    assert commits is not None
    assert commits[0].paths == frozenset({"x.py"})


class TestATrailerIsReadAsGitParsesIt:
    """BDL-083 S1 fix 3 (``beadloom-7kas``; RFC D10): a commit names its bead in a trailer."""

    def test_the_values_of_the_named_trailer_are_read(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        (root / "src" / "a.py").write_text("A = 2\n", encoding="utf-8")
        _commit(root, "two beads\n\nBead: bd-1\nBead: bd-2\nCo-Authored-By: someone")

        commits = commits_since(root, "main", trailer="Bead")

        assert commits is not None
        assert commits[0].trailer_values == ("bd-1", "bd-2")

    def test_a_trailer_shaped_line_inside_the_body_is_not_a_trailer(self, tmp_path: Path) -> None:
        """Git reads trailers from the last paragraph only, and so does the reader."""
        root = _repository(tmp_path)
        (root / "src" / "a.py").write_text("A = 2\n", encoding="utf-8")
        _commit(root, "subject\n\nBead: bd-1\n\nthe slot released after bd-1, then more prose")

        commits = commits_since(root, "main", trailer="Bead")

        assert commits is not None
        assert commits[0].trailer_values == ()

    def test_no_trailer_asked_for_reads_none(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        (root / "src" / "a.py").write_text("A = 2\n", encoding="utf-8")
        _commit(root, "subject\n\nBead: bd-1")

        commits = commits_since(root, "main")

        assert commits is not None
        assert commits[0].trailer_values == ()

    def test_a_key_that_could_close_the_placeholder_is_refused(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        with pytest.raises(ValueError, match="not a trailer key"):
            commits_since(root, "main", trailer="Bead)%H")
