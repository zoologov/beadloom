# RFC-0005: Phase 4 — Performance & Agent-Native Evolution

> **Status:** Accepted
> **Date:** 2026-02-11
> **Phase:** 4 (v0.6.0)
> **Depends on:** BDL-004 (v0.5.0 — team adoption complete)

---

## 1. Summary

Phase 4 completes the Beadloom v0 feature set with three pillars:

1. **Performance** — incremental reindex, L1 cache integration, bundle caching in SQLite
2. **Semantic search** — sqlite-vec + FTS5 for fuzzy queries beyond exact `ref_id` matching
3. **Agent-native write tools** — MCP tools that let agents update summaries, mark docs as synced, and manage nodes — replacing the deprecated LLM API integration entirely

### Design Principle

> **Beadloom = data infrastructure. Agent = intelligence.**

Beadloom does not call LLM APIs. The agent (Claude Code, Cursor, Codex, etc.) already IS the LLM. Beadloom provides the data layer; the agent provides the intelligence. This means:
- No `llm:` config section, no API keys, no token costs from Beadloom
- MCP write tools expose mutations; the agent decides what to write
- `sync-update --auto` is removed — the agent reads stale docs via MCP and updates them directly

---

## 2. Deliverables

| # | Item | Priority | Effort | Depends on |
|---|------|----------|--------|------------|
| 4.1 | L1 cache integration in MCP server | P0 | S | — |
| 4.2 | Incremental reindex | P0 | L | — |
| 4.3 | Auto-reindex in MCP server | P1 | S | 4.2 |
| 4.4 | Bundle caching in SQLite | P1 | M | 4.1 |
| 4.5 | MCP write tools (agent-native) | P1 | M | — |
| 4.6 | Semantic search (sqlite-vec + FTS5) | P2 | L | 4.2 |
| 4.7 | Remove LLM API deprecation | P0 | S | 4.5 |
| 4.8 | AGENTS.md cleanup & update | P1 | S | 4.5, 4.7 |

**Version:** 0.6.0
**Schema:** SCHEMA_VERSION remains "1" (all changes are additive tables)

---

## 3. Technical Design

### 3.1 L1 Cache Integration in MCP (4.1)

**Status:** `cache.py` (98 lines) exists with `ContextCache` class but is NOT used anywhere.

**Changes:**

1. Instantiate `ContextCache` in `create_server()` as server-level state
2. In `handle_get_context()`:
   - Compute `graph_mtime` from `_graph/*.yml` files
   - Compute `docs_mtime` from `docs/` files
   - Check cache → if hit, return short `{"cached": true, "etag": "..."}` response
   - If miss → build context, store in cache, return full bundle
3. In `handle_get_graph()`: same pattern with separate cache key space
4. Invalidate cache on `reindex` (check `meta.last_reindex_at`)

**Response format (cache hit):**

```json
{
  "cached": true,
  "etag": "sha256:abc123...",
  "unchanged_since": "2026-02-11T10:30:00Z",
  "hint": "Context unchanged since last request. Use previous bundle."
}
```

**Token savings:** ~3x reduction on repeated `get_context` calls within one session.

**Files changed:**
- `mcp_server.py` — integrate `ContextCache`, add mtime helpers
- `cache.py` — minor: add `etag` computation, typed return for cache hit

---

### 3.2 Incremental Reindex (4.2)

**Current state:** `reindex()` drops ALL tables (`_TABLES_TO_DROP`) and rebuilds from scratch.

**New approach:** Track file state in a new `file_index` table and only re-process changed files.

**New table:**

```sql
CREATE TABLE IF NOT EXISTS file_index (
    path       TEXT PRIMARY KEY,   -- relative to project root
    hash       TEXT NOT NULL,      -- SHA-256 of file content
    kind       TEXT NOT NULL CHECK(kind IN ('graph','doc','code')),
    indexed_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

**Algorithm:**

```
1. Scan all relevant files (graph YAML, docs, code)
2. For each file, compute current SHA-256
3. Compare with stored hash in file_index:
   - UNCHANGED: skip
   - CHANGED: re-process, update file_index
   - NEW: process, insert into file_index
   - DELETED: remove related data, remove from file_index
