# PLAN: BDL-001 — Beadloom v0

> **Date:** 2026-02-08
> **Beads:** 20
> **Critical path:** BEAD-01 → 02 → 03+04 → 06 → 07 → 08

---

## DAG Overview

```
Phase 0: Foundation
  BEAD-01: Project scaffolding + CLI skeleton ──┐
                                                 │
Phase 1: Context Oracle                          ▼
  BEAD-02: SQLite schema + DB layer ────────────┐
                      │                          │
          ┌───────────┼───────────┐              │
          ▼           ▼           ▼              │
  BEAD-03: YAML     BEAD-04:   BEAD-05:         │
  parser +          Doc         Code symbol      │
  graph loader      indexer     indexer (ts)      │
          │           │           │              │
          └─────┬─────┘           │              │
                ▼                 │              │
  BEAD-06: reindex cmd ──────────┘              │
                │                                │
          ┌─────┼──────────┐                     │
          ▼     ▼          ▼                     │
  BEAD-07:  BEAD-09:   BEAD-10:                  │
  Context   graph cmd  doctor cmd                │
  builder                                        │
          │                                      │
          ▼                                      │
  BEAD-08: ctx cmd                               │
          │                                      │
          ▼                                      │
  BEAD-11: status cmd                            │
                                                 │
Phase 2: MCP Server                              │
  BEAD-12: MCP server core ─────────────────────┘
          │
          ▼
  BEAD-13: L1 cache
          │
          ▼
  BEAD-14: mcp-serve + setup-mcp commands

Phase 3: Doc Sync Engine
  BEAD-15: sync_state management ───── (depends on BEAD-06)
          │
          ▼
  BEAD-16: sync-check cmd
          │
          ├──────────┐
          ▼           ▼
  BEAD-17:        BEAD-18:
  sync-update     install-hooks
  (interactive)
          │
          ▼
  BEAD-19: sync-update --auto (LLM)

Phase 0: Onboarding (requires tree-sitter from BEAD-05)
  BEAD-20: beadloom init (bootstrap + import + interactive)
```

---

## Beads Detail

### Phase 0 — Foundation

#### BEAD-01: Project scaffolding + CLI skeleton (P0)
- **Dependencies:** none
- **Tasks:**
  - pyproject.toml, src/beadloom/, tests/
  - Click CLI group with --version, --verbose, --quiet
  - ruff, mypy, pytest configs
  - conftest.py with basic fixtures
  - Test: `beadloom --version` prints the version
- **Files:** pyproject.toml, src/beadloom/__init__.py, cli.py, tests/conftest.py

### Phase 1 — Context Oracle

#### BEAD-02: SQLite schema + DB layer (P0)
- **Dependencies:** BEAD-01
- **Tasks:**
  - Module `db.py`: open_db(), create_schema(), get_meta(), set_meta()
  - All tables from RFC: nodes, edges, docs, chunks, code_symbols, sync_state, meta
  - PRAGMA journal_mode=WAL (on creation), foreign_keys=ON (each connection)
  - CHECK constraints on kind fields
  - ON DELETE CASCADE/SET NULL
  - All indexes
- **Acceptance:** Tests: DB creation, table verification, FK enforcement, WAL mode

#### BEAD-03: YAML parser + graph loader (P0)
- **Dependencies:** BEAD-02
- **Tasks:**
  - Module `graph_loader.py`: parse_graph_dir(), load_nodes(), load_edges()
  - Parsing `.beadloom/_graph/*.yml`
  - Validation: ref_id uniqueness, edge integrity (src/dst exist)
  - Mapping YAML → SQLite (nodes + edges + docs.ref_id)
  - Error/warning reporting
- **Acceptance:** Tests: parsing valid/invalid YAML, duplicate ref_id, broken edges

#### BEAD-04: Document indexer (P0)
- **Dependencies:** BEAD-02
- **Tasks:**
  - Module `doc_indexer.py`: index_docs(), chunk_markdown(), classify_section()
  - Scanning docs/ for .md files
  - Chunking by H2, 2000 character limit, splitting by paragraphs
  - Section classification: spec, invariants, api, tests, constraints, other
  - SHA256 file hashing
  - Populating docs + chunks
- **Acceptance:** Tests: chunking various .md files, heading classification, hashes

