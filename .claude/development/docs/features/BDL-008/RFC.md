# RFC: BDL-008 — Eat Your Own Dogfood: DDD Code, Docs & Knowledge Graph

> **Status:** Approved
> **Epic:** BDL-008
> **Depends on:** PRD (Approved)

---

## 1. Overview

Three parallel workstreams that transform the Beadloom repository into a showcase of its own product:

| # | Workstream | Risk | Parallelizable? |
|---|-----------|------|-----------------|
| W1 | Code → DDD packages | High (breaks imports) | No — must be first |
| W2 | Docs → domain-first | Low (content only) | Yes — after W1 |
| W3 | Self-bootstrap graph | Low (additive) | Yes — after W1 |

**Critical constraint:** W1 (code restructuring) changes import paths. W2 and W3 depend on W1 being complete because docs and graph nodes reference module paths.

---

## 2. W1: Code Restructuring

### 2.1 Dependency analysis

Current import graph (→ means "imports from"):

```
Self-contained (no internal imports):
  code_indexer, db, diff, doc_indexer, doctor, graph_loader,
  health, presets, rule_engine, search, sync_engine, watcher

One dependency:
  cache → db
  context_builder → db
  onboarding → presets
  why → context_builder

Multiple dependencies:
  reindex → db, code_indexer, doc_indexer, graph_loader, health
  linter → db, reindex, rule_engine
  import_resolver → code_indexer, reindex
  mcp_server → cache, context_builder, db, graph_loader, reindex, sync_engine
  cli → reindex, context_builder, db, doctor, health, sync_engine,
        search, mcp_server, why, diff, onboarding, linter, tui
```

**Key insight:** 12 out of 23 modules are self-contained. This makes incremental migration safe.

### 2.2 Target package layout

```
src/beadloom/
├── __init__.py                     # version only
│
├── context/                        # domain: context-oracle
│   ├── __init__.py                 # re-exports: build_context, bfs_subgraph, suggest_ref_id
│   ├── builder.py                  # ← context_builder.py
│   ├── code_indexer.py             # ← code_indexer.py (self-contained)
│   ├── cache.py                    # ← cache.py
│   └── search.py                   # ← search.py (self-contained)
│
├── graph/                          # domain: graph
│   ├── __init__.py                 # re-exports: load_graph, parse_graph_file
│   ├── loader.py                   # ← graph_loader.py (self-contained)
│   ├── diff.py                     # ← diff.py (self-contained)
│   ├── rule_engine.py              # ← rule_engine.py (self-contained)
│   ├── import_resolver.py          # ← import_resolver.py
│   └── linter.py                   # ← linter.py
│
├── sync/                           # domain: doc-sync
│   ├── __init__.py                 # re-exports: check_sync, build_sync_state
│   ├── engine.py                   # ← sync_engine.py (self-contained)
│   └── doc_indexer.py              # ← doc_indexer.py (self-contained)
│
├── onboarding/                     # domain: onboarding
│   ├── __init__.py                 # re-exports: bootstrap_project, import_docs
│   ├── scanner.py                  # ← onboarding.py
│   └── presets.py                  # ← presets.py (self-contained)
│
├── infra/                          # shared infrastructure
│   ├── __init__.py                 # re-exports: open_db, create_schema
│   ├── db.py                       # ← db.py (self-contained, most depended on)
│   ├── health.py                   # ← health.py (self-contained)
│   └── reindex.py                  # ← reindex.py (orchestrator)
│
├── cli.py                          # service: CLI entry point
├── mcp_server.py                   # service: MCP server
├── doctor.py                       # service: diagnostics (self-contained)
├── why.py                          # service: impact analysis
├── watcher.py                      # service: file watcher (self-contained)
└── tui/                            # service: TUI (unchanged)
    ├── app.py
    └── widgets/
```

### 2.3 Migration strategy — one domain at a time

Each domain migration follows the same pattern:

```
1. Create package directory + __init__.py
2. Move files (git mv to preserve history)
3. Update internal imports in moved files
4. Update imports in all dependents
5. Update test imports
6. Run: pytest + mypy + ruff
7. Commit
```

**Order matters** — migrate from leaves to roots:

