"""`beadloom init` keeps the generated portal out of the project's repository.

BDL-076 ``beadloom-ujzb.13`` (the owner's ruling after B2). ``beadloom docs site``
writes the portal into ``site/`` unless ``--out`` names another directory, and
that directory is output: rebuilt on every run, never the project's source. Init
names it in the project's ``.gitignore`` with one anchored line, only when no line
already covers it, and without touching a byte of what the file held.

`git check-ignore` is run for real where the claim is about what git does.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.ignore_block import (
    IGNORE_RELPATH,
    PORTAL_DIR,
    covers_directory,
    ensure_ignore_block,
    ensure_portal_ignored,
)

if TYPE_CHECKING:
    from pathlib import Path


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    return tmp_path


def _git_ignores(repo: Path, relpath: str) -> bool:
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    completed = subprocess.run(  # noqa: S603
        ["git", "check-ignore", "-q", relpath],  # noqa: S607
        cwd=repo,
        check=False,
    )
    return completed.returncode == 0


def test_the_portal_directory_is_the_one_docs_site_writes_by_default() -> None:
    assert PORTAL_DIR == "site"


#: Ignore files git reads as ignoring ``site/`` at the top, and ones it does not.
#: Each is also put to git itself below, so the list cannot drift from git.
_COVERING = (
    "site\n",
    "site/\n",
    "/site\n",
    "/site/\n",
    "site/**\n",
    "/site/**\n",
    "site/*\n",
    "**/site\n",
    "**/site/\n",
    "sit*/\n",
    "*\n",
    "/site/   \n",
    "/dist/\r\n/site/\r\n",
    "!site/\nsite/\n",
)
_NOT_COVERING = (
    "",
    "# site/\n",
    "  /site/\n",
    "sites/\n",
    "docs/site/\n",
    "/site/index.md\n",
    "website/\n",
    "site/\n!site/\n",
    "site/\n!/site\n",
)


class TestWhichLinesCoverThePortalDirectory:
    @pytest.mark.parametrize("text", _COVERING)
    def test_a_file_git_reads_as_ignoring_the_directory_covers_it(self, text: str) -> None:
        assert covers_directory(text, "site")

    @pytest.mark.parametrize("text", _NOT_COVERING)
    def test_anything_else_does_not(self, text: str) -> None:
        assert not covers_directory(text, "site")

    @pytest.mark.parametrize("text", _COVERING + _NOT_COVERING)
    def test_the_reading_is_gits(self, tmp_path: Path, text: str) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_bytes(text.encode("utf-8"))
        # A file one level down: a line naming one file must not read as the directory.
        assert covers_directory(text, "site") == _git_ignores(repo, "site/assets/app.js")


class TestInitWritesOneLine:
    def test_a_project_without_an_ignore_file_gets_one_holding_the_line(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path)

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == b"/site/\n"
        assert (result.outcome, result.line) == ("created", "/site/")
        assert _git_ignores(repo, "site/index.md")
        assert not _git_ignores(repo, "docs/site/index.md")

    def test_the_line_is_appended_after_every_byte_the_file_held(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        before = "# café build\n/dist/\n*.log".encode("latin-1")
        (repo / IGNORE_RELPATH).write_bytes(before)

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == before + b"\n/site/\n"
        assert result.outcome == "appended"

    def test_windows_line_endings_are_kept_and_followed(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        before = b"/dist/\r\n*.log\r\n"
        (repo / IGNORE_RELPATH).write_bytes(before)

        ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == before + b"/site/\r\n"
        assert _git_ignores(repo, "site/index.md")

    def test_a_second_run_changes_nothing(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        ensure_portal_ignored(repo)
        first = (repo / IGNORE_RELPATH).read_bytes()

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == first
        assert (result.outcome, result.covered_by) == ("covered", "/site/")

    def test_a_covering_line_of_the_project_is_left_as_it_is(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_bytes(b"site\n")

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == b"site\n"
        assert (result.outcome, result.covered_by) == ("covered", "site")

    def test_a_line_that_un_ignores_the_directory_is_the_projects_choice(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_bytes(b"!/site/\n")

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == b"!/site/\n"
        assert (result.outcome, result.covered_by) == ("negated", "!/site/")

    def test_outside_a_git_working_tree_nothing_is_written(self, tmp_path: Path) -> None:
        result = ensure_portal_ignored(tmp_path)

        assert not (tmp_path / IGNORE_RELPATH).exists()
        assert result.outcome == "skipped"
        assert "git" in result.reason

    def test_a_project_inside_a_repository_ignores_its_own_portal(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        project = repo / "services" / "orders"
        project.mkdir(parents=True)

        ensure_portal_ignored(project)

        assert (project / IGNORE_RELPATH).read_bytes() == b"/site/\n"
        assert _git_ignores(repo, "services/orders/site/index.md")
        assert not _git_ignores(repo, "site/index.md")


class TestTheWorkingSetBlockKeepsTheFilesLineEndings:
    def test_a_windows_ignore_file_stays_windows(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        before = b"/dist/\r\n*.log\r\n"
        (repo / IGNORE_RELPATH).write_bytes(before)

        ensure_ignore_block(repo)

        after = (repo / IGNORE_RELPATH).read_bytes()
        assert after.startswith(before)
        assert after.count(b"\n") == after.count(b"\r\n")


class TestInitRunsIt:
    def test_bootstrap_ignores_the_portal_before_the_working_set_block(
        self, tmp_path: Path
    ) -> None:
        from beadloom.onboarding.scanner.bootstrap import bootstrap_project

        repo = _git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        result = bootstrap_project(repo)

        lines = (repo / IGNORE_RELPATH).read_text(encoding="utf-8").splitlines()
        assert lines[0] == "/site/"
        assert result["portal_ignore"].outcome == "created"

    def test_init_says_it_ignored_the_portal(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        repo = _git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

        result = CliRunner().invoke(main, ["init", "--yes", "--project", str(repo)])

        assert result.exit_code == 0, result.output
        assert "/site/" in result.output