#### BEAD-05: Code symbol indexer (tree-sitter) (P1)
- **Dependencies:** BEAD-02
- **Tasks:**
  - Module `code_indexer.py`: index_code(), parse_annotations(), extract_symbols()
  - Parsing Python files via tree-sitter (other languages — later)
  - Extraction: functions, classes, types
  - Parsing beadloom annotations from comments
  - Populating code_symbols + edges (touches_code)
- **Acceptance:** Tests: symbol extraction from Python, annotation parsing

#### BEAD-06: `beadloom reindex` command (P0)
- **Dependencies:** BEAD-03, BEAD-04, BEAD-05
- **Tasks:**
  - CLI command `reindex`
  - Orchestration: drop all → create schema → load graph → index docs → index code
  - Updating meta (last_reindex_at, beadloom_version, schema_version)
  - Rich progress output
- **Acceptance:** Tests: full reindex on test project, meta verification

#### BEAD-07: Context builder (BFS) (P0)
- **Dependencies:** BEAD-06
- **Tasks:**
  - Module `context_builder.py`: build_context(), bfs_subgraph(), collect_chunks()
  - BFS from focus nodes with edge type prioritization
  - Parameters: depth, max_nodes, max_chunks
  - Chunk collection with section priority (spec > invariants > ...)
  - code_symbols collection
  - JSON context bundle assembly (format from RFC 4.5)
  - sync_state check + stale index warning
  - Levenshtein suggestion for unrecognized ref_id
- **Acceptance:** Tests: BFS on test graph, limits, priorities, bundle format

#### BEAD-08: `beadloom ctx` command (P0)
- **Dependencies:** BEAD-07
- **Tasks:**
  - CLI command `ctx`
  - Multiple ref_id support
  - --json / --markdown output
  - --depth, --max-nodes, --max-chunks flags
  - Rich-formatted Markdown output (default)
- **Acceptance:** Tests: CLI output in both formats, flags

#### BEAD-09: `beadloom graph` command (P1)
- **Dependencies:** BEAD-06
- **Tasks:**
  - CLI command `graph`
  - Mermaid output (default)
  - --json output
  - --depth flag
- **Acceptance:** Tests: Mermaid + JSON output on test graph

#### BEAD-10: `beadloom doctor` command (P1)
- **Dependencies:** BEAD-06
- **Tasks:**
  - Module `doctor.py`: run_checks()
  - Checks: broken ref_id, duplicates, empty summary, orphaned edges
  - Confidence warnings
  - Missing documentation files
  - Rich output grouped by severity
- **Acceptance:** Tests: each check on specially constructed data

#### BEAD-11: `beadloom status` command (P1)
- **Dependencies:** BEAD-06
- **Tasks:**
  - CLI command `status`
  - Coverage per domain/service (% coverage)
  - Stale docs count
  - Overall statistics
  - Rich progress bars
- **Acceptance:** Tests: coverage calculation on test data

### Phase 2 — MCP Server

#### BEAD-12: MCP server core (P1)
- **Dependencies:** BEAD-07
- **Tasks:**
  - Module `mcp_server.py`: creating MCP server, registering tools
  - Tools: get_context, get_graph, list_nodes, get_status, sync_check
  - stdio transport
  - Error handling
  - Stale index detection in responses
- **Acceptance:** Tests: invoking each tool, error cases

#### BEAD-13: L1 cache (P1)
- **Dependencies:** BEAD-12
- **Tasks:**
  - CacheKey = (ref_id, depth, max_nodes, max_chunks)
  - CacheEntry with mtime, etag
  - Invalidation by mtime
  - Full reset on reindex
  - Cached response format
- **Acceptance:** Tests: cache hit/miss, invalidation by mtime, full reset

#### BEAD-14: `mcp-serve` + `setup-mcp` commands (P2)
- **Dependencies:** BEAD-12, BEAD-13
- **Tasks:**
  - CLI `mcp-serve`: launch MCP server (stdio)
  - CLI `setup-mcp`: create/update .mcp.json
  - --global, --remove flags
  - Determining the absolute path to beadloom
- **Acceptance:** Tests: .mcp.json generation, --global, --remove

### Phase 3 — Doc Sync Engine

#### BEAD-15: sync_state management (P1)
- **Dependencies:** BEAD-06
- **Tasks:**
  - Module `sync_engine.py`: build_sync_state(), check_sync(), update_sync()
  - Populating sync_state during reindex (doc↔code pairs via shared ref_id)
  - Hash comparison: current vs stored
  - Status update (ok/stale)
