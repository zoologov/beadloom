"""The guard that stops a test from reaching this repository's live state.

BDL-074 A1. A test that reads the repository's live index, tracker or git
history measures whatever state the developer's working tree happens to be in,
so its result depends on the machine and on the order the suite ran in
(``beadloom-qq6m`` was one such flake). The suite now moves every test into an
empty directory, and this guard fails a test that reaches the live state anyway
— by an explicit path, by a ``cwd``, or by a ``-C``.

The module pins the classification, where an over-eager guard would start failing
innocent tests, and runs a REAL pytest subprocess to prove the verdict arrives as
``FAILED`` and names what it caught. "The hook is registered" and "the run goes
red" are different claims, and only the second one matters.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tests.contact_guard import (
    ALLOWED_CONTACTS,
    AllowedContact,
    Contact,
    ContactGuard,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    """A stand-in for the repository: the guard's subject is whatever root it is given."""
    repo = tmp_path / "repo"
    (repo / ".beadloom").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / ".beads").mkdir()
    (repo / "src").mkdir()
    return repo


@pytest.fixture()
def elsewhere(tmp_path: Path) -> Path:
    other = tmp_path / "elsewhere"
    other.mkdir()
    return other


def _popen(guard: ContactGuard, argv: object, cwd: object = None, env: object = None) -> None:
    guard.observe("subprocess.Popen", (None, argv, cwd, env))


