"""The installed pre-commit hook judges the commit, not the tree (BDL-UX #118).

Parallel agents in one working tree do not conflict on disjoint FILES; they
conflict on the one hook, because it linted and doc-checked everything present.
These tests pin the boundary — commit gate judges the commit, push gate judges
the tree — and pin that the half it does not judge is stated rather than left to
be assumed clean.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _git_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    subprocess.run(  # noqa: S603
        ["git", "init", "-q", "-b", "main", str(project)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    return project


def _hook(project: Path, mode: str) -> str:
    result = CliRunner().invoke(
        main, ["install-hooks", "--mode", mode, "--project", str(project)]
    )
    assert result.exit_code == 0, result.output
    return (project / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")


@pytest.mark.parametrize("mode", ["warn", "block"])
class TestTheCommitGateJudgesTheCommit:
    def test_the_doc_check_is_scoped_to_what_the_commit_stages(
        self, tmp_path: Path, mode: str
    ) -> None:
        content = _hook(_git_project(tmp_path), mode)
        assert "sync-check --staged" in content

    def test_the_linters_read_the_staged_paths_rather_than_the_whole_tree(
        self, tmp_path: Path, mode: str
    ) -> None:
        content = _hook(_git_project(tmp_path), mode)
        assert "git diff --cached --name-only" in content
        assert "ruff check src/ tests/\n" not in content

    def test_the_hook_states_the_part_of_the_tree_it_did_not_judge(
        self, tmp_path: Path, mode: str
    ) -> None:
        content = _hook(_git_project(tmp_path), mode)
        assert "pre-push" in content
        assert "outside this commit" in content

    def test_the_hook_says_the_content_it_reads_is_the_working_tree_content(
        self, tmp_path: Path, mode: str
    ) -> None:
        """A partially staged file is judged including the part left behind."""
        content = _hook(_git_project(tmp_path), mode)
        assert "not the staged blobs" in content

    def test_the_coherence_block_still_runs_last(self, tmp_path: Path, mode: str) -> None:
        content = _hook(_git_project(tmp_path), mode)
        assert content.index("sync-check") < content.index("ACTIVE / tracker coherence")

    def test_the_hook_states_what_it_itself_added_to_the_commit(
        self, tmp_path: Path, mode: str
    ) -> None:
        """BDL-061.22's OBSERVATION C, measured by `.22`'s own commit.

        `active-sync --stage` stages the reconciled ACTIVE tables and the tracker
        export while the commit is in flight, and a pathspec commit does not
        exclude them: `.22` committed one file by explicit path and landed two.
        The hook then printed a confident count of what it did NOT judge and said
        nothing about the file it had just put IN. The count states the remainder;
        this line states the addition.
        """
        content = _hook(_git_project(tmp_path), mode)
        assert "staged_before=$(git diff --cached --name-only)" in content
        assert "ADDED these path(s) to this commit" in content
        assert content.index("staged_before=") < content.index("active-sync --stage")

    def test_the_unjudged_count_reads_the_status_rather_than_the_diff(
        self, tmp_path: Path, mode: str
    ) -> None:
        """FINDING BDL-061.22-4: `git diff --name-only` cannot see an untracked file."""
        content = _hook(_git_project(tmp_path), mode)
        assert "outside=$(git status --porcelain" in content
        assert "outside=$(git diff --name-only" not in content

    def test_the_hook_carries_the_marker_that_says_what_it_judges(
        self, tmp_path: Path, mode: str
    ) -> None:
        """An installed hook keeps its old behaviour until install-hooks re-runs.

        Nothing told a repository to re-run it, and `.21` observed its own S6
        commit judged by the whole-tree hook the change had just replaced. The
        marker is how `beadloom waves` can tell which hook a concurrent wave is
        about to commit through.
        """
        from beadloom.services.commands.docsync import _HOOK_SCOPE_MARKER

        assert _HOOK_SCOPE_MARKER in _hook(_git_project(tmp_path), mode)


class TestNothingStopsBeingEnforced:
    def test_the_push_gate_still_judges_the_whole_tree(self, tmp_path: Path) -> None:
        project = _git_project(tmp_path)
        CliRunner().invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-push").read_text(encoding="utf-8")
        assert "beadloom ci" in content
        assert "--staged" not in content
