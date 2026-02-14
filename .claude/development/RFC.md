# RFC-0001: Architecture and Data Model of Beadloom

## 1. Summary

This RFC describes the architecture of Beadloom -- a local CLI tool and MCP server that solve two problems of agentic development on large codebases:

1. **Context Oracle** -- instant delivery of compact context bundles by feature/domain/service identifier through deterministic architecture graph traversal.
2. **Doc Sync Engine** -- tracking documentation-to-code relationships and detecting documentation staleness.

Additionally, Beadloom provides **onboarding for existing projects**: automatic generation of an initial graph and documentation from the codebase.

Source of truth is Git (YAML graph + Markdown documentation + code). Derived index is SQLite.

## 2. Motivation

### 2.1 Problem: Context Window Burn

AI agents (Claude Code, Cursor, Beads workers) on large codebases spend most of the context window on orientation:

- reading READMEs, architecture docs, specifications;
- grep/glob through code to find relevant files;
- re-opening previously read files in new sessions.

Only a small portion of the window remains for actual work (writing/modifying code). Each new agent session starts from scratch.

### 2.2 Problem: Documentation Degradation

After an agent or human modifies code:

- related documentation (specs, domain descriptions, ADRs) becomes stale;
- updating documentation requires a separate context window;
- without automatic tracking, nobody notices that documentation is lying;
- within a month, any knowledge index becomes useless.

### 2.3 Problem: Cold Start

For new Beadloom users (and any similar tool):

- there is no architecture graph, which must be created from scratch;
- there is no structured documentation;
- manually filling a graph for 50+ services is unrealistic.

Without automatic onboarding, adoption = 0.

### 2.4 Beadloom's Solution

- **YAML graph** (domains, features, services, entities, ADRs) versioned in Git.
- **Context Oracle** -- deterministic graph traversal producing a compact JSON bundle at 0 search tokens.
- **Doc Sync Engine** -- code hash tracking to detect stale documentation.
- **Onboarding** -- auto-generation of a graph and documentation from the codebase.
- **MCP server** -- native agent integration without an intermediate HTTP layer.

## 3. Architecture Overview

### 3.1 Components

```
+--------------------------------------------------+
|                  Git Repository                    |
|                                                    |
|  src/            .beadloom/_graph/*.yml    docs/   |
|  (code)          (YAML graph)              (docs)  |
+------------------------+--------------------------+
                         |
                  beadloom reindex
                         |
                         v
                +-----------------+
                |   SQLite DB      |
                |   (WAL mode)     |
                |                  |
                |  nodes, edges    |
                |  docs, chunks    |
                |  code_symbols    |
                |  sync_state      |
                +--------+--------+
                         |
              +----------+-----------+
              |          |           |
              v          v           v
            CLI      MCP Server   Git hooks
              |          |           |
          humans     agents      doc-sync
```

1. **Git repository** -- source of truth: code, YAML graph, Markdown documentation.
2. **Indexer** (`beadloom reindex`) -- parses YAML graph, documents, and code; fully rebuilds SQLite (drop + re-create in v0).
3. **SQLite** (`.beadloom/beadloom.db`) -- derived read-model. WAL mode for concurrent access. Rebuilt by the indexer.
4. **CLI** -- interface for humans: `ctx`, `graph`, `sync-check`, `doctor`, `status`, `help`, `version`.
5. **MCP server** (`beadloom mcp-serve`) -- interface for agents via MCP protocol (stdio transport). Includes L1 cache.
6. **Git hooks** -- automatic sync-check on commit.

### 3.2 Key Design Decisions

**No daemon in v0.** CLI and MCP server work directly with SQLite. This eliminates:
- the need to launch/monitor a background process;
- the network stack (HTTP/Unix socket) for a local operation.

A daemon may be added later (phase 4+) for heavy scenarios with background re-indexing.

**L1 cache in MCP server.** The MCP server is a long-lived process (stdio, lives as long as the agent session is active). In-memory bundle cache allows returning a short response `{"cached": true, "unchanged_since": "..."}` instead of the full bundle on repeated requests with the same `ref_id`. This saves agent tokens during multi-step workflows (planning -> coding -> review) when the same context is requested multiple times. Invalidation is by file modification (mtime check). Details in section 8.3.

**Stale index detection in MCP server.** On every request, the MCP server checks the mtime of `_graph/*.yml` and `docs/` files. If files have changed since the last `reindex`, the response includes a warning `"warning": "index is stale, run beadloom reindex"`. The agent sees that the data may be outdated.

**Deterministic context builder.** Graph traversal is pure logic (SQL queries to SQLite), requiring no LLM or embeddings. This provides:
- predictability (same input -> same output);
- speed (milliseconds, not seconds);
- no dependencies on external services.

Semantic search (embeddings) will be added in phase 4 for fuzzy free-text queries.

**MCP instead of HTTP API.** Agents connect Beadloom as an MCP server, not as an HTTP client. Advantages:
- native integration with Claude Code, Cursor, and other MCP clients;
- stdio transport -- no ports, no network issues;
- process launched on demand by the agent, no need to monitor a daemon.

**SQLite WAL mode.** `PRAGMA journal_mode=WAL` is set at database creation (persistent for the file). `PRAGMA foreign_keys=ON` is executed on every connection open (per-connection in SQLite). WAL allows the MCP server and CLI to read concurrently while `reindex` writes.

