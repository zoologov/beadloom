"""Shared test fixtures for Beadloom."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import loader as rules_loader
from beadloom.infrastructure.db import create_schema, open_db
from tests.contact_guard import ALLOWED_CONTACTS, OUTSIDE_ANY_TEST, ContactGuard
from tests.self_check_snapshot import build_snapshot
from tests.tracked_write_guard import TrackedWriteGuard

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# The suite may not write to a file this repository tracks in git (BDL-UX #177).
# A test that mutates the tree it measures cannot be trusted about it, and the
# mutation is invisible to `git status` whenever it happens to be byte-identical
# — which is exactly how the shipped CLAUDE.md template came to be a snapshot of
# this project's local file, and how the `agents/*.md.txt` writes per run
# survived unnoticed after the CLAUDE.md leg was closed. `beadloom-iur5` removed
# that writer; the guard's subject is the tracked tree, not that one function.
#
# Enforced as a hook rather than a fixture so the verdict lands in the CALL
# phase: a teardown-phase failure is reported as ERROR, and ERROR is not FAILED
# (this epic's TESTS MUST BITE rule). See tests/tracked_write_guard.py for the
# reach of the check and its honest limits.
# --------------------------------------------------------------------------- #

_GUARD: TrackedWriteGuard | None = None

# --------------------------------------------------------------------------- #
# The suite may not reach this repository's LIVE state either (BDL-074 A1): its
# `.beadloom/beadloom.db`, its tracker, its git history. Every test starts in an
# empty directory (the two `_…_in_an_empty_directory` fixtures below), so a
# `Path.cwd()` fallback meets nothing; the contact guard fails the test that
# reaches the live state anyway, except the nodes named in ALLOWED_CONTACTS,
# which is printed at the top of every run. See tests/contact_guard.py.
#
# BEADLOOM_CONTACT_REPORT=<file> writes every contact of the run, allowed or
# not, as JSON: the rerunnable form of the suite map's tracer measurement.
# --------------------------------------------------------------------------- #

_CONTACTS = ContactGuard(_REPO_ROOT, ALLOWED_CONTACTS)
_CONTACT_REPORT_ENV = "BEADLOOM_CONTACT_REPORT"
#: Every contact of the session, kept for the terminal summary and the report.
_SESSION_CONTACTS: list[tuple[str, str, str, bool]] = []


#: The ``self_check`` marker: set on every test under ``tests/self_check/`` and on
#: every test that reads the self-check snapshot, by
#: :func:`pytest_collection_modifyitems`, never by hand — one fact, stated once.
#: The one exception is a parametrize row whose twin is a product test of the
#: shipped template: that row carries the mark in its ``pytest.param`` (BDL-074 A3).
_SELF_CHECK_FIXTURE = "self_check_snapshot"
_SELF_CHECK_DIR = Path(__file__).resolve().parent / "self_check"
_SELF_CHECK_MARKER = (
    "self_check: asserts on this repository's own tree; set on tests/self_check/ "
    "and on every reader of the session snapshot (`self_check_snapshot`)"
)
#: What the snapshot build did, for the terminal summary; empty until a test asks.
_SNAPSHOT_BUILD: dict[str, object] = {}


def pytest_configure(config: pytest.Config) -> None:
    """Install the tracked-write and contact guards, or say why one cannot fire."""
    global _GUARD
    config.addinivalue_line("markers", _SELF_CHECK_MARKER)
    _GUARD = TrackedWriteGuard(_REPO_ROOT)
    # Installed after the tracked-write guard's own `git ls-files`: that call is
    # the guard infrastructure reading the tracked set, not a test's contact.
    _CONTACTS.install()
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
    _CONTACTS.uninstall()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every self-check: by its folder, or by reading the snapshot through any fixture."""
    for item in items:
        in_folder = _SELF_CHECK_DIR in Path(str(item.path)).resolve().parents
        if in_folder or _SELF_CHECK_FIXTURE in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.self_check)


def pytest_report_header(config: pytest.Config) -> list[str]:
    """Print the contact guard's allowed list, so an exemption is never silent."""
    return _CONTACTS.listing()


