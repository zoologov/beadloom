# beadloom:service=tui
"""Status bar widget showing health metrics, watcher status, and last action."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

# Watcher status indicators
_WATCHER_ACTIVE = "\u25cf"  # filled circle
_WATCHER_INACTIVE = "\u25cb"  # empty circle


class StatusBarWidget(Static):
    """Bottom status bar showing node/edge/doc/stale counts, watcher status, and last action.

    The watcher status is a placeholder (will be wired by BEAD-06).
    The last action message auto-dismisses on next data refresh.
    """

    DEFAULT_CSS = """
    StatusBarWidget {
        width: 100%;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
        dock: bottom;
    }
    """

    def __init__(self, *, widget_id: str | None = None) -> None:
        super().__init__(id=widget_id)
        self._node_count: int = 0
        self._edge_count: int = 0
        self._doc_count: int = 0
        self._stale_count: int = 0
        self._watcher_active: bool = False
        self._last_action: str = ""

    def render(self) -> Text:
        """Render the status bar as Rich Text."""
        text = Text()

        # Node/edge/doc counts
        text.append(f" {self._node_count} nodes", style="bold")
        text.append(f"  {self._edge_count} edges", style="bold")
        text.append(f"  {self._doc_count} docs", style="bold")

        # Stale count with color
        if self._stale_count > 0:
            text.append(f"  {self._stale_count} stale", style="bold red")
        else:
            text.append("  0 stale", style="green")

        # Separator
        text.append("  |  ")

        # Watcher status (placeholder for BEAD-06)
        if self._watcher_active:
            text.append(f"{_WATCHER_ACTIVE} watching", style="green")
        else:
            text.append(f"{_WATCHER_INACTIVE} no watch", style="dim")

        # Last action message
        if self._last_action:
            text.append(f"  |  {self._last_action}", style="italic")

        return text

    def refresh_data(
        self,
        *,
        node_count: int = 0,
        edge_count: int = 0,
        doc_count: int = 0,
        stale_count: int = 0,
    ) -> None:
        """Update count metrics and re-render.

        Clears any previous last action message.
        """
        self._node_count = node_count
        self._edge_count = edge_count
        self._doc_count = doc_count
        self._stale_count = stale_count
        self._last_action = ""
        self.refresh()

    def set_watcher_active(self, active: bool) -> None:
        """Update watcher status indicator (wired by BEAD-06)."""
        self._watcher_active = active
        self.refresh()

    def set_last_action(self, message: str) -> None:
        """Show a transient action message in the status bar."""
        self._last_action = message
        self.refresh()
