"""A ``source:`` is matched by its POSIX spelling at every site that matches it (RFC D11).

BDL-083 S2f (``beadloom-27br``), BDL-UX #353. On the first outside adopter's Windows checkout
the index held ``backend\\src\\access\\...`` while the graph declared ``backend/src/access/``,
and three sites compared the two spellings as raw strings: ``source_covers`` with
``startswith``, ``_owned_file_clause`` with ``LIKE 'prefix%'`` or ``= ?``, and the reason
``_unchecked_reason`` gives for a node with no pair. A directory node covered nothing and read
``no_indexed_code``; a file node matched nothing.

The index is written in POSIX now (the write sites are measured by the simulated-separator
scenario of the reindex node). These tests feed the backslash spelling through the three match
sites and require the answer the POSIX spelling gets: a source written either way covers the
same files, and a file path written either way is covered by the same source.
"""

from __future__ import annotations

import sqlite3

import pytest

from beadloom.doc_sync.engine import _unchecked_reason
from beadloom.infrastructure.db import create_schema
from beadloom.infrastructure.repository import (
    covering_prefix,
    get_owned_code_files,
    posix_spelling,
    source_covers,
)

#: The fixture's directory node, its nested feature and one file node, as a Windows user
#: might type them into ``source:``.
_DIRECTORY = "backend\\src\\digest\\"
_NESTED = "backend\\src\\digest\\sections\\"
_FILE = "frontend\\src\\app\\router.ts"


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_schema(c)
    return c


def _node(conn: sqlite3.Connection, ref_id: str, source: str) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'feature', 's', ?)",
        (ref_id, source),
    )


def _indexed(conn: sqlite3.Connection, path: str) -> None:
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, 'h', 'code', 't')",
        (path,),
    )


class TestThePosixSpelling:
    def test_a_backslash_becomes_a_forward_slash(self) -> None:
        assert posix_spelling("backend\\src\\digest\\") == "backend/src/digest/"

    def test_a_posix_path_is_returned_unchanged(self) -> None:
        assert posix_spelling("backend/src/digest/") == "backend/src/digest/"

    def test_the_covering_prefix_of_a_backslash_source_is_posix(self) -> None:
        assert covering_prefix(_DIRECTORY) == "backend/src/digest/"


class TestSourceCovers:
    """The pure match site: a directory prefix, or a file compared whole."""

    def test_a_backslash_directory_source_covers_a_posix_file(self) -> None:
        assert source_covers(_DIRECTORY, "backend/src/digest/sections.py")

    def test_a_posix_directory_source_covers_a_backslash_file(self) -> None:
        assert source_covers("backend/src/digest/", "backend\\src\\digest\\sections.py")

    def test_a_backslash_file_source_matches_its_posix_file(self) -> None:
        assert source_covers(_FILE, "frontend/src/app/router.ts")

    def test_a_backslash_source_still_covers_nothing_outside_it(self) -> None:
        assert not source_covers(_DIRECTORY, "backend/src/file_history/records.py")


class TestOwnedFileClause:
    """The SQL match site, read through the one reader that pairs a node with its files."""

    def test_a_backslash_directory_source_owns_its_posix_files(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "digest", _DIRECTORY)
        _indexed(conn, "backend/src/digest/model.py")
        _indexed(conn, "backend/src/file_history/records.py")

        owned = [path for path, _hash in get_owned_code_files(conn, "digest")]

        assert owned == ["backend/src/digest/model.py"]

    def test_a_backslash_nested_source_is_still_excluded_from_its_parent(
        self, conn: sqlite3.Connection
    ) -> None:
        _node(conn, "digest", "backend/src/digest/")
        _node(conn, "sections", _NESTED)
        _indexed(conn, "backend/src/digest/model.py")
        _indexed(conn, "backend/src/digest/sections/kpi.py")

        parent = [path for path, _hash in get_owned_code_files(conn, "digest")]
        child = [path for path, _hash in get_owned_code_files(conn, "sections")]

        assert parent == ["backend/src/digest/model.py"]
        assert child == ["backend/src/digest/sections/kpi.py"]

    def test_a_backslash_file_source_owns_its_posix_file(self, conn: sqlite3.Connection) -> None:
        _node(conn, "router", _FILE)
        _indexed(conn, "frontend/src/app/router.ts")

        owned = [path for path, _hash in get_owned_code_files(conn, "router")]

        assert owned == ["frontend/src/app/router.ts"]


class TestTheUncheckedReason:
    """The reason a node with no pair is given: indexed code is not reported as absent."""

    def test_a_backslash_directory_source_sees_its_indexed_code(
        self, conn: sqlite3.Connection
    ) -> None:
        _indexed(conn, "backend/src/digest/model.py")

        verdict = _unchecked_reason(conn, _DIRECTORY)

        assert verdict["reason"] == "files_owned_by_nested_nodes"

    def test_a_backslash_file_source_sees_its_indexed_file(self, conn: sqlite3.Connection) -> None:
        _indexed(conn, "frontend/src/app/router.ts")

        verdict = _unchecked_reason(conn, _FILE)

        assert verdict["reason"] == "files_owned_by_nested_nodes"

    def test_a_source_with_nothing_indexed_still_reads_no_indexed_code(
        self, conn: sqlite3.Connection
    ) -> None:
        verdict = _unchecked_reason(conn, _DIRECTORY)

        assert verdict["reason"] == "no_indexed_code"
