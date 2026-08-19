"""Tests for node file ownership — most-specific-source-wins (BDL-UX #144/#157).

A node's `source` is a path PREFIX, and graphs nest: `src/pkg/` (a domain) holds
`src/pkg/feature/` (a feature) which holds `src/pkg/feature/impl.py`. Attributing
by raw prefix therefore counts a child's files against its parent as well, so a
parent can never be relieved by carving a subpackage out into its own node — the
remedy the size limit is supposed to prompt.

The rule these tests pin: **a file belongs to exactly one node — the most
specific one whose source covers it.** Everything that counts, sizes or links
code must agree on that single answer.
"""

from __future__ import annotations

import sqlite3

import pytest

from beadloom.infrastructure.db import create_schema
from beadloom.infrastructure.repository import (
    count_symbols_owned_by_node,
    get_owned_symbols,
    owns_file,
)


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


def _symbol(conn: sqlite3.Connection, file_path: str, name: str) -> None:
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, 'function', 1, 2, 'h')",
        (file_path, name),
    )


def _seed_nested(conn: sqlite3.Connection) -> None:
    """A domain holding a feature package, a feature module, and its own file."""
    _node(conn, "domain", "src/pkg/")
    _node(conn, "feature-pkg", "src/pkg/feature/")
    _node(conn, "feature-mod", "src/pkg/single.py")

    _symbol(conn, "src/pkg/own.py", "own_one")
    _symbol(conn, "src/pkg/own.py", "own_two")
    _symbol(conn, "src/pkg/feature/impl.py", "feature_one")
    _symbol(conn, "src/pkg/feature/util.py", "feature_two")
    _symbol(conn, "src/pkg/single.py", "single_one")
    conn.commit()


class TestOwnsFile:
    """`owns_file` answers the one question every reader needs."""

    def test_directory_source_owns_a_file_directly_under_it(
        self, conn: sqlite3.Connection
    ) -> None:
        _seed_nested(conn)
        assert owns_file(conn, "domain", "src/pkg/own.py") is True

    def test_parent_does_not_own_a_nested_nodes_file(
        self, conn: sqlite3.Connection
    ) -> None:
        """The whole point: carving a subpackage out RELIEVES the parent."""
        _seed_nested(conn)
        assert owns_file(conn, "domain", "src/pkg/feature/impl.py") is False
        assert owns_file(conn, "feature-pkg", "src/pkg/feature/impl.py") is True

    def test_file_sourced_node_owns_its_own_file(self, conn: sqlite3.Connection) -> None:
        """A node whose source IS a file owns that file, not its parent directory."""
        _seed_nested(conn)
        assert owns_file(conn, "feature-mod", "src/pkg/single.py") is True
        assert owns_file(conn, "domain", "src/pkg/single.py") is False

    def test_unrelated_file_is_owned_by_nobody(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        assert owns_file(conn, "domain", "src/other/thing.py") is False

    def test_unknown_node_owns_nothing(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        assert owns_file(conn, "ghost", "src/pkg/own.py") is False

    def test_sibling_prefix_is_not_containment(self, conn: sqlite3.Connection) -> None:
        """`src/pkg2/` must not be swallowed by a `src/pkg` string prefix."""
        _node(conn, "a", "src/pkg/")
        _node(conn, "b", "src/pkg2/")
        _symbol(conn, "src/pkg2/x.py", "x")
        conn.commit()
        assert owns_file(conn, "a", "src/pkg2/x.py") is False
        assert owns_file(conn, "b", "src/pkg2/x.py") is True


class TestCountSymbolsOwnedByNode:
    """Counting follows ownership, so a size limit measures the node itself."""

    def test_parent_count_excludes_nested_nodes(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        # 2 own symbols; the feature package (2) and the module (1) are NOT its.
        assert count_symbols_owned_by_node(conn, "domain") == 2

    def test_nested_node_counts_its_own(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        assert count_symbols_owned_by_node(conn, "feature-pkg") == 2
        assert count_symbols_owned_by_node(conn, "feature-mod") == 1

    def test_package_facade_source_counts_the_whole_package(
        self, conn: sqlite3.Connection
    ) -> None:
        """BDL-UX #157: a source at `__init__.py` must not hide the package.

        The façade only re-exports, so treating it as a lone file reports zero
        for a package full of code. Ownership resolves it to the package.
        """
        _node(conn, "facade", "src/pkg/facade/__init__.py")
        _symbol(conn, "src/pkg/facade/__init__.py", "reexport")
        _symbol(conn, "src/pkg/facade/impl.py", "real_one")
        _symbol(conn, "src/pkg/facade/impl.py", "real_two")
        conn.commit()

        assert count_symbols_owned_by_node(conn, "facade") == 3

    def test_facade_still_yields_to_a_more_specific_node(
        self, conn: sqlite3.Connection
    ) -> None:
        """Resolving a façade to its package must not swallow a nested node."""
        _node(conn, "facade", "src/pkg/facade/__init__.py")
        _node(conn, "inner", "src/pkg/facade/inner/")
        _symbol(conn, "src/pkg/facade/impl.py", "real_one")
        _symbol(conn, "src/pkg/facade/inner/deep.py", "deep_one")
        conn.commit()

        assert count_symbols_owned_by_node(conn, "facade") == 1
        assert count_symbols_owned_by_node(conn, "inner") == 1

    def test_node_without_source_counts_zero(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) "
            "VALUES ('abstract', 'domain', 's', NULL)"
        )
        conn.commit()
        assert count_symbols_owned_by_node(conn, "abstract") == 0

    def test_empty_index_counts_zero(self, conn: sqlite3.Connection) -> None:
        _node(conn, "domain", "src/pkg/")
        conn.commit()
        assert count_symbols_owned_by_node(conn, "domain") == 0


class TestGetOwnedSymbols:
    """The symbol LIST follows the same ownership as the count."""

    def test_returns_only_owned_symbols_sorted(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        names = [s.symbol_name for s in get_owned_symbols(conn, "domain")]
        assert names == ["own_one", "own_two"]

    def test_nested_node_symbols_are_its_own(self, conn: sqlite3.Connection) -> None:
        _seed_nested(conn)
        names = sorted(s.symbol_name for s in get_owned_symbols(conn, "feature-pkg"))
        assert names == ["feature_one", "feature_two"]

    def test_count_and_list_agree(self, conn: sqlite3.Connection) -> None:
        """No surface may report a different number than another (#157's root)."""
        _seed_nested(conn)
        for ref_id in ("domain", "feature-pkg", "feature-mod"):
            assert count_symbols_owned_by_node(conn, ref_id) == len(
                get_owned_symbols(conn, ref_id)
            )
