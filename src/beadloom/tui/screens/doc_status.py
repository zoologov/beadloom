# beadloom:service=tui
"""Doc status screen -- documentation health overview with per-node status table."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label

from beadloom.tui.widgets.doc_health import (
    DocHealthTable,
    compute_coverage_stats,
    compute_doc_rows,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from beadloom.tui.app import BeadloomApp

logger = logging.getLogger(__name__)


class DocStatusScreen(Screen[None]):
    """Documentation health status screen.

    Shows a header with coverage stats, a DataTable of per-node doc health,
    and an action bar with keybindings for generate, polish, and back.

    Layout:
    - Header: coverage %, stale count, total nodes
    - Main: DocHealthTable (sortable, color-coded)
    - Footer: action bar [g]enerate [p]olish [Esc]back
    """

    CSS_PATH = "../styles/doc_status.tcss"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("g", "generate", "Generate"),
        Binding("p", "polish", "Polish"),
        Binding("escape", "go_back", "Back", key_display="Esc"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the doc status layout."""
        with Vertical(id="doc-status-container"):
            yield Label(
                "Documentation Health",
                id="doc-status-header",
            )
            yield Label(
                "Documentation health: coverage, freshness, staleness reasons",
                id="screen-description",
                classes="screen-desc",
            )
            yield DocHealthTable(widget_id="doc-health-table")

        yield Footer()

    def on_mount(self) -> None:
        """Load data from providers when the screen mounts."""
        self._load_data()

    def _load_data(self) -> None:
        """Load doc health data from providers and update header + table."""
        app = self._get_app()
        if app is None:
            return

        # Compute rows
        rows = compute_doc_rows(
            graph_provider=app.graph_provider,
            sync_provider=app.sync_provider,
        )

        # Update header with stats
        coverage, stale_count, total = compute_coverage_stats(rows)
        header_text = (
            f"Documentation Health \u2014 "
            f"{coverage:.0f}% covered, "
            f"{stale_count} stale, "
            f"{total} total"
        )
        try:
            header = self.query_one("#doc-status-header", Label)
            header.update(header_text)
        except Exception:
            logger.debug("Failed to update doc status header", exc_info=True)

        # Update table
        try:
            table = self.query_one("#doc-health-table", DocHealthTable)
            table.refresh_data(
                graph_provider=app.graph_provider,
                sync_provider=app.sync_provider,
            )
        except Exception:
            logger.debug("Failed to update doc health table", exc_info=True)

    def action_generate(self) -> None:
        """Generate doc skeleton for the selected node (placeholder)."""
        try:
            table = self.query_one("#doc-health-table", DocHealthTable)
            ref_id = table.get_selected_ref_id()
            if ref_id:
                self.notify(
                    f"Doc generation for '{ref_id}' not implemented yet",
                    title="Generate",
                )
            else:
                self.notify("No node selected", title="Generate")
        except Exception:
            self.notify("Doc generation not implemented yet", title="Generate")

    def action_polish(self) -> None:
        """View polish data for the selected node (placeholder)."""
        try:
            table = self.query_one("#doc-health-table", DocHealthTable)
            ref_id = table.get_selected_ref_id()
            if ref_id:
                self.notify(
                    f"Doc polish for '{ref_id}' not implemented yet",
                    title="Polish",
                )
            else:
                self.notify("No node selected", title="Polish")
        except Exception:
            self.notify("Doc polish not implemented yet", title="Polish")

    def action_go_back(self) -> None:
        """Return to the previous screen (dashboard)."""
        self.app.pop_screen()

    def refresh_all_widgets(self) -> None:
        """Refresh all doc status widgets with fresh data from providers."""
        self._load_data()

    def _get_app(self) -> BeadloomApp | None:
        """Get the BeadloomApp instance, returning None if not available."""
        try:
            from beadloom.tui.app import BeadloomApp

            app = self.app
            if isinstance(app, BeadloomApp):
                return app
        except Exception:
            logger.debug("Failed to get BeadloomApp instance", exc_info=True)
        return None
