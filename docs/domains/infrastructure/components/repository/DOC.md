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

Sync-state reads: `get_stale_pairs_for_ref`, `count_stale_pairs`,
`stale_node_refs`, and the `StaleCount` value they return.

**How many stale things there are, and the word for them** — one computation,
because there is more than one population and they were all called "stale docs".
A `sync_state` row is a PAIR: one document AND one code file, so three code files
of one package are three stale pairs over one README. Nineteen surfaces read this
table and reported a number, under four different populations, and three beads
fixed the label one surface at a time -- `beadloom-h7b3` changed one place and
found three, `beadloom-yn6i` changed those and found four more (BDL-069
`beadloom-rqma.5`).

- `StaleCount(count, noun)` — built through `StaleCount.of_pairs(n)`, never
  directly, so the number and the word for it cannot be separated at a call site.
  `.phrase` is the one spelling of `N stale pair(s)`; `.noun` is the word alone,
  for a column label or a heading.
- `count_stale_pairs(conn, ref_ids=None)` -> `StaleCount` — rows with
  `status = 'stale'`. `None` means every node; an EMPTY collection counts nothing
  rather than everything, because a caller asking about no node (`beadloom why`
  on a node with no dependents) is not asking about all of them.
- `stale_node_refs(conn)` -> `list[str]` — the NODES that own at least one stale
  pair. A different population, and therefore a different name: one node with
  three stale pairs is one entry here and three there.

Callers: the Gate summary, the site dashboard's alert, docs card and per-node
recommendations, `beadloom ctx`, `beadloom why` and the TUI dependency path,
`sync-check`'s own report, the TUI status bar and sync notification, and the MCP
`get_status` tool. `onboarding/scanner/prime.py` is the one surface that keeps
its own copy of the sentence: `onboarding-no-direct-infra` forbids the import and
exempts `infrastructure/db` only, and that entry's own exit condition is
`prime_context()` moving to this seam whole (BDL-UX #150).

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
