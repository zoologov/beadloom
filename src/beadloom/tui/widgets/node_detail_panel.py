# beadloom:service=tui
"""Node detail panel widget showing detailed info about a selected node."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from beadloom.tui.data_providers import GraphDataProvider

logger = logging.getLogger(__name__)

# Section separator
_SEPARATOR = "\u2500" * 40  # horizontal line


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

    # Edges
    text.append("\n\n")
    text.append(f"  {_SEPARATOR}\n", style="dim")
    text.append("  Edges\n", style="bold underline")

    edges = graph_provider.get_edges()
    outgoing = [e for e in edges if e["src"] == ref_id and e["dst"] != ref_id]
    incoming = [e for e in edges if e["dst"] == ref_id and e["src"] != ref_id]

    if not outgoing and not incoming:
        text.append("  (no edges)", style="dim")
    else:
        for edge in outgoing:
            text.append(f"  {ref_id} ", style="bold")
            text.append(f"--{edge['kind']}--> ", style="yellow")
            text.append(f"{edge['dst']}\n", style="cyan")
        for edge in incoming:
            text.append(f"  {edge['src']} ", style="cyan")
            text.append(f"--{edge['kind']}--> ", style="yellow")
            text.append(f"{ref_id}\n", style="bold")

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
        height: 100%;
        padding: 0 1;
        overflow-y: auto;
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

    def render(self) -> Text:
        """Render the node detail panel."""
        if not self._ref_id:
            text = Text()
            text.append("Node Detail", style="bold underline")
            text.append("\n  Select a node to see details")
            return text

        return _render_node_detail(self._ref_id, self._graph_provider)

    def set_node(self, ref_id: str) -> None:
        """Update the displayed node and re-render.

        Parameters
        ----------
        ref_id:
            The ref_id of the node to display.
        """
        self._ref_id = ref_id
        self.refresh()

    def set_provider(self, graph_provider: GraphDataProvider) -> None:
        """Set the graph data provider."""
        self._graph_provider = graph_provider
