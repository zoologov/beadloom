# doc-generator

> Doc skeleton generation + AI polish data from architecture graph

## Source

`src/beadloom/onboarding/doc_generator.py`

## Overview

Generates documentation skeletons from the architecture graph, and produces
structured data for AI agents to enrich those skeletons. Part of the
`beadloom init --bootstrap` pipeline and available as standalone CLI commands
(`beadloom docs generate`, `beadloom docs polish`) and MCP tool (`generate_docs`).

## Public API

| Function | Description |
|----------|-------------|
| `generate_skeletons(project_root)` | Create `docs/` tree from the graph on disk: architecture.md, domain READMEs, service pages, feature SPECs. Parses the code under each node it writes a document for, off the disk, for the Public API table; it reads no index. Writes `docs:` field back to the graph file each node came from, via `_patch_docs_field()`. Takes the project root and nothing else since BDL-067 `.21`: it also accepted a node list, and `docs/architecture.md` is a document about the WHOLE graph, so a caller that passed one got a whole-tree document describing part of the tree. Three of four callers read the tree and one passed a list, which left `init --bootstrap` and the wizard leaving different documents on a project that already carried a graph file (BDL-UX #216, the review of BDL-067 `.20`, major 1). Removing the parameter closes it for callers written later as well; it is an API change for anyone importing `beadloom.onboarding.generate_skeletons`. |
| `generate_polish_data(project_root, ref_id?)` | Return structured JSON (nodes with symbols/deps/existing docs, Mermaid diagram, AI enrichment prompt). Enriches with SQLite dependency edges via `_enrich_edges_from_sqlite()`. |
| `format_polish_text(data)` | Render polish data as multi-line human-readable text with node details, symbols, deps, doc status. |

## Generated File Types

| Path | Node Kind | Content |
|------|-----------|---------|
| `docs/architecture.md` | — | Domains table, services table, Mermaid dependency map |
| `docs/domains/{name}/README.md` | domain | Summary, source, modules, public API, dependencies, features list |
| `docs/services/{name}.md` | service | Summary, source, modules, public API, dependencies |
| `docs/domains/{parent}/features/{name}/SPEC.md` | feature | Summary, source, modules, public API, dependencies, parent domain |

Since BDL-061 S4b the SHAPE of every document above comes from a composed
template in [`doc-templates`](../doc-templates/SPEC.md), not from a string
literal here. The render functions compute the VALUES and call `render_doc`; the
extraction is behaviour-preserving and pinned by byte-identity tests. The
practical consequence for an adopter: `.beadloom/flow/docs/<kind>.md` appends
their own sections to a generated document, and those sections then become
required sections that `sync-check` reports when one goes missing.

## Path Resolution

Doc paths are determined by `_doc_path_for_node()` with two-level priority:

1. **`docs:` field** — if the graph node has an explicit `docs:` list, the first entry is used
2. **Convention fallback** — `domains/{ref_id}/README.md`, `services/{ref_id}.md`, `domains/{parent}/features/{ref_id}/SPEC.md`

Root service node (no `part_of` edge as src) is skipped — covered by `architecture.md`.

## docs: Writeback

After creating skeleton files, `generate_skeletons()` writes the `docs:` field back to the graph file each node came from, via `_patch_docs_field(graph_dir, docs_map)`:

- Collects `{ref_id: relative_doc_path}` for all **newly created** files only
- Reads each graph file through `graph_files.each_graph_file(graph_dir)`, which is where the skip policy lives since BDL-067 `.24`: a file that is not a graph file's by name, or will not read, or will not parse, or does not parse to a mapping, is skipped. This body carried no guard until then, so a hand-edited graph file raised out of a step whose only purpose is annotation
- Adds `docs: [path]` to nodes that don't already have the field
- Writes each `.yml` atomically via `write_yaml_atomic(yml, data, sort_keys=False, allow_unicode=True)` (the [atomic-io](../../../infrastructure/components/atomic-io/DOC.md) primitive — temp file + `fsync` + `os.replace`), so an interrupted writeback never leaves a truncated `services.yml`. `sort_keys=False` preserves key ordering; output bytes are identical to the prior direct `yaml.dump`.

This ensures `_build_doc_ref_map()` in reindex links docs to nodes correctly, so `doctor` reports real coverage.

## SQLite Edge Enrichment

`generate_polish_data()` enriches node data with real dependency edges via `_enrich_edges_from_sqlite()`:

- Opens `.beadloom/beadloom.db` (read-only, best-effort)
- Queries `edges` table for `depends_on` edges (forward and reverse)
- Merges into node data, deduplicating with YAML edges
- Graceful fallback when DB or `edges` table is missing

## Polish Symbols

`generate_polish_data()` gives each node the `code_symbols` rows of every file under
its source, through `_symbols_for_node`, and the instructions tell the agent to
describe the node from them.

- **Matched by path component.** A file is under the source when its path is the
  source, or continues it past a `/`. Until BDL-069 `beadloom-6rgr` the match was a
  string prefix. Measured on a foreign repository after `init --yes` and `reindex`:
  `docs polish --ref-id ledger` named `export, record, replay`, taking
  `src/ledger_archive/` and `src/ledger_tools.py`, where the package holds `record`.
  The equality half is what a single-file source needs, because no path starts with
  `src/ledger/core.py/`.
- **Read from the index, not the disk.** Every other field of the payload is read
  from the index too — drift, `depends_on` edges, routes, activity and tests — so a
  walk would describe a different tree from the rest of the payload after an edit
  that was not re-indexed. A walk is also not bounded by the scan paths. Measured on
  this repository over 104 nodes: the directory walk took 12.45 s and gave the site
  node 68 382 symbols from `node_modules`, while the index took 0.006 s.
- **The routes are not yet matched this way.** They come from `nodes.extra`, which
  the reindex fills by string prefix, so a node still receives a prefix-sharing
  sibling's routes. That is filed as `beadloom-rqma.4`, outside this node.

## Skeleton Enrichment

Every node document whose `source` is a directory carries a **Modules** list: the
file name of each Python file directly inside that directory, sorted, as inline
code. `_modules_for_node` reads the list off the disk and `_render_modules_section`
renders it. It exists because `missing_modules` requires a document paired with a
source directory to name each module in it, and until BDL-069 S1 the skeleton named
the directory and nothing in it. Measured on the published 4.0.0 wheel against a
repository holding `src/ledger/` and `src/billing/`: `init --yes --mode bootstrap`
exited 0 and the next `beadloom ci` exited 1 on `sync-check FAIL: 4 stale doc(s)`
(BDL-UX #282).

- **Read off the disk, not the index.** `init --yes` writes the skeletons before its
  reindex, so on a virgin project there is no index at that point.
- **The population is the rule's.** It lists Python files at the top level only,
  because a subdirectory is a node of its own. `__init__.py` is named as well, so
  the list does not depend on which boilerplate the rule exempts. The scanner's
  wider code-extension set is not used: `agent-prime` owns it and already depends
  on this node, so importing it is a cycle `no-dependency-cycles` refuses.
  `tests/test_the_init_skeleton_names_its_modules.py` runs `check_doc_coverage`
  over a generated skeleton, which is what holds the two populations together.
- **Named, not attested.** Writing a skeleton records no pair and creates no index.
  The pair's first baseline is taken by the reindex that follows, like any other,
  so the green comes from what the document says: take a module's name back out
  and the gate goes red.
- **Never a required section.** The list reaches the template through the
  `modules_section` placeholder, so a document written before this change is
  not found to lack it and no adopter's Gate changes verdict on upgrade.
- **A pair is still a document and a code file.** Two files in a package give two
  pairs over one README, and the list changes nothing about how pairs are counted.

Every node document whose source holds a public symbol also carries a **Public API**
table: the public classes and functions of every file under the node's source, sorted
by name, with `_`-prefixed names excluded. `_symbols_on_disk` parses them with
`code_indexer.extract_symbols`, the function the reindex calls per file, and
`_render_symbols_section` renders them.

- **Read off the disk, not the index.** The table came from `code_symbols` until
  BDL-069 `beadloom-8lmj`, and the index is the one input whose presence depends on
  the caller. Measured on a wheel built from the tree, against a repository holding
  `src/ledger/` and `src/billing/`: `init --yes` and `init --bootstrap` write their
  skeletons before their reindex and wrote no table, the wizard re-indexes first and
  wrote it, and `docs generate` on a clone — which has no index, because `init`
  lists it in `.gitignore` — wrote none either. `diff -r` between the `--yes` and
  wizard `docs/` trees differed in exactly the two tables, and `beadloom ci` was rc 0
  on both, because no rule reads the table. The order `init` runs its steps in was
  not changed: skeletons still precede the reindex that loads their `docs:` patch.
- **The population is the index's, with one stated difference.** `extract_symbols`
  returns nothing for an extension it has no grammar for, before it reads the file,
  so the same files yield rows. A directory source is walked, which takes the files
  the index reader `_symbols_for_node` takes by path component. The node's source is
  read wherever it is, where the index holds only the configured scan paths.
  `tests/test_the_init_skeleton_carries_its_public_api.py` builds an index with the
  real reindex and compares the two readers over one tree, and
  `tests/test_polish_symbols_match_the_source_by_path_component.py` compares them
  over a tree holding prefix-sharing siblings, for every shape of source.
- **Parsed only for a document that will be written, and each file once.** A node
  whose document already exists is skipped before rendering, and one run memoises
  its parses by path, so a feature nested in a domain costs no second parse.
  Measured on this repository: parsing every node source unconditionally walked
  17 294 files in about 13 s, 16 433 of them under the site node's `node_modules`.
- **Best effort.** A file that does not decode costs the table its rows, logged at
  debug level, and not the skeleton its existence.

Every node document also carries a **Dependencies** section: the `depends_on` and
`used_by` edges of the graph files, excluding structural `part_of`.

## Internal Functions

| Function | Role |
|----------|------|
| `_load_graph_from_yaml` | Load nodes/edges from `.beadloom/_graph/*.yml`, through `graph_files.each_graph_file`. `.21` made this the reader `init --bootstrap` reaches, and it had no unreadable-YAML guard: the adopter got a `yaml.parser.ParserError` traceback (the review of `.23`, major 3) |
| `_find_root_node` | Identify root service (no `part_of` as src) |
| `_doc_path_for_node` | Resolve doc path from `docs:` field or convention |
| `_load_symbols_by_source` | Best-effort SQLite symbol loading, for `generate_polish_data`, which runs after a reindex |
| `_symbols_for_node` | The index rows of every file under a node's source, matched by path component, for the polish payload |
| `_symbols_on_disk` | The symbols of every file under a node's source, parsed off the disk and memoised per run, for the skeleton's Public API table |
| `_parse_symbols` | One file's symbols through `code_indexer.extract_symbols`, or none when the file does not decode |
| `_modules_for_node` | File names of the Python files directly inside a directory `source`, read off the disk, sorted |
| `_render_modules_section` | The `## Modules` list, or an empty string when there is nothing to name |
| `_render_symbols_section` | Markdown table from public symbols |
| `_render_architecture` | Values for the `overview` template: domains + services tables + Mermaid |
| `_node_values` | The placeholder values every node document shares |
| `beadloom_readme_values` | Every placeholder `beadloom-readme` needs, in one place — public because `render_doc` raises on a missing value, so every caller must agree on the whole set (BDL-062 `.15`) |
| `_beadloom_description` | Beadloom's own one-line description, read from the package docstring rather than written into the scaffold template (BDL-UX #211) |
| `_mcp_tool_list` | Every MCP tool name as inline code, from the catalogue — the template had named 8 of 18 |
| `_render_domain_readme` | Domain page with features list |
| `_render_service` | Service page with dependencies |
| `_render_feature_spec` | Feature page with parent link |
| `_resolved_config` | The flow config to compose with when the caller named no project root |
| `_generate_mermaid` | `graph LR` from `depends_on`/`part_of` edges |
| `_write_if_missing` | Idempotent file writer |
| `_patch_docs_field` | Write `docs:` back to graph YAML for newly created files, through `graph_files.each_graph_file` |
| `_enrich_edges_from_sqlite` | Read `depends_on` edges from SQLite into node data |
| `format_polish_text` | Render polish data as human-readable multi-line text |

## Design Decisions

- **Never overwrites** existing files (`_write_if_missing` — idempotent, user edits preserved)
- **`<!-- enrich with: beadloom docs polish -->`** markers in all generated files
- **Standalone mode**: loads graph from YAML when called without explicit nodes/edges
- **Polish data** includes code symbols from SQLite when available (post-reindex)
- **Best-effort symbols with debug logging**: SQLite errors (e.g., missing `code_symbols` or `nodes` tables) degrade gracefully without raising, but are logged at debug level for observability (UX#127)
- **`part_of` filtering**: `_edges_for()` excludes structural edges from dependency lists
- **docs: writeback**: only for newly created files, never overwrites existing `docs:` values

## Testing

- `tests/test_doc_generator.py` — unit tests for skeletons, mermaid, polish data, docs: writeback, SQLite edges, text format (37 tests)
- `tests/test_cli_docs.py` — CLI `docs generate` / `docs polish` (8 tests)
- `tests/test_integration_onboarding.py` — end-to-end pipeline with idempotency (13 tests)

## Parent

onboarding
