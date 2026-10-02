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


class TestASiteFolderHoldingTheProjectsFiles:
    """R2 finding 5: a ``site/`` that already holds files is the project's, not the portal's.

    Appending ``/site/`` there hid every new file under it from ``git status``.
    """

    def _commit(self, repo: Path) -> None:
        for args in (["add", "-A"], ["commit", "-q", "-m", "site"]):
            subprocess.run(  # noqa: S603
                ["git", "-c", "user.name=t", "-c", "user.email=t@e.invalid", *args],  # noqa: S607
                cwd=repo,
                check=True,
            )

    def test_tracked_files_leave_the_ignore_file_unwritten(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / "site").mkdir()
        (repo / "site" / "index.html").write_text("<h1>Acme</h1>\n", encoding="utf-8")
        (repo / "site" / "app.js").write_text("go()\n", encoding="utf-8")
        self._commit(repo)

        result = ensure_portal_ignored(repo)

        assert not (repo / IGNORE_RELPATH).exists()
        assert result.outcome == "occupied"
        assert "2 files tracked by git" in result.reason
        assert "--out" in result.reason
        assert not _git_ignores(repo, "site/about.html")

    def test_an_existing_ignore_file_is_left_byte_for_byte(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_bytes(b"/dist/\n")
        (repo / "site").mkdir()
        (repo / "site" / "index.html").write_text("x\n", encoding="utf-8")
        self._commit(repo)

        result = ensure_portal_ignored(repo)

        assert (repo / IGNORE_RELPATH).read_bytes() == b"/dist/\n"
        assert result.outcome == "occupied"
        assert "1 file tracked by git" in result.reason

    def test_files_not_yet_committed_leave_it_unwritten_too(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / "site" / "pages").mkdir(parents=True)
        (repo / "site" / "pages" / "index.html").write_text("x\n", encoding="utf-8")

        result = ensure_portal_ignored(repo)

        assert not (repo / IGNORE_RELPATH).exists()
        assert result.outcome == "occupied"
        assert "1 file, none tracked by git" in result.reason

    def test_where_git_cannot_list_the_files_the_ones_on_disk_decide(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()  # a working tree git itself cannot read
        (tmp_path / "site").mkdir()
        (tmp_path / "site" / "index.html").write_text("x\n", encoding="utf-8")

        result = ensure_portal_ignored(tmp_path)

        assert not (tmp_path / IGNORE_RELPATH).exists()
        assert result.outcome == "occupied"
        assert "1 file, none tracked by git" in result.reason

    def test_an_empty_site_folder_is_the_portals_to_take(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / "site").mkdir()

        result = ensure_portal_ignored(repo)

        assert result.outcome == "created"
        assert (repo / IGNORE_RELPATH).read_bytes() == b"/site/\n"

    def test_a_line_the_project_wrote_still_decides_first(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / IGNORE_RELPATH).write_bytes(b"site/\n")
        (repo / "site").mkdir()
        (repo / "site" / "index.html").write_text("x\n", encoding="utf-8")

        result = ensure_portal_ignored(repo)

        assert (result.outcome, result.covered_by) == ("covered", "site/")

    def test_tracked_files_deleted_from_the_working_tree_still_count(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        (repo / "site").mkdir()
        (repo / "site" / "index.html").write_text("x\n", encoding="utf-8")
        self._commit(repo)
        (repo / "site" / "index.html").unlink()

        result = ensure_portal_ignored(repo)

        assert result.outcome == "occupied"
        assert "1 file tracked by git" in result.reason

    def test_init_says_why_and_what_to_do(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        repo = _git_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "site").mkdir()
        (repo / "site" / "index.html").write_text("x\n", encoding="utf-8")
        self._commit(repo)

        result = CliRunner().invoke(main, ["init", "--yes", "--project", str(repo)])

        assert result.exit_code == 0, result.output
        said = "Not ignored: /site/ - site/ already holds 1 file tracked by git"
        assert said in result.output
        assert "beadloom docs site --out" in result.output


class TestASiteFolderHoldingTheGeneratedPortal:
    """The re-review's finding m4 (``beadloom-ujzb.24``): our own portal is not the project's.

    ``init --force`` after ``docs site`` found ``site/`` holding the generated portal,
    called it the project's own and left it unignored. Whether the folder holds the
    portal is asked of the probe the caller hands in (the scaffold's marker test).
    """

    @staticmethod
    def _untracked_site(repo: Path) -> None:
        (repo / "site").mkdir()
        (repo / "site" / "package.json").write_text("{}\n", encoding="utf-8")
        (repo / "site" / "index.md").write_text("# Home\n", encoding="utf-8")

    def test_untracked_files_of_the_generated_portal_get_the_line(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        self._untracked_site(repo)
        asked: list[Path] = []

        def is_portal(folder: Path) -> bool:
            asked.append(folder)
            return True

        result = ensure_portal_ignored(repo, is_portal=is_portal)

        assert result.outcome == "created"
        assert (repo / IGNORE_RELPATH).read_bytes() == b"/site/\n"
        assert asked == [repo / "site"]
        assert _git_ignores(repo, "site/extra.md")

    def test_untracked_files_the_probe_does_not_know_stay_the_projects(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path)
        self._untracked_site(repo)

        result = ensure_portal_ignored(repo, is_portal=lambda _folder: False)

        assert result.outcome == "occupied"
        assert not (repo / IGNORE_RELPATH).exists()

    def test_tracked_files_stay_the_projects_whatever_the_probe_says(
        self, tmp_path: Path
    ) -> None:
        repo = _git_repo(tmp_path)
        self._untracked_site(repo)
        TestASiteFolderHoldingTheProjectsFiles()._commit(repo)

        result = ensure_portal_ignored(repo, is_portal=lambda _folder: True)

        assert result.outcome == "occupied"
        assert "2 files tracked by git" in result.reason
        assert not (repo / IGNORE_RELPATH).exists()

    def test_without_a_probe_the_files_on_disk_decide_as_before(self, tmp_path: Path) -> None:
        repo = _git_repo(tmp_path)
        self._untracked_site(repo)

        assert ensure_portal_ignored(repo).outcome == "occupied"


class TestInitTellsTheGeneratedPortalByTheScaffoldsMarker:
    """The re-review's finding m4 through ``init``: the probe it hands in is the marker test.

    The scaffold is written by its own writer, so the files carry the marker exactly as
    ``docs site`` writes it; the same files without the marker are the project's.
    """

    @staticmethod
    def _project(repo: Path) -> None:
        (repo / "src" / "orders").mkdir(parents=True)
        (repo / "src" / "orders" / "__init__.py").write_text("def place() -> None: ...\n")

    @staticmethod
    def _init(repo: Path, *args: str) -> str:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        result = CliRunner().invoke(main, ["init", *args, "--project", str(repo)])
        assert result.exit_code == 0, result.output
        return result.output

    @staticmethod
    def _scan_paths(repo: Path) -> list[str]:
        import yaml

        config = (repo / ".beadloom" / "config.yml").read_text(encoding="utf-8")
        paths = yaml.safe_load(config)["scan_paths"]
        assert isinstance(paths, list)
        return [str(path) for path in paths]

    def test_a_written_scaffold_is_ignored_and_not_scanned(self, tmp_path: Path) -> None:
        from beadloom.application.site.scaffold import write_scaffold

        repo = _git_repo(tmp_path)
        self._project(repo)
        write_scaffold(repo / "site", project_root=repo, version="0.0.0-test")

        output = self._init(repo, "--bootstrap")

        assert (repo / IGNORE_RELPATH).read_text(encoding="utf-8").splitlines()[0] == "/site/"
        assert "Not scanned: site/ - " in output
        assert self._scan_paths(repo) == ["src"]

    def test_the_same_files_without_the_marker_are_the_projects(self, tmp_path: Path) -> None:
        from beadloom.application.site.scaffold import shipped_files

        repo = _git_repo(tmp_path)
        self._project(repo)
        for rel, body in shipped_files().items():
            target = repo / "site" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

        output = self._init(repo, "--yes")

        assert "Not ignored: /site/" in output
        assert "Not scanned:" not in output
        assert "site" in self._scan_paths(repo)


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
