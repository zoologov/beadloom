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


class TestNothingStopsBeingEnforced:
    def test_the_push_gate_still_judges_the_whole_tree(self, tmp_path: Path) -> None:
        project = _git_project(tmp_path)
        CliRunner().invoke(main, ["install-hooks", "--project", str(project)])
        content = (project / ".git" / "hooks" / "pre-push").read_text(encoding="utf-8")
        assert "beadloom ci" in content
        assert "--staged" not in content
