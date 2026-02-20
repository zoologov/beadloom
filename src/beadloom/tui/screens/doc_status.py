# beadloom:service=tui
"""Doc status screen — documentation health overview."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DocStatusScreen(Screen[None]):
    """Documentation health status screen.

    Placeholder: widgets will be added in BEAD-05.
    """

    CSS_PATH = "../styles/doc_status.tcss"

    def compose(self) -> ComposeResult:
        """Compose the doc status layout."""
        yield Label("Doc Status — coming in BEAD-05", id="doc-status-placeholder")