**`ref_id` is globally unique.** The PK of the `nodes` table is `ref_id` (not a composite `(kind, ref_id)`). This simplifies edges, SQL queries, and eliminates ambiguity. Naming conventions ensure uniqueness: `routing` (domain), `routing-api` (service).

## 4. Data Model

### 4.1 SQLite Schema

```sql
-- Initialization
PRAGMA journal_mode=WAL;   -- persistent for the file, only needed once
PRAGMA foreign_keys=ON;    -- per-connection, required on every connection open

-- Graph nodes
CREATE TABLE nodes (
    ref_id  TEXT PRIMARY KEY,
    kind    TEXT NOT NULL CHECK(kind IN ('domain','feature','service','entity','adr')),
    summary TEXT NOT NULL DEFAULT '',
    source  TEXT,                         -- path to source code directory/file (optional)
    extra   TEXT DEFAULT '{}'             -- JSON: arbitrary metadata
);

-- Graph edges
CREATE TABLE edges (
    src_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    dst_ref_id TEXT NOT NULL REFERENCES nodes(ref_id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK(kind IN (
        'part_of','depends_on','uses','implements',
        'touches_entity','touches_code'
    )),
    extra      TEXT DEFAULT '{}',         -- JSON
    PRIMARY KEY (src_ref_id, dst_ref_id, kind)
);

-- Documents (Markdown file index)
CREATE TABLE docs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    path     TEXT NOT NULL UNIQUE,           -- relative path in repo
    kind     TEXT NOT NULL CHECK(kind IN ('feature','domain','service','adr','architecture','other')),
    ref_id   TEXT REFERENCES nodes(ref_id) ON DELETE SET NULL,  -- link to graph node
    metadata TEXT DEFAULT '{}',              -- JSON
    hash     TEXT NOT NULL                   -- SHA256 of file content
);

-- Document chunks
CREATE TABLE chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    heading     TEXT NOT NULL DEFAULT '',     -- section heading (text of ## heading)
    section     TEXT NOT NULL DEFAULT '',     -- type: spec|invariants|api|tests|constraints|other
    content     TEXT NOT NULL,
    node_ref_id TEXT REFERENCES nodes(ref_id) ON DELETE SET NULL -- direct link to node (for performance)
);

-- Code symbols
CREATE TABLE code_symbols (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,               -- relative path to file
    symbol_name TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK(kind IN ('function','class','type','route','component')),
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    annotations TEXT DEFAULT '{}',           -- JSON: {feature, domain, service, entity}
    file_hash   TEXT NOT NULL                -- SHA256 of file at indexing time
);

-- Doc-to-code synchronization state
CREATE TABLE sync_state (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path        TEXT NOT NULL,            -- path to document
    code_path       TEXT NOT NULL,            -- path to related code file
    ref_id          TEXT NOT NULL REFERENCES nodes(ref_id),
    code_hash_at_sync TEXT NOT NULL,          -- code hash at sync time
    doc_hash_at_sync  TEXT NOT NULL,          -- document hash at sync time
    synced_at       TEXT NOT NULL,            -- ISO 8601 timestamp
    status          TEXT NOT NULL DEFAULT 'ok' CHECK(status IN ('ok','stale')),
    UNIQUE(doc_path, code_path)
);

-- Index metadata
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Stores: last_reindex_at, beadloom_version, schema_version

-- Indexes
CREATE INDEX idx_nodes_kind ON nodes(kind);
CREATE INDEX idx_edges_src ON edges(src_ref_id);
CREATE INDEX idx_edges_dst ON edges(dst_ref_id);
CREATE INDEX idx_docs_ref ON docs(ref_id);
CREATE INDEX idx_chunks_doc ON chunks(doc_id);
CREATE INDEX idx_chunks_node ON chunks(node_ref_id);
CREATE INDEX idx_symbols_file ON code_symbols(file_path);
CREATE INDEX idx_sync_status ON sync_state(status);
CREATE INDEX idx_sync_ref ON sync_state(ref_id);
```

### 4.2 YAML to SQLite Mapping

During `beadloom reindex`, the indexer reads `.beadloom/_graph/*.yml` files and maps them to SQLite:

| YAML field (node) | SQLite | Description |
|--------------------|--------|-------------|
| `ref_id` | `nodes.ref_id` (PK) | Globally unique identifier |
| `kind` | `nodes.kind` | Node type |
| `summary` | `nodes.summary` | Text description |
| `source` | `nodes.source` | Path to source code (optional) |
| `docs` | -> `docs` table | For each path, creates a record in `docs` with the node's `ref_id` |
| `confidence` | -- | Not indexed. Hint during bootstrap, removed after review |
| everything else | `nodes.extra` (JSON) | Arbitrary metadata |

| YAML field (edge) | SQLite | Description |
|--------------------|--------|-------------|
| `src` | `edges.src_ref_id` | Source node ref_id |
| `dst` | `edges.dst_ref_id` | Target node ref_id |
| `kind` | `edges.kind` | Relationship type |

**Validation during reindex:**
- `ref_id` must be unique -- error on duplicates.
- `src`/`dst` in edges must reference existing `ref_id` -- warning if not found.
- `docs` paths must exist -- warning if file not found.

### 4.3 YAML Graph (Source of Truth)

The graph is stored in `.beadloom/_graph/` and versioned in Git.

**Edge placement convention:** edges are stored in the source node's file (by the `src` field). For example, edge `PROJ-123 -> routing` (part_of) is in `features.yml`, edge `billing -> routing` (depends_on) is in `domains.yml`.

