"""Tests for node_detail_panel Connections summary and Symbols section."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Skip all TUI tests if textual is not installed
textual = pytest.importorskip("textual")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def populated_db(tmp_path: Path) -> tuple[Path, Path]:
    """Create a populated SQLite database for TUI testing."""
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    from beadloom.infrastructure.db import create_schema

    create_schema(conn)

    # Insert test nodes
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("auth", "domain", "Authentication domain", "src/auth"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth-login", "feature", "User login feature"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("payments", "domain", "Payments domain"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("api", "service", "API service", "src/api/server.py"),
    )
    # Insert edges — auth has 1 incoming (part_of) from auth-login
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "auth", "part_of"),
    )
    # auth has 1 outgoing depends_on to payments
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth", "payments", "depends_on"),
    )
    # api depends_on auth (for multi-edge grouping tests)
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("api", "auth", "depends_on"),
    )
    # Insert docs
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("auth/login.md", "feature", "auth-login", "abc123"),
    )
    conn.commit()
    conn.close()

    return db_path, tmp_path


@pytest.fixture()
def ro_conn(populated_db: tuple[Path, Path]) -> sqlite3.Connection:
    """Return a read-only connection to the populated test DB."""
    db_path, _project_root = populated_db
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Connections Summary Tests
# ---------------------------------------------------------------------------


class TestConnectionsSummary:
    """Tests for the Connections section in node_detail_panel."""

    def test_connections_outgoing_and_incoming(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section shows grouped outgoing and incoming edges."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        text = _render_node_detail("auth", provider)
        plain = text.plain

        assert "Connections" in plain
        # auth has 1 outgoing depends_on to payments
        assert "1 outgoing" in plain
        assert "depends_on(1)" in plain
        # auth has 2 incoming: part_of(1) from auth-login, depends_on(1) from api
        assert "2 incoming" in plain
        assert "part_of(1)" in plain

    def test_connections_no_edges(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section shows '(no connections)' when node has no edges."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        text = _render_node_detail("payments", provider)
        plain = text.plain

        assert "Connections" in plain
        # payments has incoming edge from auth, so check a truly isolated node
        # Actually payments has 1 incoming from auth. Let's verify:
        assert "incoming" in plain

    def test_connections_no_edges_isolated_node(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section shows '(no connections)' for truly isolated node."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        db_path, project_root = populated_db
        # Insert an isolated node with a writable connection
        conn_w = sqlite3.connect(str(db_path))
        conn_w.row_factory = sqlite3.Row
        conn_w.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("isolated", "domain", "Isolated domain"),
        )
        conn_w.commit()

        # Read-only connection
        conn_ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn_ro.row_factory = sqlite3.Row

        provider = GraphDataProvider(conn=conn_ro, project_root=project_root)

        text = _render_node_detail("isolated", provider)
        plain = text.plain

        assert "Connections" in plain
        assert "(no connections)" in plain

        conn_w.close()
        conn_ro.close()

    def test_connections_outgoing_only(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section works with outgoing-only edges."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        # auth-login has 1 outgoing part_of to auth, no incoming
        text = _render_node_detail("auth-login", provider)
        plain = text.plain

        assert "Connections" in plain
        assert "1 outgoing" in plain
        assert "part_of(1)" in plain
        # Should NOT contain "incoming" since auth-login has none
        assert "incoming" not in plain

    def test_connections_replaces_edges_section(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Old 'Edges' section is gone, replaced by 'Connections'."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        text = _render_node_detail("auth", provider)
        plain = text.plain

        # Old section should be gone
        assert "  Edges\n" not in plain
        # New section should exist
        assert "Connections" in plain


# ---------------------------------------------------------------------------
# Symbols Section Tests
# ---------------------------------------------------------------------------


class TestSymbolsSection:
    """Tests for the Symbols section in node_detail_panel."""

    def test_symbols_with_data(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Symbols section renders function and class symbols."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        mock_symbols = [
            {"symbol_name": "extract_symbols", "kind": "function", "line_start": 42},
            {"symbol_name": "CodeIndexer", "kind": "class", "line_start": 15},
            {"symbol_name": "NodeType", "kind": "type", "line_start": 5},
        ]

        with patch.object(provider, "get_symbols", return_value=mock_symbols):
            text = _render_node_detail("auth", provider)
            plain = text.plain

        assert "Symbols (3)" in plain
        # Function glyph
        assert "\u0192 extract_symbols" in plain
        assert ":42" in plain
        # Class glyph
        assert "C CodeIndexer" in plain
        assert ":15" in plain
        # Type glyph
        assert "T NodeType" in plain
        assert ":5" in plain

    def test_symbols_no_symbols(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Symbols section shows '(no symbols)' when empty."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        with patch.object(provider, "get_symbols", return_value=[]):
            text = _render_node_detail("auth", provider)
            plain = text.plain

        assert "Symbols" in plain
        assert "(no symbols)" in plain

    def test_symbols_no_source_path(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Symbols section shows '(no symbols)' for nodes without source."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        # auth-login has no source path — get_symbols returns []
        text = _render_node_detail("auth-login", provider)
        plain = text.plain

        assert "Symbols" in plain
        assert "(no symbols)" in plain


# ---------------------------------------------------------------------------
# get_symbols() Data Provider Tests
# ---------------------------------------------------------------------------


class TestGetSymbols:
    """Tests for GraphDataProvider.get_symbols()."""

    def test_get_symbols_returns_symbols(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """get_symbols() returns symbol data from code_symbols table."""
        db_path, project_root = populated_db

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Insert symbols into code_symbols table
        conn.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end, file_hash)"
            " VALUES (?, ?, ?, ?, ?, 'test')",
            ("src/api/server.py", "handle_request", "function", 1, 2),
        )
        conn.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end, file_hash)"
            " VALUES (?, ?, ?, ?, ?, 'test')",
            ("src/api/server.py", "Server", "class", 4, 5),
        )
        conn.commit()

        from beadloom.tui.data_providers import GraphDataProvider

        provider = GraphDataProvider(conn=conn, project_root=project_root)
        symbols = provider.get_symbols("api")

        assert len(symbols) == 2
        names = {str(s["symbol_name"]) for s in symbols}
        assert "handle_request" in names
        assert "Server" in names

        # Check kinds
        for s in symbols:
            if s["symbol_name"] == "handle_request":
                assert s["kind"] == "function"
                assert s["line_start"] == 1
            elif s["symbol_name"] == "Server":
                assert s["kind"] == "class"
                assert s["line_start"] == 4

        conn.close()

    def test_get_symbols_nonexistent_node(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_symbols() returns empty list for non-existent node."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        symbols = provider.get_symbols("nonexistent")
        assert symbols == []

    def test_get_symbols_no_source(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_symbols() returns empty list when node has no source."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        # auth-login has no source path
        symbols = provider.get_symbols("auth-login")
        assert symbols == []

    def test_get_symbols_directory_source(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """get_symbols() returns symbols for nodes with directory source paths."""
        db_path, project_root = populated_db

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # auth node has source "src/auth" — insert symbols under that prefix
        conn.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end, file_hash)"
            " VALUES (?, ?, ?, ?, ?, 'test')",
            ("src/auth/login.py", "authenticate", "function", 1, 10),
        )
        conn.execute(
            "INSERT INTO code_symbols"
            " (file_path, symbol_name, kind, line_start, line_end, file_hash)"
            " VALUES (?, ?, ?, ?, ?, 'test')",
            ("src/auth/models.py", "User", "class", 5, 20),
        )
        conn.commit()

        from beadloom.tui.data_providers import GraphDataProvider

        # auth source is "src/auth" (no trailing slash) — exact match, returns 0
        provider = GraphDataProvider(conn=conn, project_root=project_root)
        symbols = provider.get_symbols("auth")
        assert symbols == []

        # Update source to "src/auth/" (trailing slash) — prefix match works
        conn.execute(
            "UPDATE nodes SET source = 'src/auth/' WHERE ref_id = 'auth'"
        )
        conn.commit()
        symbols = provider.get_symbols("auth")
        assert len(symbols) == 2
        names = {str(s["symbol_name"]) for s in symbols}
        assert "authenticate" in names
        assert "User" in names

        conn.close()

    def test_get_symbols_empty_code_symbols(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """get_symbols() returns empty list when no symbols in DB for the node."""
        from beadloom.tui.data_providers import GraphDataProvider

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)
        # api has source "src/api/server.py" but no code_symbols rows
        symbols = provider.get_symbols("api")
        assert symbols == []


# ---------------------------------------------------------------------------
# Edge-case Tests: _render_node_detail error paths
# ---------------------------------------------------------------------------


class TestRenderNodeDetailEdgeCases:
    """Tests for _render_node_detail edge paths not covered above."""

    def test_render_no_provider(self) -> None:
        """_render_node_detail returns 'No data provider available' when provider is None."""
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        text = _render_node_detail("any-ref", None)
        plain = text.plain

        assert "No data provider available" in plain

    def test_render_node_not_found(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """_render_node_detail returns 'not found' for non-existent ref_id."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        text = _render_node_detail("nonexistent-node", provider)
        plain = text.plain

        assert "nonexistent-node" in plain
        assert "not found" in plain

    def test_render_unknown_symbol_kind_uses_fallback_glyph(
        self, ro_conn: sqlite3.Connection, populated_db: tuple[Path, Path]
    ) -> None:
        """Unknown symbol kinds use '?' as glyph fallback."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        _, project_root = populated_db
        provider = GraphDataProvider(conn=ro_conn, project_root=project_root)

        mock_symbols = [
            {"symbol_name": "SomeConstant", "kind": "variable", "line_start": 10},
        ]

        with patch.object(provider, "get_symbols", return_value=mock_symbols):
            text = _render_node_detail("auth", provider)
            plain = text.plain

        assert "? SomeConstant" in plain
        assert ":10" in plain

    def test_connections_incoming_only(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section works with incoming-only edges."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        db_path, project_root = populated_db

        # Create a node that only has incoming edges, no outgoing
        conn_w = sqlite3.connect(str(db_path))
        conn_w.row_factory = sqlite3.Row
        conn_w.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("sink", "feature", "Sink node"),
        )
        conn_w.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("auth", "sink", "depends_on"),
        )
        conn_w.commit()

        conn_ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn_ro.row_factory = sqlite3.Row

        provider = GraphDataProvider(conn=conn_ro, project_root=project_root)

        text = _render_node_detail("sink", provider)
        plain = text.plain

        assert "Connections" in plain
        assert "1 incoming" in plain
        assert "depends_on(1)" in plain
        # Should NOT show outgoing
        assert "outgoing" not in plain

        conn_w.close()
        conn_ro.close()

    def test_connections_multiple_edge_kinds(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Connections section groups multiple edge kinds correctly."""
        from beadloom.tui.data_providers import GraphDataProvider
        from beadloom.tui.widgets.node_detail_panel import _render_node_detail

        db_path, project_root = populated_db

        # Create a node with multiple outgoing edge kinds
        conn_w = sqlite3.connect(str(db_path))
        conn_w.row_factory = sqlite3.Row
        conn_w.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("multi", "service", "Multi-edge node"),
        )
        conn_w.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("target1", "domain", "Target 1"),
        )
        conn_w.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("target2", "domain", "Target 2"),
        )
        conn_w.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("multi", "target1", "depends_on"),
        )
        conn_w.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("multi", "target2", "part_of"),
        )
        conn_w.commit()

        conn_ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn_ro.row_factory = sqlite3.Row

        provider = GraphDataProvider(conn=conn_ro, project_root=project_root)

        text = _render_node_detail("multi", provider)
        plain = text.plain

        assert "Connections" in plain
        assert "2 outgoing" in plain
        assert "depends_on(1)" in plain
        assert "part_of(1)" in plain

        conn_w.close()
        conn_ro.close()
