# beadloom:service=tui
"""Explorer screen — node deep-dive with detail, dependencies, context."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult


class ExplorerScreen(Screen[None]):
    """Node explorer screen for deep-dive analysis.

    Placeholder: widgets will be added in BEAD-04.
    """

    CSS_PATH = "../styles/explorer.tcss"

    def compose(self) -> ComposeResult:
        """Compose the explorer layout."""
        yield Label("Explorer — coming in BEAD-04", id="explorer-placeholder")