**Format of `.beadloom/_graph/domains.yml`:**

```yaml
nodes:
  - ref_id: routing
    kind: domain
    summary: "Routing and track building: route calculation, filtering, ETA."
    docs:
      - docs/domains/routing/README.md

  - ref_id: billing
    kind: domain
    summary: "Billing and payments: tariffs, subscriptions, payments."
    docs:
      - docs/domains/billing/README.md

edges:
  - src: billing
    dst: routing
    kind: depends_on
```

**Format of `.beadloom/_graph/features.yml`:**

```yaml
nodes:
  - ref_id: PROJ-123
    kind: feature
    summary: "Track filtering by date and transport type."
    docs:
      - docs/domains/routing/features/PROJ-123/SPEC.md
      - docs/domains/routing/features/PROJ-123/API.md

edges:
  - src: PROJ-123
    dst: routing
    kind: part_of
  - src: PROJ-123
    dst: api-routing
    kind: uses
  - src: PROJ-123
    dst: Track
    kind: touches_entity
```

**Format of `.beadloom/_graph/services.yml`:**

```yaml
nodes:
  - ref_id: api-routing
    kind: service
    summary: "HTTP API for routing. FastAPI, 23 endpoints."
    source: src/services/routing/

edges:
  - src: api-routing
    dst: routing
    kind: part_of
```

**Format of `.beadloom/_graph/entities.yml`:**

```yaml
nodes:
  - ref_id: Track
    kind: entity
    summary: "Route record: points, time, metadata."
    source: src/models/track.py

  - ref_id: Route
    kind: entity
    summary: "Calculated route between points."
    source: src/models/route.py

edges:
  - src: Track
    dst: Route
    kind: depends_on
```

### 4.4 Code Annotations

Optional linking of code symbols to the graph via comments:

```python
# beadloom:feature=PROJ-123 domain=routing entity=Track
async def list_tracks(filters: TrackFilters) -> list[Track]:
    ...
```

```typescript
// beadloom:feature=PROJ-123 service=mobile-app
export function TrackFilter(): JSX.Element {
  ...
}
```

Format: `beadloom:<key>=<value>[ <key>=<value>]*`

Allowed keys: `feature`, `domain`, `service`, `entity`, `adr`.

The indexer parses annotations and creates records in `code_symbols` + `touches_code` edges in `edges`.

### 4.5 Context Bundle (Output Format)

```json
{
  "version": 1,
  "focus": {
    "ref_id": "PROJ-123",
    "kind": "feature",
    "summary": "Track filtering by date and transport type."
  },
  "graph": {
    "nodes": [
      { "ref_id": "PROJ-123", "kind": "feature", "summary": "..." },
      { "ref_id": "routing", "kind": "domain", "summary": "..." },
      { "ref_id": "api-routing", "kind": "service", "summary": "..." },
      { "ref_id": "Track", "kind": "entity", "summary": "..." }
    ],
    "edges": [
      { "src": "PROJ-123", "dst": "routing", "kind": "part_of" },
      { "src": "PROJ-123", "dst": "api-routing", "kind": "uses" },
      { "src": "PROJ-123", "dst": "Track", "kind": "touches_entity" }
    ]
  },
  "text_chunks": [
    {
      "doc_path": "docs/domains/routing/features/PROJ-123/SPEC.md",
      "section": "spec",
      "heading": "Business rules",
      "content": "..."
    },
    {
      "doc_path": "docs/domains/routing/README.md",
      "section": "invariants",
      "heading": "Routing invariants",
      "content": "..."
    }
  ],
  "code_symbols": [
    {
      "file_path": "src/services/routing/api.py",
      "symbol_name": "list_tracks",
      "kind": "function",
      "line_start": 10,
      "line_end": 80
    }
  ],
  "sync_status": {
    "stale_docs": [],
    "last_reindex": "2025-01-15T10:30:00Z"
  },
  "warning": null
}
```

The `warning` field contains `"index is stale, run beadloom reindex"` if the index is outdated; `null` in normal state.

## 5. Onboarding: Initialization Process

### 5.1 Interactive Mode (`beadloom init` without flags)

```
$ beadloom init

Welcome to Beadloom!

What would you like to do?
  1. Bootstrap — generate graph and docs from code (no existing docs)
  2. Import    — import and classify existing documentation
  3. Scope     — bootstrap a specific directory only

Choose [1/2/3]:
```

On repeated run (`.beadloom/_graph/` already exists):

```
$ beadloom init

Beadloom is already initialized in this project.

  1. Re-bootstrap — regenerate graph (manual edits will be LOST)
  2. Merge        — add new nodes, keep existing (mark conflicts)
  3. Cancel

Choose [1/2/3]:
```

Merge mode: scans the project, generates new nodes, compares with the existing graph. New nodes are added with `confidence`. Existing nodes are left untouched. Conflicts (changed `source` or `summary`) are flagged for manual review.

### 5.2 Bootstrap (No Documentation)

**Command:** `beadloom init --bootstrap`

**Steps:**

1. **Project structure scanning:**
   - detecting manifests (`package.json`, `go.mod`, `pyproject.toml`, `Cargo.toml`);
   - detecting entry points (`main.*`, `app.*`, `index.*`);
   - analyzing directory structure (src/, services/, lib/, packages/).

