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
from beadloom.tui.file_watcher import ReindexNeeded, start_file_watcher
from beadloom.tui.screens.dashboard import DashboardScreen
from beadloom.tui.screens.doc_status import DocStatusScreen
from beadloom.tui.screens.explorer import ExplorerScreen

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from textual.worker import Worker

    from beadloom.tui.widgets.status_bar import StatusBarWidget

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
        self._file_watcher_worker: Worker[None] | None = None

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
        """Open DB, initialize providers, install screens, push default, start watcher."""
        self._conn = self._open_db()
        self._init_providers()
        # Install named screens for keyboard switching
        self.install_screen(DashboardScreen(), name=SCREEN_DASHBOARD)
        self.install_screen(ExplorerScreen(), name=SCREEN_EXPLORER)
        self.install_screen(DocStatusScreen(), name=SCREEN_DOC_STATUS)
        self.push_screen(SCREEN_DASHBOARD)

        # Start file watcher when enabled
        if not self.no_watch:
            self._start_file_watcher()

    def _start_file_watcher(self) -> None:
        """Start the file watcher Worker and update status bar."""
        source_paths: list[str] = []
        if self.graph_provider is not None:
            source_paths = self.graph_provider.get_source_paths()

        worker = start_file_watcher(
            self,
            self.project_root,
            source_paths,
        )
        self._file_watcher_worker = worker

        # Update status bar to show watcher state
        self._for_each_status_bar(lambda bar: bar.set_watcher_active(worker is not None))

    def _for_each_status_bar(self, action: Callable[[StatusBarWidget], None]) -> None:
        """Apply *action* to every StatusBarWidget across installed screens.

        Silently skips screens that are not yet composed or have no status bar.
        """
        from beadloom.tui.widgets.status_bar import StatusBarWidget as _StatusBar

        for screen_name in self._VALID_SCREENS:
            screen_obj = self._installed_screens.get(screen_name)
            if screen_obj is None or not hasattr(screen_obj, "query_one"):
                continue
            try:
                bar = screen_obj.query_one(_StatusBar)
            except Exception:
                logger.debug("StatusBar not found on screen %s", screen_name)
                continue
            action(bar)

    def on_reindex_needed(self, message: ReindexNeeded) -> None:
        """Handle file-change notification from the watcher."""
        count = len(message.changed_paths)
        logger.info("Reindex needed: %d file(s) changed", count)

        # Update status bar to show "changes detected" badge
        self._for_each_status_bar(lambda bar: bar.set_changes_detected(count))

    def on_unmount(self) -> None:
        """Cancel watcher and close DB connection on unmount."""
        if self._file_watcher_worker is not None:
            self._file_watcher_worker.cancel()
            self._file_watcher_worker = None
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
        """Trigger reindex in background, refresh providers, clear watcher badge."""
        from beadloom.infrastructure.reindex import incremental_reindex

        incremental_reindex(self.project_root)
        self._refresh_providers()

        # Clear the "changes detected" badge on all screens
        self._for_each_status_bar(lambda bar: bar.clear_changes())

        # Refresh visible screen widgets
        self._refresh_screen_widgets()

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

    def _refresh_screen_widgets(self) -> None:
        """Refresh widgets on the currently active screen."""
        screen = self.screen
        if hasattr(screen, "refresh_all_widgets"):
            screen.refresh_all_widgets()
