# beadloom:service=tui
"""Debt gauge widget showing architecture debt score with severity coloring."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

# Severity thresholds and labels
_THRESHOLD_LOW = 20
_THRESHOLD_MEDIUM = 50


def _severity_label(score: float) -> str:
    """Return severity label based on debt score."""
    if score <= _THRESHOLD_LOW:
        return "low"
    if score <= _THRESHOLD_MEDIUM:
        return "medium"
    return "high"


def _severity_style(score: float) -> str:
    """Return Rich style string for the debt score severity."""
    if score <= _THRESHOLD_LOW:
        return "green"
    if score <= _THRESHOLD_MEDIUM:
        return "yellow"
    return "red"


class DebtGaugeWidget(Static):
    """Displays architecture debt score with color-coded severity.

    Colors:
    - Green (0-20): low debt
    - Yellow (21-50): medium debt
    - Red (51+): high debt
    """

    DEFAULT_CSS = """
    DebtGaugeWidget {
        width: auto;
        height: 1;
        content-align: right middle;
    }
    """

    def __init__(self, *, score: float = 0.0, widget_id: str | None = None) -> None:
        super().__init__(id=widget_id)
        self._score = score

    def render(self) -> Text:
        """Render the debt gauge as a Rich Text object."""
        style = _severity_style(self._score)
        label = _severity_label(self._score)
        arrow = "\u25b2" if self._score > _THRESHOLD_LOW else "\u25bc"
        text = Text()
        text.append("Debt: ", style="bold")
        text.append(f"{self._score:.0f} {arrow} {label}", style=f"bold {style}")
        return text

    def refresh_data(self, score: float) -> None:
        """Update the displayed debt score and re-render."""
        self._score = score
        self.refresh()
