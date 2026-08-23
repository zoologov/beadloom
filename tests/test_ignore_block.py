"""The one-time `.gitignore` block naming Beadloom's generated working set (BDL-061.35).

Two decisions are pinned here, because both are defaults an adopter inherits:

* the block is written **once** and never rewritten, which is what makes deleting a
  line a real override rather than an edit Beadloom undoes on the next run;
* every pattern carries its reason in the file itself, since a bare pattern in
  someone else's ignore file is indistinguishable from a mistake.

`git check-ignore` is run for real (FAKES PROVE FAKES): the claim is about what git
does with the file, not about the text we wrote.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from beadloom.onboarding.ignore_block import (
    BLOCK_MARKER,
    GENERATED_WORKING_SET,
    IGNORE_RELPATH,
    ensure_ignore_block,
)

if TYPE_CHECKING:
    from pathlib import Path

FIRINGS_PATTERN = ".beadloom/guard-firings.jsonl"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)  # noqa: S603, S607


def _git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    return tmp_path


def _is_ignored(repo: Path, relpath: str) -> bool:
    """Ask git itself, on a path that exists, whether it would be ignored."""
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    completed = subprocess.run(  # noqa: S603
        ["git", "check-ignore", "-q", relpath],  # noqa: S607
        cwd=repo,
        check=False,
    )
    return completed.returncode == 0


class TestTheFiringRecordStopsBeingUntrackedChurn:
    def test_git_ignores_the_firing_record_after_the_block_is_written(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path)
        assert not _is_ignored(repo, FIRINGS_PATTERN)
        ensure_ignore_block(repo)
        assert _is_ignored(repo, FIRINGS_PATTERN)

    def test_git_ignores_the_index_and_its_sqlite_sidecars(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        for relpath in (
            ".beadloom/beadloom.db",
            ".beadloom/beadloom.db-wal",
            ".beadloom/_graph/beadloom.db",
        ):
            assert _is_ignored(repo, relpath), relpath

    def test_the_graph_and_flow_config_stay_committable(self, tmp_path: Path) -> None:
        """The block covers derived state only; source under .beadloom/ must stay tracked."""
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        for relpath in (".beadloom/_graph/services.yml", ".beadloom/flow.yml"):
            assert not _is_ignored(repo, relpath), relpath


class TestEveryPatternCarriesItsReason:
    def test_each_written_pattern_is_preceded_by_its_reason(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        text = (repo / IGNORE_RELPATH).read_text(encoding="utf-8")
        for entry in GENERATED_WORKING_SET:
            assert entry.why, entry.pattern
            assert entry.why.split(".")[0] in text, entry.pattern

    def test_the_firing_record_names_its_default_and_the_override(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        why = next(e.why for e in GENERATED_WORKING_SET if e.pattern == FIRINGS_PATTERN)
        assert "machine-local" in why
        assert "deletes this line" in why

    def test_the_firing_record_names_that_it_is_never_rotated(self, tmp_path: Path) -> None:
        """m7 is named, not hidden: ignoring the file removes it from git, not from disk."""
        why = next(e.why for e in GENERATED_WORKING_SET if e.pattern == FIRINGS_PATTERN)
        assert "rotated" in why
        assert "--liveness" in why


class TestWrittenOnceNeverRewritten:
    def test_a_second_run_leaves_the_file_byte_identical(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        before = (repo / IGNORE_RELPATH).read_bytes()
        second = ensure_ignore_block(repo)
        assert (repo / IGNORE_RELPATH).read_bytes() == before
        assert second.added == []
        assert second.skipped_reason

    def test_a_deleted_entry_does_not_come_back(self, tmp_path: Path) -> None:
        """The override: a team that wants the record committed removes the line, once."""
        repo = _git_repo(tmp_path)
        ensure_ignore_block(repo)
        path = repo / IGNORE_RELPATH
        kept = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() != FIRINGS_PATTERN
        ]
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        ensure_ignore_block(repo)
        assert FIRINGS_PATTERN not in path.read_text(encoding="utf-8")
        assert not _is_ignored(repo, FIRINGS_PATTERN)

    def test_the_projects_own_lines_are_never_touched(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        path = repo / IGNORE_RELPATH
        original = "# mine\n*.log\nnode_modules/\n"
        path.write_text(original, encoding="utf-8")
        ensure_ignore_block(repo)
        text = path.read_text(encoding="utf-8")
        assert text.startswith(original)
        assert BLOCK_MARKER in text

    def test_a_pattern_the_project_already_has_is_not_duplicated(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_text(".beadloom/**/*.db\n", encoding="utf-8")
        result = ensure_ignore_block(repo)
        text = (repo / IGNORE_RELPATH).read_text(encoding="utf-8")
        assert text.count(".beadloom/**/*.db\n") == 1
        assert ".beadloom/**/*.db" not in result.added
        assert FIRINGS_PATTERN in result.added


class TestWhereItRefusesToWrite:
    def test_a_project_that_is_not_under_git_gets_no_ignore_file(self, tmp_path: Path) -> None:
        result = ensure_ignore_block(tmp_path)
        assert not (tmp_path / IGNORE_RELPATH).exists()
        assert "git" in result.skipped_reason
        assert result.added == []

    def test_a_subdirectory_of_a_repo_is_still_under_git(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        nested = repo / "packages" / "service"
        nested.mkdir(parents=True)
        result = ensure_ignore_block(nested)
        assert (nested / IGNORE_RELPATH).is_file()
        assert result.added


class TestTheCallersThatOwnIt:
    """`init` creates the working set, so `init` names it — not the guard scaffolder.

    `setup-agentic-flow` makes the same call for the repository that was initialised
    by an older Beadloom: it is the identical whole-working-set call, so the flow
    guards stay one entry in a list rather than a special case.
    """

    def test_bootstrap_writes_the_block_and_reports_what_it_added(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner.bootstrap import bootstrap_project

        repo = _git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        result = bootstrap_project(repo)

        assert BLOCK_MARKER in (repo / IGNORE_RELPATH).read_text(encoding="utf-8")
        assert FIRINGS_PATTERN in result["ignore_added"]

    def test_init_says_it_edited_the_projects_ignore_file(self, tmp_path: Path) -> None:
        """Editing someone's .gitignore without saying so is its own surprise."""
        from click.testing import CliRunner

        from beadloom.services.cli import main

        repo = _git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(repo)])

        assert result.exit_code == 0, result.output
        assert ".gitignore" in result.output

    def test_setup_agentic_flow_ensures_the_block_for_an_older_project(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        repo = _git_repo(tmp_path)
        (repo / ".beadloom").mkdir()
        (repo / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n", encoding="utf-8"
        )

        result = CliRunner().invoke(main, ["setup-agentic-flow", "--project", str(repo)])

        assert result.exit_code == 0, result.output
        assert _is_ignored(repo, FIRINGS_PATTERN)
        assert ".gitignore" in result.output
