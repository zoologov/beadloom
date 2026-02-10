"""Tests for Beadloom TUI."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Skip all TUI tests if textual is not installed
textual = pytest.importorskip("textual")


def _get_static_content(widget: object) -> str:
    """Extract the raw content string from a Textual Static widget.

    Uses the name-mangled ``_Static__content`` attribute which stores
    the string passed to ``widget.update()``.
    """
    return str(getattr(widget, "_Static__content", ""))


@pytest.fixture()
def populated_db(tmp_path: Path) -> tuple[Path, Path]:
    """Create a populated SQLite database for TUI testing."""
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    db_path.parent.mkdir(parents=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create schema
    from beadloom.db import create_schema

    create_schema(conn)

    # Insert test data
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth", "domain", "Authentication domain"),
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
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "auth", "part_of"),
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("auth/login.md", "feature", "auth-login", "abc123"),
    )
    conn.commit()
    conn.close()

    return db_path, tmp_path


def test_app_launches(populated_db: tuple[Path, Path]) -> None:
    """App can be instantiated without errors."""
    db_path, project_root = populated_db
    from beadloom.tui.app import BeadloomApp

    app = BeadloomApp(db_path=db_path, project_root=project_root)
    assert app.db_path == db_path
    assert app.project_root == project_root
    assert app.TITLE == "Beadloom"


def test_domain_list_loads(populated_db: tuple[Path, Path]) -> None:
    """DomainList.load_domains() populates options from the database."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.domain_list import DomainList

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = DomainList()
    widget.load_domains(conn)

    # Should have 2 domains: auth and payments
    assert widget.option_count == 2

    conn.close()


def test_node_detail_shows_domain(populated_db: tuple[Path, Path]) -> None:
    """NodeDetail.show_domain() shows correct info for a domain."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.node_detail import NodeDetail

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = NodeDetail()
    widget.show_domain(conn, "auth")

    rendered = _get_static_content(widget)
    assert "auth" in rendered
    assert "domain" in rendered
    assert "auth-login" in rendered

    conn.close()


def test_node_detail_shows_domain_not_found(populated_db: tuple[Path, Path]) -> None:
    """NodeDetail.show_domain() handles missing nodes."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.node_detail import NodeDetail

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = NodeDetail()
    widget.show_domain(conn, "nonexistent")

    rendered = _get_static_content(widget)
    assert "not found" in rendered

    conn.close()


def test_node_detail_shows_node(populated_db: tuple[Path, Path]) -> None:
    """NodeDetail.show_node() shows edges and docs for a node."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.node_detail import NodeDetail

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = NodeDetail()
    widget.show_node(conn, "auth-login")

    rendered = _get_static_content(widget)
    assert "auth-login" in rendered
    assert "feature" in rendered
    # Should show outgoing edge to auth (part_of)
    assert "auth" in rendered
    assert "part_of" in rendered
    # Should show docs
    assert "auth/login.md" in rendered

    conn.close()


def test_node_detail_shows_node_not_found(populated_db: tuple[Path, Path]) -> None:
    """NodeDetail.show_node() handles missing nodes."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.node_detail import NodeDetail

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = NodeDetail()
    widget.show_node(conn, "nonexistent")

    rendered = _get_static_content(widget)
    assert "not found" in rendered

    conn.close()


def test_status_bar_loads(populated_db: tuple[Path, Path]) -> None:
    """StatusBar.load_stats() shows metrics from the database."""
    db_path, _project_root = populated_db
    from beadloom.tui.widgets.status_bar import StatusBar

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    widget = StatusBar()
    widget.load_stats(conn)

    rendered = _get_static_content(widget)
    # Should contain node, edge, doc counts
    assert "3 nodes" in rendered
    assert "1 edges" in rendered
    assert "1 docs" in rendered
    # Should show coverage percentage
    assert "Coverage:" in rendered
    # Should show stale count
    assert "Stale:" in rendered

    conn.close()


@pytest.mark.asyncio()
async def test_app_runs_headless(populated_db: tuple[Path, Path]) -> None:
    """App runs via pilot (headless mode) and can be quit."""
    db_path, project_root = populated_db
    from beadloom.tui.app import BeadloomApp

    app = BeadloomApp(db_path=db_path, project_root=project_root)
    async with app.run_test() as pilot:
        # App should be running
        assert app.is_running
        await pilot.press("q")


def test_cli_ui_missing_textual() -> None:
    """CLI shows friendly error when textual not installed."""
    from click.testing import CliRunner

    from beadloom.cli import ui

    runner = CliRunner()

    # Simulate ImportError by setting module to None in sys.modules
    with patch.dict("sys.modules", {"beadloom.tui": None}):
        result = runner.invoke(ui, [])
        # Should show error about missing textual
        assert result.exit_code != 0


def test_cli_ui_missing_db(tmp_path: Path) -> None:
    """CLI shows error when database does not exist."""
    from click.testing import CliRunner

    from beadloom.cli import ui

    runner = CliRunner()
    result = runner.invoke(ui, ["--project", str(tmp_path)])
    assert result.exit_code != 0
    assert "database not found" in result.output or result.exit_code == 1
