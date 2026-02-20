"""Tests for screen description labels (BDL-025, BEAD-02)."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

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
    # Insert edges
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "auth", "part_of"),
    )
    # Insert docs
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("auth/login.md", "feature", "auth-login", "abc123"),
    )
    conn.commit()
    conn.close()

    return db_path, tmp_path


# ---------------------------------------------------------------------------
# Dashboard screen description
# ---------------------------------------------------------------------------


class TestDashboardScreenDescription:
    """Tests for the Dashboard screen description label."""

    @pytest.mark.asyncio()
    async def test_dashboard_has_screen_description(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen has a Label with id='screen-description'."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            desc = app.screen.query_one("#screen-description", Label)
            assert desc is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_dashboard_description_text(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DashboardScreen description matches expected text."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            desc = app.screen.query_one("#screen-description", Label)
            expected = (
                "Architecture overview: graph structure, "
                "git activity, lint & debt health"
            )
            assert str(desc.content) == expected
            await pilot.press("q")


# ---------------------------------------------------------------------------
# Explorer screen description
# ---------------------------------------------------------------------------


class TestExplorerScreenDescription:
    """Tests for the Explorer screen description label."""

    @pytest.mark.asyncio()
    async def test_explorer_has_screen_description(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen has a Label with id='screen-description'."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")  # switch to explorer
            assert isinstance(app.screen, ExplorerScreen)

            desc = app.screen.query_one("#screen-description", Label)
            assert desc is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_explorer_description_text(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """ExplorerScreen description matches expected text."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.explorer import ExplorerScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(app.screen, ExplorerScreen)

            desc = app.screen.query_one("#screen-description", Label)
            expected = "Node deep-dive: detail, dependencies, context bundle"
            assert str(desc.content) == expected
            await pilot.press("q")


# ---------------------------------------------------------------------------
# Doc Status screen description
# ---------------------------------------------------------------------------


class TestDocStatusScreenDescription:
    """Tests for the DocStatus screen description label."""

    @pytest.mark.asyncio()
    async def test_doc_status_has_screen_description(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen has a Label with id='screen-description'."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")  # switch to doc status
            assert isinstance(app.screen, DocStatusScreen)

            desc = app.screen.query_one("#screen-description", Label)
            assert desc is not None
            await pilot.press("q")

    @pytest.mark.asyncio()
    async def test_doc_status_description_text(
        self, populated_db: tuple[Path, Path]
    ) -> None:
        """DocStatusScreen description matches expected text."""
        db_path, project_root = populated_db
        from textual.widgets import Label

        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.screens.doc_status import DocStatusScreen

        app = BeadloomApp(db_path=db_path, project_root=project_root)
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(app.screen, DocStatusScreen)

            desc = app.screen.query_one("#screen-description", Label)
            expected = (
                "Documentation health: coverage, freshness, staleness reasons"
            )
            assert str(desc.content) == expected
            await pilot.press("q")
