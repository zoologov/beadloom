# beadloom:service=tui
"""Node detail panel widget showing detailed info about a selected node."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from beadloom.tui.data_providers import GraphDataProvider

logger = logging.getLogger(__name__)

# Section separator
_SEPARATOR = "\u2500" * 40  # horizontal line

# Symbol kind -> display glyph mapping
_KIND_GLYPHS: dict[str, str] = {"function": "\u0192", "class": "C", "type": "T"}


def _render_node_detail(
    ref_id: str,
    graph_provider: GraphDataProvider | None,
) -> Text:
    """Render detailed node information as Rich Text.

    Displays ref_id, kind, summary, source path, edges, and doc status.
    """
    text = Text()
    text.append("Node Detail", style="bold underline")

    if graph_provider is None:
        text.append("\n  No data provider available")
        return text

    node = graph_provider.get_node_with_source(ref_id)
    if node is None:
        text.append(f"\n  Node '{ref_id}' not found")
        return text

    kind = str(node.get("kind") or "")
    summary = str(node.get("summary") or "")
    source = str(node.get("source") or "")

    # Basic info
    text.append("\n\n")
    text.append("  ref_id:  ", style="dim")
    text.append(ref_id, style="bold cyan")
    text.append("\n")
    text.append("  kind:    ", style="dim")
    text.append(kind, style="bold")
    text.append("\n")
    text.append("  summary: ", style="dim")
    text.append(summary if summary else "(none)", style="italic" if not summary else "")

    # Source path
    text.append("\n\n")
    text.append(f"  {_SEPARATOR}\n", style="dim")
    text.append("  Source\n", style="bold underline")
    if source:
        text.append(f"  {source}", style="green")
    else:
        text.append("  (no source path)", style="dim")

    # Connections (grouped summary of edges)
    text.append("\n\n")
    text.append(f"  {_SEPARATOR}\n", style="dim")
    text.append("  Connections\n", style="bold underline")

    edges = graph_provider.get_edges()
    outgoing = [e for e in edges if e["src"] == ref_id and e["dst"] != ref_id]
    incoming = [e for e in edges if e["dst"] == ref_id and e["src"] != ref_id]

    if not outgoing and not incoming:
        text.append("  (no connections)", style="dim")
    else:
        if outgoing:
            out_counts: dict[str, int] = {}
            for e in outgoing:
                edge_kind = e["kind"]
                out_counts[edge_kind] = out_counts.get(edge_kind, 0) + 1
            out_parts = ", ".join(f"{k}({v})" for k, v in out_counts.items())
            text.append(
                f"  \u2192 {len(outgoing)} outgoing: {out_parts}\n",
                style="yellow",
            )
        if incoming:
            in_counts: dict[str, int] = {}
            for e in incoming:
                edge_kind = e["kind"]
                in_counts[edge_kind] = in_counts.get(edge_kind, 0) + 1
            in_parts = ", ".join(f"{k}({v})" for k, v in in_counts.items())
            text.append(
                f"  \u2190 {len(incoming)} incoming: {in_parts}",
                style="cyan",
            )

    # Symbols (top-level functions/classes from code indexer)
    text.append("\n\n")
    text.append(f"  {_SEPARATOR}\n", style="dim")

    symbols = graph_provider.get_symbols(ref_id)
    if symbols:
        text.append(f"  Symbols ({len(symbols)})\n", style="bold underline")
        for sym in symbols:
            glyph = _KIND_GLYPHS.get(str(sym["kind"]), "?")
            name = str(sym["symbol_name"])
            line = str(sym["line_start"])
            text.append(f"  {glyph} {name:<24} :{line}\n", style="")
    else:
        text.append("  Symbols\n", style="bold underline")
        text.append("  (no symbols)", style="dim")

    # Doc status
    text.append("\n")
    text.append(f"  {_SEPARATOR}\n", style="dim")
    text.append("  Documentation\n", style="bold underline")

    doc_ref_ids = graph_provider.get_doc_ref_ids()
    if ref_id in doc_ref_ids:
        text.append("  \u25cf documented", style="green")
    else:
        text.append("  \u2716 missing", style="red")

    return text


class NodeDetailPanel(Static):
    """Scrollable panel showing detailed info about a selected node.

    Displays ref_id, kind, summary, source path, edges, and doc status.
    Uses GraphDataProvider for data.
    """

    DEFAULT_CSS = """
    NodeDetailPanel {
        width: 100%;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        graph_provider: GraphDataProvider | None = None,
        ref_id: str = "",
        widget_id: str | None = None,
    ) -> None:
        super().__init__(id=widget_id)
        self._graph_provider = graph_provider
        self._ref_id = ref_id

    def _build_text(self) -> Text:
        """Build the Rich Text for the current state."""
        if not self._ref_id:
            text = Text()
            text.append("Node Detail", style="bold underline")
            text.append("\n  Select a node to see details")
            return text

        return _render_node_detail(self._ref_id, self._graph_provider)

    def _push_content(self) -> None:
        """Push pre-built text into the widget via ``update()``.

        Safe to call before the widget is mounted.
        """
        with contextlib.suppress(Exception):  # NoActiveAppError, etc.
            self.update(self._build_text())

    def set_node(self, ref_id: str) -> None:
        """Update the displayed node and re-render.

        Parameters
        ----------
        ref_id:
            The ref_id of the node to display.
        """
        self._ref_id = ref_id
        self._push_content()

    def set_provider(self, graph_provider: GraphDataProvider) -> None:
        """Set the graph data provider."""
        self._graph_provider = graph_provider