2. **Symbol extraction via tree-sitter:**
   - parsing files by language (Python, TypeScript, Go, Rust, Java);
   - extracting: modules, classes, functions, HTTP routes, GraphQL types;
   - counting cross-references between symbols (imports, calls).

3. **Clustering:**
   - grouping by top-level directories -> `service` candidates;
   - grouping by domain directories -> `domain` candidates;
   - frequently used types/classes -> `entity` candidates.

4. **Draft graph generation:**
   ```yaml
   # .beadloom/_graph/services.yml (auto-generated)
   nodes:
     - ref_id: api-gateway
       kind: service
       summary: "HTTP API entry point, FastAPI, 23 routes"
       confidence: high
       source: src/api/
     - ref_id: payments
       kind: domain
       summary: "Payment processing logic"
       confidence: medium
       source: src/domains/payments/
   ```
   The `confidence` field is a hint for humans: `high` = confident, `medium` = verify, `low` = possibly incorrect. Not stored in SQLite; `beadloom doctor` warns if `confidence` remains in the graph after review.

5. **Stub documentation generation:**
   ```markdown
   # Domain: payments

   > Auto-generated by beadloom init. Review and update.

   ## Summary
   <!-- TODO: describe the payments domain -->

   ## Invariants
   <!-- TODO: list business invariants -->

   ## Key entities
   - PaymentIntent (src/domains/payments/models.py)
   - Subscription (src/domains/payments/subscription.py)
   ```

6. **Configuration and .gitignore creation:**
   - Creates `.beadloom/config.yml` with default settings (auto-detected languages, scan_paths).
   - Adds `.beadloom/beadloom.db` to `.gitignore` (if not already present).

7. **Interactive report:**
   ```
   Scanned 847 files, 12 languages
   Found 5 services, 3 domains, 28 entities

   Generated:
     .beadloom/config.yml           (default settings)
     .beadloom/_graph/domains.yml   (3 nodes, review needed)
     .beadloom/_graph/services.yml  (5 nodes, 8 edges)
     .beadloom/_graph/entities.yml  (28 nodes)
     docs/domains/payments/README.md  (stub)
     docs/domains/routing/README.md   (stub)
     docs/domains/auth/README.md      (stub)
   Updated .gitignore

   Next: review .beadloom/_graph/*.yml, then run beadloom reindex
   ```

### 5.3 Import (Existing Documentation)

**Command:** `beadloom init --import ./docs`

**Steps:**

1. **Discovery:** recursive search for `.md` files.

2. **Document classification** (heuristics):
   - contains "## Decision" / "## Status: Accepted" -> `adr`;
   - contains "## API" / "## Endpoints" -> `feature` or `service`;
   - contains "## Invariants" / "## Business rules" -> `domain`;
   - file name contains `ADR-`, `RFC-` -> `adr`;
   - path contains `features/`, `specs/` -> `feature`;
   - otherwise -> `other` (requires manual classification).

3. **Entity extraction from text:**
   - mentions of class/type names (CamelCase) -> `entity` candidates;
   - mentions of services (`*-service`, `*-api`) -> `service` candidates;
   - references to code files -> `touches_code` relationships.

4. **Interactive strategy selection:**

   ```
   How should Beadloom organize your documentation?

     1. Restructure — copy docs into standard layout (docs/domains/<domain>/features/, ...)
        + Better integration with context builder and sync engine
        + Clean, consistent structure
        + GitHub/GitLab renders domain README.md automatically
        - Original file paths change
        - May require updating internal links

     2. Map in place — keep docs where they are, just build the graph
        + No file changes, zero risk
        + Works with any existing doc structure
        - Sync engine tracks changes less precisely
        - Context builder relies on naming heuristics

   Choose [1/2]:
   ```

   Mode 1 (Restructure): classified documents are copied to `docs/` following the domain-first convention (features grouped under domains). Unrecognized documents go to `docs/_imported/` for manual review. Original files are not deleted.

   Mode 2 (Map in place): documents stay where they are. The YAML graph references original paths. Unrecognized documents are mapped as `other`.

5. **Report:**
   ```
   Scanned 47 markdown files

   Classified:
     12 x feature spec    -> docs/domains/*/features/
      4 x domain overview -> docs/domains/*/README.md
      7 x ADR             -> docs/decisions/
      3 x architecture    -> docs/architecture.md
     21 x unclassified    -> docs/_imported/ (review needed)

   Generated graph: 12 features, 4 domains, 8 services, 15 entities
   Auto-detected edges: 67% | Need manual review: 33%
   ```

### 5.4 Incremental (Gradual Coverage)

**Command:** `beadloom init --scope src/payments`

Same as bootstrap, but limited to a single scope (directory or set of directories). The rest of the project is marked as `unmapped`.

**`beadloom status`** shows coverage:

```
Coverage:
  payments       ############ 100%  (3 features, 12 symbols, 2 docs)
  routing        ########....  67%  (2 features, 5 symbols, no domain doc)
  auth           ####........  33%  (1 feature, no specs)
  notifications  ............   0%  (unmapped)

Overall: 42% documented | 3 stale docs
```

## 6. Context Oracle: Context Assembly Process

### 6.1 Algorithm (Deterministic)

**Input:** one or more `ref_id`s (e.g., `PROJ-123` or `PROJ-123 routing`), optionally `depth` (default 2), `max_nodes` (default 20), `max_chunks` (default 10).

For multiple `ref_id`s, each becomes a focus node, and subgraphs are merged.

**Step 1: Find focus nodes.**