4. For changed graph YAML: reload affected nodes/edges
5. For changed docs: re-chunk, update docs/chunks tables
6. For changed code: re-extract symbols, update code_symbols
7. Rebuild sync_state for affected ref_ids only
8. Update meta.last_reindex_at
9. Take health snapshot
```

**CLI interface:**

```bash
beadloom reindex              # Incremental (default, new behavior)
beadloom reindex --full       # Force full rebuild (old behavior)
```

**Edge cases:**
- **Graph node deleted from YAML:** CASCADE deletes edges, SET NULL on docs/chunks/sync_state refs
- **Graph node renamed:** Detected as delete + add (user should update annotations)
- **First run (no file_index):** Equivalent to full reindex, populates file_index

**Performance estimate:** For a 1000-file project with 5 changed files, incremental reindex should be <200ms vs ~2s for full.

**Files changed:**
- `db.py` — add `file_index` table to schema
- `reindex.py` — new `incremental_reindex()` function, refactor `reindex()` to use it, add `--full` flag support
- `cli.py` — add `--full` option to reindex command
- `graph_loader.py` — support partial graph reload (specific YAML files)
- `doc_indexer.py` — support re-indexing specific docs
- `code_indexer.py` — support re-indexing specific files

---

### 3.3 Auto-reindex in MCP Server (4.3)

**Current state:** MCP server adds `"warning": "index is stale"` but does nothing about it.

**New behavior:** On tool call, if stale index detected → run incremental reindex before responding.

**Detection:** Compare `meta.last_reindex_at` with max mtime of `_graph/*.yml` and `docs/` files.

**Implementation:**

```python
async def _ensure_fresh_index(project_root: Path, conn: sqlite3.Connection) -> bool:
    """Auto-reindex if stale. Returns True if reindex was performed."""
    last_reindex = get_meta(conn, "last_reindex_at")
    if last_reindex is None:
        return False
    last_ts = datetime.fromisoformat(last_reindex).timestamp()
    max_mtime = _compute_max_mtime(project_root)
    if max_mtime > last_ts:
        incremental_reindex(project_root)
        return True
    return False
```

**Configurable:** `.beadloom/config.yml`:

```yaml
mcp:
  auto_reindex: true   # default: true
```

**Files changed:**
- `mcp_server.py` — add `_ensure_fresh_index()`, call before each tool handler
- `reindex.py` — expose `incremental_reindex()` as importable function

---

### 3.4 Bundle Caching in SQLite (4.4)

**Current state:** L1 cache is in-memory only, lost on MCP server restart.

**New table:**

```sql
CREATE TABLE IF NOT EXISTS bundle_cache (
    cache_key   TEXT PRIMARY KEY,    -- "ref_id:depth:max_nodes:max_chunks"
    bundle_json TEXT NOT NULL,       -- serialized JSON bundle
    etag        TEXT NOT NULL,       -- SHA-256 of bundle_json
    graph_mtime REAL NOT NULL,       -- mtime of graph files at cache time
    docs_mtime  REAL NOT NULL,       -- mtime of docs at cache time
    created_at  TEXT NOT NULL        -- ISO 8601
);
```

**Two-tier cache:**
1. **L1 (in-memory):** `ContextCache` — fast, per-process, survives within session
2. **L2 (SQLite):** `bundle_cache` — persistent, survives MCP server restarts

**Lookup order:** L1 → L2 → compute → store in both L1 and L2.

**Invalidation:**
- L1: mtime check (existing logic)
- L2: mtime check on read; `DELETE FROM bundle_cache` on full reindex; row-level delete on incremental reindex for affected ref_ids

**NOT in `_TABLES_TO_DROP`:** Like `health_snapshots`, `bundle_cache` persists across full reindex (but entries are invalidated).

**Files changed:**
- `db.py` — add `bundle_cache` table to schema
- `cache.py` — add `SqliteCache` class for L2, compose with existing `ContextCache`
- `mcp_server.py` — use two-tier cache in handlers

---

### 3.5 MCP Write Tools (4.5)

**Current state:** All 5 MCP tools are read-only. Agents cannot modify data.

**New MCP tools (3 write tools):**

#### `update_node`

Update summary or metadata of an existing graph node. Modifies YAML source of truth and updates SQLite.

```json
{
  "name": "update_node",
  "description": "Update a graph node's summary or metadata. Modifies YAML graph (source of truth) and SQLite index. Use after reading context to improve node descriptions.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ref_id": { "type": "string", "description": "Node identifier" },
      "summary": { "type": "string", "description": "New summary text (optional)" },
      "source": { "type": "string", "description": "New source path (optional)" }
    },
    "required": ["ref_id"]
  }
}
```

**Implementation:**
1. Find the node in YAML graph files (scan `_graph/*.yml`)
2. Update the `summary` (and/or `source`) field in YAML
3. Write YAML back to disk
4. Update `nodes` table in SQLite
5. Invalidate cache for this ref_id

#### `mark_synced`

Mark doc-code pairs as synchronized after the agent has updated documentation.

```json
{
  "name": "mark_synced",
  "description": "Mark documentation as synchronized with code for a ref_id. Call this after updating stale documentation to reset sync state.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ref_id": { "type": "string", "description": "Node identifier whose doc-code pairs should be marked as synced" }
    },
    "required": ["ref_id"]
  }
}
```

**Implementation:**
1. Find all `sync_state` rows for the ref_id
2. Recompute current file hashes (doc + code)
3. Update `code_hash_at_sync`, `doc_hash_at_sync`, `synced_at`, `status='ok'`

#### `search`

Fuzzy search across nodes, docs, and code symbols (see 3.6 for details).

```json
{
  "name": "search",
  "description": "Search for nodes, documents, and code symbols by keyword or natural language query. Returns ranked results with ref_ids and summaries.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query (keywords or natural language)" },
      "kind": { "type": "string", "enum": ["domain","feature","service","entity","adr"], "description": "Filter by node kind (optional)" },
      "limit": { "type": "integer", "default": 10, "description": "Max results" }
    },
    "required": ["query"]
  }
}
```

**Agent workflow (example — update stale docs):**

```
1. Agent calls sync_check() → gets list of stale ref_ids
2. Agent calls get_context(ref_id) → gets full context + stale details
3. Agent reads the doc file and changed code file
4. Agent updates the doc file (using its own intelligence)
5. Agent calls mark_synced(ref_id) → sync state reset to "ok"
```

**Agent workflow (example — improve summaries):**

```
1. Agent calls get_status() → sees nodes with empty summaries
2. Agent calls get_context(ref_id) → reads code and docs
3. Agent generates a summary (using its own LLM capabilities)
4. Agent calls update_node(ref_id, summary="...") → YAML + SQLite updated
```

**Files changed:**
- `mcp_server.py` — add 3 new tool definitions, handlers, dispatch
- `graph_loader.py` — add `update_node_in_yaml()` function for YAML modification
- `sync_engine.py` — add `mark_synced_by_ref()` function

**Total MCP tools after Phase 4: 8** (5 read + 3 write)

---

### 3.6 Semantic Search (4.6)

**Current state:** Only exact `ref_id` matching + Levenshtein suggestions for typos.

**Two-tier search architecture:**

#### Tier 1: FTS5 (built-in, always available)

SQLite FTS5 virtual table for keyword search. Zero new dependencies.

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    ref_id,
    kind,
    summary,
    content,             -- concatenated chunk text
    tokenize='porter unicode61'
);
```

**Populated during reindex** from nodes + chunks:
- One row per node: `ref_id`, `kind`, `summary`, concatenated chunk content
- Porter stemming for English, unicode61 for multilingual support

**Query:**

```sql
SELECT ref_id, kind, summary, rank
FROM search_index
WHERE search_index MATCH :query
ORDER BY rank
LIMIT :limit;
```

#### Tier 2: sqlite-vec (optional, semantic search)

Vector similarity search using embeddings. Requires optional dependency.

**Optional dependency:**

```toml
[project.optional-dependencies]
search = [
    "sqlite-vec>=0.1",
]
```

**Vector table:**

```sql
-- Created only when sqlite-vec is available
CREATE VIRTUAL TABLE IF NOT EXISTS vec_nodes USING vec0(
    ref_id TEXT PRIMARY KEY,
    embedding float[384]        -- dimension depends on model
);
```

**Embedding generation strategy:**

Since Beadloom is agent-native and doesn't call LLM APIs, embeddings are generated using a **lightweight local model** bundled as an optional dependency:

```toml
search = [
    "sqlite-vec>=0.1",
    "fastembed>=0.4",           # Lightweight ONNX-based embeddings (~80MB)
]
```

`fastembed` uses ONNX Runtime with small models (e.g., `BAAI/bge-small-en-v1.5`, 384 dimensions, ~33MB). Runs locally, no API calls, fast inference.

**Fallback chain:**

```
1. sqlite-vec available? → vector similarity search
2. sqlite-vec not available? → FTS5 keyword search
3. FTS5 miss? → Levenshtein suggestions (existing)
```

**CLI:**

```bash
beadloom search "payment processing"     # Search nodes and docs
beadloom search "auth" --kind service    # Filter by kind
beadloom search "how routes are built"   # Semantic (if sqlite-vec installed)
```

**Files changed:**
- `db.py` — add FTS5 table to schema, conditional vec table
- `reindex.py` — populate FTS5 during reindex, optional vec population
- `cli.py` — new `search` command
- `mcp_server.py` — `search` tool handler
- NEW: `src/beadloom/search.py` — search logic, FTS5 query builder, optional vec integration
- `pyproject.toml` — add `[search]` optional dependency group

---

### 3.7 Remove LLM API Deprecation (4.7)

**What's being removed:**

| Item | Location | Action |
|------|----------|--------|
| `--auto` flag on `sync-update` | `cli.py:675` | Remove entirely (currently hidden + deprecated) |
| Deprecation warning code | `cli.py:703-710` | Remove |
| `auto` parameter | `cli.py:681` | Remove |
| Test for deprecation | `test_cli_sync_update.py:185-197` | Remove |
| `llm_updater.py` reference in AGENTS.md | `AGENTS.md:26` | Remove line |
| `llm` config examples in PRD | `PRD.md:229-237` | Mark as removed |
| LLM config examples in RFC-0001 | `RFC.md:1180-1186` | Mark as removed |
| `httpx` mention in AGENTS.md | `AGENTS.md:11` | Remove |
| LLM test mocking note | `AGENTS.md:76` | Remove |

**Files changed:**
- `cli.py` — remove `--auto` flag and handler from sync-update
- `test_cli_sync_update.py` — remove `TestSyncUpdateAutoDeprecated` class
- `AGENTS.md` — clean up references

---

### 3.8 AGENTS.md Update (4.8)

Update AGENTS.md to reflect Phase 4 reality:

1. **Remove** `llm_updater.py` from file tree (deleted in v0.3)
2. **Remove** `httpx` from stack description
3. **Remove** LLM test mocking note
4. **Update** test count (398 → new count after Phase 4)
5. **Add** section on MCP write tools and agent-driven workflows:
   - How to update summaries via `update_node`
   - How to resolve stale docs via `mark_synced`
   - How to search via `search`
6. **Add** "Adding a New MCP Tool" section update for write tools
7. **Update** file organization to reflect new modules (`search.py`)

---

## 4. Schema Changes

**New tables (additive, no version bump needed):**

| Table | Purpose |
|-------|---------|
| `file_index` | Track file hashes for incremental reindex |
| `bundle_cache` | Persistent L2 cache for context bundles |
| `search_index` (FTS5) | Full-text search over nodes and chunks |
| `vec_nodes` (sqlite-vec, optional) | Vector embeddings for semantic search |

All use `CREATE TABLE IF NOT EXISTS` / `CREATE VIRTUAL TABLE IF NOT EXISTS`.

None added to `_TABLES_TO_DROP` (persist across reindex, invalidated/rebuilt as needed).

Exception: `search_index` and `vec_nodes` ARE rebuilt on reindex (they derive from indexed data).

---

## 5. Dependency Changes

**pyproject.toml updates:**

```toml
[project.optional-dependencies]
search = [
    "sqlite-vec>=0.1",
    "fastembed>=0.4",
]
languages = [
    "tree-sitter-typescript>=0.23",
    "tree-sitter-go>=0.23",
    "tree-sitter-rust>=0.23",
]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.8",
    "mypy>=1.13",
    "types-PyYAML>=6.0",
]
all = [
    "beadloom[languages,search,dev]",
]
```

**Core dependencies unchanged.** `sqlite-vec` and `fastembed` are optional — FTS5 works without them.

---

## 6. CLI Changes

| Command | Change |
|---------|--------|
| `beadloom reindex` | Now incremental by default |
| `beadloom reindex --full` | NEW flag: force full rebuild |
| `beadloom search <query>` | NEW command |
| `beadloom search <query> --kind <kind>` | Filter by node kind |
| `beadloom sync-update --auto` | REMOVED |

---

## 7. MCP Tool Changes

| Tool | Change |
|------|--------|
| `get_context` | Now uses L1+L2 cache, returns `cached: true` on hit |
| `update_node` | NEW (write): update node summary/source in YAML + SQLite |
| `mark_synced` | NEW (write): reset sync state for ref_id |
| `search` | NEW (read): fuzzy search across graph |

**Total: 8 tools** (6 read + 2 write)

---

## 8. Migration Notes

- **No breaking changes for existing users.** All new tables are additive.
- `beadloom reindex` (without `--full`) is the new default behavior. First run after upgrade populates `file_index`, subsequent runs are incremental.
- `--auto` flag removal: already deprecated since v0.3. Users who still pass it will get a Click error ("No such option: --auto") — acceptable since it was hidden and non-functional.
- `sqlite-vec` is optional: `beadloom search` works without it via FTS5.

---

## 9. Testing Strategy

| Deliverable | Test approach |
|-------------|---------------|
| 4.1 L1 cache in MCP | Mock mtime, verify cache hit/miss, token savings |
| 4.2 Incremental reindex | Hash comparison, changed/added/deleted files, partial reload |
| 4.3 Auto-reindex in MCP | Mock stale detection, verify reindex triggered |
| 4.4 Bundle cache SQLite | L2 persistence across "restarts", invalidation on reindex |
| 4.5 MCP write tools | YAML round-trip (write + read), sync state update, error cases |
| 4.6 Semantic search | FTS5 queries, ranking, kind filtering; sqlite-vec mocked if not installed |
| 4.7 LLM removal | Verify --auto flag removed, no import errors |
| 4.8 AGENTS.md | No test (documentation only) |

**Coverage target:** ≥80% (maintained)

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Incremental reindex misses edge cases (renamed nodes, moved files) | Comprehensive tests; `--full` as escape hatch |
| sqlite-vec not available on all platforms | FTS5 fallback always works; `search` optional dep clearly documented |
| fastembed download on first use (~80MB model) | Lazy download on first `reindex` with `[search]` installed; clear progress indication |
| MCP write tools modify YAML (source of truth) | Atomic writes (write to temp file, rename); backup in-memory before write |
| Cache invalidation bugs (stale data served) | Conservative invalidation: any doubt → invalidate; `--full` reindex clears all caches |
| Auto-reindex blocks MCP response | Incremental reindex is fast (<200ms); timeout with warning if >2s |

---

## 11. Phase 5 — Developer Experience (v0.7)

DX items moved to a dedicated Phase 5 before Architecture as Code (Phase 6):

| Item | Description |
|------|-------------|
| TUI (`beadloom ui`) | Interactive terminal dashboard (Textual) |
| Graph diff (`beadloom diff`) | What changed in graph since last commit/tag |
| `beadloom why REF_ID` | Explain node's role (upstream/downstream, impact) |
| Watch mode (`beadloom watch`) | Auto-reindex on file changes (extends 4.3) |

---

## 12. Implementation Order

```
Phase 4.1: L1 Cache in MCP          (P0, Small)   — quick win, immediate value
Phase 4.7: Remove --auto + LLM      (P0, Small)   — cleanup, unblocks 4.5/4.8
Phase 4.2: Incremental Reindex      (P0, Large)    — core infrastructure
Phase 4.5: MCP Write Tools          (P1, Medium)   — agent-native evolution
Phase 4.3: Auto-reindex in MCP      (P1, Small)    — depends on 4.2
Phase 4.4: Bundle Cache SQLite      (P1, Medium)   — depends on 4.1
Phase 4.8: AGENTS.md Update         (P1, Small)    — depends on 4.5, 4.7
Phase 4.6: Semantic Search          (P2, Large)    — depends on 4.2
```
