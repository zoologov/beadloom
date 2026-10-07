# beadloom:service=tui
"""Activity widget showing per-node changed lines and activity levels."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static

from beadloom.application.graph_reads import NO_CHANGE_WORDS, count_in_words

# Bar rendering constants
_BAR_MAX_WIDTH = 20
_BAR_CHAR_FILLED = "\u2588"  # full block
_BAR_CHAR_EMPTY = "\u2591"  # light shade
_PERCENT = 100

#: The style of each activity level, busiest brightest (BDL-078 F-activity: the
#: levels are relative to the project, measured in changed lines).
LEVEL_STYLES: dict[str, str] = {
    "hot": "bold green",
    "warm": "yellow",
    "cool": "cyan",
    "quiet": "dim",
    "dormant": "dim",
}


def _field(activity: Any, name: str, attribute: str) -> object:
    """A field of a GitActivity object or of the dict the index stores; ``None`` if absent."""
    if isinstance(activity, dict):
        return activity.get(name)
    return getattr(activity, attribute, None)


def _lines_30d(activity: Any) -> int:
    """Changed lines in 30 days; 0 for an activity recorded before lines were counted."""
    value = _field(activity, "lines_30d", "lines_30d")
    return value if isinstance(value, int) else 0


def _level_of(activity: Any) -> str:
    """The activity level, or ``""`` when none is recorded."""
    value = _field(activity, "level", "activity_level")
    return value if isinstance(value, str) else ""


def _style_of(level: str) -> str:
    """The style of *level*; plain for a level this widget does not know."""
    return LEVEL_STYLES.get(level, "")


def _describe(activity: Any) -> str:
    """The activity in words, as the node card words it."""
    level = _level_of(activity)
    if level in NO_CHANGE_WORDS:
        return f"{NO_CHANGE_WORDS[level]}, {level}"
    lines = count_in_words(_lines_30d(activity), "line")
    return f"{lines}, {level}" if level else lines


def _render_bar(percent: int, width: int = _BAR_MAX_WIDTH) -> str:
    """A bar *percent* full."""
    filled = max(0, min(width, int(percent / _PERCENT * width)))
    return _BAR_CHAR_FILLED * filled + _BAR_CHAR_EMPTY * (width - filled)


class ActivityWidget(Static):
    """Displays per-node git activity as bars.

    Each node shows its name, a bar of its changed lines in 30 days relative to
    the busiest node shown, and its lines and level in words.
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
        self._pending = False

    def render(self) -> Text:
        """Render per-domain activity bars as Rich Text."""
        text = Text()
        text.append("Activity", style="bold underline")

        if self._pending:
            text.append("\n  Analyzing git history\u2026", style="dim")
            return text

        if not self._activities:
            text.append("\n  No activity data")
            return text

        busiest = max((_lines_30d(a) for a in self._activities.values()), default=0)
        for ref_id in sorted(self._activities):
            activity = self._activities[ref_id]
            percent = _lines_30d(activity) * _PERCENT // busiest if busiest else 0
            style = _style_of(_level_of(activity))

            text.append("\n  ")
            text.append(f"{ref_id:<20s}", style="bold")
            text.append(" ")
            text.append(_render_bar(percent), style=style)
            text.append(f" {_describe(activity)}", style="dim")

        return text

    def refresh_data(self, activities: dict[str, Any]) -> None:
        """Update the activities data and re-render."""
        self._activities = dict(activities)
        self._pending = False
        self.refresh()

    def set_pending(self) -> None:
        """Show a placeholder while git history is analyzed in the background."""
        self._pending = True
        self.refresh()