```sql
SELECT * FROM nodes WHERE ref_id IN (:ref_ids);
```

If a node is not found -- error with suggestion: `"PROJ-123" not found. Did you mean: PROJ-124, PROJ-132?` (by Levenshtein distance from existing ref_ids). Future: fuzzy search by summary via embeddings.

**Step 2: Expand subgraph.**

BFS from focus nodes along edges with prioritization:

```
Priority 1: part_of (feature's domain)
Priority 2: touches_entity (key entities)
Priority 3: uses, implements (related services)
Priority 4: depends_on (dependencies)
Priority 5: touches_code (code symbols)
```

Traversal is limited by `depth` and `max_nodes`. Both incoming and outgoing edges are traversed.

```sql
-- Outgoing edges
SELECT e.*, n.* FROM edges e
JOIN nodes n ON (n.ref_id = e.dst_ref_id)
WHERE e.src_ref_id IN (:current_frontier);

-- Incoming edges
SELECT e.*, n.* FROM edges e
JOIN nodes n ON (n.ref_id = e.src_ref_id)
WHERE e.dst_ref_id IN (:current_frontier);
```

**Step 3: Collect chunks.**

For each node in the subgraph:

```sql
SELECT c.* FROM chunks c
JOIN docs d ON c.doc_id = d.id
WHERE d.ref_id IN (:subgraph_ref_ids)
ORDER BY
  CASE c.section
    WHEN 'spec' THEN 1
    WHEN 'invariants' THEN 2
    WHEN 'constraints' THEN 3
    WHEN 'api' THEN 4
    WHEN 'tests' THEN 5
    ELSE 6
  END
LIMIT :max_chunks;
```

**Step 4: Collect code symbols.**

Via annotations:

```sql
SELECT * FROM code_symbols
WHERE json_extract(annotations, '$.feature') IN (:subgraph_ref_ids)
   OR json_extract(annotations, '$.domain') IN (:subgraph_ref_ids)
   OR json_extract(annotations, '$.service') IN (:subgraph_ref_ids);
```

Or via the `source` field of nodes:

```sql
SELECT cs.* FROM code_symbols cs
JOIN nodes n ON cs.file_path LIKE n.source || '%'
WHERE n.ref_id IN (:subgraph_ref_ids)
  AND n.source IS NOT NULL;
```

**Step 5: Assemble bundle.**

Build the JSON context bundle (format in section 4.5).

**Step 6: Check sync_state and stale index.**

```sql
SELECT doc_path, code_path, status FROM sync_state
WHERE ref_id IN (:subgraph_ref_ids) AND status = 'stale';
```

```sql
SELECT value FROM meta WHERE key = 'last_reindex_at';
```

Stale docs are added to `sync_status`. If the mtime of `_graph/*.yml` or `docs/` is newer than `last_reindex_at`, a `warning` is added.

### 6.2 Document Chunking Strategy

During `reindex`, Markdown files are split into chunks:

1. **Split by `##` (H2) headings.** Each H2 section is a separate chunk. H1 (`#`) is the document title, not a chunk.
2. **Maximum chunk size: 2000 characters.** Sections exceeding 2000 characters are split by paragraphs (blank line).
3. **Section classification by keywords in the heading:**
   - `spec`, `specification`, `requirements`, `description`, `business rules` -> `spec`
   - `invariant`, `constraint`, `invariants`, `constraints` -> `invariants`
   - `api`, `endpoint`, `route` -> `api`
   - `test`, `tests`, `testing` -> `tests`
   - `constraint`, `limit` -> `constraints`
   - everything else -> `other`
4. **Chunk metadata:** `heading` (heading text), `section` (classification), `chunk_index` (ordinal number), `node_ref_id` (from `docs.ref_id`).

### 6.3 Performance

For a typical project (1000 nodes, 5000 edges, 2000 chunks):
- BFS at depth 2 with 20-node limit: <5ms.
- Chunk retrieval: <10ms.
- JSON assembly: <1ms.

Total time: **<20ms**. No caching needed in CLI. The MCP server uses an L1 cache to save tokens on repeated requests (see section 8.3).

## 7. Doc Sync Engine

### 7.1 Mechanism

Doc-to-code relationships are determined through:

1. **Graph:** node `PROJ-123` is linked to `docs/domains/routing/features/PROJ-123/SPEC.md` (via `docs.ref_id`) and to `src/services/routing/api.py` (via `code_symbols` or `nodes.source`).
2. **Annotations:** `# beadloom:feature=PROJ-123` in a code file links to the feature's documents.

During `beadloom reindex`:
- for each pair (doc, code_file) linked through a common `ref_id`, hashes are computed;
- if the code hash changed since the last sync, `status = 'stale'`.

### 7.2 `beadloom sync-check`

```
$ beadloom sync-check

Stale documentation (3 docs):

  docs/domains/routing/features/PROJ-123/SPEC.md
    <-> src/services/routing/api.py (changed 2 days ago, +47 -12 lines)
    <-> src/services/routing/models.py (changed 2 days ago, +8 -3 lines)

  docs/domains/routing/README.md
    <-> src/services/routing/engine.py (changed 5 days ago, +120 -45 lines)

  docs/decisions/ADR-015.md
    <-> src/lib/cache.py (changed 1 day ago, +15 -8 lines)

Run: beadloom sync-update <ref_id> to update docs
```

**`--porcelain` format** (for git hooks and scripts):

