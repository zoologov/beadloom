"""Application read facade over the infrastructure the presentation layer reads.

# beadloom:domain=application
# beadloom:feature=graph-reads

One responsibility: **expose the infrastructure reads the presentation layer
needs without leaking the infrastructure import**. The ``tui-no-direct-infra``
boundary forbids ``tui`` from importing :mod:`beadloom.infrastructure`, so the
TUI cannot call :mod:`beadloom.infrastructure.repository` directly. This thin
application-layer facade re-exports the repository's typed rows and delegates
each read, giving the TUI a layer-correct seam (service -> application ->
infrastructure) while keeping behavior identical.

Two read sources sit behind it, both of them things the dashboard displays: the
graph index (:mod:`~beadloom.infrastructure.repository`) and per-node git
activity (:mod:`~beadloom.infrastructure.git_activity`, added in BDL-UX #150,
when repairing the dead ``to:`` glob made the boundary rule fire on the TUI's
direct ``analyze_git_activity`` import).

It is a pure pass-through (no orchestration, no business rules); every function
forwards to the matching infrastructure call.
"""

from __future__ import annotations

from beadloom.infrastructure.git_activity import GitActivity, analyze_git_activity
from beadloom.infrastructure.repository import (
    EdgeRow,
    NodeRow,
    SymbolRow,
    count_docs,
    count_docs_for_ref,
    count_edges_touching,
    get_all_edges,
    get_all_nodes,
    get_doc_ref_ids,
    get_docs_for_ref,
    get_incoming_edges,
    get_node,
    get_node_sources,
    get_node_with_source,
    get_nodes_by_kind,
    get_outgoing_edges,
    get_part_of_children,
    get_source_paths,
    get_stale_pairs_for_ref,
    get_symbols_for_source,
    search_nodes_like,
)

__all__ = [
    "EdgeRow",
    "GitActivity",
    "NodeRow",
    "SymbolRow",
    "analyze_git_activity",
    "count_docs",
    "count_docs_for_ref",
    "count_edges_touching",
    "get_all_edges",
    "get_all_nodes",
    "get_doc_ref_ids",
    "get_docs_for_ref",
    "get_incoming_edges",
    "get_node",
    "get_node_sources",
    "get_node_with_source",
    "get_nodes_by_kind",
    "get_outgoing_edges",
    "get_part_of_children",
    "get_source_paths",
    "get_stale_pairs_for_ref",
    "get_symbols_for_source",
    "search_nodes_like",
]
