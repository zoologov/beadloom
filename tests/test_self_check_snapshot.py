"""The self-check snapshot: this repository's working tree, copied once and indexed there.

BDL-074 A2. Self-checks assert on this repository's own graph, and until this
bead they read the shared ``.beadloom/beadloom.db`` after reindexing it in
place (``live_repo_reindexed``). Any other writer of that file — another test, a
git hook, a concurrent ``beadloom lint`` — could rebuild it underneath them,
which is the ``beadloom-qq6m`` flake. The snapshot is a copy of the working tree
with an index of its own, built once per session.

The cases below pin what the copy holds, because a snapshot that quietly holds
less than the tree is a self-check that is green about a different project:
the working-tree CONTENT (so a concurrent edit is what is judged, never a
frozen copy), the untracked files git would not ignore (a new module is judged
the way ``reindex`` on the tree would judge it), never an index file, and the
git history (``sync-check`` corroborates a freshly built index against ``HEAD``,
and without history every pair reads ``no_baseline``).
"""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from tests.support.repository_root import TESTS_ROOT
from tests.support.self_check_snapshot import build_snapshot, working_tree_files

if TYPE_CHECKING:
    from pathlib import Path


def _git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
        env=env,
    )
    return result.stdout


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A committed repository with one tracked edit, one untracked file and one ignored."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _write(root, ".gitignore", ".beadloom/**/*.db\nbuild/\n")
    _write(root, "src/app.py", "print('committed')\n")
    _write(root, "docs/gone.md", "deleted after the commit\n")
    _write(root, ".beads/issues.jsonl", '{"id": "x-1"}\n')
    _write(root, ".beadloom/_graph/services.yml", "nodes: []\n")
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "-m", "init")
    _write(root, "src/app.py", "print('edited in the working tree')\n")
    (root / "docs" / "gone.md").unlink()
    _write(root, "src/new_module.py", "x = 1\n")
    _write(root, "build/out.txt", "ignored\n")
    _write(root, ".beadloom/beadloom.db", "not a real index\n")
    return root


class TestWhatTheCopyHolds:
    def test_tracked_and_unignored_untracked_files_are_listed(self, repo: Path) -> None:
        files = set(working_tree_files(repo))

        assert {"src/app.py", "src/new_module.py", ".beads/issues.jsonl"} <= files
        assert ".beadloom/_graph/services.yml" in files

    def test_an_ignored_file_a_deleted_file_and_the_index_are_not(self, repo: Path) -> None:
        files = set(working_tree_files(repo))

        assert "build/out.txt" not in files
        assert "docs/gone.md" not in files
        assert ".beadloom/beadloom.db" not in files

    def test_the_copy_carries_the_working_tree_content_not_head(
        self, repo: Path, tmp_path: Path
    ) -> None:
        dest = tmp_path / "snapshot"

        build_snapshot(repo, dest)

        assert (dest / "src" / "app.py").read_text(encoding="utf-8") == (
            "print('edited in the working tree')\n"
        )
        assert (dest / "src" / "new_module.py").is_file()
        assert not (dest / ".beadloom" / "beadloom.db").exists()
        assert not (dest / "build").exists()

    def test_the_copy_carries_the_history_and_reads_the_edit_as_an_edit(
        self, repo: Path, tmp_path: Path
    ) -> None:
        dest = tmp_path / "snapshot"

        build_snapshot(repo, dest)

        assert _git(dest, "rev-parse", "HEAD") == _git(repo, "rev-parse", "HEAD")
        status = _git(dest, "status", "--porcelain").splitlines()
        assert " M src/app.py" in status
        assert " D docs/gone.md" in status
        assert "?? src/new_module.py" in status

    def test_the_copy_returns_the_population_it_copied(self, repo: Path, tmp_path: Path) -> None:
        files = build_snapshot(repo, tmp_path / "snapshot")

        assert sorted(files) == sorted(working_tree_files(repo))


class TestADirectoryThatIsNotARepository:
    """A clean room (no ``.git``) and mutmut's ``mutants/`` copy: the tree is walked."""

    @pytest.fixture()
    def room(self, tmp_path: Path) -> Path:
        root = tmp_path / "room"
        _write(root, "src/app.py", "x = 1\n")
        _write(root, ".beadloom/_graph/services.yml", "nodes: []\n")
        _write(root, ".beadloom/beadloom.db", "index\n")
        _write(root, ".beadloom/beadloom.db-wal", "log\n")
        _write(root, ".venv/lib/site.py", "venv\n")
        _write(root, "src/__pycache__/app.cpython-313.pyc", "bytecode\n")
        return root

    def test_the_walk_keeps_the_project_and_drops_environments_and_indexes(
        self, room: Path
    ) -> None:
        files = set(working_tree_files(room))

        assert files == {"src/app.py", ".beadloom/_graph/services.yml"}

    def test_a_directory_inside_a_repository_is_not_its_top(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # mutmut's `mutants/` lives inside this checkout and is ignored by it, so
        # asking git for its files would answer with nothing at all.
        inner = repo / "build"
        _write(inner, "src/app.py", "x = 1\n")

        assert "src/app.py" in working_tree_files(inner)

    def test_the_copy_of_a_room_has_no_history(self, room: Path, tmp_path: Path) -> None:
        dest = tmp_path / "snapshot"

        build_snapshot(room, dest)

        assert (dest / "src" / "app.py").is_file()
        assert not (dest / ".git").exists()


class TestTheSessionSnapshot:
    """The marking rule for the fixture every self-check reads instead of the live index.

    What the session snapshot holds is checked against the snapshot itself, in
    ``tests/self_check/process/test_self_check_snapshot.py``: those two tests read
    this repository's copy, so they are self-checks (BDL-074 F3). The two here
    read no snapshot, and stay beside the helper's product tests.
    """

    def test_a_test_that_reads_it_is_marked_a_self_check(
        self, request: pytest.FixtureRequest
    ) -> None:
        """The collection hook marks an item that asks for the snapshot.

        The item is this test's own -- outside ``tests/self_check/``, so the folder
        cannot be what marks it -- with the snapshot added to what it asks for.
        Until BDL-074 F3 this test asked for the real session snapshot, which made
        it a self-check outside the self-check folder; moving it into that folder
        would have made it pass whatever the rule did.

        The hook is the conftest's own, taken from the plugin manager that
        registered it: a test module does not import another suite module
        (``test_the_suite_shares_helpers_through_support.py``).
        """
        conftest = request.config.pluginmanager.get_plugin(str(TESTS_ROOT / "conftest.py"))
        assert conftest is not None, "the suite's conftest is not registered under its path"

        marks: list[str] = []
        asks_for_the_snapshot = SimpleNamespace(
            path=request.node.path,
            fixturenames=[*request.node.fixturenames, "self_check_snapshot"],
            add_marker=lambda mark: marks.append(mark.name),
        )

        conftest.pytest_collection_modifyitems([asks_for_the_snapshot])

        assert marks == ["self_check"]

    def test_a_test_that_does_not_read_it_is_not(self, request: pytest.FixtureRequest) -> None:
        assert request.node.get_closest_marker("self_check") is None
