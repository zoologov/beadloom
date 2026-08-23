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

Code-symbol reads: `get_symbols_for_source` (raw LIKE prefix for directory
sources — kept for callers that genuinely want the whole subtree).

**Node file ownership** — the single answer every counter, sizer and linker
shares: **a file belongs to exactly one node, the most specific one whose
`source` covers it.** A `source` is a path prefix and graphs nest, so raw prefix
attribution counts a child's files against its parent too — which is why carving
a subpackage into its own node used to leave the parent's size unchanged, the
very remedy a size limit exists to prompt (BDL-UX #144). A source that names a
package's `__init__.py` covers its PACKAGE, not just that file: the facade only
re-exports, so treating it as a lone file reported an empty node for a package
full of code (BDL-UX #157).

- `get_owning_ref_id(conn, file_path)` -> `str | None` — the node that owns a file
- `owns_file(conn, ref_id, file_path)` -> `bool`
- `count_symbols_owned_by_node(conn, ref_id)` -> `int` — what `max_symbols` measures
- `count_files_owned_by_node(conn, ref_id)` -> `int` — what `max_files` measures
- `get_owned_symbols(conn, ref_id)` -> `list[SymbolRow]` — what a node page lists
- `get_owned_code_files(conn, ref_id)` -> `list[tuple[str, str]]` — `(path, hash)`
  for the indexed CODE files a node owns; what pairs a doc with code when no
  symbol carries the node's annotation
- `covering_prefix(source)` / `source_covers(source, file_path)` — the ownership
  rule itself, public since BDL-061.50 because the linter's file attribution now
  applies the same rule and the two must not each keep a copy

`get_owned_code_files` reads **`file_index`**, not `code_symbols` (BDL-061.50):
keyed on symbols it could not see a module holding no top-level `def`/`class` —
a pure re-export facade — so such a module was reachable through neither the
annotation path nor this fallback, and `sync-check` reported its node as having
"no indexed code" while the index held the file. A file with no symbol is still
a file whose content can change under a doc.

Consumers: the `max_symbols` / `max_files` cardinality rules, the architecture
view's symbol badge, node-page symbol listings, `import_resolver`'s
file-to-node attribution and the rule engine's `FileAttribution` — so no two
surfaces can report different numbers, or different owners, for the same node.

Search fallback: `search_nodes_like` (the non-FTS5 LIKE path).

## Collaborators

Reads the tables created by the [`db`](../db/DOC.md) component. Wrapped, for the
presentation layer, by `application/graph_reads.py`.

> Component doc (BDL-059 S2 / #122). Public surface verified against `repository.py`.
