"""`scope_to_commit` and `staged_paths` — the commit gate's two halves (#118).

`staged_paths` is exercised against a real git repository, because what it means
is entirely a fact about git's index; a double would prove the double.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.doc_sync.commit_scope import (
    GIT_SILENT,
    NOTHING_STAGED,
    scope_to_commit,
)
from beadloom.doc_sync.git_baseline import staged_paths

if TYPE_CHECKING:
    from pathlib import Path


def _pair(ref: str, doc: str, code: str) -> dict[str, Any]:
    return {"ref_id": ref, "doc_path": doc, "code_path": code, "status": "stale"}


_PAIRS = [
    _pair("alpha", "alpha.md", "src/alpha.py"),
    _pair("beta", "beta.md", "src/beta.py"),
]


class TestScopeToCommit:
    def test_only_the_pairs_this_commit_stages_are_kept(self) -> None:
        scope = scope_to_commit(_PAIRS, {"src/alpha.py"}, docs_dir="docs")
        assert [p["ref_id"] for p in scope.pairs] == ["alpha"]
        assert scope.not_checked == 1

    def test_staging_only_the_doc_keeps_the_pair(self) -> None:
        """The commit that fixes a stale pair stages the DOC, not the code."""
        scope = scope_to_commit(_PAIRS, {"docs/beta.md"}, docs_dir="docs")
        assert [p["ref_id"] for p in scope.pairs] == ["beta"]

    def test_a_commit_that_stages_nothing_indexed_says_why(self) -> None:
        scope = scope_to_commit(_PAIRS, {"README.md"}, docs_dir="docs")
        assert scope.pairs == ()
        assert scope.not_checked == 2
        assert scope.reason == NOTHING_STAGED

    def test_a_silent_git_narrows_nothing_and_says_so(self) -> None:
        """An absent answer must never read as 'nothing staged'."""
        scope = scope_to_commit(_PAIRS, None, docs_dir="docs")
        assert len(scope.pairs) == 2
        assert scope.not_checked == 0
        assert not scope.narrowed
        assert GIT_SILENT in scope.describe()

    def test_the_description_carries_both_numbers(self) -> None:
        scope = scope_to_commit(_PAIRS, {"src/alpha.py"}, docs_dir="docs")
        assert "1 pair(s) checked" in scope.describe()
        assert "1 pair(s) outside this commit were not checked" in scope.describe()

    def test_a_docs_dir_that_is_the_project_root_still_matches(self) -> None:
        scope = scope_to_commit(_PAIRS, {"alpha.md"}, docs_dir=".")
        assert [p["ref_id"] for p in scope.pairs] == ["alpha"]


class TestStagedPathsAgainstRealGit:
    def _repo(self, tmp_path: Path) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "t@example.invalid"],
            ["config", "user.name", "T"],
        ):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
        (root / "a.py").write_text("a = 1\n", encoding="utf-8")
        (root / "b.py").write_text("b = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)  # noqa: S607
        subprocess.run(
            ["git", "commit", "-q", "-m", "base"],  # noqa: S607
            cwd=root,
            check=True,
            capture_output=True,
        )
        return root

    def test_a_staged_edit_is_reported_and_an_unstaged_one_is_not(
        self, tmp_path: Path
    ) -> None:
        root = self._repo(tmp_path)
        (root / "a.py").write_text("a = 2\n", encoding="utf-8")
        (root / "b.py").write_text("b = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "a.py"], cwd=root, check=True, capture_output=True)  # noqa: S607
        assert staged_paths(root) == frozenset({"a.py"})

    def test_a_repository_with_no_commit_answers_nothing_rather_than_empty(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "fresh"
        root.mkdir()
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],  # noqa: S607
            cwd=root,
            check=True,
            capture_output=True,
        )
        assert staged_paths(root) is None

    def test_outside_a_work_tree_the_answer_is_unknown(self, tmp_path: Path) -> None:
        assert staged_paths(tmp_path) is None

    def test_a_staged_deletion_is_not_a_path_with_content_to_judge(
        self, tmp_path: Path
    ) -> None:
        root = self._repo(tmp_path)
        subprocess.run(["git", "rm", "-q", "a.py"], cwd=root, check=True, capture_output=True)  # noqa: S607
        assert staged_paths(root) == frozenset()


class TestSyncCheckStagedFlagIsWiredThroughOnePath:
    def test_the_flag_exists_on_the_command(self) -> None:
        from beadloom.services.commands.docsync import sync_check

        flags = {param.name for param in sync_check.params}
        assert "staged" in flags

    @pytest.mark.parametrize("template", ["_HOOK_TEMPLATE_WARN", "_HOOK_TEMPLATE_BLOCK"])
    def test_both_hook_modes_use_the_same_scope_header(self, template: str) -> None:
        from beadloom.services.commands import docsync

        assert docsync._HOOK_COMMIT_SCOPE in getattr(docsync, template)


class TestTheDeclaredSurfaceIsNotNarrowedByAReportFilter:
    """`--ref` and `--staged` restrict what is REPORTED, not what was declared.

    Counted after the filter, `beadloom sync-check --ref sync-check` on this
    repository read `declared surface SHRANK: 322 -> 6 pair(s)`, and
    `--record-surface` would have written that 6 into the committed ledger — the
    exact "surface got smaller in silence" failure the ledger exists to catch,
    manufactured by the tool. The count is now taken before any narrowing.
    """

    def test_the_surface_count_precedes_every_filter(self) -> None:
        import inspect

        from beadloom.services.commands import docsync

        # Click wraps the callback, so the ordering is read off the module text
        # between the command's own def and the next top-level statement.
        module = inspect.getsource(docsync)
        start = module.index("def sync_check(")
        source = module[start : module.index("\n# The four verdicts", start)]
        assert source.index("declared_pairs = len(") < source.index("if ref_filter:")
        assert source.index("declared_pairs = len(") < source.index("if staged:")
        assert "pair_count = declared_pairs" in source
