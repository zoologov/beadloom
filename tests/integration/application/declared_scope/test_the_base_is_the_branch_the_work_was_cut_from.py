"""BDL-083 S1d (``beadloom-fgu8``; RFC D4; BDL-UX #330, #344, #300).

The ref a branch's work is judged against. Measured on 9.0.0 on an outside
monorepo: a branch cut from a feature branch not yet merged was judged against the
trunk, so the parent's whole diff came back as 304 ``outside-the-declared-axes``
warnings about files the work item never touched, and the base was not printed.
The rule agreed with the owner (PRD ruling 4): ``--base`` when given, else the
merge-base with the branch the work was cut from, else the trunk — printed always.

Real git in a real repository, because what is under test is the git question
(which commit is the branch point, and which branch it belongs to); a double would
prove the double. Every case passes its environment explicitly, so a run inside a
pull request's CI job (where ``GITHUB_HEAD_REF`` is set) judges the same repository.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.scope_base import (
    BASE_EXPLICIT,
    BASE_PARENT,
    BASE_TRUNK,
    scope_base,
    trunk_ref,
    working_branch,
)
from beadloom.doc_sync.git_baseline import paths_changed_since

if TYPE_CHECKING:
    from pathlib import Path

#: No CI variable at all: the developer's own shell.
_NO_CI: dict[str, str] = {}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by this test
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _commit(root: Path, path: str, message: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{message}\n", encoding="utf-8")
    _git(root, "add", path)
    _git(root, "commit", "-q", "-m", message)


@pytest.fixture
def stacked(tmp_path: Path) -> Path:
    """``main`` <- ``features/W1`` (two files, unmerged) <- ``features/W2`` (one file)."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "base.txt", "the project")
    _git(root, "switch", "-q", "-c", "features/W1")
    _commit(root, "parent/one.txt", "parent one")
    _commit(root, "parent/two.txt", "parent two")
    _git(root, "switch", "-q", "-c", "features/W2")
    _commit(root, "own/work.txt", "own work")
    return root


def _forget_how_branches_were_made(root: Path) -> None:
    """Remove the reflogs, as a fresh clone or a CI checkout has none of this machine's."""
    shutil.rmtree(root / ".git" / "logs")


