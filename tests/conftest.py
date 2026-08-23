"""Shared test fixtures for Beadloom."""

from __future__ import annotations

import sqlite3
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db
from tests.tracked_write_guard import TrackedWriteGuard

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# The suite may not write to a file this repository tracks in git (BDL-UX #177).
# A test that mutates the tree it measures cannot be trusted about it, and the
# mutation is invisible to `git status` whenever it happens to be byte-identical
# — which is exactly how the shipped CLAUDE.md template came to be a snapshot of
# this project's local file, and how four `agents/*.md.txt` writes per run
# survived unnoticed after the CLAUDE.md leg was closed.
#
# Enforced as a hook rather than a fixture so the verdict lands in the CALL
# phase: a teardown-phase failure is reported as ERROR, and ERROR is not FAILED
# (this epic's TESTS MUST BITE rule). See tests/tracked_write_guard.py for the
# reach of the check and its honest limits.
# --------------------------------------------------------------------------- #

_GUARD: TrackedWriteGuard | None = None


def pytest_configure(config: pytest.Config) -> None:
    """Install the tracked-write guard, or say why it cannot fire."""
    global _GUARD
    _GUARD = TrackedWriteGuard(_REPO_ROOT)
    if _GUARD.inert:
        # A guard that cannot fire says so, rather than passing silently: a
        # clean-room extraction has no .git, so that run does not answer for
        # this property and must not be reported as though it did.
        warnings.warn(_GUARD.inert_reason, RuntimeWarning, stacklevel=1)
        return
    _GUARD.install()


def pytest_unconfigure(config: pytest.Config) -> None:
    if _GUARD is not None:
        _GUARD.uninstall()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Iterator[None]:
    """Fail the test that wrote to a tracked file, naming the file and the call.

    Writes made by a fixture count toward the test the fixture set up; a write
    made during teardown surfaces on the next test, which is stated here rather
    than left to be discovered from a confusing message.
    """
    outcome = yield
    if _GUARD is not None:
        written = _GUARD.take()
        if written:
            pytest.fail(_GUARD.describe(written), pytrace=False)
    return outcome


@pytest.fixture(scope="session")
def live_repo_reindexed() -> Path:
    """Reindex the live repo's shared DB once per session, returning the repo root.

    A handful of tests assert against the *live* repo's graph (via ``beadloom
    ctx`` subprocesses or ``lint --no-reindex --project <repo>``). They read the
    shared on-disk ``.beadloom/beadloom.db``, so their result depends on its
    ambient state — and ``pytest-randomly`` exposed that any test reindexing the
    live DB into a divergent state (or a stale checkout in CI) breaks them under
    a different order. This session-scoped fixture guarantees the on-disk live
    DB reflects the current source tree before any such assertion runs, making
    those tests order-independent. It runs at most once per session and is
    idempotent on an unchanged source tree.
    """
    from beadloom.application.reindex import reindex

    reindex(_REPO_ROOT)
    return _REPO_ROOT


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    return tmp_path


@pytest.fixture()
def schema_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Yield a schema-initialized SQLite connection, closed on teardown.

    Shared db fixture for tests that need a live, writable connection. The
    ``yield``/``finally`` shape guarantees the connection is closed even when
    the test fails, keeping the suite clean under ``-W error::ResourceWarning``.
    Tests that need a separate read-only handle should use ``read_only_db``.
    """
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = open_db(db_path)
    create_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def read_only_db(schema_db: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Yield a read-only connection to the ``schema_db`` file, closed on teardown."""
    # ``schema_db`` already created and committed the schema to this path.
    db_path = next(iter(schema_db.execute("PRAGMA database_list")))[2]
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Flow guards (BDL-061 S1) — shared factories so a matrix test states only the
# cell it is about. Kept here rather than duplicated per file because four test
# modules need the same two things: a flow.yml body and a stub probe set.
# --------------------------------------------------------------------------- #


class _StubTracker:
    """WorkTracker stub. ``None`` means "unavailable", ``()`` means "nothing claimed"."""

    def __init__(self, beads) -> None:
        self._beads = beads

    def claimed_beads(self):
        return self._beads


class _StubWorkspace:
    """Workspace stub. ``None`` means "no branch / not a repo"."""

    def __init__(self, branch) -> None:
        self._branch = branch

    def current_branch(self):
        return self._branch


class _ExplodingTracker:
    """A tracker that must never be consulted — proves a short-circuit really short-circuits."""

    def claimed_beads(self):
        msg = "the check ran even though the evaluation should have short-circuited"
        raise AssertionError(msg)


@pytest.fixture()
def write_flow_yml(tmp_path: Path):
    """Write a ``.beadloom/flow.yml`` body into ``tmp_path`` (or *root*); return its path."""

    def write(body: str, *, root: Path | None = None) -> Path:
        target = (root or tmp_path) / ".beadloom" / "flow.yml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    return write


@pytest.fixture()
def guard_project(tmp_path: Path) -> Path:
    """``tmp_path`` as a Beadloom project: the marker exists, so a guard locates it.

    ``--project`` names a *project* and not merely a directory (BDL-061.31), so a
    test that points a guard at a bare temporary directory is exercising "the
    project could not be located" rather than the guard it named.
    """
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture()
def make_guard_probes():
    """Factory for stub guard probes: ``make(beads=..., branch=...)``.

    Defaults are the "nothing to complain about" corner (a bead claimed, a
    working branch), so each test overrides only the axis it exercises.
    """
    from beadloom.application.guards.contract import ClaimedBead, GuardProbes

    default_beads = (ClaimedBead(id="bd-1"),)

    def make(*, beads=default_beads, branch="features/BDL-061", exploding=False):
        tracker = _ExplodingTracker() if exploding else _StubTracker(beads)
        return GuardProbes(tracker=tracker, workspace=_StubWorkspace(branch))

    return make
