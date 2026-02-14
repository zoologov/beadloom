# Beadloom Architecture

Beadloom is a tool for managing codebase context, synchronizing documentation with code, and providing intelligent context to AI agents.

## System Design

The system is organized into five DDD domain packages and top-level services:

**Domains:**
1. **Context Oracle** (`context_oracle/`) — BFS graph traversal, context bundle assembly, code indexing, caching, FTS5 search
2. **Doc Sync** (`doc_sync/`) — doc↔code synchronization tracking and stale detection
3. **Graph** (`graph/`) — YAML graph loader, diff, rule engine, import resolver, architecture linter
4. **Onboarding** (`onboarding/`) — project bootstrap, doc import, architecture-aware presets
5. **Infrastructure** (`infrastructure/`) — SQLite database layer, health metrics, reindex orchestrator, doctor, watcher

**Services:**
- **CLI** (`services/cli.py`) — Click-based CLI with 21 commands
- **MCP Server** (`services/mcp_server.py`) — stdio server with 10 tools for AI agents
- **TUI** (`tui/`) — interactive terminal dashboard (Textual)

## Specification

### Data Flow

```
YAML Graph Files (.beadloom/_graph/*.yml)
       ↓
   graph/loader.py    → SQLite (nodes, edges)
       ↓
   doc_sync/doc_indexer.py → SQLite (docs, chunks)
       ↓
   context_oracle/code_indexer.py → SQLite (code_symbols)
       ↓
   context_oracle/builder.py ← BFS traversal → context bundle (JSON)
       ↓
   services/cli.py / services/mcp_server.py → user / AI agent
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

- Code indexer supports `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs` (tree-sitter)
- Import analysis supports Python, TypeScript/JavaScript, Go, Rust
- Documentation root is configurable via `docs_dir` in `.beadloom/config.yml` (default: `docs/`)
- Source scan paths are configurable via `scan_paths` in `.beadloom/config.yml` (default: `src`, `lib`, `app`)
- Graph is read only from `.beadloom/_graph/*.yml`
- Maximum chunk size: 2000 characters
- Levenshtein suggestions: maximum 5, distance threshold = max(len/2, 3)