| Phase | Package | Modules | Dependents to update |
|-------|---------|---------|---------------------|
| 1 | `infra/` | db, health | reindex, context_builder, cache, linter, mcp_server, cli |
| 2 | `context/` | code_indexer, cache, search, context_builder | reindex, import_resolver, mcp_server, cli, why |
| 3 | `sync/` | sync_engine, doc_indexer | reindex, mcp_server, cli |
| 4 | `onboarding/` | onboarding, presets | cli |
| 5 | `graph/` | graph_loader, diff, rule_engine, import_resolver, linter | reindex, mcp_server, cli |
| 6 | `infra/reindex` | reindex | linter, import_resolver, mcp_server, cli |
| 7 | Update services | cli, mcp_server, why, doctor, watcher | tests only |

### 2.4 Entry point

`pyproject.toml` currently has:
```toml
[project.scripts]
beadloom = "beadloom.cli:main"
```

`cli.py` stays at the top level → **entry point unchanged**.

### 2.5 `__init__.py` convention

Each domain package `__init__.py` re-exports the public API:

```python
"""Context Oracle domain — BFS traversal and context bundle assembly."""

from beadloom.context.builder import bfs_subgraph, build_context, suggest_ref_id
from beadloom.context.cache import ContextCache, SqliteCache, compute_etag
from beadloom.context.code_indexer import extract_symbols, get_lang_config
from beadloom.context.search import has_fts5, search_fts5

__all__ = [
    "bfs_subgraph", "build_context", "suggest_ref_id",
    "ContextCache", "SqliteCache", "compute_etag",
    "extract_symbols", "get_lang_config",
    "has_fts5", "search_fts5",
]
```

Consumers can import via either path:
- `from beadloom.context import build_context` (preferred)
- `from beadloom.context.builder import build_context` (also valid)

### 2.6 Test impact

Tests use `from beadloom.<module> import ...` pattern. Every test file that imports a moved module needs updating. Based on the 37 test files, estimate ~25 files affected.

Strategy: after each domain migration, run `ruff check` to catch import errors, then fix systematically.

---

## 3. W2: Documentation Restructuring

### 3.1 Content migration map

| Current file | Target location | Action |
|-------------|----------------|--------|
| `architecture.md` | `architecture.md` | **Rewrite** — expand from 3 to 14+ domains, add diagrams |
| `getting-started.md` | `getting-started.md` | **Update** — fix examples, mention new commands |
| `context-oracle.md` | `domains/context-oracle/README.md` | **Move + expand** — add cache, search sections |
| `graph-format.md` | `domains/graph/README.md` | **Move + expand** — add rules, diff sections |
| `sync-engine.md` | `domains/doc-sync/README.md` | **Move** — content is current |
| `cli-reference.md` | `services/cli.md` | **Rewrite** — add 6 missing commands |
| `mcp-server.md` | `services/mcp.md` | **Rewrite** — add 2 tools, cache, auto-reindex |
| `ci-setup.md` | `guides/ci-setup.md` | **Update** — lint integration |

### 3.2 New content to create

| File | Content source |
|------|---------------|
| `domains/context-oracle/search.md` | From code: `search.py`, FTS5 internals |
| `domains/context-oracle/impact-analysis.md` | From code: `why.py`, bidirectional BFS |
| `domains/graph/diff.md` | From code: `diff.py`, git ref comparison |
| `domains/graph/rules.md` | From code: `rule_engine.py`, `linter.py` |
| `domains/onboarding/README.md` | From code: `onboarding.py`, `presets.py` |
| `domains/infrastructure/README.md` | From code: `db.py`, `health.py`, `reindex.py` |
| `services/tui.md` | From code: `tui/app.py` |

### 3.3 README updates

Both `README.md` and `README.ru.md` need:
1. Updated "Documentation structure" block to show domain-first layout
2. Updated "Docs" table with new file paths
3. Updated feature counts (18 CLI commands, 7+ MCP tools)

---

## 4. W3: Self-Bootstrap

### 4.1 Current state

`.beadloom/_graph/services.yml` already has 11 nodes but is outdated:
- Says "5 MCP tools" → actually 7+
- Says "12 CLI commands" → actually 18
- Missing domains: search, impact-analysis (why), watcher, import-resolver, linter (partially present)

`.beadloom/_graph/rules.yml` has 1 rule (`domain-needs-parent`).

### 4.2 Target state

After code restructuring (W1), the graph should reflect the new package layout:

**Nodes (~20):**

