# beadloom:service=tui
"""Search overlay — modal screen with FTS5 search and result navigation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

if TYPE_CHECKING:
    import sqlite3

    from textual.app import ComposeResult

logger = logging.getLogger(__name__)


def _search_nodes(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> list[dict[str, str]]:
    """Search nodes using FTS5 if available, falling back to SQL LIKE.

    Parameters
    ----------
    conn:
        Read-only SQLite connection.
    query:
        Search query string.
    limit:
        Maximum number of results.

    Returns
    -------
    list[dict[str, str]]:
        List of dicts with ref_id, kind, summary keys.
    """
    from beadloom.context_oracle.search import has_fts5, search_fts5

    if has_fts5(conn):
        results = search_fts5(conn, query, limit=limit)
        return [
            {
                "ref_id": r["ref_id"],
                "kind": r["kind"],
                "snippet": r.get("snippet") or r.get("summary", ""),
            }
            for r in results
        ]

    # Fallback to SQL LIKE on nodes table
    like_pattern = f"%{query}%"
    rows = conn.execute(
        "SELECT ref_id, kind, summary FROM nodes "
        "WHERE ref_id LIKE ? OR summary LIKE ? "
        "ORDER BY ref_id LIMIT ?",
        (like_pattern, like_pattern, limit),
    ).fetchall()
    return [
        {
            "ref_id": str(row["ref_id"]),
            "kind": str(row["kind"]),
            "snippet": str(row["summary"] or ""),
        }
        for row in rows
    ]


def _format_results(results: list[dict[str, str]]) -> str:
    """Format search results as a text block for display."""
    if not results:
        return "  No results found."

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        ref_id = r["ref_id"]
        kind = r["kind"]
        snippet = r.get("snippet", "")
        # Truncate snippet to 60 chars
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        lines.append(f"  {i:>2}. [{kind}] {ref_id}")
        if snippet:
            lines.append(f"      {snippet}")
    return "\n".join(lines)


class SearchOverlay(ModalScreen[str | None]):
    """Modal overlay for FTS5 search across architecture nodes.

    Activated by pressing ``/`` globally.

    - Type a query in the input field and press Enter to search.
    - Results are shown below the input.
    - Press Enter again on the results to navigate to the first result.
    - Press Esc to dismiss without navigating.
    """

    DEFAULT_CSS = """
    SearchOverlay {
        align: center middle;
    }

    SearchOverlay #search-container {
        width: 70;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    SearchOverlay #search-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    SearchOverlay #search-input {
        width: 100%;
        margin-bottom: 1;
    }

    SearchOverlay #search-results {
        width: 100%;
        min-height: 3;
    }

    SearchOverlay #search-hint {
        text-align: center;
        color: $text-muted;
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Close", key_display="Esc"),
    ]

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        super().__init__()
        self._conn = conn
        self._results: list[dict[str, str]] = []

    def compose(self) -> ComposeResult:
        """Compose the search overlay layout."""
        with Vertical(id="search-container"):
            yield Label("Search", id="search-title")
            yield Input(placeholder="Type query and press Enter...", id="search-input")
            yield Static("", id="search-results")
            yield Label("Enter: search/navigate  Esc: close", id="search-hint")

    def on_mount(self) -> None:
        """Focus the input field when the overlay mounts."""
        try:
            inp = self.query_one("#search-input", Input)
            inp.focus()
        except Exception:
            logger.debug("Failed to focus search input", exc_info=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the search input."""
        query = event.value.strip()
        if not query:
            return

        # If we already have results and user presses Enter again,
        # navigate to the first result
        if self._results and query == self._last_query:
            first = self._results[0]
            self.dismiss(first["ref_id"])
            return

        self._last_query = query
        self._run_search(query)

    _last_query: str = ""

    def _run_search(self, query: str) -> None:
        """Execute search and update results display."""
        if self._conn is None:
            self._show_results_text("  No database connection.")
            return

        try:
            self._results = _search_nodes(self._conn, query)
        except Exception:
            logger.debug("Search failed", exc_info=True)
            self._results = []

        text = _format_results(self._results)
        self._show_results_text(text)

    def _show_results_text(self, text: str) -> None:
        """Update the results display widget."""
        try:
            results_widget = self.query_one("#search-results", Static)
            results_widget.update(text)
        except Exception:
            logger.debug("Failed to update search results", exc_info=True)

    def action_cancel(self) -> None:
        """Dismiss the search overlay without navigating."""
        self.dismiss(None)
