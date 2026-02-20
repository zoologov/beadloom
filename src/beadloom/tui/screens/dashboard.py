# beadloom:service=tui
"""Dashboard screen — main overview with graph tree, debt gauge, lint panel, activity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DashboardScreen(Screen[None]):
    """Main dashboard screen with architecture overview.

    Placeholder: widgets will be added in BEAD-02.
    """

    CSS_PATH = "../styles/dashboard.tcss"

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Label("Dashboard — coming in BEAD-02", id="dashboard-placeholder")
