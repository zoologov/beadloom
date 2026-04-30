<!-- beadloom:badge-start -->
> ⚪ **untracked** — not tracked by any doc-code pair
> 
> coverage 100% (`beadloom`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Beadloom Architecture

Beadloom turns Architecture as Code into Architectural Intelligence — structured, queryable knowledge about your system that humans and AI agents consume in <20ms.

## System Design

The system is organized into five DDD domain packages and three service layers:

**Domains:**
1. **Context Oracle** (`context_oracle/`) — BFS graph traversal, context bundle assembly, code indexing, two-tier caching, FTS5 search
2. **Doc Sync** (`doc_sync/`) — doc↔code synchronization tracking, stale detection, symbol-level hashing, docs audit
3. **Graph** (`graph/`) — YAML graph loader, diff engine, rule engine, import resolver (9 languages), architecture linter
4. **Onboarding** (`onboarding/`) — project bootstrap, doc generation/polishing, architecture-aware presets, Agent Prime, AGENTS.md generation
5. **Infrastructure** (`infrastructure/`) — SQLite database layer, incremental reindex, health snapshots with trends, doctor, file watcher

**Services:**
- **CLI** (`services/cli.py`) — Click-based CLI with 29 commands
- **MCP Server** (`services/mcp_server.py`) — stdio server with 14 tools for AI agents
- **TUI** (`tui/`) — interactive terminal dashboard (Textual)

---

## Specification

### Data Flow

```
YAML Graph Files (.beadloom/_graph/*.yml)
       ↓
   graph/loader.py       → SQLite (nodes, edges, rules)
       ↓
   graph/import_resolver.py → SQLite (code_imports)
       ↓
   doc_sync/doc_indexer.py → SQLite (docs, chunks, search_index)
       ↓
   context_oracle/code_indexer.py → SQLite (code_symbols)
       ↓
   infrastructure/reindex.py → SQLite (file_index, health_snapshots)
       ↓
   context_oracle/builder.py ← BFS traversal → context bundle (JSON)
       ↓                                       ↕ L1 memory / L2 SQLite cache
   services/cli.py / services/mcp_server.py → user / AI agent
```

### SQLite Schema

The database is stored in `.beadloom/beadloom.db` and uses WAL mode for concurrent access.

**Core tables (7):**

| Table | Key columns | Description |
|-------|-------------|-------------|
| `nodes` | ref_id (PK), kind, summary, source, extra | Graph nodes (domain, feature, service, entity, adr) |
| `edges` | src_ref_id, dst_ref_id, kind (composite PK), extra | Graph edges (part_of, depends_on, uses, implements, touches_entity, touches_code) |
| `docs` | id (PK), path (UNIQUE), kind, ref_id (FK→nodes), hash, metadata | Document index |
| `chunks` | id (PK), doc_id (FK→docs), chunk_index, heading, section, content, node_ref_id | Document chunks (max 2000 chars) |
| `code_symbols` | id (PK), file_path, symbol_name, kind, line_start, line_end, annotations, file_hash | Code symbols (function, class, type, route, component) |
| `sync_state` | id (PK), doc_path, code_path, ref_id (FK→nodes), code_hash_at_sync, doc_hash_at_sync, synced_at, status, symbols_hash | Doc↔code sync state (ok, stale) |
| `meta` | key (PK), value | Index metadata (key-value) |

**Infrastructure tables (7):**

| Table | Key columns | Description |
|-------|-------------|-------------|
| `health_snapshots` | id (PK), taken_at, nodes_count, edges_count, docs_count, coverage_pct, stale_count, isolated_count, extra | Trend tracking across reindexes |
| `file_index` | path (PK), hash (SHA-256), kind (graph/doc/code), indexed_at | Incremental reindex support |
| `bundle_cache` | cache_key (PK), bundle_json, etag, graph_mtime, docs_mtime, created_at | L2 persistent context cache |
| `search_index` | ref_id, kind, summary, content | FTS5 virtual table for full-text search |
| `code_imports` | id (PK), file_path, line_number, import_path, resolved_ref_id, file_hash | Import relationships between files |
| `rules` | id (PK), name (UNIQUE), description, rule_type (deny/require/forbid_edge/layer/cycle_detection/import_boundary/cardinality), rule_json, enabled | Architecture rules from rules.yml |
| `graph_snapshots` | id (PK), label, created_at, nodes_json, edges_json | Point-in-time architecture graph captures for drift detection |

### BFS Algorithm

Context Oracle uses BFS with edge prioritization:

| Priority | Edge type | Description |
|----------|-----------|-------------|
| 1 | part_of | Component is part of |
| 2 | touches_entity | Touches entity |
| 3 | uses / implements | Uses / implements |
| 4 | depends_on | Depends on |
| 5 | touches_code | Touches code |

BFS traverses the graph bidirectionally (outgoing + incoming edges), sorting neighbors by priority.

Default parameters:
- `depth` = 2 — graph traversal depth
- `max_nodes` = 20 — node limit per bundle
- `max_chunks` = 10 — text chunk limit per bundle

### Rules Engine

Architecture rules are defined in `.beadloom/_graph/rules.yml` (schema version 3) and enforce boundaries between graph nodes.

**Rule types (v1.8.0):**

| Type | Semantics | Example |
|------|-----------|---------|
| `deny` | Forbid imports between matched nodes | `domain:* → service:*` — domains must not depend on services |
| `require` | Require edges from matched nodes to targets | Every `service:*` must have a `part_of` edge to a `domain:*` |
| `forbid_edge` | Forbid specific edge patterns between tagged node groups | Nodes tagged `ui-layer` must not have `uses` edges to `native-layer` |
| `layer` | Enforce layered architecture direction | Top-down: presentation → domain → infrastructure |
| `cycle_detection` | Detect circular dependencies in the graph | No cycles on `uses`/`depends_on` edges |
| `import_boundary` | Control file-level import boundaries | Files in `components/map/**` must not import from `components/calendar/**` |
| `cardinality` | Enforce complexity limits per node | Max 500 symbols, max 50 files per domain |

**Evaluation:**
- Deny rules are checked against the `code_imports` table: resolved import ref_ids are matched against rule patterns
- Require rules are checked against the `edges` table: nodes matching `from` pattern must have specified edge kind to nodes matching `to` pattern
- Node matchers support an optional `exclude` field (list of ref_ids) to exempt specific nodes from rule matching
- `unless_edge` exemptions allow otherwise-forbidden imports when a specific edge kind exists between the nodes
- ForbidEdge rules check edge patterns between nodes matching tag selectors
- Layer rules verify dependency direction across ordered architectural layers
- Cycle detection uses BFS/DFS to find circular dependency paths
- Import boundary rules query the `code_imports` table for forbidden cross-boundary imports
- Cardinality rules count symbols/files per node and check against limits

**Output formats:**
- **Rich** — human-readable with Unicode indicators (✓, ✗, ▲, ▼)
- **JSON** — structured violations array + summary
- **Porcelain** — machine-readable, one TAB-separated line per violation

**CLI:** `beadloom lint [--strict] [--format rich|json|porcelain] [--no-reindex]`

The `--strict` flag exits with code 1 on `error`-severity violations (for CI/CD). Rules support `error` and `warn` severity levels.

### Node Tags

Nodes can be assigned tags for use in rule matching:

```yaml
# In services.yml
nodes:
  - ref_id: my-feature
    kind: feature
    tags: [ui-layer, presentation]
```

Tags are arbitrary strings. Rules reference them via `{ tag: <tag-name> }` selectors in `forbid_edge` and `layer` rules.

### Cache Architecture

Context bundles use a two-tier cache to achieve <20ms response times:

**L1 — In-memory (ContextCache):**
- Key: `(ref_id, depth, max_nodes, max_chunks)`
- Invalidation: mtime comparison against `.beadloom/_graph/` and docs directories
- Cleared on reindex

**L2 — SQLite (SqliteCache):**
- Table: `bundle_cache`
- Key: `"<ref_id>:<depth>:<max_nodes>:<max_chunks>"`
- Survives MCP server restarts
- Invalidation: mtime-based, same as L1

**ETag validation:**
- Format: `"sha256:<first-16-hex-chars>"` of sorted bundle JSON
- Returned on cache hit with `cached: true` and `unchanged_since` timestamp
- Clients skip re-fetching if ETag is unchanged

### Incremental Reindex

The `file_index` table tracks SHA-256 hashes of all indexed files (graph YAML, docs, source code).

**Process:**
1. Scan relevant files across graph, docs, and source directories
2. Compute SHA-256 hash per file
3. Compare with stored `file_index.hash`
4. Only re-parse files with changed hashes; skip unchanged
5. Update `file_index` with new hash and timestamp
6. Return `ReindexResult` with `nothing_changed` flag

When nothing changed, the CLI displays current DB counts instead of "0 indexed".

### Health Snapshots

Each reindex captures a health snapshot:

| Metric | Description |
|--------|-------------|
| `nodes_count` | Total graph nodes |
| `edges_count` | Total graph edges |
| `docs_count` | Total indexed documents |
| `coverage_pct` | % of nodes with linked docs |
| `stale_count` | Stale sync_state records |
| `isolated_count` | Nodes with zero edges |

**Trends:** compared against the previous snapshot, displayed as `▲ +8%`, `▼ +2`, etc. Arrows are inverted for "bad increase" metrics (stale, isolated). Snapshots persist across reindexes.

### Architecture Snapshots

`beadloom snapshot` manages point-in-time captures of the architecture graph for historical comparison.

**Commands:**
- `beadloom snapshot save [--name NAME]` — save current graph state
- `beadloom snapshot list` — list saved snapshots
- `beadloom snapshot compare [SNAP_ID]` — compare current graph with a snapshot

Snapshots are stored in SQLite and enable architecture drift detection across releases.

### Agent Prime

`beadloom prime` outputs a compact project context (target: ≤2000 tokens) for AI agent session initialization.

**Sections:**
1. Project metadata (name, version)
2. Architecture summary (node counts by kind, symbol count)
3. Health metrics (stale docs, lint violations, last reindex)
4. Architecture rules (from rules.yml)
5. Domain list (all domain nodes with summaries)
6. Stale docs (doc/code path pairs)
7. Lint violations (evaluated without reindex)
8. Key CLI commands (reference table)
9. Agent instructions (workflow guidance)

**Output formats:** Markdown (default), JSON.

**Graceful degradation:** works without DB (static-only mode with warning).

---

## Invariants

- All `ref_id` values are unique within the graph
- Edges reference only existing nodes (FK with ON DELETE CASCADE)
- A document is linked to at most one node via `ref_id`
- On full reindex all tables except `health_snapshots` are recreated (drop + create)
- WAL mode is enabled on every connection open
- Foreign keys are enabled per-connection

## Constraints

- **Code indexer** supports `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs` (tree-sitter)
- **Import analysis** supports 9 languages: Python, TypeScript, JavaScript, Go, Rust, Kotlin, Java, Swift, Objective-C, C/C++ (16 file extensions total)
- Documentation root is configurable via `docs_dir` in `.beadloom/config.yml` (default: `docs/`)
- Source scan paths are configurable via `scan_paths` in `.beadloom/config.yml` (default: `src`, `lib`, `app`)
- Graph is read only from `.beadloom/_graph/*.yml`
- Rules are read from `.beadloom/_graph/rules.yml`
- Rules support 7 types: deny, require, forbid_edge, layer, cycle_detection, import_boundary, cardinality
- Maximum chunk size: 2000 characters
- Levenshtein suggestions: maximum 5, distance threshold = max(len/2, 3)

## Configuration

`.beadloom/config.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `languages` | all supported | File extensions to parse (e.g. `[".py", ".ts"]`) |
| `scan_paths` | `["src", "lib", "app"]` | Source directories to scan |
| `docs_dir` | `docs/` | Documentation root directory |
| `sync.hook_mode` | `warn` | Pre-commit hook mode: `warn` or `block` |
