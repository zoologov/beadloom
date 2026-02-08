# Beadloom Architecture

Beadloom is a tool for managing codebase context, synchronizing documentation with code, and providing intelligent context to AI agents.

## System Design

The system consists of three domains:

1. **Context Oracle** — the core that builds context bundles via BFS traversal of the knowledge graph
2. **Doc Sync Engine** — tracks desynchronization between documentation and code
3. **MCP Server** — a stdio server providing 5 tools for AI agents

## Specification

### Data Flow

```
YAML Graph Files (.beadloom/_graph/*.yml)
       ↓
   graph_loader.py → SQLite (nodes, edges)
       ↓
   doc_indexer.py  → SQLite (docs, chunks)
       ↓
   code_indexer.py → SQLite (code_symbols)
       ↓
   context_builder.py ← BFS traversal → context bundle (JSON)
       ↓
   CLI / MCP Server → user / AI agent
```

### SQLite Schema

The database is stored in `.beadloom/beadloom.db` and uses WAL mode for concurrent access.

Tables:
- `nodes` — graph nodes (ref_id, kind, summary, source, extra)
- `edges` — graph edges (src_ref_id, dst_ref_id, kind, extra)
- `docs` — document index (path, kind, ref_id, hash)
- `chunks` — document chunks (heading, section, content)
- `code_symbols` — code symbols (file_path, symbol_name, kind, line_start, line_end, annotations)
- `sync_state` — doc↔code synchronization state
- `meta` — index metadata (key-value)

### BFS Algorithm

Context Oracle uses BFS with edge prioritization:

| Priority | Edge type | Description |
|-----------|-----------|----------|
| 1 | part_of | Component is part of |
| 2 | touches_entity | Touches entity |
| 3 | uses / implements | Uses / implements |
| 4 | depends_on | Depends on |
| 5 | touches_code | Touches code |

BFS traverses the graph bidirectionally (outgoing + incoming edges), sorting neighbors by priority. Parameters: `depth` (default 2), `max_nodes` (node limit, default 20).

## Invariants

- All ref_id values are unique within the graph
- Edges reference only existing nodes
- A document is linked to at most one node via ref_id
- On reindex all tables are recreated (drop + create)
- WAL mode is enabled on every connection open
- Foreign keys are enabled per-connection

## Constraints

- Only Python (.py) is supported for code_indexer (tree-sitter)
- Documentation is scanned only from `docs/` (hardcoded path)
- Graph is read only from `.beadloom/_graph/*.yml`
- Maximum chunk size: 2000 characters
- Levenshtein suggestions: maximum 5, distance threshold = max(len/2, 3)