def _contact_refusal() -> str:
    """Take the recorded contacts, keep them for the session; the refusal message, if any.

    A contact is judged by the test it was MADE in (``PYTEST_CURRENT_TEST``), so
    the allowed list is matched against that test's node id.
    """
    refused = []
    for contact in _CONTACTS.take():
        in_a_test = contact.nodeid != OUTSIDE_ANY_TEST
        allowed = in_a_test and _CONTACTS.allows(contact.nodeid)
        _SESSION_CONTACTS.append((contact.during, contact.kind, contact.detail, allowed))
        if in_a_test and not allowed:
            refused.append(contact)
    return _CONTACTS.describe(refused) if refused else ""


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Iterator[None]:
    """Fail the test that wrote to a tracked file or reached the live state.

    Writes and contacts made by a fixture count toward the test the fixture set
    up; a tracked write made during teardown surfaces on the next test, which is
    stated here rather than left to be discovered from a confusing message. A
    contact made during teardown fails that test's teardown (see below).
    """
    try:
        outcome = yield
    finally:
        # Judged even when the test raised: a test that reached the live state
        # and then failed or skipped still reached it (measured in A1: without
        # this, the contact surfaced as an ERROR in teardown instead).
        refused = _contact_refusal()
        if refused:
            pytest.fail(refused, pytrace=False)
    if _GUARD is not None:
        written = _GUARD.take()
        if written:
            pytest.fail(_GUARD.describe(written), pytrace=False)
    return outcome


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> Iterator[None]:
    """A contact made while tearing a test down is that test's, reported as its ERROR."""
    outcome = yield
    refused = _contact_refusal()
    if refused:
        pytest.fail(refused, pytrace=False)
    return outcome


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """State what the contact guard saw: allowed contacts, contacts outside any test."""
    for contact in _CONTACTS.take():
        _SESSION_CONTACTS.append((contact.during, contact.kind, contact.detail, False))
    allowed = sorted({during for during, _, _, ok in _SESSION_CONTACTS if ok})
    outside = [row for row in _SESSION_CONTACTS if row[0] == OUTSIDE_ANY_TEST]
    write = terminalreporter.write_line
    write(
        f"contact guard: {len(allowed)} allowed test phase(s) reached the live state; "
        f"{len(outside)} contact(s) outside any test; "
        f"{len(_CONTACTS.errors)} classification error(s)"
    )
    for _, kind, detail, _ in outside:
        write(f"  outside any test: {kind}: {detail}")
    write(_snapshot_summary())
    for error in _CONTACTS.errors:
        write(f"  guard error: {error}")
    report = os.environ.get(_CONTACT_REPORT_ENV)
    if report:
        rows = [
            {"during": d, "kind": k, "detail": t, "allowed": ok}
            for d, k, t, ok in _SESSION_CONTACTS
        ]
        Path(report).write_text(json.dumps(rows, indent=1), encoding="utf-8")
        write(f"contact guard: {len(rows)} contact(s) written to {report}")


@pytest.fixture(scope="session", autouse=True)
def _the_session_starts_in_an_empty_directory(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Session and module fixtures run in an empty directory, not in this repository."""
    previous = Path.cwd()
    os.chdir(tmp_path_factory.mktemp("session-cwd"))
    try:
        yield
    finally:
        os.chdir(previous)


@pytest.fixture(autouse=True)
def _each_test_starts_in_an_empty_directory(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Every test starts in its own EMPTY directory (BDL-074 A1).

    Not ``tmp_path``: a test that builds its project there and leaves the root to
    the ``Path.cwd()`` default would pass without ever naming its root. And not
    ``monkeypatch.chdir``: requesting ``monkeypatch`` from an autouse fixture
    sets it up before every module's own autouse fixtures, which moves its undo
    after their teardown (measured: ten ERRORs in tests/test_room_extras.py).
    """
    previous = Path.cwd()
    os.chdir(tmp_path_factory.mktemp("cwd"))
    try:
        yield
    finally:
        os.chdir(previous)


@pytest.fixture(autouse=True)
def _load_rules_forgets_between_tests() -> None:
    """Forget every ``rules.yml`` parse before each test (BDL-073 B4).

    ``load_rules`` remembers what it parsed for as long as the process lives, which
    is right for one ``init`` and for the TUI, and wrong for a suite. A test would
    be answered from a parse another test made of a path both read — this
    repository's own ``rules.yml`` is one. And mutmut forks each mutant's run from
    a parent that already ran the clean suite in-process: an inherited memo answers
    the child without executing the mutated parse, which is a false survival.
    tests/test_load_rules_parses_once.py holds this fixture to every test.
    """
    rules_loader.forget_parsed_rules()


def _snapshot_summary() -> str:
    """One line on the self-check snapshot: its population and its cost, or its absence."""
    if not _SNAPSHOT_BUILD:
        return "self-check snapshot: not built (no test in this run reads it)"
    return (
        f"self-check snapshot: {_SNAPSHOT_BUILD['files']} file(s) of the working tree "
        f"copied {_SNAPSHOT_BUILD['history']} in {_SNAPSHOT_BUILD['copy_s']:.1f} s and "
        f"indexed in {_SNAPSHOT_BUILD['index_s']:.1f} s, at {_SNAPSHOT_BUILD['root']}; "
        "the copy is the one reader of the live tree, and the contact guard is "
        "suspended while it runs"
    )


@pytest.fixture(scope="session")
def self_check_snapshot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """This repository's working tree, copied once per session and indexed there.

    Self-checks assert on this repository's own graph. They read THIS root, never
    the live ``.beadloom/beadloom.db``: that file is shared with every other
    writer on the machine (a hook, a concurrent ``lint``, another test), and a
    reader of it was the ``beadloom-qq6m`` flake. The copy is taken from the
    working tree at test time, so a concurrent edit is what the self-checks
    judge; it carries the git history, so ``sync-check`` can corroborate the
    fresh index against ``HEAD``. What it holds, and its limits, are stated in
    tests/self_check_snapshot.py. Every test that requests it is marked
    ``self_check``, so ``-m "not self_check"`` deselects them all.

    It replaces ``live_repo_reindexed`` (BDL-074 A2). A test that WRITES the
    index (``lint`` without ``--no-reindex``) writes this copy, which only the
    session's own tests share.
    """
    from beadloom.application.reindex import reindex

    root = tmp_path_factory.mktemp("self-check-snapshot") / _REPO_ROOT.name
    started = time.monotonic()
    with _CONTACTS.suspended():
        files = build_snapshot(_REPO_ROOT, root)
    copied = time.monotonic()
    reindex(root)
    _SNAPSHOT_BUILD.update(
        files=len(files),
        history="with its git history" if (root / ".git").is_dir() else "without history",
        copy_s=copied - started,
        index_s=time.monotonic() - copied,
        root=root,
    )
    return root


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