class TestABranchCutFromAnUnmergedBranch:
    def test_its_base_is_the_merge_base_with_the_parent(self, stacked: Path) -> None:
        base = scope_base(stacked, environ=_NO_CI)
        assert base.kind == BASE_PARENT
        assert base.parent == "features/W1"
        fork = _git(stacked, "merge-base", "HEAD", "features/W1")
        assert _git(stacked, "rev-parse", base.ref) == fork

    def test_only_its_own_files_are_judged(self, stacked: Path) -> None:
        base = scope_base(stacked, environ=_NO_CI)
        assert paths_changed_since(stacked, base.ref) == frozenset({"own/work.txt"})

    def test_the_parent_s_files_are_counted_as_the_parent_s(self, stacked: Path) -> None:
        assert scope_base(stacked, environ=_NO_CI).parent_files == 2

    def test_the_description_names_the_base_the_parent_and_the_count(self, stacked: Path) -> None:
        described = scope_base(stacked, environ=_NO_CI).describe()
        assert "features/W1" in described
        assert "merge-base" in described
        assert "2 file(s) attributed to the parent branch" in described

    def test_a_start_point_named_on_the_command_line_is_read_too(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _commit(root, "base.txt", "the project")
        _git(root, "branch", "features/W1")
        _git(root, "switch", "-q", "features/W1")
        _commit(root, "parent/one.txt", "parent one")
        _git(root, "switch", "-q", "main")
        _git(root, "switch", "-q", "-c", "features/W2", "features/W1")
        _commit(root, "own/work.txt", "own work")
        base = scope_base(root, environ=_NO_CI)
        assert (base.kind, base.parent) == (BASE_PARENT, "features/W1")

    def test_without_a_reflog_the_nearest_branch_holding_the_fork_is_found(
        self, stacked: Path
    ) -> None:
        _forget_how_branches_were_made(stacked)
        base = scope_base(stacked, environ=_NO_CI)
        assert (base.kind, base.parent) == (BASE_PARENT, "features/W1")

    def test_a_copy_of_this_branch_is_not_its_parent(self, stacked: Path) -> None:
        _git(stacked, "branch", "backup")
        _forget_how_branches_were_made(stacked)
        base = scope_base(stacked, environ=_NO_CI)
        assert base.parent == "features/W1"

    def test_in_ci_the_pull_request_s_target_names_the_parent(self, stacked: Path) -> None:
        _git(stacked, "checkout", "-q", "--detach")
        _forget_how_branches_were_made(stacked)
        _git(stacked, "branch", "-q", "-D", "features/W2")
        environ = {"GITHUB_HEAD_REF": "features/W2", "GITHUB_BASE_REF": "features/W1"}
        base = scope_base(stacked, environ=environ)
        assert (base.kind, base.parent) == (BASE_PARENT, "features/W1")


class TestABranchWhoseParentIsTheTrunk:
    def test_a_branch_cut_from_the_trunk_is_judged_against_the_trunk(self, stacked: Path) -> None:
        _git(stacked, "switch", "-q", "main")
        _git(stacked, "switch", "-q", "-c", "features/W3")
        _commit(stacked, "three.txt", "three")
        base = scope_base(stacked, environ=_NO_CI)
        assert (base.kind, base.ref, base.parent, base.parent_files) == (
            BASE_TRUNK,
            "main",
            None,
            0,
        )

    def test_the_trunk_is_named_as_the_trunk(self, stacked: Path) -> None:
        _git(stacked, "switch", "-q", "main")
        _git(stacked, "switch", "-q", "-c", "features/W3")
        assert "main (the trunk" in scope_base(stacked, environ=_NO_CI).describe()

    def test_a_parent_already_merged_into_the_trunk_is_the_trunk(self, stacked: Path) -> None:
        _git(stacked, "switch", "-q", "main")
        _git(stacked, "merge", "-q", "--no-ff", "-m", "merge W1", "features/W1")
        _git(stacked, "switch", "-q", "features/W2")
        assert scope_base(stacked, environ=_NO_CI).kind == BASE_TRUNK

    def test_in_ci_a_pull_request_into_the_trunk_is_judged_against_the_trunk(
        self, stacked: Path
    ) -> None:
        _forget_how_branches_were_made(stacked)
        _git(stacked, "branch", "-q", "-D", "features/W1")
        environ = {"GITHUB_HEAD_REF": "features/W2", "GITHUB_BASE_REF": "main"}
        assert scope_base(stacked, environ=environ).kind == BASE_TRUNK

    def test_outside_a_repository_the_trunk_is_named_and_nothing_is_counted(
        self, tmp_path: Path
    ) -> None:
        base = scope_base(tmp_path, environ=_NO_CI)
        assert (base.kind, base.ref, base.parent_files) == (BASE_TRUNK, "main", None)
        assert "no file was counted" in base.describe()


class TestABaseNamedByHand:
    def test_an_explicit_base_wins_over_the_parent(self, stacked: Path) -> None:
        base = scope_base(stacked, explicit="main", environ=_NO_CI)
        assert (base.kind, base.ref) == (BASE_EXPLICIT, "main")

    def test_an_explicit_base_still_counts_what_left_the_trunk_s_diff(self, stacked: Path) -> None:
        base = scope_base(stacked, explicit="features/W1", environ=_NO_CI)
        assert base.parent_files == 2
        assert "named by the caller" in base.describe()

    def test_an_explicit_base_git_cannot_resolve_is_kept_and_not_counted(
        self, stacked: Path
    ) -> None:
        base = scope_base(stacked, explicit="no-such-ref", environ=_NO_CI)
        assert (base.ref, base.parent_files) == ("no-such-ref", None)


class TestTheBranchTheWorkIsOn:
    def test_the_checked_out_branch_outside_ci(self, stacked: Path) -> None:
        assert working_branch(stacked, environ=_NO_CI) == "features/W2"

    def test_a_github_pull_request_names_its_head_branch_first(self, stacked: Path) -> None:
        assert working_branch(stacked, environ={"GITHUB_HEAD_REF": "features/PR"}) == (
            "features/PR"
        )

    def test_a_gitlab_merge_request_names_its_source_branch(self, stacked: Path) -> None:
        _git(stacked, "checkout", "-q", "--detach")
        environ = {"CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "features/MR"}
        assert working_branch(stacked, environ=environ) == "features/MR"

    def test_an_empty_variable_names_nothing(self, stacked: Path) -> None:
        assert working_branch(stacked, environ={"GITHUB_HEAD_REF": ""}) == "features/W2"

    def test_a_detached_head_outside_ci_names_no_branch(self, stacked: Path) -> None:
        _git(stacked, "checkout", "-q", "--detach")
        assert working_branch(stacked, environ=_NO_CI) is None


class TestTheTrunk:
    def test_the_local_trunk_without_a_remote(self, stacked: Path) -> None:
        assert trunk_ref(stacked) == "main"

    def test_the_remote_tracking_trunk_when_it_exists(self, stacked: Path) -> None:
        _git(stacked, "update-ref", "refs/remotes/origin/main", "main")
        assert trunk_ref(stacked) == "origin/main"


def test_the_suite_runs_outside_the_pull_request_it_is_tested_in() -> None:
    """The suite's own CI job sets these; ``tests/conftest.py`` removes them for every test."""
    import os

    from beadloom.application.scope_base import (
        HEAD_BRANCH_VARIABLES,
        TARGET_BRANCH_VARIABLES,
    )

    assert not [v for v in (*HEAD_BRANCH_VARIABLES, *TARGET_BRANCH_VARIABLES) if v in os.environ]
