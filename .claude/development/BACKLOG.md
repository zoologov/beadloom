# Beadloom: Backlog & Deferred Work

> **Last updated:** 2026-02-15
> **Current version:** 1.4.0
> **Completed phases:** 1 (v0.3), 2 (v0.4), 3 (v0.5), 4 (v0.6), 5 (v0.7), 6 (v1.0), Agent Prime (v1.4)

---

## 1. Documentation Debt (P0) — ALL DONE

All items fixed in v1.0.0 release preparation. Counts updated in v1.4.0 doc audit.

| # | Item | Status |
|---|------|--------|
| D1 | README.md: all 21 CLI commands listed | DONE (updated v1.4) |
| D2 | README.md: all 10 MCP tools listed | DONE (updated v1.4) |
| D3 | README.md: Architecture-as-Code section added | DONE |
| D4 | README.ru.md fully synced with English version | DONE (updated v1.4) |
| D5 | STRATEGY.md updated — all phases marked DONE, version 1.0.0 | DONE |
| D6 | pyproject.toml: classifier set to `5 - Production/Stable` | DONE |
| D7 | CHANGELOG.md created covering v0.1.0 through v1.4.0 | DONE (updated v1.4) |

---

## 2. Deferred from Phase 4 (v0.6)

Items planned in RFC-0005 but consciously deferred during implementation.

| Item | RFC Section | Why Deferred | Effort | Status |
|------|-------------|--------------|--------|--------|
| **sqlite-vec integration** | §3.6 Tier 2 | FTS5 covers 95% at single-repo scale | M | **Planned in STRATEGY-2 Phase 13.3 (v2.0)** |
| **`vec_nodes` table** | §3.6 | Depends on sqlite-vec | S | **Planned in STRATEGY-2 Phase 13.3 (v2.0)** |
| **Incremental graph YAML reindex** | §3.2 step 4 | Graph changes cascade; full reindex is safe and fast | L | **Not planned** — UX #21 fix in Phase 8.5.4 addresses the specific bug |
| **Atomic YAML writes** | §10 risk row | `update_node_in_yaml` writes directly; temp-file+rename not implemented | S | **Planned in STRATEGY-2 Phase 14.1 (cross-cutting)** |

---

## 3. Deferred from Phase 6 (v1.0)

| Item | Why Deferred | Effort | Status |
|------|--------------|--------|--------|
| **Multi-repo federated graphs** (6.5) | Design complexity | L | **Planned in STRATEGY-2 Phase 12.1 (v1.7) + Phase 13.1 (v2.0)** |
| **Plugin system** (6.6) | Premature; need real extension requests | L | **Planned in STRATEGY-2 Phase 13.5 (v2.0)** |
| **Web dashboard** (6.7) | TUI covers interactive use | L | **Deferred to STRATEGY-3** |
| **Rule severity levels / tags** | YAML deny/require covers 80% | S | Severity: **Planned in Phase 10.4 (v1.6)**. Tags: **Deferred to STRATEGY-3** |
| **DSL-based rules (OPA/Rego)** | YAML is simpler, PR-reviewable | L | **Not planned** — YAML sufficient |
| **Re-export / alias resolution** | Import resolver handles direct imports | M | **Planned in STRATEGY-2 Phase 14.3 (cross-cutting)** |

---

## 4. QA Findings (all fixed in v1.0.0)

Bugs found during self-testing on the beadloom repository. All fixed and pushed.

| Bug | Root Cause | Fix | Commit |
|-----|-----------|-----|--------|
| `beadloom ui` traceback when textual not installed | Lazy import: `try/except` guarded module import, not `launch()` call | Added second `try/except ImportError` around `launch()` | `78c97dd` |
| TUI shows empty data (all [0] counts, no detail) | 5 sub-bugs: `show_domain()` instead of `show_node()`, `part_of` count query, no highlight handler, no auto-select, hidden status bar | Rewrote domain_list queries, added highlight handler, fixed CSS | `b5273f6` |
| `beadloom reindex` shows "0 nodes, 0 edges" on no-change | Incremental reindex returns empty `ReindexResult` when nothing changed | Added `nothing_changed` flag, show "up to date" + DB totals | `7dba199` |
| `beadloom watch` traceback when watchfiles not installed | Same lazy import pattern as TUI | Added `try/except ImportError` around `watch()` call | `7dba199` |

**Lesson learned:** All optional-dependency commands need `try/except` around both `import` AND the function call (lazy imports).

---

## 5. Phase 7: Messaging & Guides (post-dev)

> **Source:** STRATEGY.md §2, Phase 7
> **Status:** **Planned in STRATEGY-2 Phase 7 (parallel)**

| # | Item | Type | Priority | Effort | Status |
|---|------|------|----------|--------|--------|
| 7.1 | **Guide: "Onboarding a new developer in 1 day"** | docs | P1 | S | Planned in STRATEGY-2 |
| 7.2 | **Guide: "Multi-agent workflow with Beadloom + Claude Code"** | docs | P1 | S | Planned in STRATEGY-2 |
| 7.3 | **Guide: "Keeping docs alive in a fast-moving codebase"** | docs | P1 | S | Planned in STRATEGY-2 |
| 7.4 | **Quick demo GIF/asciicast** | docs | P1 | S | Planned in STRATEGY-2 |
| 7.5 | **Update README.ru.md** for v1.4+ features | docs | P1 | S | Planned in STRATEGY-2 |

---

## 6. Future Feature Ideas — Status after STRATEGY-2

### 6a. Architecture as Code — Enhancements

