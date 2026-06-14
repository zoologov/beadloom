<!-- beadloom:badge-start -->
> 📘 **reference** — overview/guide, not tied to a code symbol
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Beadloom Architecture

> 📘 **reference** — overview/deep-dive, not tied to a single code symbol. It aligns with (does not replace) the generated [`/architecture` C4 overview](../services/cli.md#beadloom-docs-site) on the published portal.

Beadloom turns Architecture as Code into Architectural Intelligence — structured, queryable knowledge about your system that humans and AI agents consume in <20ms.

## System Design

The system is organized into seven DDD domain packages, an application (use-case orchestration) layer, and two interface layers:

**Domains:**
1. **Context Oracle** (`context_oracle/`) — BFS graph traversal, context bundle assembly, code indexing, two-tier caching, FTS5 search, `why` impact analysis
2. **Doc Sync** (`doc_sync/`) — doc↔code synchronization tracking, stale detection, symbol-level hashing, docs audit
3. **Graph** (`graph/`) — YAML graph loader, diff engine, rule engine, import resolver (9 languages), architecture linter, C4 diagram emitter, federation
4. **Onboarding** (`onboarding/`) — project bootstrap, doc generation/polishing, architecture-aware presets, AGENTS.md / IDE-rules generation, config sync, and the **agentic-flow role configurator** (`flow_config.py`, `role_composer.py`, `role_adapters.py`)
5. **Infrastructure** (`infrastructure/`) — domain-agnostic SQLite database layer, health metrics, git-activity tracking
6. **AI Agents** (`ai_agents/`) — governed AI-agent harnesses that ship inside the wheel; hosts the deterministic, seam-isolated **AI tech-writer** (`ai_agents/ai_techwriter/`, run via `python -m beadloom.ai_agents.ai_techwriter`). A **leaf consumer**: it may read `application`/`context_oracle`/`graph`/`doc_sync` APIs but must never be imported by the core domains or services (enforced by the `core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import` rules).

**Application (use-case orchestration)** (`application/`) — composes the domains into end-to-end use cases. It owns:
- `reindex.py` — the full + incremental reindex pipeline (drop → recreate → reload graph/docs/code/sync; SHA-256 `file_index` for incremental runs)
- `doctor.py` — graph + data integrity checks
- `debt_report.py` — architecture-debt aggregation, scoring, trend tracking, CI gating
- `watcher.py` — file watcher for auto-reindex on change
- `gate.py` — the unified `beadloom ci` gate (reindex → lint → sync-check → config-check → doctor → optional federate)
- the VitePress site generators — `site.py` (orchestrator), `site_pages.py`, `site_nav.py`, `site_about.py`, `site_dashboard.py`, `site_landscape.py`, `site_published.py`, `site_mermaid_guard.py`, `site_metrics_history.py`

**Interface layers:**
- **Services** (`services/`) — **CLI** (`services/cli.py`, Click-based) and **MCP Server** (`services/mcp_server.py`, stdio server with 18 tools for AI agents — 14 graph read/write tools + four BDL-048 process-tools). Both call into the application layer and Context Oracle; the CLI never reaches past those layers.
- **TUI** (`tui/`) — interactive terminal architecture workstation (Textual): dashboard, explorer, doc-status screens.

A `layers` rule in `.beadloom/_graph/rules.yml` enforces the direction `services / tui → application → domains` (the interface layers depend inward; domains never depend on the application or service layers).

### Node Kinds

The graph distinguishes the kinds of node it tracks:

| Kind | Doc | Annotation | Description |
|------|-----|------------|-------------|
| `service` | `services/<name>.md` | `# beadloom:service=<id>` | An interface/process boundary (CLI, MCP server, TUI) |
| `domain` | `domains/<name>/README.md` | `# beadloom:domain=<id>` | A DDD domain package |
| `feature` | `features/<name>/SPEC.md` | `# beadloom:feature=<id>` | A user-facing capability inside a domain |
| `component` | `<name>/DOC.md` | `# beadloom:component=<id>` | An internal/infra building block — the mirror of a `feature` for code that is not user-facing |
| `entity` / `adr` | — | — | Domain entities and architecture decisions |

The **`component` kind** (BDL-051) and the **`module-coverage` lint** (promoted to `severity: error`) together close the no-shadow-code gap: every `src` module with at least one symbol must be a tracked node (`feature` or `component`, or covered by a node's `source` — including a **directory** source like `tui/`) or named on a small, visible `exempt:` list in `rules.yml`. A new untracked module therefore fails `beadloom lint --strict` / `beadloom ci`.

---

## Specification

### Data Flow

The `application/reindex.py` orchestrator drives the indexing pipeline, calling
each domain in order; the resulting SQLite index is then read back by Context
Oracle for sub-20ms context bundles.

```
YAML Graph Files (.beadloom/_graph/*.yml)
       ↓
   application/reindex.py  (orchestrates the pipeline below)
       │
       ├─ graph/loader.py            → SQLite (nodes, edges, rules)
       ├─ graph/import_resolver.py   → SQLite (code_imports)
       ├─ doc_sync/doc_indexer.py    → SQLite (docs, chunks, search_index)
       ├─ context_oracle/code_indexer.py → SQLite (code_symbols)
       └─ (writes file_index, health_snapshots)
       ↓
   context_oracle/builder.py ← BFS traversal → context bundle (JSON)
       ↓                                       ↕ L1 memory / L2 SQLite cache
   services/cli.py / services/mcp_server.py / tui/ → user / AI agent
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

Architecture rules are defined in `.beadloom/_graph/rules.yml` (schema version 3) and enforce boundaries between graph nodes. The YAML key on each rule selects its type.

**Rule types** (7, parsed by `graph/rule_engine.py`, evaluated by `graph/linter.py`):

| YAML key | Semantics | Example |
|----------|-----------|---------|
| `deny` | Forbid `depends_on`/import relationships between matched nodes | `domain:* → service:*` — domains must not depend on services |
| `require` | Require edges from matched nodes to targets | Every `domain:*` must have a `part_of` edge to the `beadloom` service |
| `forbid` | Forbid specific edge patterns between tagged node groups | Nodes tagged `ui-layer` must not have `uses` edges to `native-layer` |
| `layers` | Enforce layered architecture direction | Top-down: services → domains → infrastructure |
| `forbid_cycles` | Detect circular dependencies in the graph | No cycles on `uses`/`depends_on` edges |
| `forbid_import` | Control file-level import boundaries | Files in `src/beadloom/tui/**` must not import from `src/beadloom/infrastructure/**` |
| `check` | Enforce complexity / coverage limits per node | `max_symbols: 200` per domain; `module-coverage` (every src module tracked) |

> Internally each parsed rule carries a `rule_type` string (`deny` / `require` / `forbid` / `layer` / `forbid_import` / `cardinality` / …) used by the evaluators; the **authoring key** in `rules.yml` is the column above.

**Evaluation:**
- `deny` rules are checked against the `code_imports` table: resolved import ref_ids are matched against rule patterns
- `require` rules are checked against the `edges` table: nodes matching the `for`/`from` pattern must have the specified edge kind to the target
- Node matchers support an optional `exclude` field (list of ref_ids) to exempt specific nodes from rule matching
- `unless_edge` exemptions allow otherwise-forbidden imports when a specific edge kind exists between the nodes
- `forbid` rules check edge patterns between nodes matching tag selectors
- `layers` rules verify dependency direction across ordered architectural layers
- `forbid_cycles` uses BFS/DFS to find circular dependency paths
- `forbid_import` rules query the `code_imports` table for forbidden cross-boundary imports
- `check` rules count symbols/files per node (cardinality) and verify module coverage; `module-coverage` is `severity: error`

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

### CI Gate

`application/gate.py` powers `beadloom ci` — the unified gate that composes the
existing checkers into one verdict with a single exit code: **reindex → `lint
--strict` → sync-check → config-check → doctor → (optional) federate landscape
gate**. Every step's honest result is printed (PASS / FAIL / SKIP) — never a
green that silently skipped a step. `--format rich|json|github` applies
uniformly; `--hub <export>` arms the cross-service landscape gate. The same gate
runs as the **pre-push Beadloom Gate** hook (`install-hooks --pre-push`) and in
CI (`.github/workflows/ci.yml`).

### Agentic Flow Configurator

The `onboarding` domain composes the packaged multi-agent dev flow from a
declaration in `.beadloom/flow.yml`:

```
.beadloom/flow.yml  ──load──▶  flow_config.py (FlowConfig: tools, architecture, stack, quality)
                                      │
                                      ▼
                              role_composer.py  compose_role(role, architecture=, stack=)
                                      │   = CORE protocol + ONE architecture overlay (ddd|fsd)
                                      │     + sorted stack overlays (byte-deterministic)
                                      ▼
                              role_adapters.py  generate_adapters(config, project_root)
                                      │
                          ┌───────────┴───────────┐
                          ▼                        ▼
                .claude/agents/* (Claude Code)   .cursor/agents/* (Cursor)
```

- **`flow_config.py`** — `FlowConfig` (frozen) + `resolve_flow_config` (flag → `flow.yml` → default) + `detect_stack`; strict validation. Supported: tools `claude`/`cursor`; architecture `ddd`/`fsd` (exactly one); stack `python`/`fastapi`/`javascript`/`typescript`/`vuejs`.
- **`role_composer.py`** — `compose_role(role, *, architecture, stack)` = CORE + one architecture overlay + sorted stack overlays; FSD at parity with DDD. Overlay templates live under `onboarding/templates/roles/{core,architecture/<arch>,stack/<stack>}/`.
- **`role_adapters.py`** — `generate_adapters(config, project_root)` writes the per-tool adapter set(s). `beadloom setup-agentic-flow --tool/--architecture/--stack` is the CLI entrypoint; `config-check`/`--fix` byte-guards each composed adapter against `compose_role(...)` and recomposes drift.

The AI tech-writer harness (`ai_agents/ai_techwriter/`) is the runtime half of
the flow: a PR-triggered, symbol-scoped, bounded-parallel doc-refresh harness —
see the `ai_agents` domain README + the `ai-techwriter` feature SPEC.

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
- Rules support 7 authoring keys: `deny`, `require`, `forbid`, `layers`, `forbid_cycles`, `forbid_import`, `check`
- `ai_agents` is a leaf consumer — never imported by core domains/services (`forbid_import` enforced)
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
