# PLAN: BDL-008 — Bead Decomposition & DAG

> **Epic:** BDL-008
> **Total beads:** 13
> **Critical path:** BEAD-01 → BEAD-02 → ... → BEAD-07 → BEAD-08..10 (parallel) → BEAD-11 → BEAD-12 → BEAD-13

---

## Phase 1: Code Restructuring (W1) — Sequential

```
BEAD-01: Create infra/ package (db, health)
  Priority: P0
  Blocked by: —
  Scope: mkdir infra/, git mv db.py + health.py, create __init__.py,
         update imports in: reindex, context_builder, cache, linter, mcp_server, cli
         + update tests
  Validation: pytest + mypy + ruff

BEAD-02: Create context/ package (code_indexer, cache, search, context_builder)
  Priority: P0
  Blocked by: BEAD-01 (cache imports db)
  Scope: mkdir context/, git mv 4 files, create __init__.py,
         update imports in: reindex, import_resolver, mcp_server, cli, why
         + update tests
  Validation: pytest + mypy + ruff

BEAD-03: Create sync/ package (sync_engine, doc_indexer)
  Priority: P0
  Blocked by: BEAD-01 (reindex uses both)
  Scope: mkdir sync/, git mv 2 files, create __init__.py,
         update imports in: reindex, mcp_server, cli
         + update tests
  Validation: pytest + mypy + ruff

BEAD-04: Create onboarding/ package (onboarding, presets)
  Priority: P0
  Blocked by: —
  Scope: mkdir onboarding/, git mv 2 files, create __init__.py,
         update imports in: cli
         + update tests
  Validation: pytest + mypy + ruff

BEAD-05: Create graph/ package (graph_loader, diff, rule_engine, import_resolver, linter)
  Priority: P0
  Blocked by: BEAD-01 (linter imports db), BEAD-02 (import_resolver imports code_indexer)
  Scope: mkdir graph/, git mv 5 files, create __init__.py,
         update imports in: reindex, mcp_server, cli
         + update tests
  Validation: pytest + mypy + ruff

BEAD-06: Move reindex into infra/ package
  Priority: P0
  Blocked by: BEAD-01, BEAD-02, BEAD-03, BEAD-05 (reindex imports from all)
  Scope: git mv reindex.py → infra/reindex.py,
         update imports in: linter, import_resolver, mcp_server, cli
         + update tests
  Validation: pytest + mypy + ruff

BEAD-07: Final service import fixup + full validation
  Priority: P0
  Blocked by: BEAD-06
  Scope: Update all remaining imports in cli.py, mcp_server.py, why.py,
         update any remaining test imports,
         final run: pytest + mypy + ruff + full test suite
  Validation: ALL green
```

## Phase 2: Docs + Self-Bootstrap — Parallel

```
BEAD-08: Restructure docs/ to domain-first layout
  Priority: P1
  Blocked by: BEAD-07 (need final package paths for docs)
  Scope: Create domains/, services/, guides/ directories,
         migrate existing content from 8 flat files,
         update file paths and cross-references
  Validation: all links valid, no broken refs

BEAD-09: Document undocumented features
  Priority: P1
  Blocked by: BEAD-08 (need directory structure)
  Scope: Write docs for: search, why, diff, ui, watch, lint
         Update CLI reference (18/18 commands)
         Update MCP docs (7+ tools, cache, auto-reindex)
  Validation: all features documented

BEAD-10: Self-bootstrap — .beadloom/_graph/ for Beadloom
  Priority: P1
  Blocked by: BEAD-07 (need final package layout)
  Scope: Update services.yml with ~20 nodes reflecting new DDD structure,
         update rules.yml, add doc bindings,
         run: beadloom reindex + doctor + lint
  Validation: beadloom ctx <any-node> works

BEAD-11: Update README.md and README.ru.md
  Priority: P1
  Blocked by: BEAD-08, BEAD-09 (need final doc structure and content)
  Scope: Update "Documentation structure" block,
         update "Docs" table with new paths,
         update feature counts (18 CLI, 7+ MCP),
         ensure both languages are in sync
  Validation: all links resolve
```

## Phase 3: Final Validation

```
BEAD-12: End-to-end validation
  Priority: P0
  Blocked by: BEAD-10, BEAD-11
  Scope: Run full validation suite:
         - uv run pytest (all pass, >=80% coverage)
         - uv run mypy --strict (0 errors)
         - uv run ruff check src/ (0 errors)
         - beadloom doctor (0 errors)
         - beadloom sync-check (0 stale)
         - beadloom lint (0 violations)
         - beadloom ctx context-oracle (valid bundle)
  Fix any remaining issues
  Validation: ALL metrics green

BEAD-13: CHANGELOG entry + final commit
  Priority: P1
  Blocked by: BEAD-12
  Scope: Add CHANGELOG.md entry for restructuring,
         final git commit with all changes,
         git push
  Validation: CI passes
```

---

## DAG Visualization

```
BEAD-01 (infra/) ──────┬──→ BEAD-02 (context/) ──┬──→ BEAD-05 (graph/) ──→ BEAD-06 (reindex→infra)
                        │                          │                              │
BEAD-04 (onboarding/) ─┤                          │                              │
                        │   BEAD-03 (sync/) ───────┘                              │
                        │                                                         │
                        └─────────────────────────────────────────────────→ BEAD-07 (final fixup)
                                                                               │
                                                              ┌────────────────┼────────────────┐
                                                              ↓                ↓                ↓
                                                     BEAD-08 (docs)    BEAD-09 (new docs)  BEAD-10 (graph)
                                                              │                │
                                                              └───────┬────────┘
                                                                      ↓
                                                              BEAD-11 (READMEs)
                                                                      │
                                                                      ↓
                                                              BEAD-12 (validation)
                                                                      │
                                                                      ↓
                                                              BEAD-13 (changelog + push)
```

---

## Parallelization opportunities

| Phase | Parallel beads | Agents needed |
|-------|---------------|---------------|
| Phase 1 | BEAD-01 + BEAD-04 | 2 (but BEAD-04 is small) |
| Phase 1 | BEAD-02 + BEAD-03 (after BEAD-01) | 2 |
| Phase 2 | BEAD-08 + BEAD-10 | 2 |
| Phase 2 | BEAD-09 (after BEAD-08) | 1 |

Maximum parallelism: 2 concurrent agents in Phase 1 and Phase 2.
