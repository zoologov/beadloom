# beadloom:service=tui
"""Activity widget showing per-domain git activity levels."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static

# Bar rendering constants
_BAR_MAX_WIDTH = 20
_BAR_CHAR_FILLED = "\u2588"  # full block
_BAR_CHAR_EMPTY = "\u2591"  # light shade


def _activity_level(activity: Any) -> int:
    """Extract a numeric activity level (0-100) from a GitActivity object or dict."""
    if activity is None:
        return 0
    # GitActivity dataclass has commits_30d and activity_level attributes
    if hasattr(activity, "commits_30d"):
        # Normalize: cap at 50 commits for 100%
        return min(int(activity.commits_30d) * 2, 100)
    if isinstance(activity, dict):
        return min(int(activity.get("commits_30d", 0)) * 2, 100)
    return 0


def _render_bar(level: int, width: int = _BAR_MAX_WIDTH) -> tuple[str, str]:
    """Render a progress bar string and its style.

    Returns (bar_string, style).
    """
    filled = max(0, min(width, int(level / 100 * width)))
    empty = width - filled
    bar = _BAR_CHAR_FILLED * filled + _BAR_CHAR_EMPTY * empty

    if level >= 70:
        style = "green"
    elif level >= 30:
        style = "yellow"
    else:
        style = "dim"

    return bar, style


class ActivityWidget(Static):
    """Displays per-domain git activity as progress bars.

    Each domain shows its name and a bar representing relative activity level.
    """

    DEFAULT_CSS = """
    ActivityWidget {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        activities: dict[str, Any] | None = None,
        widget_id: str | None = None,
    ) -> None:
        super().__init__(id=widget_id)
        self._activities: dict[str, Any] = activities or {}

    def render(self) -> Text:
        """Render per-domain activity bars as Rich Text."""
        text = Text()
        text.append("Activity", style="bold underline")

        if not self._activities:
            text.append("\n  No activity data")
            return text

        for ref_id in sorted(self._activities):
            activity = self._activities[ref_id]
            level = _activity_level(activity)
            bar, style = _render_bar(level)

            text.append("\n  ")
            text.append(f"{ref_id:<20s}", style="bold")
            text.append(" ")
            text.append(bar, style=style)
            text.append(f" {level}%", style="dim")

        return text

    def refresh_data(self, activities: dict[str, Any]) -> None:
        """Update the activities data and re-render."""
        self._activities = dict(activities)
        self.refresh()