| ref_id | kind | maps to |
|--------|------|---------|
| `beadloom` | service | Root — the CLI + MCP product |
| `context-oracle` | domain | `src/beadloom/context/` |
| `doc-sync` | domain | `src/beadloom/sync/` |
| `graph` | domain | `src/beadloom/graph/` |
| `onboarding` | domain | `src/beadloom/onboarding/` |
| `infrastructure` | domain | `src/beadloom/infra/` |
| `cli` | service | `src/beadloom/cli.py` |
| `mcp-server` | service | `src/beadloom/mcp_server.py` |
| `tui` | service | `src/beadloom/tui/` |
| `doctor` | service | `src/beadloom/doctor.py` |
| `why` | feature | `src/beadloom/why.py` |
| `watcher` | service | `src/beadloom/watcher.py` |
| `search` | feature | `src/beadloom/context/search.py` |
| `graph-diff` | feature | `src/beadloom/graph/diff.py` |
| `rule-engine` | feature | `src/beadloom/graph/rule_engine.py` |
| `import-resolver` | feature | `src/beadloom/graph/import_resolver.py` |
| `cache` | feature | `src/beadloom/context/cache.py` |
| `reindex` | feature | `src/beadloom/infra/reindex.py` |

**Edges:**
- `part_of`: domains → beadloom, features → domains
- `uses`: cli → all domains, mcp-server → context-oracle/doc-sync/graph/infrastructure
- `depends_on`: auto-generated from import analysis

**Doc bindings:** Each domain node links to its `docs/domains/<name>/README.md`.

### 4.3 Config update

`.beadloom/config.yml` should reflect new structure:
```yaml
languages:
  - .py
scan_paths:
  - src
sync:
  hook_mode: warn
```

No changes needed — scan_paths already covers the restructured code.

### 4.4 Validation targets

After bootstrap:
```bash
beadloom reindex       # builds index
beadloom doctor        # 0 errors
beadloom sync-check    # 0 stale
beadloom lint          # 0 violations
beadloom ctx context-oracle  # returns valid bundle
beadloom why context-oracle  # shows impact
```

---

## 5. Technical Decisions

### D1: No backward-compatible re-exports from old paths

Old `from beadloom.context_builder import ...` paths will break. This is intentional:
- Beadloom has no published API (internal tool)
- All consumers are within the repo (cli, mcp_server, tests)
- Stale re-exports create maintenance burden

### D2: Services stay at top level

`cli.py`, `mcp_server.py`, `doctor.py`, `why.py`, `watcher.py` stay at `src/beadloom/` (not inside domain packages) because:
- They are entry points / orchestrators, not domain logic
- `cli.py` is the pyproject.toml entry point
- They depend on multiple domains (fan-in pattern)

### D3: git mv for history preservation

Use `git mv` instead of creating new files. This preserves blame/log history.

### D4: Incremental commits

One commit per domain migration. If anything breaks, easy to bisect and revert.

### D5: Documentation is English-only in domain docs

`docs/` content is in English. `README.ru.md` links to the same docs (English).

---

## 6. Execution order

```
Phase 1: Code restructuring (W1) — sequential, one domain at a time
  1a. infra/ (db, health)
  1b. context/ (code_indexer, cache, search, context_builder)
  1c. sync/ (sync_engine, doc_indexer)
  1d. onboarding/ (onboarding, presets)
  1e. graph/ (graph_loader, diff, rule_engine, import_resolver, linter)
  1f. infra/reindex (depends on 1a-1e being done)
  1g. Update services (cli, mcp_server, why) — final import fixup
  1h. Update all tests
  1i. Final validation: pytest + mypy + ruff

Phase 2: Parallel after W1 complete
  2a. Docs restructuring (W2) — can be parallelized per domain
  2b. Self-bootstrap (W3) — can run alongside 2a

Phase 3: Final validation
  3a. beadloom reindex + doctor + sync-check + lint
  3b. Update README.md + README.ru.md
  3c. CHANGELOG entry
```

---

## 7. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular imports after restructuring | Build fails | Dependency graph is acyclic; verified above |
| mypy can't resolve new paths | Type check fails | Update mypy config if needed; test after each step |
| tree-sitter query paths break | Code indexer fails | `code_indexer.py` is self-contained; paths are relative |
| Test fixtures reference old paths | Test failures | Systematic grep + replace after each migration |
| `.beadloom/_graph/` references stale paths | Graph invalid | W3 runs after W1; graph is rebuilt from scratch |