```
$ beadloom sync-check --porcelain
stale	PROJ-123	docs/domains/routing/features/PROJ-123/SPEC.md	src/services/routing/api.py
stale	PROJ-123	docs/domains/routing/features/PROJ-123/SPEC.md	src/services/routing/models.py
stale	routing	docs/domains/routing/README.md	src/services/routing/engine.py
stale	ADR-015	docs/decisions/ADR-015.md	src/lib/cache.py
```

TAB-separated: `status`, `ref_id`, `doc_path`, `code_path`.

**Exit codes:**
- `0` -- all documents are up-to-date.
- `1` -- execution error.
- `2` -- stale documents found.

### 7.3 `beadloom sync-update`

```
$ beadloom sync-update PROJ-123
```

Two modes:

**Interactive (default):**
- shows the code diff since the last sync;
- opens the document in `$EDITOR` for manual update;
- after saving, updates hashes in `sync_state`.

**Automatic (`--auto`, requires LLM):**
- collects the context bundle for `ref_id`;
- adds the code diff;
- sends an LLM request: "Update the documentation to reflect the code changes";
- shows the proposed changes for confirmation;
- after confirmation, writes and updates `sync_state`.

**LLM configuration** (`.beadloom/config.yml`):

```yaml
llm:
  provider: anthropic       # anthropic | openai | ollama | none
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY  # name of environment variable with API key
```

If LLM is not configured, `--auto` returns an error:
```
Error: LLM not configured. Add 'llm' section to .beadloom/config.yml
See: beadloom help sync-update
```

### 7.4 Git Hook Integration

`beadloom install-hooks` adds a pre-commit hook:

```bash
#!/bin/sh
# .git/hooks/pre-commit (managed by beadloom)
stale=$(beadloom sync-check --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Warning: stale documentation detected"
  echo "$stale"
  echo ""
  echo "Run: beadloom sync-update <ref_id> to update docs"
  # In block mode -- abort the commit
  # exit 1
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi
```

Configuration via `.beadloom/config.yml`:

```yaml
sync:
  hook_mode: warn    # warn | block | off
  ignore_paths:
    - "docs/_imported/**"
    - "*.test.*"
```

With `hook_mode: block`, the script includes `exit 1` -- the commit is blocked when stale docs are present.

## 8. MCP Server

### 8.1 Configuration

`.mcp.json` (in project root):

```json
{
  "mcpServers": {
    "beadloom": {
      "command": "beadloom",
      "args": ["mcp-serve"]
    }
  }
}
```

Transport: stdio (standard for local MCP servers).

### 8.2 Tools

**`get_context`**

```json
{
  "name": "get_context",
  "description": "Get a compact context bundle for a feature/domain/service/entity by ref_id. Returns graph, relevant documentation chunks, and code symbols. Includes sync status and stale index warnings.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ref_id":     { "type": "string", "description": "Node identifier (e.g. PROJ-123, routing, api-routing)" },
      "depth":      { "type": "integer", "default": 2, "description": "Graph traversal depth" },
      "max_nodes":  { "type": "integer", "default": 20, "description": "Max nodes in subgraph" },
      "max_chunks": { "type": "integer", "default": 10, "description": "Max text chunks in bundle" }
    },
    "required": ["ref_id"]
  }
}
```

**`get_graph`**

```json
{
  "name": "get_graph",
  "description": "Get a subgraph around a node. Returns nodes and edges as JSON.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ref_id": { "type": "string" },
      "depth":  { "type": "integer", "default": 2 }
    },
    "required": ["ref_id"]
  }
}
```

**`sync_check`**

```json
{
  "name": "sync_check",
  "description": "Check if documentation is up-to-date with code. Returns list of stale docs with changed code paths.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ref_id": { "type": "string", "description": "Check specific node. Omit for full project check." }
    }
  }
}
```

**`list_nodes`**

```json
{
  "name": "list_nodes",
  "description": "List all graph nodes, optionally filtered by kind. Returns ref_id, kind, and summary for each node.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "kind": { "type": "string", "enum": ["domain","feature","service","entity","adr"] }
    }
  }
}
```

**`get_status`**

```json
{
  "name": "get_status",
  "description": "Get project documentation coverage and index status. Returns coverage percentages per domain/service and stale doc count.",
  "inputSchema": { "type": "object", "properties": {} }
}
```

### 8.3 L1 Cache (In-Memory)

The MCP server is a long-lived process. During one session, an agent may call `get_context("PROJ-123")` multiple times (planning, coding, review). Without cache, each call returns the full bundle (~1000-3000 tokens). With cache, a repeated call returns ~20 tokens.

**Cache structure:**

```python
CacheKey = tuple[str, int, int, int]  # (ref_id, depth, max_nodes, max_chunks)

@dataclass
class CacheEntry:
    bundle: dict          # full context bundle
    created_at: float     # creation time
    graph_mtime: float    # mtime of _graph/*.yml files at assembly time
    docs_mtime: float     # max mtime of docs/ files at assembly time
    etag: str             # SHA256(bundle_json)
```

**Logic:**

1. Agent calls `get_context(ref_id="PROJ-123", depth=2, max_nodes=20, max_chunks=10)`.
2. MCP server forms key `("PROJ-123", 2, 20, 10)` and checks `cache.get(key)`.
3. If an entry exists -- checks mtime of `_graph/*.yml` files and related documents:
   - mtime unchanged -> returns short response:
     ```json
     {
       "cached": true,
       "etag": "abc123",
       "unchanged_since": "2025-01-15T10:30:00Z",
       "hint": "Context unchanged. Use previous bundle."
     }
     ```
   - mtime changed -> invalidates the entry, reassembles the bundle.
