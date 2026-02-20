# beadloom:service=tui
"""Help overlay — modal screen showing all keyboard bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Keybinding definitions organized by context
_GLOBAL_BINDINGS: list[tuple[str, str]] = [
    ("1", "Switch to Dashboard"),
    ("2", "Switch to Explorer"),
    ("3", "Switch to Doc Status"),
    ("Tab", "Cycle panel focus"),
    ("q", "Quit"),
    ("?", "Help overlay (this screen)"),
    ("/", "Search overlay (FTS5)"),
    ("r", "Trigger reindex"),
    ("l", "Run lint check"),
    ("s", "Run sync-check"),
    ("S", "Save snapshot"),
]

_EXPLORER_BINDINGS: list[tuple[str, str]] = [
    ("d", "Downstream dependents"),
    ("u", "Upstream dependencies"),
    ("c", "Context preview"),
    ("o", "Open in $EDITOR"),
    ("Esc", "Back to previous screen"),
]

_DOC_STATUS_BINDINGS: list[tuple[str, str]] = [
    ("g", "Generate doc skeleton"),
    ("p", "Polish doc data"),
    ("Esc", "Back to previous screen"),
]

_DASHBOARD_BINDINGS: list[tuple[str, str]] = [
    ("Enter", "Expand/collapse or open detail"),
    ("e", "Open node in Explorer"),
]


def _format_section(title: str, bindings: list[tuple[str, str]]) -> str:
    """Format a section of keybindings as a text block."""
    lines: list[str] = [f"  {title}", "  " + "-" * len(title)]
    for key, desc in bindings:
        lines.append(f"  {key:<8} {desc}")
    lines.append("")
    return "\n".join(lines)


def build_help_text() -> str:
    """Build the full help text with all keybinding sections."""
    sections: list[str] = [
        "",
        "  Beadloom TUI — Keyboard Reference",
        "  " + "=" * 35,
        "",
        _format_section("Global", _GLOBAL_BINDINGS),
        _format_section("Dashboard", _DASHBOARD_BINDINGS),
        _format_section("Explorer", _EXPLORER_BINDINGS),
        _format_section("Doc Status", _DOC_STATUS_BINDINGS),
        "  Press Esc to close this help screen.",
        "",
    ]
    return "\n".join(sections)


class HelpOverlay(ModalScreen[None]):
    """Modal overlay showing all keyboard bindings.

    Activated by pressing ``?`` globally.  Press ``Esc`` to dismiss.
    """

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }

    HelpOverlay #help-container {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    HelpOverlay #help-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    HelpOverlay #help-content {
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "close_help", "Close", key_display="Esc"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help overlay layout."""
        with Vertical(id="help-container"):
            yield Label("Help", id="help-title")
            yield Static(build_help_text(), id="help-content")

    def action_close_help(self) -> None:
        """Dismiss the help overlay."""
        self.dismiss()
