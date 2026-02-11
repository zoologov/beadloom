# Beadloom: Backlog & Deferred Work

> **Last updated:** 2026-02-11
> **Current version:** 1.0.0
> **Completed phases:** 1 (v0.3), 2 (v0.4), 3 (v0.5), 4 (v0.6), 5 (v0.7), 6 (v1.0)

---

## 1. Deferred from Phase 4 (v0.6)

Items planned in RFC-0005 but consciously deferred during implementation.

| Item | RFC Section | Why Deferred | Effort | Blocker? |
|------|-------------|--------------|--------|----------|
| **sqlite-vec integration** | §3.6 Tier 2 | FTS5 covers 95% of search; sqlite-vec needs fastembed (~80MB), ONNX Runtime, embedding pipeline | M | No |
| **`vec_nodes` table** | §3.6 | Depends on sqlite-vec; table schema designed but not created | S | sqlite-vec |
| **Auto-reindex config toggle** | §3.3 | No user has requested disabling; incremental is fast (<200ms) | S | No |
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

## 2. Phase 5: Developer Experience (v0.7)

> **Source:** STRATEGY.md §2, Phase 5

| # | Item | Type | Priority | Effort | Notes |
|---|------|------|----------|--------|-------|
| 5.1 | **TUI** — `beadloom ui` | feature | P1 | L | Textual framework; graph explorer, node details, status |
| 5.2 | **Graph diff** — `beadloom diff` | feature | P2 | M | What changed since last commit/tag |
| 5.3 | **`beadloom why REF_ID`** | feature | P2 | M | Explain node role: upstream/downstream, impact |
| 5.4 | **Watch mode** — `beadloom watch` | feature | P3 | M | Auto-reindex on file changes (extends 4.3) |

### Technical Notes

- **TUI:** Textual is already a pure-Python dep, fits the stack. Panels: domain list, node detail, graph view, status.
- **Graph diff:** Compare two reindex snapshots (or git commits). Output: added/removed/changed nodes and edges.
- **Why:** BFS from node, collect upstream (who depends on me) + downstream (what I depend on). Rich table output.
- **Watch:** `watchfiles` (or `watchdog`) + `incremental_reindex()`. Already have auto-reindex in MCP; this extends to CLI.

---

## 3. Phase 6: Architecture as Code (v1.0)

> **Source:** STRATEGY.md §2, Phase 6 + §4.4

| # | Item | Type | Priority | Effort | Notes |
|---|------|------|----------|--------|-------|
| 6.1 | **Architecture rules & lint** | feature | P0 | L | `beadloom lint` validates code against graph boundaries |
| 6.2 | **Constraint language** | feature | P0 | L | `rules.yml`: deny/require rules in YAML |
| 6.3 | **Agent-aware constraints** | feature | P1 | M | MCP `get_context` returns constraints for the node |
| 6.4 | **CI architecture gate** | feature | P1 | M | `beadloom lint --strict` as CI check |
| 6.5 | **Multi-repo support** | feature | P1 | L | Federated graphs across repositories |
| 6.6 | **Plugin system** | feature | P2 | L | Custom node kinds, edge types, indexers |
| 6.7 | **Web dashboard** | feature | P3 | L | Read-only graph visualization |

### Key Design Decision (Open)

- **Rule engine:** Simple YAML deny/require vs. DSL (OPA/Rego-like). Start simple.
- **Import detection:** Static analysis via tree-sitter (already have code_indexer). Build `imports` edge type.
- **Constraint delivery:** Add `constraints` field to context bundle → agent receives rules alongside context.

---

## 4. Phase 7: Messaging & Guides (post-dev)

> **Source:** STRATEGY.md §2, Phase 7

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 7.1 | **Guide: "Onboarding a new developer in 1 day"** | docs | P1 | S |
| 7.2 | **Guide: "Multi-agent workflow with Beadloom + Claude Code"** | docs | P1 | S |
| 7.3 | **Guide: "Keeping docs alive in a fast-moving codebase"** | docs | P1 | S |
| 7.4 | **Quick demo GIF/asciicast** | docs | P1 | S |
| 7.5 | **Update README.ru.md** for final features | docs | P1 | S |

---

## 5. Open Questions (from STRATEGY.md)

1. **TUI framework:** Textual vs. simple Rich-based interactive mode?
2. **AaC rule engine:** Simple YAML deny/require or invest in DSL?
3. **AaC scope:** Import boundaries only, or also naming/placement/completeness?
4. **Naming:** "Knowledge Graph" vs "Architecture Graph"?
5. **Multi-repo:** Git submodules? Remote graph refs? Federation protocol?
6. **Plugin system:** Entry points? Hook-based? Config-driven?

---

## 6. Quick Reference: What's Done

| Phase | Version | Status | Tests | Key Deliverables |
|-------|---------|--------|-------|------------------|
| 1 — Foundation | v0.3 | Done | ~280 | README rewrite, AGENTS.md, deprecate --auto |
| 2 — Lower Barrier | v0.4 | Done | ~330 | Presets, smarter bootstrap, zero-doc mode |
| 3 — Team Adoption | v0.5 | Done | 398 | CI integration, health dashboard, links, MCP templates |
| 4 — Performance | v0.6 | Done | 464 | L1+L2 cache, incremental reindex, write tools, FTS5 search |
| 5 — DX | v0.7 | Done | 541 | TUI, graph diff, why, watch |
| 6 — AaC | v1.0 | Done | 646 | Lint, rules engine, import resolver, constraints |
| 7 — Guides | post | — | — | Use-case guides, demos |
