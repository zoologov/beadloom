"""Tests for Dashboard action bar — keybinding hints at the bottom of the screen."""

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


class TestDashboardActionBar:
    """Tests for the dashboard action bar widget."""

    @pytest.mark.asyncio()
    async def test_dashboard_has_action_bar(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a Label with id='dashboard-action-bar'."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            action_bar = app.screen.query_one("#dashboard-action-bar", Label)
            assert action_bar is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_action_bar_contains_keybindings(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """Action bar text contains expected keybinding hints."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            action_bar = app.screen.query_one("#dashboard-action-bar", Label)
            text = str(action_bar.content)

            # Verify all expected keybinding hints are present
            assert "[Enter]explore" in text
            assert "[r]eindex" in text
            assert "[l]int" in text
            assert "[s]ync-check" in text
            assert "[S]napshot" in text
            assert "[?]help" in text
            await pilot.press("q")
