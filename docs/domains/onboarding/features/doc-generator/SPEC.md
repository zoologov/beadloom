# doc-generator

> Doc skeleton generation + AI polish data from knowledge graph

## Source

`src/beadloom/onboarding/doc_generator.py`

## Overview

Generates documentation skeletons from the knowledge graph, and produces
structured data for AI agents to enrich those skeletons. Part of the
`beadloom init --bootstrap` pipeline and available as standalone CLI commands
(`beadloom docs generate`, `beadloom docs polish`) and MCP tool (`generate_docs`).

## Public API

| Function | Description |
|----------|-------------|
| `generate_skeletons(project_root, nodes?, edges?)` | Create `docs/` tree from graph: architecture.md, domain READMEs, service pages, feature SPECs. Loads symbols from SQLite for Public API sections. |
| `generate_polish_data(project_root, ref_id?)` | Return structured JSON (nodes with symbols/deps/existing docs, Mermaid diagram, AI enrichment prompt) |

## Generated File Types

| Path | Node Kind | Content |
|------|-----------|---------|
| `docs/architecture.md` | — | Domains table, services table, Mermaid dependency map |
| `docs/domains/{name}/README.md` | domain | Summary, source, public API, dependencies, features list |
| `docs/services/{name}.md` | service | Summary, source, public API, dependencies |
| `docs/domains/{parent}/features/{name}/SPEC.md` | feature | Summary, source, public API, dependencies, parent domain |

## Path Resolution

Doc paths are determined by `_doc_path_for_node()` with two-level priority:

1. **`docs:` field** — if the graph node has an explicit `docs:` list, the first entry is used
2. **Convention fallback** — `domains/{ref_id}/README.md`, `services/{ref_id}.md`, `domains/{parent}/features/{ref_id}/SPEC.md`

Root service node (no `part_of` edge as src) is skipped — covered by `architecture.md`.

## Skeleton Enrichment

When SQLite database exists (post-reindex), skeletons include:

- **Public API** table — public symbols (classes, functions) extracted from `code_symbols`, filtered by source path prefix, private symbols (`_`-prefixed) excluded
- **Dependencies** section — `depends_on` and `used_by` edges (excluding structural `part_of`)

## Internal Functions

| Function | Role |
|----------|------|
| `_load_graph_from_yaml` | Load nodes/edges from `.beadloom/_graph/*.yml` |
| `_find_root_node` | Identify root service (no `part_of` as src) |
| `_doc_path_for_node` | Resolve doc path from `docs:` field or convention |
| `_load_symbols_by_source` | Best-effort SQLite symbol loading |
| `_render_symbols_section` | Markdown table from public symbols |
| `_render_architecture` | Domains + services tables + Mermaid |
| `_render_domain_readme` | Domain page with features list |
| `_render_service` | Service page with dependencies |
| `_render_feature_spec` | Feature page with parent link |
| `_generate_mermaid` | `graph LR` from `depends_on`/`part_of` edges |
| `_write_if_missing` | Idempotent file writer |

## Design Decisions

- **Never overwrites** existing files (`_write_if_missing` — idempotent, user edits preserved)
- **`<!-- enrich with: beadloom docs polish -->`** markers in all generated files
- **Standalone mode**: loads graph from YAML when called without explicit nodes/edges
- **Polish data** includes code symbols from SQLite when available (post-reindex)
- **Best-effort symbols**: no error if DB or `code_symbols` table is missing
- **`part_of` filtering**: `_edges_for()` excludes structural edges from dependency lists

## Testing

- `tests/test_doc_generator.py` — unit tests for skeletons, mermaid, polish data (19 tests)
- `tests/test_cli_docs.py` — CLI `docs generate` / `docs polish` (8 tests)
- `tests/test_integration_onboarding.py` — end-to-end pipeline with idempotency (13 tests)

## Parent

onboarding
