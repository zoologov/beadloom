# Beadloom: Backlog & Deferred Work

> **Last updated:** 2026-02-11
> **Current version:** 1.0.0
> **Completed phases:** 1 (v0.3), 2 (v0.4), 3 (v0.5), 4 (v0.6), 5 (v0.7), 6 (v1.0)

---

## 1. Documentation Debt (P0) — ALL DONE

All items fixed in v1.0.0 release preparation.

| # | Item | Status |
|---|------|--------|
| D1 | README.md: all 18 CLI commands listed | DONE |
| D2 | README.md: all 8 MCP tools listed | DONE |
| D3 | README.md: Architecture-as-Code section added | DONE |
| D4 | README.ru.md fully synced with English version | DONE |
| D5 | STRATEGY.md updated — all phases marked DONE, version 1.0.0 | DONE |
| D6 | pyproject.toml: classifier set to `5 - Production/Stable` | DONE |
| D7 | CHANGELOG.md created covering v0.1.0 through v1.0.0 | DONE |

---

## 2. Deferred from Phase 4 (v0.6)

Items planned in RFC-0005 but consciously deferred during implementation.

| Item | RFC Section | Why Deferred | Effort | Blocker? |
|------|-------------|--------------|--------|----------|
| **sqlite-vec integration** | §3.6 Tier 2 | FTS5 covers 95% of search; sqlite-vec needs fastembed (~80MB), ONNX Runtime | M | No |
| **`vec_nodes` table** | §3.6 | Depends on sqlite-vec; table schema designed but not created | S | sqlite-vec |
| **Incremental graph YAML reindex** | §3.2 step 4 | Graph changes cascade (edges, docs, sync_state); full reindex is safe and fast | L | No |
| **Atomic YAML writes** | §10 risk row | `update_node_in_yaml` writes directly; temp-file+rename not implemented | S | No |

### sqlite-vec Integration Plan (when needed)

```
1. pip install beadloom[search]  → gets sqlite-vec + fastembed
2. On reindex: detect fastembed → generate embeddings for nodes+chunks
3. Store in vec_nodes table (float[384], BAAI/bge-small-en-v1.5)
4. search.py: try vec similarity first → fall back to FTS5 → fall back to LIKE
5. First run downloads model (~33MB) — show progress bar
```

---

## 3. Deferred from Phase 6 (v1.0)

Items planned but scoped out of BDL-007 per CONTEXT.md §2.

| Item | Why Deferred | Effort | Notes |
|------|--------------|--------|-------|
| **Multi-repo federated graphs** (6.5) | Design complexity; no multi-repo user yet | L | Git submodules? Remote refs? Federation protocol? |
| **Plugin system** (6.6) | Premature; need real extension requests first | L | Entry points? Hook-based? Config-driven? |
| **Web dashboard** (6.7) | Read-only Mermaid graph; TUI covers interactive use for now | L | Could be a simple static site generator |
| **Rule severity levels / tags** | YAML deny/require covers 80%; warn vs error adds complexity | S | Useful once teams have many rules |
| **DSL-based rules (OPA/Rego)** | YAML is simpler, PR-reviewable; no demand for complex logic | L | Revisit if YAML becomes limiting |
| **Re-export / alias resolution** | Import resolver handles direct imports; re-exports are rare edge case | M | Needs cross-file analysis |

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

| # | Item | Type | Priority | Effort | Notes |
|---|------|------|----------|--------|-------|
| 7.1 | **Guide: "Onboarding a new developer in 1 day"** | docs | P1 | S | Step-by-step with beadloom ctx flow |
| 7.2 | **Guide: "Multi-agent workflow with Beadloom + Claude Code"** | docs | P1 | S | MCP tools, constraints, context bundles |
| 7.3 | **Guide: "Keeping docs alive in a fast-moving codebase"** | docs | P1 | S | Hooks, sync-check, CI gate |
| 7.4 | **Quick demo GIF/asciicast** | docs | P1 | S | Record with asciinema or VHS |
| 7.5 | **Update README.ru.md** for v1.0 features | docs | P1 | S | Overlaps with D4 above |

---

## 6. Future Feature Ideas (for STRATEGY-2)

Organized by theme. No decisions made — these are candidates for evaluation.

