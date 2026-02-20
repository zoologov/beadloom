"""Tests for Dashboard Footer — Textual Footer widget with keybinding hints."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# Skip all TUI tests if textual is not installed
textual = pytest.importorskip("textual")


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
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth", "domain", "Authentication domain"),
    )
    conn.commit()
    conn.close()

    return db_path, tmp_path


class TestDashboardFooter:
    """Tests for the dashboard Footer widget."""

    @pytest.mark.asyncio()
    async def test_dashboard_has_footer(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a Textual Footer widget."""
        db_path, project_root = populated_db
        from textual.widgets import Footer

        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            footer = app.screen.query_one(Footer)
            assert footer is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_has_footer(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen has a Textual Footer widget."""
        db_path, project_root = populated_db
        from textual.widgets import Footer

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            footer = app.screen.query_one(Footer)
            assert footer is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_has_footer(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen has a Textual Footer widget."""
        db_path, project_root = populated_db
        from textual.widgets import Footer

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            footer = app.screen.query_one(Footer)
            assert footer is not None
            await pilot.press("q")