4. If no entry -- assembles the bundle, saves to cache.

**Invalidation:**

- By file mtime (cheap check, no hashing).
- On `reindex` call (via checking `meta.last_reindex_at`) -- full cache flush.
- TTL is not used -- mtime is sufficient.

**Token savings (example):**

| Scenario | Without cache | With cache |
|----------|---------------|------------|
| 3 calls to `get_context("PROJ-123")` per session | ~6000 tokens | ~2040 tokens |
| 5 different `ref_id`s, each twice | ~20000 tokens | ~10100 tokens |

The cache is a `dict[CacheKey, CacheEntry]` in process memory. Size is limited by the number of unique parameter combinations per session (typically <100). No need for LRU/eviction.

**Multi-ref_id requests:** CLI `beadloom ctx` supports multiple `ref_id`s, but MCP tool `get_context` accepts a single `ref_id` (agent calls multiple times). Cache works only for single-ref_id calls via MCP.

### 8.4 `setup-mcp` Command

```
$ beadloom setup-mcp
```

Automatically creates or updates `.mcp.json` in the project root:

- if the file does not exist -- creates it with Beadloom configuration;
- if the file exists -- adds a `beadloom` section to existing servers without touching the rest;
- determines the path to `beadloom` in `$PATH` and substitutes an absolute path if needed;
- outputs confirmation:

```
Created .mcp.json with beadloom MCP server config.
Claude Code will auto-detect it on next session.
```

Flag support:
- `--global` -- write to `~/.claude/mcp.json` (for all projects);
- `--remove` -- remove Beadloom configuration from `.mcp.json`.

## 9. Installation and Setup

### 9.1 Installation

**Recommended method (uv):**

```bash
# uv manages Python versions and isolated environments automatically
uv tool install beadloom
```

Or run without installing:

```bash
uvx beadloom init --bootstrap
```

**Alternative methods:**

```bash
# pipx (isolated installation)
pipx install beadloom

# pip (into active environment)
pip install beadloom
```

**Install script (for automation):**

```bash
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
```

The script checks for `uv` -> `pipx` -> `pip` and uses the first available.

### 9.2 Quick Start (Full Flow)

```bash
# 1. Installation (one-time)
uv tool install beadloom

# 2. Project initialization (one-time)
cd your-project
beadloom init --bootstrap       # auto-generate graph and documentation

# 3. Review the generated graph
$EDITOR .beadloom/_graph/*.yml  # fix what's needed

# 4. Build the index
beadloom reindex

# 5. Verify
beadloom doctor                 # integrity validation
beadloom status                 # project coverage

# 6. Connect to agents (one-time)
beadloom setup-mcp              # creates .mcp.json

# 7. Optional: git hooks
beadloom install-hooks          # pre-commit sync-check

# Done. Agent can call get_context() via MCP.
```

### 9.3 Requirements

- Python 3.10+ (if via uv -- managed automatically).
- Git (for determining project root and file hashes).
- No other system dependencies.
- LLM API key -- only for `sync-update --auto` (optional).

## 10. CLI: Full Reference

| Command | Description |
|---------|-------------|
| `beadloom help [command]` | Help for all commands or a specific command |
| `beadloom version` | Beadloom version and environment information |
| `beadloom init` | Interactive project initialization |
| `beadloom init --bootstrap` | Auto-generate graph and documentation from codebase |
| `beadloom init --import <path>` | Import and classify existing documentation |
| `beadloom init --scope <path>` | Bootstrap for a specific scope (domain/service) |
| `beadloom reindex` | Full rebuild of SQLite from Git -- drop + re-create (incremental -- phase 4) |
| `beadloom ctx <ref_id> [<ref_id>...]` | Get context bundle (default: Markdown, human-readable) |
| `beadloom ctx <ref_id> --json` | Get context bundle (JSON for agents) |
| `beadloom ctx <ref_id> --markdown` | Get context bundle (Markdown, explicit) |
| `beadloom ctx <ref_id> --depth N` | Graph traversal depth (default 2) |
| `beadloom ctx <ref_id> --max-nodes N` | Maximum nodes in subgraph (default 20) |
| `beadloom ctx <ref_id> --max-chunks N` | Maximum text chunks (default 10) |
| `beadloom graph <ref_id>` | Show subgraph (Mermaid by default) |
| `beadloom graph <ref_id> --json` | Subgraph in JSON format |
| `beadloom graph <ref_id> --depth N` | Traversal depth (default 2) |
| `beadloom sync-check` | Check freshness of all documentation |
| `beadloom sync-check --ref <ref_id>` | Check specific node |
| `beadloom sync-check --porcelain` | Machine-readable output (TAB-separated) |
| `beadloom sync-update <ref_id>` | Update documentation (interactively) |
| `beadloom sync-update <ref_id> --auto` | Update documentation (via LLM) |
| `beadloom status` | Project coverage and index status |
| `beadloom doctor` | Integrity validation (broken ref_ids, duplicates, empty summaries) |
| `beadloom install-hooks` | Install git pre-commit hook |
| `beadloom setup-mcp` | Create/update `.mcp.json` for agents |
| `beadloom setup-mcp --global` | Write MCP configuration globally (`~/.claude/mcp.json`) |
| `beadloom setup-mcp --remove` | Remove Beadloom configuration from `.mcp.json` |
| `beadloom mcp-serve` | Launch MCP server (stdio, called automatically) |