- **Acceptance:** Tests: stale detection on code change

#### BEAD-16: `beadloom sync-check` command (P1)
- **Dependencies:** BEAD-15
- **Tasks:**
  - CLI command `sync-check`
  - Human-readable output (Rich)
  - --porcelain (TAB-separated)
  - --ref filter
  - Exit codes: 0 (ok), 1 (error), 2 (stale found)
- **Acceptance:** Tests: both output formats, exit codes

#### BEAD-17: `beadloom sync-update` (interactive) (P2)
- **Dependencies:** BEAD-16
- **Tasks:**
  - CLI command `sync-update`
  - Showing code diff since last sync
  - Opening document in $EDITOR
  - Updating hashes in sync_state after save
- **Acceptance:** Tests: hash update flow

#### BEAD-18: `beadloom install-hooks` (P2)
- **Dependencies:** BEAD-16
- **Tasks:**
  - CLI command `install-hooks`
  - Generating pre-commit hook script
  - hook_mode from config.yml (warn/block/off)
- **Acceptance:** Tests: hook file generation, modes

#### BEAD-19: `beadloom sync-update --auto` (P3)
- **Dependencies:** BEAD-17
- **Tasks:**
  - LLM integration (anthropic/openai/ollama)
  - Parsing llm section from config.yml
  - Collecting context bundle + code diff → LLM prompt
  - Showing proposed changes for confirmation
  - Error when LLM config is missing
- **Acceptance:** Tests: error without config, mock LLM call

### Phase 0 — Onboarding

#### BEAD-20: `beadloom init` (bootstrap + import + interactive) (P1)
- **Dependencies:** BEAD-05, BEAD-06
- **Tasks:**
  - Module `onboarding.py`
  - Interactive mode (3 options)
  - Re-init detection (re-bootstrap/merge/cancel)
  - Bootstrap: scan → tree-sitter → cluster → generate YAML + stub docs
  - Import: classify docs → restructure/map-in-place
  - Scope mode
  - Config creation (.beadloom/config.yml)
  - .gitignore management
  - Interactive report
- **Acceptance:** Tests: each mode on test project

---

## Waves (parallel work)

### Wave 1: Foundation (P0)
- **BEAD-01:** Project scaffolding

### Wave 2: DB + Parsers (P0)
- **BEAD-02:** SQLite schema

### Wave 3: Loaders (P0, parallel)
- **BEAD-03:** YAML parser (→ BEAD-02)
- **BEAD-04:** Doc indexer (→ BEAD-02)
- **BEAD-05:** Code indexer (→ BEAD-02)

### Wave 4: Reindex (P0)
- **BEAD-06:** reindex command (→ BEAD-03, 04, 05)

### Wave 5: Core + Satellite (P0/P1, parallel)
- **BEAD-07:** Context builder (→ BEAD-06) — P0, critical path
- **BEAD-09:** graph cmd (→ BEAD-06) — P1
- **BEAD-10:** doctor cmd (→ BEAD-06) — P1
- **BEAD-15:** sync_state (→ BEAD-06) — P1

### Wave 6: CLI + MCP (P0/P1, parallel)
- **BEAD-08:** ctx cmd (→ BEAD-07) — P0, critical path
- **BEAD-11:** status cmd (→ BEAD-06) — P1
- **BEAD-12:** MCP server core (→ BEAD-07) — P1
- **BEAD-16:** sync-check cmd (→ BEAD-15) — P1

### Wave 7: Integration (P1/P2)
- **BEAD-13:** L1 cache (→ BEAD-12)
- **BEAD-17:** sync-update interactive (→ BEAD-16)
- **BEAD-18:** install-hooks (→ BEAD-16)
- **BEAD-20:** beadloom init (→ BEAD-05, 06)

### Wave 8: Final (P2/P3)
- **BEAD-14:** mcp-serve + setup-mcp (→ BEAD-12, 13)
- **BEAD-19:** sync-update --auto (→ BEAD-17)

---

## Priorities

| Priority | Beads | Description |
|----------|-------|----------|
| **P0** | 01, 02, 03, 04, 06, 07, 08 | Critical path: scaffolding → oracle |
| **P1** | 05, 09, 10, 11, 12, 13, 15, 16, 20 | High: satellite commands + MCP + onboarding |
| **P2** | 14, 17, 18 | Medium: setup-mcp, sync-update, hooks |
| **P3** | 19 | Low: LLM sync-update |
