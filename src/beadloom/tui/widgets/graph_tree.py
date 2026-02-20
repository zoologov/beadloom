# beadloom:service=tui
"""Graph tree widget showing architecture hierarchy with doc status indicators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.message import Message
from textual.widgets import Tree

if TYPE_CHECKING:
    from textual.widgets._tree import TreeNode

    from beadloom.tui.data_providers import GraphDataProvider, SyncDataProvider

logger = logging.getLogger(__name__)

# Doc status indicators
_DOC_FRESH = "\u25cf"  # filled circle ●
_DOC_STALE = "\u25b2"  # triangle ▲
_DOC_MISSING = "\u2716"  # heavy X ✖

# Kind display ordering
_KIND_ORDER: dict[str, int] = {
    "service": 0,
    "domain": 1,
    "feature": 2,
    "other": 3,
}

# Label for empty graph
_EMPTY_LABEL = "No nodes found"

# Root label for the tree
_ROOT_LABEL = "Architecture"


class NodeSelected(Message):
    """Emitted when a node is selected in the graph tree."""

    def __init__(self, ref_id: str) -> None:
        self.ref_id = ref_id
        super().__init__()


def _doc_status_indicator(
    ref_id: str,
    *,
    doc_ref_ids: set[str],
    stale_ref_ids: set[str],
) -> tuple[str, str]:
    """Return (indicator_char, style) for a node's doc status.

    Returns:
        Tuple of (indicator character, Rich style string).
    """
    if ref_id not in doc_ref_ids:
        return _DOC_MISSING, "red"
    if ref_id in stale_ref_ids:
        return _DOC_STALE, "yellow"
    return _DOC_FRESH, "green"


def _build_node_label(
    ref_id: str,
    *,
    doc_ref_ids: set[str],
    stale_ref_ids: set[str],
    edge_counts: dict[str, int],
) -> str:
    """Build a display label for a tree node.

    Format: ``<indicator> <ref_id> [<N> edge(s)]`` (omitted when *N* == 0).
    """
    indicator, _style = _doc_status_indicator(
        ref_id, doc_ref_ids=doc_ref_ids, stale_ref_ids=stale_ref_ids
    )
    count = edge_counts.get(ref_id, 0)
    if count == 0:
        return f"{indicator} {ref_id}"
    if count == 1:
        return f"{indicator} {ref_id} [1 edge]"
    return f"{indicator} {ref_id} [{count} edges]"


class GraphTreeWidget(Tree[str]):
    """Interactive tree widget showing the architecture graph hierarchy.

    Nodes are organized by part_of edges: root -> domains -> features/services.
    Each node label includes a doc status indicator and edge count badge.

    Messages:
        NodeSelected: Emitted when the user selects a tree node.
    """

    DEFAULT_CSS: ClassVar[str] = """
    GraphTreeWidget {
        width: 100%;
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    def __init__(
        self,
        *,
        graph_provider: GraphDataProvider | None = None,
        sync_provider: SyncDataProvider | None = None,
        widget_id: str | None = None,
    ) -> None:
        super().__init__(_ROOT_LABEL, id=widget_id)
        self._graph_provider = graph_provider
        self._sync_provider = sync_provider

    def on_mount(self) -> None:
        """Build the tree when the widget is mounted."""
        self._build_tree()

    def _build_tree(self) -> None:
        """Build the tree structure from graph data providers."""
        root = self.root
        root.remove_children()

        if self._graph_provider is None:
            root.add_leaf(_EMPTY_LABEL)
            return

        nodes = self._graph_provider.get_nodes()
        if not nodes:
            root.add_leaf(_EMPTY_LABEL)
            return

        hierarchy = self._graph_provider.get_hierarchy()
        edge_counts = self._graph_provider.get_edge_counts()
        doc_ref_ids = self._graph_provider.get_doc_ref_ids()

        # Get stale ref_ids from sync provider
        stale_ref_ids: set[str] = set()
        if self._sync_provider is not None:
            try:
                sync_results = self._sync_provider.get_sync_results()
                stale_ref_ids = {
                    str(r.get("ref_id", ""))
                    for r in sync_results
                    if r.get("status") == "stale"
                }
            except Exception:
                logger.debug("Failed to load sync data for tree", exc_info=True)

        # Collect all ref_ids that are children of something
        all_children: set[str] = set()
        for children in hierarchy.values():
            all_children.update(children)

        # Identify root-level nodes (not children of anything)
        all_ref_ids = {n["ref_id"] for n in nodes}
        root_level = sorted(
            all_ref_ids - all_children,
            key=lambda r: (_KIND_ORDER.get(
                self._get_node_kind(r, nodes), 99
            ), r),
        )

        for ref_id in root_level:
            label = _build_node_label(
                ref_id,
                doc_ref_ids=doc_ref_ids,
                stale_ref_ids=stale_ref_ids,
                edge_counts=edge_counts,
            )
            if hierarchy.get(ref_id):
                branch = root.add(label, data=ref_id)
                self._add_child_nodes(
                    branch,
                    ref_id,
                    hierarchy=hierarchy,
                    doc_ref_ids=doc_ref_ids,
                    stale_ref_ids=stale_ref_ids,
                    edge_counts=edge_counts,
                    nodes=nodes,
                )
            else:
                root.add_leaf(label, data=ref_id)

        root.expand()

    def _add_child_nodes(
        self,
        parent_node: TreeNode[str],
        parent_ref_id: str,
        *,
        hierarchy: dict[str, list[str]],
        doc_ref_ids: set[str],
        stale_ref_ids: set[str],
        edge_counts: dict[str, int],
        nodes: list[dict[str, str]],
    ) -> None:
        """Recursively add children to a tree node."""
        children = hierarchy.get(parent_ref_id, [])
        sorted_children = sorted(
            children,
            key=lambda r: (_KIND_ORDER.get(
                self._get_node_kind(r, nodes), 99
            ), r),
        )
        for child_ref_id in sorted_children:
            label = _build_node_label(
                child_ref_id,
                doc_ref_ids=doc_ref_ids,
                stale_ref_ids=stale_ref_ids,
                edge_counts=edge_counts,
            )
            if hierarchy.get(child_ref_id):
                branch = parent_node.add(label, data=child_ref_id)
                self._add_child_nodes(
                    branch,
                    child_ref_id,
                    hierarchy=hierarchy,
                    doc_ref_ids=doc_ref_ids,
                    stale_ref_ids=stale_ref_ids,
                    edge_counts=edge_counts,
                    nodes=nodes,
                )
            else:
                parent_node.add_leaf(label, data=child_ref_id)

    @staticmethod
    def _get_node_kind(ref_id: str, nodes: list[dict[str, str]]) -> str:
        """Get the kind for a ref_id from the nodes list."""
        for node in nodes:
            if node["ref_id"] == ref_id:
                return node["kind"]
        return "other"

    def on_tree_node_selected(self, event: Tree.NodeSelected[str]) -> None:
        """Handle tree node selection — emit NodeSelected message."""
        node_data = event.node.data
        if node_data is not None and node_data != _EMPTY_LABEL:
            self.post_message(NodeSelected(node_data))

    def refresh_data(
        self,
        graph_provider: GraphDataProvider | None = None,
        sync_provider: SyncDataProvider | None = None,
    ) -> None:
        """Rebuild the tree from updated providers.

        If providers are given, they replace the current ones.
        Then the tree is rebuilt from scratch.
        """
        if graph_provider is not None:
            self._graph_provider = graph_provider
        if sync_provider is not None:
            self._sync_provider = sync_provider
        self._build_tree()