### 6a. Architecture as Code — Enhancements

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| Rule severity levels | `warn` vs `error` per rule; `--strict` only fails on errors | S | High for adoption |
| Rule tags / categories | Group rules (`security`, `perf`, `style`); filter in lint | S | High for large teams |
| Autofix suggestions | Lint output includes "move import to X" or "add node Y" | M | Nice DX |
| Re-export resolution | Track `from X import Y` chains through re-exports | M | Correctness |
| More languages | Java, C#, C++ import resolution (tree-sitter grammars exist) | M per lang | Reach |

### 6b. Scale & Federation

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| Multi-repo graphs | Federated graphs across repositories | L | Enterprise |
| Remote graph refs | Reference nodes from external repos (`@org/other-repo:AUTH-001`) | L | Enterprise |
| Monorepo workspace support | Multiple `_graph/` roots in one repo | M | Monorepo users |

### 6c. Visualization & DX

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| Web dashboard | Static site with interactive graph (D3/Cytoscape) | L | Sharing |
| VS Code extension | Graph overlay, node navigation, lint diagnostics | L | Adoption |
| TUI graph view | Visual graph panel in Textual TUI (currently only list + detail) | M | Power users |
| `beadloom export` | Export graph to DOT, D2, Mermaid file, JSON | S | Interop |
| ASCII graph in terminal | `beadloom graph --ascii` for environments without Mermaid renderer | S | DX |

### 6d. Integration & Ecosystem

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| GitHub Actions marketplace action | `uses: beadloom/lint-action@v1` | M | Adoption |
| pre-commit framework hook | `.pre-commit-config.yaml` integration | S | Adoption |
| More MCP tools | Expose `lint`, `diff`, `why` via MCP | M | Agent DX |
| Slack / Discord notifications | Stale doc alerts, lint failures | M | Team workflow |
| GitLab / Bitbucket CI recipes | Extend beyond GitHub Actions | S | Reach |

### 6e. Search & Intelligence

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| sqlite-vec semantic search | Vector similarity over node+chunk embeddings | M | Fuzzy search |
| Symbol-level search | Find functions by signature, not just name | M | Code navigation |
| "Did you mean?" suggestions | Fuzzy matching on ref_id typos | S | DX |
| Cross-reference report | "Which features touch this file?" reverse lookup | S | Impact analysis |

### 6f. Robustness & Quality

| Item | Description | Effort | Value |
|------|-------------|--------|-------|
| Performance benchmarks | Automated benchmark suite, track regressions | M | Confidence |
| Atomic YAML writes | temp-file + rename for crash safety | S | Reliability |
| Schema migrations | Versioned SQLite schema with forward migration | M | Upgrades |
| Property-based testing | Hypothesis for graph/reindex edge cases | M | Correctness |

---

## 7. Open Questions

### Answered (for reference)

| Question | Answer | Phase |
|----------|--------|-------|
| TUI framework? | **Textual** — full-featured, pure-Python, async | Phase 5 |
| AaC rule engine? | **YAML deny/require** — simple, PR-reviewable | Phase 6 |
| AaC scope? | **Import boundaries** — deny/require cross-boundary imports | Phase 6 |

### Still Open

| # | Question | Context |
|---|----------|---------|
| 1 | **Naming:** "Architecture Graph" (decided) | Renamed codebase-wide in BDL-013 D13 |
| 2 | **Multi-repo:** Git submodules? Remote graph refs? Federation protocol? | No design yet |
| 3 | **Plugin system:** Entry points? Hook-based? Config-driven? | No design yet |
| 4 | **Web dashboard:** Static site generator? SPA? Server? | Trade-offs differ for sharing vs interactivity |
| 5 | **Version strategy post-1.0:** SemVer strict? Calendar versioning? | Affects schema migration story |

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
| 7 — Guides | post | — | — | Use-case guides, demos |

### Current Totals (v1.0.0)

- **18 CLI commands**, **8 MCP tools**
- **653 tests**, 0 TODO/FIXME in source
- **21 modules** + TUI subpackage
- **4 languages** supported in import resolver (Python, TS/JS, Go, Rust)
- Self-tested: beadloom lint on beadloom = 0 violations