class TestTheLiveIndex:
    """Opening ``.beadloom/beadloom.db`` of the root is a contact; any other database is not."""

    def test_connecting_to_the_roots_index_is_a_contact(self, root: Path) -> None:
        # Arrange
        guard = ContactGuard(root)

        # Act
        guard.observe("sqlite3.connect", (str(root / ".beadloom" / "beadloom.db"),))

        # Assert
        (contact,) = guard.take()
        assert contact.kind == "live index"
        assert ".beadloom/beadloom.db" in contact.detail

    def test_a_read_only_uri_names_the_same_file(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("sqlite3.connect", (f"file:{root / '.beadloom' / 'beadloom.db'}?mode=ro",))

        assert [c.kind for c in guard.take()] == ["live index"]

    def test_a_relative_path_resolves_against_the_working_directory(
        self, root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the cwd default this epic stops the suite from relying on
        guard = ContactGuard(root)
        monkeypatch.chdir(root)

        # Act
        guard.observe("sqlite3.connect", (Path(".beadloom") / "beadloom.db",))

        # Assert
        assert [c.kind for c in guard.take()] == ["live index"]

    def test_the_write_ahead_log_is_the_same_database(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("open", (str(root / ".beadloom" / "beadloom.db-wal"), "rb", 0))

        assert [c.kind for c in guard.take()] == ["live index"]

    def test_another_projects_index_is_not_a_contact(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("sqlite3.connect", (str(elsewhere / ".beadloom" / "beadloom.db"),))
        guard.observe("sqlite3.connect", (":memory:",))

        assert guard.take() == []

    def test_a_tracked_graph_file_under_dot_beadloom_is_not_the_index(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("open", (str(root / ".beadloom" / "_graph" / "services.yml"), "r", 0))

        assert guard.take() == []

    def test_a_prefix_neighbour_of_the_root_is_not_the_root(self, root: Path) -> None:
        guard = ContactGuard(root)
        neighbour = root.parent / (root.name + "-other") / ".beadloom" / "beadloom.db"

        guard.observe("sqlite3.connect", (str(neighbour),))

        assert guard.take() == []

    def test_a_real_connection_is_seen_through_the_installed_hook(self, root: Path) -> None:
        # Arrange — the audit hook, not a direct call: this is what the suite relies on
        guard = ContactGuard(root)
        previous = guard.install()

        # Act
        try:
            sqlite3.connect(root / ".beadloom" / "beadloom.db").close()
        finally:
            guard.uninstall(previous)

        # Assert
        assert [c.kind for c in guard.take()] == ["live index"]


class TestTheTrackerAndTheHistory:
    """Files under ``.beads/`` and ``.git/`` are the tracker and the history."""

    def test_reading_the_git_directory_is_a_history_contact(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("open", (str(root / ".git" / "HEAD"), "r", 0))

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_reading_the_tracker_directory_is_a_tracker_contact(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("open", (str(root / ".beads" / "issues.jsonl"), "r", 0))

        assert [c.kind for c in guard.take()] == ["tracker"]

    def test_a_relative_low_level_open_is_not_classified(
        self, root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # `os.open(name, dir_fd=fd)` resolves against the DESCRIPTOR, and the audit
        # event does not carry it. Measured: pytest's own temp-dir cleanup opened
        # `.git` of a temp repo this way while the cwd was this repository.
        guard = ContactGuard(root)
        monkeypatch.chdir(root)

        guard.observe("open", (".git", None, os.O_RDONLY))
        guard.observe("open", (".git/HEAD", "r", os.O_RDONLY))  # builtins.open: cwd-relative

        assert [c.detail for c in guard.take()] == ["open(.git/HEAD)"]

    def test_reading_a_source_file_is_not_a_contact(self, root: Path) -> None:
        guard = ContactGuard(root)

        guard.observe("open", (str(root / "src" / "module.py"), "r", 0))
        guard.observe("open", (3, "r", 0))  # a descriptor names no path

        assert guard.take() == []


class TestProcessesRootedAtTheRoot:
    """``git`` and ``bd`` rooted at the root — by cwd, by ``-C``, by a path argument."""

    def test_git_with_the_root_as_cwd(self, root: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "log", "-1"], cwd=str(root))

        (contact,) = guard.take()
        assert contact.kind == "git history"
        assert "git log -1" in contact.detail

    def test_git_with_a_subdirectory_as_cwd(self, root: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["/usr/bin/git", "status"], cwd=root / "src")

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_git_inheriting_the_root_as_cwd(
        self, root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        guard = ContactGuard(root)
        monkeypatch.chdir(root)

        _popen(guard, ["git", "rev-parse", "HEAD"])

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_git_dash_c_names_the_root(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "-C", str(root), "ls-files"], cwd=str(elsewhere))

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_git_dash_c_away_from_the_root_is_not_a_contact(
        self, root: Path, elsewhere: Path
    ) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "-C", str(elsewhere), "status"], cwd=str(root))

        assert guard.take() == []

    def test_cloning_the_root_reads_its_history(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "clone", "-q", str(root), "copy"], cwd=str(elsewhere))

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_git_dir_in_the_environment_overrides_the_cwd(
        self, root: Path, elsewhere: Path
    ) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "status"], cwd=str(root), env={"GIT_DIR": str(elsewhere)})

        assert guard.take() == []

    def test_a_shell_string_is_split(self, root: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, "git log --oneline", cwd=str(root))

        assert [c.kind for c in guard.take()] == ["git history"]

    def test_bd_with_the_root_as_cwd_is_a_tracker_contact(self, root: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["bd", "ready"], cwd=str(root))

        assert [c.kind for c in guard.take()] == ["tracker"]

    def test_bd_pointed_at_the_roots_database_is_a_tracker_contact(
        self, root: Path, elsewhere: Path
    ) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["bd", "--db", str(root / ".beads" / "x.db"), "list"], cwd=str(elsewhere))

        assert [c.kind for c in guard.take()] == ["tracker"]

    def test_git_and_bd_elsewhere_are_not_contacts(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["git", "init", "-q"], cwd=str(elsewhere))
        _popen(guard, ["bd", "ready"], cwd=str(elsewhere))

        assert guard.take() == []

    def test_another_tool_at_the_root_is_not_a_contact(self, root: Path) -> None:
        # Reading source files is not the live state this guard is about.
        guard = ContactGuard(root)

        _popen(guard, ["ruff", "check", str(root / "src")], cwd=str(root))

        assert guard.take() == []


class TestBeadloomProcessesRootedAtTheRoot:
    """A ``beadloom`` process rooted at the root opens the live index in the child."""

    def test_a_project_flag_naming_the_root(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["beadloom", "lint", "--project", str(root)], cwd=str(elsewhere))

        assert [c.kind for c in guard.take()] == ["live index"]

    def test_the_module_form_with_the_root_as_cwd(self, root: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, [sys.executable, "-m", "beadloom", "ctx", "graph"], cwd=str(root))

        assert [c.kind for c in guard.take()] == ["live index"]

    def test_a_project_flag_elsewhere_wins_over_the_cwd(self, root: Path, elsewhere: Path) -> None:
        guard = ContactGuard(root)

        _popen(guard, ["beadloom", "lint", f"--project={elsewhere}"], cwd=str(root))

        assert guard.take() == []


class TestWhoIsAllowed:
    """The allowed list is explicit: a node-id prefix at a ``::`` boundary, with a reason."""

    def test_a_class_prefix_allows_its_tests_and_their_parameters(self, root: Path) -> None:
        guard = ContactGuard(root, (AllowedContact("tests/test_x.py::TestA", "a self-check"),))

        assert guard.allows("tests/test_x.py::TestA::test_b")
        assert guard.allows("tests/test_x.py::TestA::test_b[p1]")

    def test_a_prefix_that_is_not_a_node_boundary_allows_nothing(self, root: Path) -> None:
        guard = ContactGuard(root, (AllowedContact("tests/test_x.py::TestA", "a self-check"),))

        assert not guard.allows("tests/test_x.py::TestAB::test_b")
        assert not guard.allows("tests/test_x.py::TestB::test_b")

    def test_every_entry_of_the_real_list_names_a_file_and_a_reason(self) -> None:
        # A stale entry is an exemption nothing uses; A2 (beadloom-kixx) empties the list.
        for entry in ALLOWED_CONTACTS:
            assert entry.reason.strip(), entry
            assert (_REPO_ROOT / entry.target.split("::", 1)[0]).is_file(), entry

    def test_no_entry_is_left_for_the_snapshot_to_retire(self) -> None:
        # A2 (beadloom-kixx) moved every entry it was named the exit of onto the
        # self-check snapshot; an entry still naming it is an exemption nothing retires.
        assert [e.target for e in ALLOWED_CONTACTS if "beadloom-kixx" in e.reason] == []

    def test_the_printed_list_names_every_entry_and_its_reason(self, root: Path) -> None:
        entries = (AllowedContact("tests/test_x.py::TestA", "reads the live lint"),)
        guard = ContactGuard(root, entries)

        listing = "\n".join(guard.listing())

        assert "1 " in listing
        assert "tests/test_x.py::TestA" in listing
        assert "reads the live lint" in listing


class TestTheSanctionedReader:
    """The self-check snapshot reads the live tree once, and says so; nothing else may."""

    def test_nothing_is_recorded_while_the_guard_is_suspended(self, root: Path) -> None:
        guard = ContactGuard(root)

        with guard.suspended():
            guard.observe("open", (str(root / ".beads" / "issues.jsonl"), "r", 0))
            _popen(guard, ["git", "ls-files"], cwd=str(root))

        assert guard.take() == []

    def test_recording_resumes_when_the_suspension_ends(self, root: Path) -> None:
        guard = ContactGuard(root)

        with guard.suspended():
            pass
        guard.observe("open", (str(root / ".beads" / "issues.jsonl"), "r", 0))

        assert [c.kind for c in guard.take()] == ["tracker"]

    def test_a_suspension_that_raised_still_ends(self, root: Path) -> None:
        guard = ContactGuard(root)

        with pytest.raises(RuntimeError), guard.suspended():
            raise RuntimeError
        guard.observe("open", (str(root / ".beads" / "issues.jsonl"), "r", 0))

        assert [c.kind for c in guard.take()] == ["tracker"]


class TestTheMessage:
    def test_the_message_names_the_kind_the_detail_and_the_way_out(self, root: Path) -> None:
        guard = ContactGuard(root)
        contact = Contact(kind="git history", detail="git log -1 (cwd <root>)", during="t (call)")

        message = guard.describe([contact])

        assert "git history" in message
        assert "git log -1" in message
        assert "tmp_path" in message
        assert "--project" in message


class TestTheSuiteRunsInAnEmptyDirectory:
    """The chdir half: a ``Path.cwd()`` fallback meets nothing, not this repository."""

    def test_the_working_directory_is_empty_and_is_not_the_repository(self) -> None:
        cwd = Path.cwd()

        assert cwd != _REPO_ROOT
        assert _REPO_ROOT not in cwd.parents
        assert list(cwd.iterdir()) == []

    def test_each_test_gets_its_own_directory(self, tmp_path: Path) -> None:
        # The directory is not tmp_path: a test that builds its project in tmp_path
        # and relies on the cwd default would otherwise pass without naming its root.
        assert Path.cwd() != tmp_path


_CONFTEST = '''
from pathlib import Path
import pytest
from tests.contact_guard import ContactGuard, AllowedContact

ROOT = Path({root!r})
_GUARD = ContactGuard(ROOT, (AllowedContact("test_suite.py::test_allowed", "a self-check"),))

def pytest_configure(config):
    _GUARD.install()

@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    try:
        outcome = yield
    finally:
        contacts = [c for c in _GUARD.take() if not _GUARD.allows(item.nodeid)]
        if contacts:
            pytest.fail(_GUARD.describe(contacts), pytrace=False)
    return outcome
'''

_SUITE = '''
import subprocess
import pytest
from pathlib import Path
from conftest import ROOT

def test_runs_git_at_the_root():
    subprocess.run(["git", "-C", str(ROOT), "status"], capture_output=True)

def test_allowed():
    subprocess.run(["git", "-C", str(ROOT), "status"], capture_output=True)

def test_runs_git_elsewhere(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "status"], capture_output=True)

def test_reaches_the_root_then_skips():
    subprocess.run(["git", "-C", str(ROOT), "status"], capture_output=True)
    pytest.skip("a skip after the contact does not excuse it")
'''


class TestTheVerdictArrivesInARealRun:
    """A real pytest process over a real ``git`` call: the run goes red, and says why."""

    @pytest.fixture()
    def run_result(self, root: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
        suite = tmp_path / "suite"
        suite.mkdir()
        (suite / "conftest.py").write_text(_CONFTEST.format(root=str(root)), encoding="utf-8")
        (suite / "test_suite.py").write_text(_SUITE, encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT)}
        return subprocess.run(  # noqa: S603 - fixed argv (this interpreter)
            [sys.executable, "-m", "pytest", "-p", "no:randomly", "-p", "no:cacheprovider",
             "-rA", str(suite)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(suite),
            env=env,
            timeout=120,
            check=False,
        )

    def test_only_the_test_that_reached_the_root_fails(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        out = run_result.stdout

        assert run_result.returncode == 1, out
        assert "FAILED test_suite.py::test_runs_git_at_the_root" in out
        assert "PASSED test_suite.py::test_allowed" in out
        assert "PASSED test_suite.py::test_runs_git_elsewhere" in out

    def test_a_test_that_raises_after_the_contact_still_fails_for_it(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        # Measured in A1: judged only after a clean `yield`, the contact of a test
        # that skipped surfaced as an ERROR in teardown, or not at all.
        assert "FAILED test_suite.py::test_reaches_the_root_then_skips" in run_result.stdout

    def test_the_failure_says_what_it_caught(
        self, run_result: subprocess.CompletedProcess[str]
    ) -> None:
        assert "git history" in run_result.stdout
        assert "git -C" in run_result.stdout
