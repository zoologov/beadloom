# Graph Reads

The application read facade over the infrastructure graph-index repository.

**Source:** `src/beadloom/application/graph_reads.py`

---

## Specification

### Purpose

Expose the graph-index reads the presentation layer needs **without leaking the
infrastructure import**. The `tui-no-direct-infra` architecture boundary forbids
`tui` from importing `beadloom.infrastructure`, so the TUI cannot call
`beadloom.infrastructure.repository` directly. This thin application-layer facade
re-exports the repository's typed rows and delegates each read, giving the TUI a
layer-correct seam (`service -> application -> infrastructure`) while keeping
behavior identical.

### Surface

`graph_reads` re-exports the repository's typed rows (`NodeRow`, `EdgeRow`,
`SymbolRow`) and the read functions the TUI uses:

- Nodes: `get_all_nodes`, `get_node`, `get_node_with_source`,
  `get_nodes_by_kind`, `get_source_paths`, `get_node_sources`.
- Edges: `get_all_edges`, `get_part_of_children`, `get_outgoing_edges`,
  `get_incoming_edges`, `count_edges_touching`.
- Docs: `get_doc_ref_ids`, `count_docs`, `count_docs_for_ref`,
  `get_docs_for_ref`.
- Sync: `get_stale_pairs_for_ref`.
- Symbols: `get_symbols_for_source`.
- Search fallback: `search_nodes_like`.

### Behavior

A pure pass-through: no orchestration and no business rules. Every function
forwards to the matching `beadloom.infrastructure.repository` call with the same
arguments and return type.

> Feature doc (BDL-059 S2 / #122). Surface verified against `graph_reads.py`.
