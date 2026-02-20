# beadloom:service=tui
"""Main Textual application for Beadloom TUI — multi-screen architecture."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from beadloom.tui.data_providers import (
    ActivityDataProvider,
    ContextDataProvider,
    DebtDataProvider,
    GraphDataProvider,
    LintDataProvider,
    SyncDataProvider,
    WhyDataProvider,
)
from beadloom.tui.screens.dashboard import DashboardScreen
from beadloom.tui.screens.doc_status import DocStatusScreen
from beadloom.tui.screens.explorer import ExplorerScreen

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Screen name constants
SCREEN_DASHBOARD = "dashboard"
SCREEN_EXPLORER = "explorer"
SCREEN_DOC_STATUS = "doc_status"


class BeadloomApp(App[None]):
    """Beadloom interactive terminal dashboard — multi-screen architecture."""

    TITLE = "Beadloom"
    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("1", "switch_screen('dashboard')", "Dashboard", key_display="1"),
        Binding("2", "switch_screen('explorer')", "Explorer", key_display="2"),
        Binding("3", "switch_screen('doc_status')", "Doc Status", key_display="3"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help"),
        Binding("slash", "search", "Search"),
        Binding("r", "reindex", "Reindex"),
        Binding("l", "lint", "Lint"),
        Binding("s", "sync_check", "Sync"),
        Binding("tab", "focus_next", "Next panel"),
    ]

    def __init__(
        self,
        db_path: Path,
        project_root: Path,
        *,
        no_watch: bool = False,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.project_root = project_root
        self.no_watch = no_watch
        self._conn: sqlite3.Connection | None = None

        # Data providers (initialized on mount)
        self.graph_provider: GraphDataProvider | None = None
        self.lint_provider: LintDataProvider | None = None
        self.sync_provider: SyncDataProvider | None = None
        self.debt_provider: DebtDataProvider | None = None
        self.activity_provider: ActivityDataProvider | None = None
        self.why_provider: WhyDataProvider | None = None
        self.context_provider: ContextDataProvider | None = None

    def _open_db(self) -> sqlite3.Connection:
        """Open read-only SQLite connection."""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_providers(self) -> None:
        """Initialize all data providers with the open DB connection."""
        if self._conn is None:
            return
        self.graph_provider = GraphDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.lint_provider = LintDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.sync_provider = SyncDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.debt_provider = DebtDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.activity_provider = ActivityDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.why_provider = WhyDataProvider(
            conn=self._conn, project_root=self.project_root
        )
        self.context_provider = ContextDataProvider(
            conn=self._conn, project_root=self.project_root
        )

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Open DB, initialize providers, install screens, push default."""
        self._conn = self._open_db()
        self._init_providers()
        # Install named screens for keyboard switching
        self.install_screen(DashboardScreen(), name=SCREEN_DASHBOARD)
        self.install_screen(ExplorerScreen(), name=SCREEN_EXPLORER)
        self.install_screen(DocStatusScreen(), name=SCREEN_DOC_STATUS)
        self.push_screen(SCREEN_DASHBOARD)

    def on_unmount(self) -> None:
        """Close DB connection on unmount."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    _VALID_SCREENS: ClassVar[frozenset[str]] = frozenset({
        SCREEN_DASHBOARD,
        SCREEN_EXPLORER,
        SCREEN_DOC_STATUS,
    })

    async def action_switch_screen(self, screen_name: str) -> None:
        """Switch to the named screen."""
        if screen_name in self._VALID_SCREENS:
            self.switch_screen(screen_name)

    def action_help(self) -> None:
        """Show help overlay (placeholder for BEAD-07)."""
        self.notify("Help overlay coming in BEAD-07")

    def action_search(self) -> None:
        """Show search overlay (placeholder for BEAD-07)."""
        self.notify("Search overlay coming in BEAD-07")

    def action_reindex(self) -> None:
        """Trigger reindex in background."""
        from beadloom.infrastructure.reindex import incremental_reindex

        incremental_reindex(self.project_root)
        self._refresh_providers()
        self.notify("Reindex complete")

    def action_lint(self) -> None:
        """Run lint check and notify."""
        if self.lint_provider is not None:
            self.lint_provider.refresh()
            count = self.lint_provider.get_violation_count()
            self.notify(f"Lint: {count} violation(s)")

    def action_sync_check(self) -> None:
        """Run sync-check and notify."""
        if self.sync_provider is not None:
            self.sync_provider.refresh()
            stale = self.sync_provider.get_stale_count()
            self.notify(f"Sync: {stale} stale doc(s)")

    def _refresh_providers(self) -> None:
        """Refresh all data providers after reindex."""
        if self.graph_provider is not None:
            self.graph_provider.refresh()
        if self.lint_provider is not None:
            self.lint_provider.refresh()
        if self.sync_provider is not None:
            self.sync_provider.refresh()
        if self.debt_provider is not None:
            self.debt_provider.refresh()
        if self.activity_provider is not None:
            self.activity_provider.refresh()
