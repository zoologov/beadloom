# Repository (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/repository.py`

---

## Overview

Centralized, typed **read queries** over the graph-index SQLite tables. Before
this seam (BDL-059 S2, #122), the same row queries — most notably
`SELECT ref_id, kind, summary FROM nodes` (~16 copies) — were inlined across
services, domains, and the TUI. This component owns those reads in one place and
returns plain dataclasses instead of bare `sqlite3.Row` tuples, so every caller
shares the same typed results.

Each function takes an open `sqlite3.Connection` and performs a pure read, which
keeps the module in the lowest (infrastructure) layer, consumed downward by
domains / application / services. The presentation layer (`tui`) does not import
this module directly — the `tui-no-direct-infra` boundary forbids it — and
reaches these reads through the `graph-reads` application facade.

## Public surface

Typed rows:

- `NodeRow(ref_id, kind, summary, source=None)`
- `EdgeRow(src_ref_id, dst_ref_id, kind)`
- `SymbolRow(symbol_name, kind, line_start)`

Node reads: `get_all_nodes`, `get_node`, `get_node_with_source`,
`get_nodes_by_kind`, `get_source_paths`, `get_node_sources`.

Edge reads: `get_all_edges`, `get_part_of_children`, `get_outgoing_edges`,
`get_incoming_edges`, `count_edges_touching`.

Doc reads: `get_doc_ref_ids`, `count_docs`, `count_docs_for_ref`,
`get_docs_for_ref`.

Sync-state reads: `get_stale_pairs_for_ref`.

Code-symbol reads: `get_symbols_for_source` (LIKE prefix for directory sources).

Search fallback: `search_nodes_like` (the non-FTS5 LIKE path).

## Collaborators

Reads the tables created by the [`db`](../db/DOC.md) component. Wrapped, for the
presentation layer, by `application/graph_reads.py`.

> Component doc (BDL-059 S2 / #122). Public surface verified against `repository.py`.
