"""The guard that stops a test from writing to a git-tracked file.

The guard exists because BDL-UX #177 was a TEST: it rewrote the shipped
``CLAUDE.md`` template from this project's live file and passed while doing it.
A guard installed in ``conftest.py`` is itself untested unless something proves
it fires, so this module does two things: it pins the path classification (which
is where an over-eager guard would start failing innocent tests), and it runs a
REAL pytest subprocess over a REAL temporary git repository to prove the verdict
arrives — as ``FAILED``, in the call phase, naming the file.

``FAKES PROVE FAKES``: the integration half uses real ``git`` and a real pytest
process rather than a stub, because "the hook is registered" and "the run goes
red" are different claims and only the second one matters.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.tracked_write_guard import TrackedWriteGuard, tracked_files


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo), *args],  # noqa: S607 - git resolved on PATH
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """A real git repository with one tracked file and one untracked file."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "shipped.txt").write_text("shipped\n", encoding="utf-8")
    (repo / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "pkg/shipped.txt")
    return repo


class TestWhatCountsAsTracked:
    """Classification — the half that decides whether an innocent test is safe."""

    def test_a_tracked_file_is_named_relative_to_the_root(self, git_repo: Path) -> None:
        # Arrange
        guard = TrackedWriteGuard(git_repo)

        # Act
        rel = guard.relpath(git_repo / "pkg" / "shipped.txt")

        # Assert
        assert rel == "pkg/shipped.txt"

    def test_an_untracked_file_inside_the_repo_is_not_guarded(self, git_repo: Path) -> None:
        # Arrange
        guard = TrackedWriteGuard(git_repo)

        # Act + Assert — a test may write anywhere it likes, except the tracked tree
        assert guard.relpath(git_repo / "scratch.txt") is None
        assert guard.relpath(git_repo / "pkg" / "generated.txt") is None

    def test_a_path_outside_the_repo_is_not_guarded(self, git_repo: Path, tmp_path: Path) -> None:
        # Arrange
        guard = TrackedWriteGuard(git_repo)

        # Act + Assert
        assert guard.relpath(tmp_path / "elsewhere.txt") is None
        assert guard.relpath("/etc/hosts") is None

    def test_a_relative_path_is_resolved_against_the_working_directory(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the same write, spelled without a root
        guard = TrackedWriteGuard(git_repo)
        monkeypatch.chdir(git_repo)

        # Act
        rel = guard.relpath("pkg/shipped.txt")

        # Assert
        assert rel == "pkg/shipped.txt"

    def test_a_prefix_neighbour_of_the_root_is_not_guarded(self, tmp_path: Path) -> None:
        """``/x/repo-backup`` starts with ``/x/repo`` as a STRING but is not inside it."""
        # Arrange
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(repo, "add", "a.txt")
        guard = TrackedWriteGuard(repo)

        # Act + Assert
        assert guard.relpath(tmp_path / "repo-backup" / "a.txt") is None

    def test_a_repo_without_git_makes_the_guard_inert_and_it_says_so(
        self, tmp_path: Path
    ) -> None:
        """A clean room has no ``.git``; that run does not answer for this property."""
        # Arrange
        plain = tmp_path / "clean-room"
        plain.mkdir()
        (plain / "file.txt").write_text("x\n", encoding="utf-8")

        # Act
        guard = TrackedWriteGuard(plain)

        # Assert
        assert guard.inert is True
        assert "cannot fire" in guard.inert_reason
        assert tracked_files(plain) == frozenset()


class TestTheGuardRecordsWrites:
    """Interception — every door a test could use to reach a tracked file."""

    @pytest.fixture()
    def installed(self, git_repo: Path) -> TrackedWriteGuard:
        guard = TrackedWriteGuard(git_repo)
        guard.install()
        try:
            yield guard
        finally:
            guard.uninstall()

    @pytest.mark.parametrize(
        ("label", "write"),
        [
            ("Path.write_text", lambda p: p.write_text("edited\n", encoding="utf-8")),
            ("Path.write_bytes", lambda p: p.write_bytes(b"edited\n")),
            ("Path.open", lambda p: p.open("w", encoding="utf-8").close()),
            # `builtins.open` on purpose: it is a door the guard must watch, so
            # PTH123's advice to use Path.open would remove the case under test.
            ("builtins.open", lambda p: open(p, "a", encoding="utf-8").close()),  # noqa: PTH123
            ("Path.unlink", lambda p: p.unlink()),
            ("Path.touch", lambda p: p.touch()),
        ],
    )
    def test_each_write_door_is_recorded(
        self, installed: TrackedWriteGuard, git_repo: Path, label: str, write: object
    ) -> None:
        # Act
        write(git_repo / "pkg" / "shipped.txt")  # type: ignore[operator]

        # Assert
        recorded = installed.take()
        assert list(recorded) == ["pkg/shipped.txt"], label
        assert installed.take() == {}, "take() clears, so the next test starts clean"

    def test_a_write_to_an_untracked_file_is_not_recorded(
        self, installed: TrackedWriteGuard, git_repo: Path
    ) -> None:
        # Act
        (git_repo / "scratch.txt").write_text("edited\n", encoding="utf-8")

        # Assert
        assert installed.take() == {}

    def test_copying_a_tracked_file_as_a_source_is_not_a_write(
        self, installed: TrackedWriteGuard, git_repo: Path, tmp_path: Path
    ) -> None:
        """Snapshotting the shipped templates into tmp_path is how a test should work."""
        # Act
        shutil.copytree(git_repo / "pkg", tmp_path / "snapshot")
        shutil.copy2(git_repo / "pkg" / "shipped.txt", tmp_path / "copy.txt")

        # Assert
        assert installed.take() == {}

    def test_moving_a_tracked_file_away_is_a_write(
        self, installed: TrackedWriteGuard, git_repo: Path, tmp_path: Path
    ) -> None:
        # Act
        shutil.move(str(git_repo / "pkg" / "shipped.txt"), str(tmp_path / "taken.txt"))

        # Assert
        assert list(installed.take()) == ["pkg/shipped.txt"]

    def test_reading_a_tracked_file_is_not_a_write(
        self, installed: TrackedWriteGuard, git_repo: Path
    ) -> None:
        # Act
        (git_repo / "pkg" / "shipped.txt").read_text(encoding="utf-8")

        # Assert
        assert installed.take() == {}

    def test_the_message_names_the_file_and_the_operation(
        self, installed: TrackedWriteGuard, git_repo: Path
    ) -> None:
        # Act
        (git_repo / "pkg" / "shipped.txt").write_text("edited\n", encoding="utf-8")
        message = installed.describe(installed.take())

        # Assert
        assert "pkg/shipped.txt" in message
        assert "Path.write_text" in message
        assert "tmp_path" in message, "a finding without a next move is half a finding"


_SUBPROCESS_CONFTEST = '''
import sys
sys.path.insert(0, {guard_dir!r})
import pytest
from tracked_write_guard import TrackedWriteGuard

_GUARD = None


def pytest_configure(config):
    global _GUARD
    _GUARD = TrackedWriteGuard({repo!r})
    _GUARD.install()


def pytest_unconfigure(config):
    if _GUARD is not None:
        _GUARD.uninstall()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    written = _GUARD.take()
    if written:
        pytest.fail(_GUARD.describe(written), pytrace=False)
    return outcome
'''

_SUBPROCESS_TESTS = '''
from pathlib import Path

REPO = Path({repo!r})


def test_writes_a_tracked_file():
    (REPO / "pkg" / "shipped.txt").write_text("propagated\\n", encoding="utf-8")


def test_writes_an_untracked_file():
    (REPO / "generated.txt").write_text("fine\\n", encoding="utf-8")
'''


class TestTheGuardFailsTheRunItGuards:
    """The claim that matters: a real pytest run goes RED, in the call phase."""

    @pytest.fixture()
    def run_result(self, git_repo: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
        # Arrange — a real suite, outside this one, guarding the temp repo
        suite = tmp_path / "suite"
        suite.mkdir()
        guard_dir = str(Path(__file__).resolve().parent)
        (suite / "conftest.py").write_text(
            _SUBPROCESS_CONFTEST.format(guard_dir=guard_dir, repo=str(git_repo)),
            encoding="utf-8",
        )
        (suite / "test_writes.py").write_text(
            _SUBPROCESS_TESTS.format(repo=str(git_repo)), encoding="utf-8"
        )

        # Act
        return subprocess.run(  # noqa: S603 - fixed argv (this interpreter)
            [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly", str(suite)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(suite),
        )

    def test_the_run_fails(self, run_result: subprocess.CompletedProcess[str]) -> None:
        # Assert — exit code, never a line count (#148), and not by crashing:
        # a non-zero exit from an INTERNALERROR would pass this test while
        # proving nothing about the guard (it did, once, while this was written)
        output = run_result.stdout + run_result.stderr
        assert "INTERNALERROR" not in output, output
        assert run_result.returncode != 0, output

    def test_the_verdict_is_failed_and_not_an_error(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        """``ERROR`` is not ``FAILED``: a teardown-phase verdict reads as neither."""
        # Assert
        output = run_result.stdout + run_result.stderr
        assert "1 failed" in output, output
        assert "error" not in output.lower(), output

    def test_only_the_offending_test_fails(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        # Assert — the untracked write is left alone; a guard that fails
        # everything would simply be turned off
        output = run_result.stdout + run_result.stderr
        assert "test_writes_a_tracked_file" in output
        assert "1 passed" in output, output

    def test_the_failure_names_the_tracked_file(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        # Assert
        assert "pkg/shipped.txt" in run_result.stdout + run_result.stderr