**Global flags:**

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Verbose output |
| `--quiet` / `-q` | Minimal output (errors only) |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error |
| `2` | Stale documents found (`sync-check`) |

## 11. Configuration

**`.beadloom/config.yml`:**

```yaml
# Configuration version
version: 1

# Languages to parse during bootstrap/reindex
languages:
  - python
  - typescript
  - go

# Paths to scan (default: entire repo)
scan_paths:
  - src/
  - services/
  - lib/

# Paths to ignore
ignore_paths:
  - node_modules/
  - vendor/
  - "*.test.*"
  - "*.spec.*"

# Documentation settings
docs:
  root: docs/                # Documentation root directory
  graph: .beadloom/_graph/   # YAML graph directory

# Sync settings
sync:
  hook_mode: warn      # warn | block | off
  ignore_paths:
    - "docs/_imported/**"

# Context builder settings
context:
  default_depth: 2
  max_nodes: 20
  max_chunks: 10
  max_chunk_size: 2000   # characters
  chunk_sections_priority:
    - spec
    - invariants
    - constraints
    - api
    - tests

# LLM for sync-update --auto (optional)
# Without this section, --auto is unavailable
# llm:
#   provider: anthropic       # anthropic | openai | ollama
#   model: claude-sonnet-4-20250514
#   api_key_env: ANTHROPIC_API_KEY
```

**Configuration creation:**
- `beadloom init` creates `config.yml` with default values.
- Languages and scan_paths are auto-detected from the project structure.
- The `llm` section is commented out by default.

## 12. Phased Implementation

### Phase 0 -- Onboarding

Without data, other phases are meaningless.

- Project structure parsing (tree-sitter).
- Clustering and YAML graph generation.
- Stub documentation generation.
- Import and classification of existing documents (two modes: restructure/map).
- Interactive `init` mode and merge on repeated runs.
- Automatic `.gitignore` management.
- `beadloom init`, `beadloom status`.

### Phase 1 -- Context Oracle

Core value: instant context at 0 search tokens.

- SQLite schema (WAL mode, `ref_id` as PK) and indexer (`beadloom reindex`).
- YAML to SQLite mapping with validation.
- Document chunking strategy (H2, 2000 characters, section classification).
- Deterministic context builder (BFS on graph).
- `beadloom ctx` (with `--depth`, `--max-chunks`, multiple ref_ids), `beadloom graph` (mermaid / json).
- `beadloom doctor`, `beadloom help`, `beadloom version`.

### Phase 2 -- MCP Server

Native agent integration.

- MCP server (stdio transport).
- Tools: `get_context`, `get_graph`, `sync_check`, `list_nodes`, `get_status`.
- L1 cache (in-memory) for saving tokens on repeated requests.
- Stale index detection (warning in response).
- `beadloom setup-mcp` -- auto-configuration of `.mcp.json`.

### Phase 3 -- Doc Sync Engine

Killer feature: documentation doesn't become stale.

- `sync_state` table, hash tracking.
- `beadloom sync-check` (+ `--porcelain`, exit code 2).
- `beadloom sync-update` (interactive + `--auto` with LLM).
- Git pre-commit hook (`beadloom install-hooks`).
- `llm` section in configuration.

### Phase 4 -- Polish

Scaling and additional capabilities.

- Embeddings (sqlite-vss or external vector store) for fuzzy queries.
- Incremental re-indexing (only changed files).
- Bundle caching in SQLite.
- Auto-generation of summaries via LLM.
- Auto-reindex in MCP server.

## 13. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Onboarding generates junk (incorrect clustering) | `confidence` field + interactive review. Merge mode on repeated init |
| ref_id collisions between types | Global ref_id uniqueness + `doctor` checks naming conventions |
| SQLite at high volumes (>100K chunks) | WAL mode, indexes on key columns. Migration to external store in phase 4 |
| YAML graph becomes out-of-sync with code | `doctor` + `sync-check` + stale index detection in MCP |
| Tree-sitter doesn't support needed language | Fallback to regex-based directory parsing. `languages` configuration |
| MCP standard changes | MCP server is a thin wrapper over CLI logic. Easy to adapt |
| `--auto` depends on external LLM | Explicit optionality: commented out by default, error with instructions when config is missing |
| `init --import` restructure breaks links | "Map in place" mode as a safe alternative. Originals are not deleted on restructure |
| Concurrent CLI + MCP access to SQLite | WAL mode allows concurrent reads |

## 14. Decision

Adopt Beadloom v0 architecture:

- **CLI-first:** no daemon, direct SQLite access (WAL mode);
- **`ref_id` is globally unique:** simple edges, unambiguous SQL queries;
- **Context Oracle:** deterministic graph traversal producing a compact bundle;
- **Doc Sync Engine:** doc-to-code relationship tracking, staleness detection, LLM-based update (optional);
- **Onboarding:** bootstrap/import (restructure or map)/incremental, interactive init, merge on repeated runs;
- **MCP server:** native agent integration, L1 cache, stale index detection;
- **Clear exit codes, --porcelain, --verbose/--quiet:** for integration with scripts and git hooks;
- **Phased implementation:** Onboarding -> Context Oracle -> MCP -> Doc Sync -> Polish.
