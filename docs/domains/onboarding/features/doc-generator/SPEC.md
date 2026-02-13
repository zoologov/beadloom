# doc-generator

> Doc skeleton generation + AI polish data from knowledge graph

## Source

`src/beadloom/onboarding/doc_generator.py`

## Overview

Generates documentation skeletons from the knowledge graph, and produces
structured data for AI agents to enrich those skeletons.

## Public API

| Function | Description |
|----------|-------------|
| `generate_skeletons(project_root, nodes?, edges?)` | Create `docs/` tree from graph: architecture.md, domain READMEs, service pages, feature SPECs |
| `generate_polish_data(project_root, ref_id?)` | Return structured JSON (nodes with symbols/deps, mermaid diagram, AI prompt) |

## Generated File Types

| Path | Node Kind | Content |
|------|-----------|---------|
| `docs/architecture.md` | — | Domains table, services table, Mermaid dependency map |
| `docs/domains/{name}/README.md` | domain | Summary, source, dependencies, features list |
| `docs/services/{name}.md` | service | Summary, source, dependencies |
| `docs/features/{name}/SPEC.md` | feature | Summary, source, parent domain |

## Design Decisions

- **Never overwrites** existing files (idempotent, user edits preserved)
- **`<!-- enrich with: beadloom docs polish -->`** markers in all generated files
- **Standalone mode**: loads graph from YAML when called without explicit nodes/edges
- **Polish data** includes code symbols from SQLite when available (post-reindex)

## Parent

onboarding
