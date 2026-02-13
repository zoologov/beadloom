# Context Oracle

Context Oracle is the core of beadloom, responsible for building context bundles via BFS traversal of the knowledge graph.

## Specification

### Purpose

When an AI agent or developer requests context for a `ref_id`, Context Oracle:

1. Validates the requested ref_id(s) (with Levenshtein + prefix suggestions on error)
2. Performs BFS traversal of the graph from focus nodes
3. Collects text chunks of documentation for subgraph nodes
4. Collects code symbols via `# beadloom:key=value` annotations
5. Checks sync_state for stale doc↔code pairs
6. Returns a compact JSON bundle

### BFS Algorithm

BFS traverses the graph bidirectionally (outgoing + incoming edges), sorting neighbors by edge priority:

| Priority | Edge type | Description |
|-----------|-----------|----------|
| 1 | part_of | Component is part of |
| 2 | touches_entity | Touches entity |
| 3 | uses / implements | Uses / implements |
| 4 | depends_on | Depends on |
| 5 | touches_code | Touches code |

Parameters: `depth` (default 2), `max_nodes` (node limit, default 20).

### Context Bundle Format

```json
{
  "version": 1,
  "focus": { "ref_id": "...", "kind": "...", "summary": "..." },
  "graph": { "nodes": [...], "edges": [...] },
  "text_chunks": [
    { "doc_path": "...", "section": "spec", "heading": "...", "content": "..." }
  ],
  "code_symbols": [
    { "file_path": "...", "symbol_name": "...", "kind": "function", "line_start": 10, "line_end": 80 }
  ],
  "sync_status": { "stale_docs": [...], "last_reindex": "..." },
  "warning": null
}
```

### Chunk Priority

Chunks are sorted by section:

| Priority | Section | Description |
|-----------|--------|----------|
| 1 | spec | Specification |
| 2 | invariants | Invariants |
| 3 | constraints | Constraints |
| 4 | api | API |
| 5 | tests | Tests |
| 6 | other | Other |

### suggest_ref_id

When a non-existent ref_id is requested, the system suggests similar ones using two strategies:

1. **Prefix matching** (case-insensitive) — `mcp` will find `mcp-server`
2. **Levenshtein distance** — `PROJ-125` will find `PROJ-123`, `PROJ-124`

Maximum 5 suggestions, prefix matches take priority.

## Invariants

- BFS does not cycle (visited set)
- Each node in the subgraph appears exactly once
- Edges are recorded even for already visited nodes (graph completeness)
- Focus nodes are always included in the subgraph (if they exist)
- `max_nodes` is a hard limit, BFS stops when reached

## Constraints

- Maximum chunks in a bundle: 10 (default)
- Maximum nodes in a subgraph: 20 (default)
- BFS depth: 2 (default)
- Levenshtein suggestions: maximum 5