| Item | Effort | Status |
|------|--------|--------|
| Rule severity levels | S | **Planned: Phase 10.4 (v1.6)** |
| Rule tags / categories | S | **Deferred to STRATEGY-3** |
| Autofix suggestions | M | **Not planned** — low ROI |
| Re-export resolution | M | **Planned: Phase 14.3 (cross-cutting)** |
| More languages (Java, Kotlin, Swift, C/C++) | M/lang | **Planned: Phase 9 (v1.5)** — elevated to P0 |
| C# | M | **Deferred to STRATEGY-3** — no dogfood project |

### 6b. Scale & Federation

| Item | Effort | Status |
|------|--------|--------|
| Multi-repo graphs | L | **Planned: Phase 12.1 (v1.7) + Phase 13.1 (v2.0)** |
| Remote graph refs | L | **Planned: Phase 12.1 (v1.7)** |
| Monorepo workspace support | M | **Planned: Phase 12.4 (v1.7)** |

### 6c. Visualization & DX

| Item | Effort | Status |
|------|--------|--------|
| Web dashboard | L | **Deferred to STRATEGY-3** |
| VS Code extension | L | **Deferred to STRATEGY-3** |
| TUI graph view | M | **Deferred to STRATEGY-3** |
| `beadloom export` | S | **Planned: Phase 12.3 (v1.7)** |
| ASCII graph in terminal | S | **Deferred to STRATEGY-3** |

### 6d. Integration & Ecosystem

| Item | Effort | Status |
|------|--------|--------|
| GitHub Actions marketplace action | M | **Deferred to STRATEGY-3** |
| pre-commit framework hook | S | **Deferred to STRATEGY-3** |
| More MCP tools (lint, diff, why) | M | **Planned: Phase 11.1-11.3 (v1.6)** — elevated to P0-P1 |
| Slack / Discord notifications | M | **Not planned** — not our zone |
| GitLab / Bitbucket CI recipes | S | **Deferred to STRATEGY-3** |

### 6e. Search & Intelligence

| Item | Effort | Status |
|------|--------|--------|
| sqlite-vec semantic search | M | **Planned: Phase 13.3-13.4 (v2.0)** — tied to multi-repo scale |
| Symbol-level search | M | **Deferred to STRATEGY-3** |
| "Did you mean?" suggestions | S | **Deferred to STRATEGY-3** — Levenshtein already in MCP |
| Cross-reference report | S | **Not planned** — covered by `beadloom why` |

### 6f. Robustness & Quality

| Item | Effort | Status |
|------|--------|--------|
| Performance benchmarks | M | **Planned: Phase 14.4 (cross-cutting)** |
| Atomic YAML writes | S | **Planned: Phase 14.1 (cross-cutting)** |
| Schema migrations | M | **Planned: Phase 14.2 (cross-cutting)** |
| Property-based testing | M | **Planned: Phase 14.5 (cross-cutting)** |

---

## 7. Open Questions

### Answered (for reference)

| Question | Answer | Phase |
|----------|--------|-------|
| TUI framework? | **Textual** — full-featured, pure-Python, async | Phase 5 |
| AaC rule engine? | **YAML deny/require** — simple, PR-reviewable | Phase 6 |
| AaC scope? | **Import boundaries** — deny/require cross-boundary imports | Phase 6 |
| Naming? | **Architecture Graph** — renamed in BDL-013 | v1.2 |
| Semantic layer: when? | **v2.0** — tied to multi-repo scale | STRATEGY-2 rev2 |
| Language order? | **Kotlin → Java → Swift → C/C++ → Obj-C** — by dogfood priority | STRATEGY-2 rev2 |
| Routes storage? | **JSON in `nodes.extra`** | STRATEGY-2 rev2 |
| Git analysis depth? | **6 months, configurable** | STRATEGY-2 rev2 |
| Framework detection approach? | **File markers + import scan side-effect** | STRATEGY-2 rev2 |

### Still Open

| # | Question | Context |
|---|----------|---------|
| 1 | **Multi-repo refs format?** | `@org/repo:REF_ID`? Config in `config.yml`? Git submodules? |
| 2 | **Federation protocol?** | Shared SQLite? JSON API? File-based? |
| 3 | **Plugin system format?** | Entry points? Hook-based? Config-driven? |
| 4 | **Embedding model for code?** | Start with bge-small, switch to code-specific if needed? |
| 5 | **Version strategy post-1.0?** | SemVer strict? Affects schema migration story |

---

## 8. Quick Reference: What's Done

| Phase | Version | Status | Tests | Key Deliverables |
|-------|---------|--------|-------|------------------|
| 1 — Foundation | v0.3 | Done | ~280 | README rewrite, AGENTS.md, deprecate --auto |
| 2 — Lower Barrier | v0.4 | Done | ~330 | Presets, smarter bootstrap, zero-doc mode |
| 3 — Team Adoption | v0.5 | Done | 398 | CI integration, health dashboard, links, MCP templates |
| 4 — Performance | v0.6 | Done | 464 | L1+L2 cache, incremental reindex, write tools, FTS5 search |
| 5 — DX | v0.7 | Done | 541 | TUI, graph diff, why, watch |
| 6 — AaC | v1.0 | Done | 653 | Lint, rules engine, import resolver, agent constraints |
| Onboarding QA | v1.3.1 | Done | 811 | 10 bug-fixes from dogfooding |
| Agent Prime | v1.4.0 | Done | 847 | Prime CLI/MCP, setup-rules, AGENTS.md v2, doc audit |
| 7 — Guides | planned | — | — | Use-case guides, demos |

### Current Totals (v1.4.0)

- **21 CLI commands**, **10 MCP tools**
- **847 tests**, 0 TODO/FIXME in source
- **35 modules** across 7 domain packages
- **4 languages** in import resolver (Python, TS/JS, Go, Rust) — expanding to 9 in v1.5
- Self-tested: beadloom lint on beadloom = 0 violations
