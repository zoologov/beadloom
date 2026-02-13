"""Main Textual application for Beadloom TUI."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from beadloom.tui.widgets.domain_list import DomainList
from beadloom.tui.widgets.node_detail import NodeDetail
from beadloom.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from pathlib import Path


class BeadloomApp(App[None]):
    """Beadloom interactive terminal dashboard."""

    TITLE = "Beadloom"
    CSS_PATH = "styles/app.tcss"
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "quit", "Quit"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "reindex", "Reindex"),
    ]

    def __init__(self, db_path: Path, project_root: Path) -> None:
        super().__init__()
        self.db_path = db_path
        self.project_root = project_root

    def _open_db(self) -> sqlite3.Connection:
        """Open read-only SQLite connection."""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        with Horizontal(id="main-content"):
            yield DomainList(id="domain-list")
            yield NodeDetail(id="node-detail")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load data when app mounts."""
        self._refresh_data()

    def _refresh_data(self) -> None:
        """Refresh all panels from database."""
        conn = self._open_db()
        try:
            domain_list = self.query_one("#domain-list", DomainList)
            domain_list.load_domains(conn)

            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.load_stats(conn)

            # Auto-select first domain to populate detail panel
            if domain_list.option_count > 0:
                first = domain_list.get_option_at_index(0)
                if first.id is not None:
                    detail = self.query_one("#node-detail", NodeDetail)
                    detail.show_node(conn, str(first.id))
        finally:
            conn.close()

    def on_domain_list_domain_selected(self, event: DomainList.DomainSelected) -> None:
        """Handle domain selection."""
        conn = self._open_db()
        try:
            detail = self.query_one("#node-detail", NodeDetail)
            detail.show_node(conn, event.ref_id)
        finally:
            conn.close()

    def on_domain_list_node_selected(self, event: DomainList.NodeSelected) -> None:
        """Handle node selection."""
        conn = self._open_db()
        try:
            detail = self.query_one("#node-detail", NodeDetail)
            detail.show_node(conn, event.ref_id)
        finally:
            conn.close()

    def action_reindex(self) -> None:
        """Trigger reindex."""
        from beadloom.infrastructure.reindex import incremental_reindex

        incremental_reindex(self.project_root)
        self._refresh_data()

    def action_focus_search(self) -> None:
        """Focus the domain list for keyboard navigation."""
        self.query_one("#domain-list", DomainList).focus()
