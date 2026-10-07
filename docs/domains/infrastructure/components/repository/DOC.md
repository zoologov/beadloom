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

Edge reads: `get_all_edges`, `get_part_of_children`, `get_part_of_containers`,
`get_outgoing_edges`, `get_incoming_edges`, `count_edges_touching`.
`get_part_of_containers(conn)` -> `dict[str, list[str]]` maps every node with a container to the
nodes it is `part_of`; git activity rolls a box's descendants up through it (BDL-078).

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
- `most_specific_owner(sources, file_path)` -> `str | None` — the same answer over
  `(ref_id, source)` pairs instead of the index: among the sources that cover the
  path, the longest covering prefix wins, and on a tie the FIRST pair wins. A
  blank source owns nothing. `get_owning_ref_id` delegates to it. It is pure so a
  path that is in no index — a test file's mirrored code path, a declared
  `tests:` prefix — is owned by the same rule (BDL-074 C1)
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
file-to-node attribution, the rule engine's `FileAttribution` and the test binding
(`context_oracle.test_binding`, through `most_specific_owner`) — so no two
surfaces can report different numbers, or different owners, for the same node.

**Test files by placement** — `count_test_files_by_placement(conn)` -> `dict[str, int]`:
how many indexed test files each placement (`mirror`, `override`, `unowned`, `unplaced`,
`other_kind`) holds, read from `test_files` (BDL-074 C2). It lives here because three readers
state the same counts and two of them may not import the reindex: `reindex`'s `Tests:` line
(through `test_index.placement_counts`), the `test_placements` key of a `ctx` bundle, and the
debt report's untested count. An index written before the test tables has no `test_files`
table; the `sqlite3.OperationalError` is caught and the answer is `{}`, because `ctx` opens
such an index without creating the schema.

**The placement vocabulary** — `PLACEMENT_MIRROR` (`"mirror"`, bound by the mirror of its
path under a mirrored kind folder or a build tool's test tree), `PLACEMENT_BESIDE_CODE`
(`"beside_code"`, BDL-074 G2: outside every test root, inside a node's source, bound to the
node covering it — `foo_test.go` beside `foo.go`), `PLACEMENT_OVERRIDE` (`"override"`, bound by
a node's `tests:` declaration), `PLACEMENT_UNOWNED` (`"unowned"`, under a mirrored kind folder
or a test tree and no node owns the code its path names), `PLACEMENT_UNPLACED` (`"unplaced"`,
reached by no mirror, no place beside the code and no declaration), `PLACEMENT_NAMED`
(`"named"`, BDL-078 `beadloom-76mk`: a flat Python test in a root, bound to the one node owning
the module its name names, when the layout declares `flat_tests`), `PLACEMENT_IMPORTED`
(`"imported"`, the same flat test bound to the one node its imports reach when no module is
named) and `PLACEMENT_OTHER_KIND` (`"other_kind"`, under a kind folder whose binding is not the
mirror).
`read_unbound_test_files(conn)` -> `list[tuple[str, str]]` lists every indexed test file bound
to no node, by path, with its placement, leaving out the `other_kind` files a kind folder
places; `init` prints them (BDL-078). `[]` for an index without the test tables.
They are the values `test_files.placement` holds. Defined here since BDL-074 C3, because two
peer domains share them: `context_oracle.test_binding` assigns a placement and re-exports the
names under its old import path, and `graph.rules.test_binding` judges it.

**The kind vocabulary, and the count by kind** (BDL-074 F1) — `KIND_ACCEPTANCE`
(`"acceptance"`, an acceptance step file whose scenarios bind by their `@node:` tag) and
`KIND_SELF_CHECK` (`"self_check"`, a test of the project's own files and configuration, bound
to no node by design) are the `test_files.kind` values an `other_kind` file carries.
`KIND_UNRECORDED` (`"unrecorded"`) is stated for an `other_kind` row that recorded no kind.
`label_test_kind(kind)` gives the words a count is stated in (`acceptance step`, `self-check`,
otherwise the kind as recorded). `count_other_kind_test_files(conn)` -> `dict[str, int]` reads
how many `other_kind` files each kind holds from `test_files`, `{}` for an index without the
table. They sit beside the placement vocabulary for the same reason: `test_binding` assigns a
kind, and the rule engine, the reindex `Tests:` line and `beadloom mutation --changed-since`
name it, so a count by kind is read from the index rather than inferred from a folder. The two
kinds bind to no node for different reasons, and a count that merged them would state neither.

**The recorded test layout** (BDL-074 G2) — `TEST_LAYOUT_KEY` (`"test_layout"`) is the `meta`
key the reindex records the test layout it read under. `RecordedTestLayout` is that record:
`kind_prefixes` (each kind's folders under every root that exists, `tests/unit/`),
`declared_kinds` (the kinds whose folder `.beadloom/config.yml` declares rather than
defaults), `beside_code`, `roots` (the roots in force that exist on disk, since
`beadloom-2mj3.17`), `frameworks` (the names of the pattern groups a file path is matched against),
`mirror_roots` (the build tools' test trees the project has, `src/test/java`; BDL-074 G2b) and
`patterns` (each group's patterns in the order they are matched, `beadloom-2mj3.15`; `()` in a
record written before it, which named the groups alone) and `absent_roots` (the roots in force
the project does not have, so a reader names the roots that exist and can say which were
looked for, `beadloom-2mj3.17`; `()` in an older record) and `flat_tests` (whether a flat
Python test binds by the module it names, then by its imports, BDL-078 `beadloom-76mk`; `false`
in an older record). `encode()` gives the JSON the `meta`
table holds, `patterns` as `[[name, [pattern, ...]], ...]` and `absent_roots` as a list, and a
changed record forces one test re-index. `read_test_layout(conn)` ->
`RecordedTestLayout | None` reads it back, `None` for an index written before G2 or a record
that does not parse, so a reader states that the layout is unknown rather than a default. It
sits beside the placement vocabulary for the same reason: `context_oracle.test_layout` writes
it and the rule engine states it, and neither may import the other. Its readers are the
builder's `test_unplaced` sentence and `test_recognition` clause, the debt report's population,
the `test_binding` rule's recognition clause and, since `beadloom-2mj3.15`,
`ChangePlan.test_layout` in `beadloom mutation --changed-since`.

**Test files with their binding** — `get_test_file_bindings(conn)`, added in BDL-074 D1 to
give `beadloom mutation --changed-since` every indexed test file as `(path, ref_id, placement)`,
was removed by `beadloom-2mj3.13`. Since BDL-074 G1
`application.mutation_scope.change.plan_change` reads the test files through
`graph.rules.suite_tables.read_test_files`, which carries the recorded kind its selection
needs, so the reader had no caller left.

Search fallback: `search_nodes_like` (the non-FTS5 LIKE path).

## Collaborators

Reads the tables created by the [`db`](../db/DOC.md) component. Wrapped, for the
presentation layer, by `application/graph_reads.py`.

> Component doc (BDL-059 S2 / #122). Public surface verified against `repository.py`.
