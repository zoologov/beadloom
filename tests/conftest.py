"""Shared test fixtures for Beadloom."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
