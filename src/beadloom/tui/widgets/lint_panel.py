# beadloom:service=tui
"""Lint panel widget showing architecture violation counts and details."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

# Icons for severity levels
_ICON_ERROR = "\u2716"  # heavy X
_ICON_WARNING = "\u26a0"  # warning sign
_ICON_INFO = "\u2139"  # info


def _severity_icon(severity: str | None) -> str:
    """Return an icon for the given severity level."""
    if severity == "error":
        return _ICON_ERROR
    if severity == "warning":
        return _ICON_WARNING
    return _ICON_INFO


def _severity_style(severity: str | None) -> str:
    """Return a Rich style for the given severity level."""
    if severity == "error":
        return "bold red"
    if severity == "warning":
        return "bold yellow"
    return "dim"


class LintPanelWidget(Static):
    """Displays lint violation count and individual violations list.

    Shows error/warning counts with icons, plus a scrollable list
    of individual violations with rule name and affected nodes.
    """

    DEFAULT_CSS = """
    LintPanelWidget {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        violations: list[dict[str, str | None]] | None = None,
        widget_id: str | None = None,
    ) -> None:
        super().__init__(id=widget_id)
        self._violations: list[dict[str, str | None]] = violations or []

    def render(self) -> Text:
        """Render the lint panel as Rich Text."""
        text = Text()

        # Header with counts
        error_count = sum(
            1 for v in self._violations if v.get("severity") == "error"
        )
        warning_count = sum(
            1 for v in self._violations if v.get("severity") == "warning"
        )
        total = len(self._violations)

        text.append("Lint", style="bold underline")
        text.append(" ")

        if total == 0:
            text.append("No violations", style="green")
            return text

        # Summary line
        if error_count > 0:
            text.append(f"{_ICON_ERROR} {error_count} error(s)", style="bold red")
            text.append("  ")
        if warning_count > 0:
            text.append(
                f"{_ICON_WARNING} {warning_count} warning(s)", style="bold yellow"
            )
            text.append("  ")
        info_count = total - error_count - warning_count
        if info_count > 0:
            text.append(f"{_ICON_INFO} {info_count} info", style="dim")

        # Individual violations
        for violation in self._violations:
            text.append("\n")
            sev = violation.get("severity")
            icon = _severity_icon(sev)
            style = _severity_style(sev)
            rule_name = violation.get("rule_name", "unknown")
            from_ref = violation.get("from_ref_id", "?")
            desc = violation.get("description", "")

            text.append(f"  {icon} ", style=style)
            text.append(f"{rule_name}", style="bold")
            text.append(f" ({from_ref})", style="dim")
            if desc:
                text.append(f" - {desc}", style="italic")

        return text

    def refresh_data(self, violations: list[dict[str, str | None]]) -> None:
        """Update the violations list and re-render."""
        self._violations = list(violations)
        self.refresh()
