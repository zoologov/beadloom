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
| `generate_skeletons(project_root)` | Create `docs/` tree from the graph on disk: architecture.md, domain READMEs, service pages, feature SPECs. Loads symbols from SQLite for Public API sections. Writes `docs:` field back to the graph file each node came from, via `_patch_docs_field()`. Takes the project root and nothing else since BDL-067 `.21`: it also accepted a node list, and `docs/architecture.md` is a document about the WHOLE graph, so a caller that passed one got a whole-tree document describing part of the tree. Three of four callers read the tree and one passed a list, which left `init --bootstrap` and the wizard leaving different documents on a project that already carried a graph file (BDL-UX #216, the review of BDL-067 `.20`, major 1). Removing the parameter closes it for callers written later as well; it is an API change for anyone importing `beadloom.onboarding.generate_skeletons`. |
| `generate_polish_data(project_root, ref_id?)` | Return structured JSON (nodes with symbols/deps/existing docs, Mermaid diagram, AI enrichment prompt). Enriches with SQLite dependency edges via `_enrich_edges_from_sqlite()`. |
| `format_polish_text(data)` | Render polish data as multi-line human-readable text with node details, symbols, deps, doc status. |

## Generated File Types

| Path | Node Kind | Content |
|------|-----------|---------|
| `docs/architecture.md` | — | Domains table, services table, Mermaid dependency map |

Since BDL-061 S4b the SHAPE of every document above comes from a composed
template in [`doc-templates`](../doc-templates/SPEC.md), not from a string
literal here. The render functions compute the VALUES and call `render_doc`; the
extraction is behaviour-preserving and pinned by byte-identity tests. The
practical consequence for an adopter: `.beadloom/flow/docs/<kind>.md` appends
their own sections to a generated document, and those sections then become
required sections that `sync-check` reports when one goes missing.
| `docs/domains/{name}/README.md` | domain | Summary, source, public API, dependencies, features list |
| `docs/services/{name}.md` | service | Summary, source, public API, dependencies |
| `docs/domains/{parent}/features/{name}/SPEC.md` | feature | Summary, source, public API, dependencies, parent domain |

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

## Skeleton Enrichment

When SQLite database exists (post-reindex), skeletons include:

- **Public API** table — public symbols (classes, functions) extracted from `code_symbols`, filtered by source path prefix, private symbols (`_`-prefixed) excluded
- **Dependencies** section — `depends_on` and `used_by` edges (excluding structural `part_of`)

## Internal Functions

| Function | Role |
|----------|------|
| `_load_graph_from_yaml` | Load nodes/edges from `.beadloom/_graph/*.yml`, through `graph_files.each_graph_file`. `.21` made this the reader `init --bootstrap` reaches, and it had no unreadable-YAML guard: the adopter got a `yaml.parser.ParserError` traceback (the review of `.23`, major 3) |
| `_find_root_node` | Identify root service (no `part_of` as src) |
| `_doc_path_for_node` | Resolve doc path from `docs:` field or convention |
| `_load_symbols_by_source` | Best-effort SQLite symbol loading |
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
