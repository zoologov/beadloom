# beadloom:service=tui
"""Dependency path widget showing upstream/downstream dependency trees."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.widgets import Static

if TYPE_CHECKING:
    from beadloom.tui.data_providers import WhyDataProvider

logger = logging.getLogger(__name__)

# Tree rendering characters
_BRANCH = "\u251c\u2500\u2500 "  # |-
_LAST_BRANCH = "\u2514\u2500\u2500 "  # L-
_PIPE = "\u2502   "  # |
_SPACE = "    "

# Direction labels
_LABEL_UPSTREAM = "Upstream Dependencies"
_LABEL_DOWNSTREAM = "Downstream Dependents"


def _render_tree_node(
    text: Text,
    node: Any,
    prefix: str = "",
    is_last: bool = True,
    depth: int = 0,
) -> None:
    """Recursively render a TreeNode into Rich Text.

    Parameters
    ----------
    text:
        The Rich Text object to append to.
    node:
        A TreeNode from the why module (has ref_id, kind, edge_kind, children).
    prefix:
        The indentation prefix string.
    is_last:
        Whether this is the last sibling at this level.
    depth:
        Current depth level (0 = root).
    """
    connector = _LAST_BRANCH if is_last else _BRANCH

    if depth == 0:
        # Root node: no connector
        text.append("  ")
    else:
        text.append(f"  {prefix}{connector}", style="dim")

    text.append(node.ref_id, style="bold cyan")
    text.append(f" ({node.kind})", style="dim")
    if hasattr(node, "edge_kind") and node.edge_kind:
        text.append(f" [{node.edge_kind}]", style="yellow")
    text.append("\n")

    children = node.children if hasattr(node, "children") else ()
    for i, child in enumerate(children):
        child_is_last = i == len(children) - 1
        child_prefix = "" if depth == 0 else prefix + (_SPACE if is_last else _PIPE)

        _render_tree_node(
            text,
            child,
            prefix=child_prefix,
            is_last=child_is_last,
            depth=depth + 1,
        )


def _render_dependency_tree(
    ref_id: str,
    why_provider: WhyDataProvider | None,
    *,
    direction: str = "downstream",
) -> Text:
    """Render a dependency tree as Rich Text.

    Parameters
    ----------
    ref_id:
        The ref_id to analyze.
    why_provider:
        The WhyDataProvider instance.
    direction:
        Either "upstream" or "downstream".
    """
    text = Text()
    label = _LABEL_UPSTREAM if direction == "upstream" else _LABEL_DOWNSTREAM
    text.append(label, style="bold underline")

    if why_provider is None:
        text.append("\n  No data provider available")
        return text

    reverse = direction == "upstream"
    result = why_provider.analyze(ref_id, reverse=reverse)

    if result is None:
        text.append(f"\n  Node '{ref_id}' not found")
        return text

    tree_nodes = result.upstream if direction == "upstream" else result.downstream

    if not tree_nodes:
        text.append("\n  No dependencies found")
        return text

    text.append("\n")
    for i, node in enumerate(tree_nodes):
        _render_tree_node(
            text,
            node,
            is_last=(i == len(tree_nodes) - 1),
            depth=0,
        )

    # Impact summary
    impact = result.impact
    text.append("\n  ")
    text.append("\u2500" * 30, style="dim")
    text.append("\n  Direct: ", style="dim")
    text.append(str(impact.downstream_direct), style="bold")
    text.append("  Transitive: ", style="dim")
    text.append(str(impact.downstream_transitive), style="bold")
    text.append("  Stale docs: ", style="dim")
    stale_style = "red bold" if impact.stale_count > 0 else "green"
    text.append(str(impact.stale_count), style=stale_style)

    return text


class DependencyPathWidget(Static):
    """Widget showing upstream/downstream dependency trees.

    Uses WhyDataProvider for impact analysis.
    The right panel of the Explorer screen can switch between upstream,
    downstream, and context preview modes.
    """

    DEFAULT_CSS = """
    DependencyPathWidget {
        width: 100%;
        height: 100%;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def __init__(
        self,
        *,
        why_provider: WhyDataProvider | None = None,
        ref_id: str = "",
        direction: str = "downstream",
        widget_id: str | None = None,
    ) -> None:
        super().__init__(id=widget_id)
        self._why_provider = why_provider
        self._ref_id = ref_id
        self._direction = direction

    def render(self) -> Text:
        """Render the dependency path widget."""
        if not self._ref_id:
            text = Text()
            label = _LABEL_UPSTREAM if self._direction == "upstream" else _LABEL_DOWNSTREAM
            text.append(label, style="bold underline")
            text.append("\n  Select a node to see dependencies")
            return text

        return _render_dependency_tree(
            self._ref_id, self._why_provider, direction=self._direction
        )

    def show_upstream(self, ref_id: str) -> None:
        """Show upstream dependencies for the given ref_id."""
        self._ref_id = ref_id
        self._direction = "upstream"
        self.refresh()

    def show_downstream(self, ref_id: str) -> None:
        """Show downstream dependents for the given ref_id."""
        self._ref_id = ref_id
        self._direction = "downstream"
        self.refresh()

    def set_provider(self, why_provider: WhyDataProvider) -> None:
        """Set the why data provider."""
        self._why_provider = why_provider
