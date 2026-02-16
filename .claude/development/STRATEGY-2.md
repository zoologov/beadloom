# Beadloom: Strategy 2 — Architecture Infrastructure for the AI Agent Era

> **Status:** Active (Phases 8-11 complete, Phase 12+ planned)
> **Date:** 2026-02-17 (revision 4)
> **Current version:** 1.6.0
> **Predecessor:** STRATEGY.md (Phases 1-6, all completed)
> **Sources:** STRATEGY.md, BACKLOG.md §2-§6, BDL-UX-Issues.md, competitive analysis February 2026

---

## 1. Strategic Context

### What We Solved (Strategy 1)

Beadloom v1.0-1.4 is a full-featured **Architecture as Code** platform: architecture graph, Context Oracle, Doc Sync, architecture lint, MCP server, Agent Prime. The pipeline works: `init` → `reindex` → `ctx` → agent receives context.

### Market Context (February 2026)

AI model context windows are growing rapidly:

| Model | Context |
|-------|---------|
| Claude Opus 4.6 | 1M tokens |
| Gemini 1.5 Pro | up to 2M tokens |
| GPT-5 | 400K tokens |

A typical 50-100 module project is ~500K-2M tokens. Models **can already** read an entire project in one go.

### Why Beadloom Remains Valuable

2026 research (Martin Fowler "Context Engineering for Coding Agents", Anthropic "2026 Agentic Coding Trends Report", ITBrief "AI coding tools face 2026 reset towards architecture") shows:

1. **"Lost in the middle"** — at >100K tokens, models lose 15-30% accuracy on information in the middle of the context
2. **Structure breaks down** — 500K tokens of raw code = text without architectural relationships
3. **Cost** — filling a 1M-token window on every agent step = minutes + dollars
4. **80% of tech debt in 2026 is architectural** — agents write more code, boundary violations happen more often

> **Beadloom is not "more context". It's "the right 2K tokens instead of the wrong 500K".**

### What Context Windows Do NOT Replace

| Capability | Why irreplaceable |
|------------|-------------------|
| **Doc-Code Sync** | Temporal tracking: requires file hashes over time, not a one-time snapshot |
| **Architecture Lint** | Deterministic validation: an agent can violate boundaries, lint catches it |
| **Context Oracle (<20ms)** | In multi-step workflows (plan→code→review→test) 2K in 20ms >> 500K in 30s |
| **YAML graph in Git** | Diffable, reviewable, mergeable — no cloud SaaS offers this |

### What Was Broken (Fixed in v1.5.0)

**Three critical problems — ALL SOLVED:**

1. ~~**Bootstrap is shallow**~~ **FIXED (Phase 8)** — Bootstrap now ingests README, detects 18+ frameworks, discovers entry points, runs import analysis, and generates contextual summaries like "FastAPI service: auth — JWT auth, 3 classes, 5 fns".

2. ~~**Doc Sync is broken**~~ **FIXED (Phase 8.5 + BDL-016)** — Symbol-level drift detection via `symbols_hash` catches semantic drift. BDL-016 fixed the incremental reindex path to preserve baselines. `sync-check` now honestly reports stale docs.

3. ~~**4 languages aren't enough**~~ **FIXED (Phase 9)** — Added Kotlin, Java, Swift, C/C++, Objective-C. 9 languages total.

### Strategy 2 Key Message

> **Strategy 1: Beadloom manages knowledge.**
> **Strategy 2: Beadloom is architecture infrastructure: understands a project from second one, honestly tracks drift, works on any stack, scales to IT landscapes.**

---

## 2. Design Principles

### Principle 1: Agent-native (unchanged)

Beadloom remains an **infrastructure layer**, not an agent. No built-in LLM API calls. The agent the developer already uses does the thinking — Beadloom provides richer data.

### Principle 2: Structure Over Volume

More context ≠ better context. Beadloom delivers **structured data** (graph, symbols, edges, rules, sync status) — what an LLM cannot extract from raw code in a single pass.

### Principle 3: Sync Honesty

Doc Sync must **actually** catch discrepancies, not create a false sense of security. "5 stale" truth is better than "0 stale" lies.

### Principle 4: Core is Deterministic, Semantics are Optional

The core remains deterministic (tree-sitter, BFS, FTS5, symbol-level hashing). Semantic capabilities (embeddings, similarity) are optional via `beadloom[semantic]` and tied to multi-repo scale.

### Principle 5: Engineering Tool

Beadloom is for engineers who build and maintain serious IT systems. YAML graph in Git, deterministic lint, CI gate, multi-repo federation — this is enterprise architecture tooling.

### Why Not a Built-in LLM?

| Factor | Built-in LLM | Rich structured data |
|--------|--------------|----------------------|
| Download size | 3-8 GB model weights | 0 (uses existing tree-sitter) |
| Time to start | Minutes to download model | Instant |
| Hardware requirements | 8+ GB RAM, GPU preferred | Any machine |
| Result quality | 7B << Claude/GPT-4 | Agent's LLM generates ideal summaries |
| Maintenance | Model versions, backends, CUDA/Metal | Standard Python |
| Design compliance | Violates "agent-native" | Fully compliant |

---

## 3. Competitive Landscape

### Direct Competitors

| Tool | What it does | Threat | Our advantage |
|------|-------------|--------|---------------|
| **Greptile** | Semantic code graph, cloud SaaS, $0.45/file | Medium | Local-first, YAML in Git, doc-sync |
| **Augment Code** | Proprietary Context Engine, 400K+ files | High (if opened) | Open format, deterministic |
| **DeepDocs** | GitHub-native doc sync, auto-PR with updates | High for doc-sync | Any Git, not just GitHub; architecture graph |
| **Sourcegraph Cody** | Cross-repo code search + AI | Medium | Not search-first, but architecture-first |

### Complementary Tools

| Tool | How it complements Beadloom |
|------|-----------------------------|
| **Cursor / Windsurf** | IDE with index → Beadloom as MCP backend for architectural context |
| **AGENTS.md (Vercel)** | Static instructions → Beadloom generates AGENTS.md from a live graph |
| **Repomix** | Flat file aggregation → Beadloom delivers structured bundles |
| **Claude Code** | CLAUDE.md + MCP → Beadloom as context MCP server |

### Beadloom's Unique Position

**Local-first, graph-based, Git-versioned architecture infrastructure with doc-sync and multi-language support.** No competitor covers all of this simultaneously.

---

## 4. Roadmap

### Phase 8: Smart Bootstrap (v1.5) — DONE

**Goal:** `beadloom init` creates a graph with real architectural meaning, not just file counts.

**Metric:** Bootstrapping a 50-module project yields nodes with framework, entry points, key symbols, and dependency edges.

**Delivered in:** BDL-015 (17 beads, 306 new tests). Released as v1.5.0.

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 8.1 | **README/documentation ingestion** — `_ingest_readme()` extracts project description, tech stack, architecture notes | feature | P0 | DONE |
| 8.2 | **Extended framework detection** — 18+ frameworks detected by files and imports | feature | P0 | DONE |
| 8.3 | **Entry point discovery** — `_discover_entry_points()` across 6 languages | feature | P0 | DONE |
| 8.4 | **Import analysis at bootstrap** — `_quick_import_scan()` builds `depends_on` edges | feature | P0 | DONE |
| 8.5 | **Contextual node summaries** — `_build_contextual_summary()` with rich descriptions | feature | P1 | DONE |
| 8.6 | **AGENTS.md in bootstrap** — auto-called from `bootstrap_project()` (fix UX #19) | fix | P1 | DONE |
| 8.7 | **`service-needs-parent` rule** — auto-generated in `generate_rules()` | fix | P1 | DONE |

### Phase 8.5: Doc Sync v2 — Semantic Drift Detection (v1.5) — DONE

**Goal:** Doc Sync honestly catches discrepancies between code and documentation, rather than creating a false sense of security.

**Metric:** After changing 3 functions in a module, `sync-check` shows "stale" for the corresponding documentation, even if the doc file hasn't changed between reindexes.

**Fix:** UX Issues #15, #18 — critical product problems. **Additionally fixed E2E in BDL-016.**

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 8.5.1 | **Symbol-level drift detection** — `_compute_symbols_hash()` + `symbols_hash` in `sync_state` | feature | P0 | DONE |
| 8.5.2 | **`doctor` warns about drift** — `_check_symbol_drift()` + `_check_stale_sync()` | feature | P0 | DONE |
| 8.5.3 | **Symbol diff in `docs polish`** — `_detect_symbol_changes()` in polish output | feature | P0 | DONE |
| 8.5.4 | **Incremental reindex: graph YAML** — `_graph_yaml_changed()` (fix UX #21) | fix | P0 | DONE |
| 8.5.5 | **`setup-rules` auto-detect fix** — content check instead of presence (fix UX #17) | fix | P2 | DONE |

### Phase 9: Mobile and Server Languages (v1.5) — DONE

**Goal:** Beadloom supports mobile, cross-platform, and server-side development languages. Critical for dogfood project (dreamteam: React Native + Expo + Valhalla C++ + Meshtastic).

**Metric:** `beadloom reindex` on a project with `.kt`, `.swift`, `.cpp`, `.m` files extracts symbols, imports, and dependencies.

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 9.1 | **Kotlin** — `_load_kotlin()`, `_extract_kotlin_imports()` with stdlib filtering | feature | P0 | DONE |
| 9.2 | **Java** — `_load_java()`, `_extract_java_imports()` with static/wildcard imports | feature | P0 | DONE |
| 9.3 | **Swift** — `_load_swift()`, `_extract_swift_imports()` with 35 Apple framework filters | feature | P0 | DONE |
| 9.4 | **C/C++** — `_load_c()`, `_load_cpp()`, `_extract_c_cpp_imports()` with 80+ system headers | feature | P1 | DONE |
| 9.5 | **Objective-C** — `_load_objc()`, `_extract_objc_imports()` with 48 system frameworks | feature | P1 | DONE |

### Phase 10: Deep Code Analysis (v1.6) — DONE

**Goal:** Graph nodes become rich contextual objects: routes, activity, tests.

**Metric:** `beadloom ctx AUTH` returns API routes, activity level, test coverage — enough for an agent to start working without reading a single file.

**Delivered in:** BDL-017 (15 beads, 3 waves). Plus BDL-018 (honest detection, 4 beads, 43 tests) and BDL-020 (hierarchy fix, 3 beads, 4 tests).

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 10.1 | **API surface extraction** — 12 frameworks: FastAPI, Flask, Django, Express, NestJS, Spring Boot, Gin, Echo, Fiber, Actix, GraphQL, gRPC | feature | P0 | DONE |
| 10.2 | **Git history analysis** — hot/warm/cold/dormant classification, 6-month window | feature | P0 | DONE |
| 10.3 | **Test mapping** — pytest, jest, go test, JUnit, XCTest; maps tests to modules | feature | P1 | DONE |
| 10.4 | **Rule severity levels** — `error`/`warn`, backward-compatible v1→v2, `--strict` fails on errors only | feature | P1 | DONE |
| 10.5 | **Smart `docs polish`** — enriched with routes, activity, tests, config, symbol diff | feature | P1 | DONE |

### Phase 10.5: Doc-Sync Honest Detection (v1.6) — DONE

**Goal:** Doc-Sync honestly catches ALL types of staleness, not just file-hash changes.

**Metric:** After changing code in a domain, `sync-check` reports stale with specific reasons.

**Delivered in:** BDL-018 (4 beads, 43 new tests) + BDL-019 (doc refresh) + BDL-020 (hierarchy fix).

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 10.5.1 | **3-layer staleness** — `symbols_changed` + `untracked_files` + `missing_modules` | feature | P0 | DONE |
| 10.5.2 | **Source coverage check** — detect untracked files in node source dirs | feature | P0 | DONE |
| 10.5.3 | **Doc coverage check** — verify docs mention all source modules | feature | P0 | DONE |
| 10.5.4 | **Hierarchy-aware coverage** — `part_of` edges count child node files as tracked | fix | P0 | DONE |
| 10.5.5 | **Baseline fix** — `_compute_symbols_hash()` handles both JSON formats, snapshot preserves hashes | fix | P0 | DONE |

### Phase 11: Agent Infrastructure (v1.6) — DONE

**Goal:** Agents have full access to all validation and context tools via MCP and CLI.

**Metric:** An agent can run lint via MCP, get impact analysis (`why`), see graph diff — not just `get_context`.

**Delivered in:** BDL-017 (15 beads, 3 waves).

| # | Task | Type | P | Status |
|---|------|------|---|--------|
| 11.1 | **MCP tool `lint`** — architecture validation via MCP with severity in JSON | feature | P0 | DONE |
| 11.2 | **MCP tool `why`** — impact analysis via MCP; upstream deps + downstream dependents | feature | P1 | DONE |
| 11.3 | **MCP tool `diff`** — graph changes since git ref via MCP | feature | P1 | DONE |
| 11.4 | **Context cost metrics** — `beadloom status` shows avg/max bundle sizes in tokens | feature | P2 | DONE |
| 11.5 | **Deep config reading** — pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle | feature | P2 | DONE |

### Phase 12: Cross-System Foundation (v1.7)

**Goal:** Beadloom works across repository boundaries. Beginning of the path to serving IT landscapes.

**Metric:** `beadloom ctx AUTH` in repo-A can show a dependency on `@repo-B:BILLING`; `beadloom export` generates a graph for external consumption.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 12.1 | **Multi-repo graph refs** — references to nodes from external repositories (`@org/other-repo:AUTH-001`); configuration in `config.yml` | feature | P0 | L |
| 12.2 | **Polyglot API contract edges** — frontend↔backend links via OpenAPI, GraphQL, protobuf; cross-language `depends_on` | feature | P1 | L |
| 12.3 | **`beadloom export`** — export graph to DOT, D2, Mermaid file, JSON for external consumption | feature | P1 | S |
| 12.4 | **Monorepo workspace** — multiple `_graph/` roots in a single repository; isolated contexts per package | feature | P2 | M |

### Phase 13: Full Cross-System + Semantic Layer (v2.0)

**Goal:** Beadloom serves IT landscapes of dozens of repositories. Semantic search works across a federated graph of 1000+ nodes.

**Rationale for tying semantics to multi-repo:** At single-project scale (50-200 nodes) FTS5 covers 95% of search queries. At 1000+ nodes from 15 repositories, different teams name identical concepts differently — this is where embedding-based search provides real value.

**Metric:** `beadloom search "authentication flow"` returns relevant nodes from 5 repositories, even when the word "authentication" doesn't appear in the graph.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 13.1 | **Graph federation** — index synchronization protocol between repositories; shared node registry | feature | P0 | L |
| 13.2 | **`beadloom[semantic]` extra** — `sqlite-vec>=0.1` + `fastembed>=0.4`; `uv tool install beadloom[semantic]` | feature | P0 | S |
| 13.3 | **Embedding index** — on `reindex`, generate embeddings via BAAI/bge-small-en-v1.5 (77MB, CPU-only); `vec_nodes` table via sqlite-vec | feature | P0 | M |
| 13.4 | **Semantic search** — `beadloom search --semantic "auth flow"`; fallback: semantic → FTS5 → LIKE | feature | P0 | M |
| 13.5 | **Plugin system** — entry points for custom nodes, edges, indexers, rules | feature | P1 | L |
| 13.6 | **Code similarity** — `beadloom similar REF_ID` finds similar nodes by embedding distance | feature | P2 | S |
| 13.7 | **Embedding cache invalidation** — re-embed only changed nodes | feature | P2 | S |

### Phase 14: Quality and Robustness (cross-cutting)

**Goal:** Improve reliability and maintainability for production use.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 14.1 | **Atomic YAML writes** — temp-file + rename for crash protection | fix | P1 | S |
| 14.2 | **SQLite schema migrations** — versioned schema with forward migration | feature | P1 | M |
| 14.3 | **Re-export/alias resolution** — `from X import Y` chains through re-exports | feature | P2 | M |
| 14.4 | **Performance benchmarks** — automated benchmark suite | feature | P2 | M |
| 14.5 | **Property-based testing** — Hypothesis for graph edge cases | feature | P2 | M |

### Phase 7: Guides and Demos (parallel)

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 7.1 | **Guide: "Onboarding a new developer in 1 day"** | docs | P1 | S |
| 7.2 | **Guide: "Multi-agent workflow with Beadloom + Claude Code"** | docs | P1 | S |
| 7.3 | **Guide: "Keeping documentation alive in a fast-moving codebase"** | docs | P1 | S |
| 7.4 | **Demo GIF/asciicast** for README | docs | P1 | S |
| 7.5 | **Update README.ru.md** — bring up to date for v1.4+ | docs | P1 | S |

### Deferred to STRATEGY-3 (visualization and ecosystem)

The following tasks have value but are not priorities for architecture infrastructure:

| Task | Why deferred |
|------|-------------|
| Web dashboard (D3/Cytoscape) | High effort, non-core; TUI covers this |
| VS Code extension | High effort; MCP tools are sufficient |
| ASCII graph in terminal | Low ROI; Mermaid covers this |
| GitHub Actions marketplace | Useful, but `beadloom lint --strict` in CI already works |
| pre-commit hook | `beadloom install-hooks` already exists |
| Architecture pattern detection (MVC/hex) | LLMs identify patterns from context better |
| Dependency weight analysis | Low ROI for single repo; useful at multi-repo |
| Rule tags / categories | Useful with many rules; premature |
| "Did you mean?" | Levenshtein already exists in MCP; CLI can be added |
| Symbol search (by signature) | tree-sitter already provides names; signatures are edge case |
| C# (tree-sitter-c-sharp) | No dogfood project; on user request |

---

## 5. Key Feature Details

### 5.1 Symbol-level Drift Detection (Phase 8.5)

**Problem:** Sync-check shows "31/31 OK" with 12 real discrepancies (UX Issues #15, #18). Hash-based detection compares files between reindexes but doesn't catch the "code changed, doc didn't" situation.

**Solution:** Two-level sync verification:

```
Level 1 (existing): file-hash based
  sync_state.doc_hash != current hash → stale

Level 2 (NEW): symbol-level drift
  sync_state.symbols_hash != current node symbols_hash → stale
  where symbols_hash = SHA256(sorted(code_symbols for ref_id))
```

**Implementation:**

```python
def compute_symbols_hash(conn: sqlite3.Connection, ref_id: str) -> str:
    """Compute symbol hash for a node."""
    rows = conn.execute(
        "SELECT symbol_name, kind, line_start, line_end "
        "FROM code_symbols WHERE annotations LIKE ? "
        "ORDER BY file_path, symbol_name",
        (f'%"{ref_id}"%',),
    ).fetchall()
    return hashlib.sha256(str(rows).encode()).hexdigest()

# In sync-check:
# 1. Check file-level hashes (existing)
# 2. Check symbols_hash vs symbols_hash_at_sync (NEW)
# 3. If symbols_hash changed but doc_hash didn't → STALE (semantic drift)
```

**Symbol diff for `docs polish`:**

```python
def compute_symbol_diff(old_symbols: list, new_symbols: list) -> dict:
    """Compute symbol difference for docs polish."""
    old_set = {(s.name, s.kind) for s in old_symbols}
    new_set = {(s.name, s.kind) for s in new_symbols}
    return {
        "added": new_set - old_set,      # new functions/classes
        "removed": old_set - new_set,    # removed
        "changed": [...],                 # changed signatures
    }
```

### 5.2 README Ingestion (Phase 8)

**Problem:** README.md contains architecture descriptions, tech stack, instructions. Bootstrap ignores it.

**Solution:**

```python
def ingest_readme(project_root: Path) -> dict[str, Any]:
    """Extract project metadata from README and root documents."""
    # Parses: README.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/README.md
    # Extracts: project description, technology mentions, architecture diagrams
    # Returns: {"description": "...", "tech_stack": [...], "architecture_notes": "..."}
```

### 5.3 Import Analysis at Bootstrap (Phase 8)

**Problem:** `bootstrap_project()` generates only `part_of` edges. `depends_on` edges only appear after `reindex`.

**Solution:** Lightweight import extraction during bootstrap:

```python
def bootstrap_project(project_root, *, preset_name=None):
    # ... existing scanning + clustering ...

    # NEW: lightweight import scanning
    import_edges = _quick_import_scan(project_root, clusters, scan["source_dirs"])
    edges.extend(import_edges)
```

Reuses `extract_imports()` from `import_resolver.py`, maps to cluster names. Fast and accurate enough for the initial graph.

### 5.4 Mobile Languages (Phase 9)

**Dogfood project:** dreamteam — React Native + Expo + native modules:
- Valhalla Routing Engine (C++)
- Meshtastic (C++/embedded)
- Potential iOS/Android native modules (Swift, Kotlin)

**Approach:** Adding tree-sitter loaders to `_EXTENSION_LOADERS` following the existing pattern (Python, TS, Go, Rust):

| Language | tree-sitter package | Extensions | What we extract |
|----------|-------------------|------------|-----------------|
| Kotlin | tree-sitter-kotlin | `.kt`, `.kts` | classes, data classes, `@Composable`, `@HiltViewModel`, imports |
| Java | tree-sitter-java | `.java` | classes, interfaces, `@RestController`, `@Service`, imports |
| Swift | tree-sitter-swift | `.swift` | classes, structs, protocols, `@main`, `import` |
| C/C++ | tree-sitter-c/cpp | `.h`, `.c`, `.cpp` | functions, classes, `#include` |
| Obj-C | tree-sitter-objc | `.m`, `.mm` | classes, methods, `#import`, `@interface` |

### 5.5 API Surface Extraction (Phase 10)

**Solution:** Tree-sitter queries for framework-specific routes:

```python
# Python (FastAPI/Flask)
@app.post("/api/login")           → Route("POST", "/api/login")

# Go (Gin/Echo/Fiber)
r.POST("/api/login", handler)     → Route("POST", "/api/login")

# TypeScript (NestJS/Express)
@Get("/me")                       → Route("GET", "/me")

# Java/Kotlin (Spring Boot)
@GetMapping("/api/users")         → Route("GET", "/api/users")
```

Routes are stored as JSON in `nodes.extra` and included in context bundles.

### 5.6 Git History Analysis (Phase 10)

```python
def analyze_git_activity(project_root: Path, source_dirs: list[str]) -> dict[str, GitActivity]:
    """Analyze git history by source directory cluster."""
    # git log --format="%H %aI" --name-only --since="6 months ago"
    # Tags: hot (>20 commits/month), warm (5-20), cold (<5), dormant (0 for 3 months)
```

### 5.7 `beadloom[semantic]` — Technical Specification (Phase 13)

**Model:** BAAI/bge-small-en-v1.5 — 77MB, 384-dimensional embeddings, CPU-only, 5-14K docs/sec.

**Schema:**

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS vec_nodes USING vec0(
    ref_id TEXT PRIMARY KEY,
    embedding FLOAT[384]
);
CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
```

**Fallback chain:**

```
1. [semantic] installed? → cosine similarity via vec_nodes
2. FTS5 match? → full-text search
3. Fallback → LIKE query
```

**Value at scale:**

| Scale | FTS5 sufficient? | Semantic needed? |
|-------|-------------------|-----------------|
| 1 project, 50 nodes | Yes | No |
| 1 project, 200 nodes | Yes | Optional |
| 5 repos, 500 nodes | No | Yes |
| 15 repos, 2000 nodes | No | Required |

---

## 6. Dependency Map

```
v1.5 ── DONE ─────────────────────────────────────────────
│
├── Phase 8 (Smart Bootstrap) ─── DONE (7/7 tasks)
├── Phase 8.5 (Doc Sync v2) ───── DONE (5/5 tasks)
└── Phase 9 (Languages) ──────── DONE (5/5 tasks)

v1.6 ── DONE ─────────────────────────────────────────────
│
├── Phase 10 (Deep Analysis) ──── DONE (5/5 tasks)
├── Phase 10.5 (Honest Detection) DONE (5/5 tasks)
└── Phase 11 (Agent Infra) ────── DONE (5/5 tasks)

v1.7 ──────────────────────────────────────────────────────
│
└── Phase 12 (Cross-System) ──── after Phases 10+11
    ├── 12.1 Multi-repo refs ───── standalone
    ├── 12.2 API contract edges ── depends on 10.1
    ├── 12.3 beadloom export ───── standalone
    └── 12.4 Monorepo workspace ── standalone

v2.0 ──────────────────────────────────────────────────────
│
└── Phase 13 (Full Cross-System + Semantic) ── after Phase 12
    ├── 13.1 Graph federation ──── depends on 12.1
    ├── 13.2 [semantic] extra ──── standalone
    ├── 13.3 Embedding index ───── depends on 13.2
    ├── 13.4 Semantic search ───── depends on 13.3
    ├── 13.5 Plugin system ─────── standalone
    ├── 13.6 Code similarity ───── depends on 13.3
    └── 13.7 Embedding cache ───── depends on 13.3

Cross-cutting ─────────────────────────────────────────────
├── Phase 14 (Quality) ─────── parallel with all
└── Phase 7 (Guides) ──────── parallel with all
```

---

## 7. Success Metrics

| Metric | v1.4 | v1.5 | v1.6 (current) | v1.7 (target) | v2.0 (target) |
|--------|------|------|----------------|---------------|---------------|
| **Node summaries** | "15 files" | Framework + entry points | **+ routes, activity, tests** | + cross-repo | + cross-repo |
| **First graph edges** | `part_of` only | `part_of` + `depends_on` | + API contracts | + inter-repo | + federated |
| **Doc drift detection** | file-hash only | symbol-level (E2E) | **3-layer: symbols + files + modules** | + cross-repo | + cross-repo |
| **Frameworks** | 4 patterns | 18+ | **18+ with route extraction** | 18+ | + custom |
| **Languages** | 4 | 9 | 9 | 9 | 9+ |
| **Tests** | 847 | 1153 | **1408** | — | — |
| **MCP tools** | 10 | 10 | **13** (+lint, why, diff) | 13 | 13+ |
| **Multi-repo** | No | No | No | **refs** | **federation** |
| **Search** | FTS5 | FTS5 | FTS5 | FTS5 | FTS5 + **semantic** |

---

## 8. Priority Summary

| Phase | Version | Tasks | Status | Key outcome |
|-------|---------|-------|--------|-------------|
| **8 — Smart Bootstrap** | v1.5 | 7 | **DONE** | Rich graph from first `init` |
| **8.5 — Doc Sync v2** | v1.5 | 5 | **DONE** | Honest drift tracking (fix #15, #18, #21) |
| **9 — Mobile Languages** | v1.5 | 5 | **DONE** | +Kotlin, Java, Swift, C/C++, Obj-C |
| **10 — Deep Analysis** | v1.6 | 5 | **DONE** | Routes, activity, tests |
| **10.5 — Honest Detection** | v1.6 | 5 | **DONE** | 3-layer staleness, hierarchy coverage |
| **11 — Agent Infra** | v1.6 | 5 | **DONE** | MCP lint/why/diff, metrics |
| **12 — Cross-System** | v1.7 | 4 | Planned | Multi-repo refs, export |
| **13 — Full Cross + Semantic** | v2.0 | 7 | Planned | Federation, semantic search |
| **14 — Quality** | cross-cutting | 5 | Planned | Atomic writes, migrations |
| **7 — Guides** | parallel | 5 | Planned | Guides, demos |

**v1.5 delivered:** Phases 8 + 8.5 + 9 in parallel. Three critical problems solved in one release (BDL-015, 17 beads, 306 new tests).

**v1.6 delivered:** Phases 10 + 10.5 + 11. Deep analysis + honest detection + agent infrastructure (BDL-017 15 beads + BDL-018 4 beads + BDL-020 3 beads, 255 new tests).

**Next priority:** Phase 12 for v1.7.

---

## 9. BACKLOG.md Integration

| BACKLOG item | Mapped to | Status |
|--------------|-----------|--------|
| sqlite-vec integration (§2) | Phase 13.3 | Planned (v2.0) |
| vec_nodes table (§2) | Phase 13.3 | Planned (v2.0) |
| Atomic YAML writes (§2) | Phase 14.1 | Planned (cross-cutting) |
| Multi-repo federated graphs (§3) | Phase 12.1 + 13.1 | Planned (v1.7 + v2.0) |
| Plugin system (§3) | Phase 13.5 | Planned (v2.0) |
| Web dashboard (§3) | Deferred to STRATEGY-3 | — |
| Rule severity levels (§3) | Phase 10.4 | Planned (v1.6) |
| Re-export resolution (§3) | Phase 14.3 | Planned (cross-cutting) |
| Phase 7 guides (§5) | Phase 7 | Planned (parallel) |
| More languages — Java, Kotlin, Swift, C/C++ (§6a) | Phase 9 | **DONE (v1.5)** |
| C# (§6a) | Deferred to STRATEGY-3 | — |
| Rule tags/categories (§6a) | Deferred to STRATEGY-3 | — |
| Monorepo workspace (§6b) | Phase 12.4 | Planned (v1.7) |
| VS Code extension (§6c) | Deferred to STRATEGY-3 | — |
| `beadloom export` (§6c) | Phase 12.3 | Planned (v1.7) |
| ASCII graph (§6c) | Deferred to STRATEGY-3 | — |
| GH Actions marketplace (§6d) | Deferred to STRATEGY-3 | — |
| pre-commit hook (§6d) | Deferred to STRATEGY-3 | — |
| More MCP tools (§6d) | Phase 11.1-11.3 | **Elevated to v1.6** |
| Symbol-level search (§6e) | Deferred to STRATEGY-3 | — |
| "Did you mean?" (§6e) | Deferred to STRATEGY-3 | — |
| Performance benchmarks (§6f) | Phase 14.4 | Planned (cross-cutting) |
| Schema migrations (§6f) | Phase 14.2 | Planned (cross-cutting) |
| Property-based testing (§6f) | Phase 14.5 | Planned (cross-cutting) |

**Not carried over (consciously excluded):**

| Item | Why |
|------|-----|
| Incremental graph YAML reindex (§2) | Full reindex is fast; UX #21 is fixed by 8.5.4 |
| DSL-based rules (OPA/Rego) (§3) | YAML covers 80% of needs |
| Autofix suggestions (§6a) | Low ROI vs effort |
| Slack/Discord notifications (§6d) | Not our zone |
| Cross-reference report (§6e) | Covered by `beadloom why` |

---

## 10. BDL-UX-Issues.md Integration

| UX Issue | Where resolved | Status |
|----------|---------------|--------|
| #15 [HIGH] doctor 100% coverage misleading | Phase 8.5.1 + 8.5.2 + BDL-016 | **DONE** |
| #16 [MEDIUM] beadloom's own docs outdated | BDL-019 (4 parallel tech-writer agents) | **DONE** |
| #17 [LOW] setup-rules auto-detect for Windsurf/Cline | Phase 8.5.5 | **DONE** |
| #18 [HIGH] sync-check "31/31 OK" despite drift | Phase 8.5.1 + BDL-016 | **DONE** |
| #19 [MEDIUM] AGENTS.md not in bootstrap | Phase 8.6 | **DONE** |
| #20 [LOW] .beadloom/README.md no auto-update | Low priority; manual | Open |
| #21 [HIGH] incremental reindex Nodes: 0 | Phase 8.5.4 | **DONE** |
| #26 [MEDIUM] test mapping 0 tests for domains | Future: aggregate by source path | Open |
| #27 [LOW] docs polish missing deep data | BDL-017 BEAD-14 | **DONE** |
| #29 [HIGH] route extraction false positives | Future: self-exclusion + scoping | Open |
| #30 [MEDIUM] routes poor formatting | Future: improve rendering | Open |
| #31 [LOW] bd dep remove bug | Beads CLI bug, not beadloom | Open (external) |

---

## 11. Closed and Open Questions

### Closed (decisions made)

| Question | Decision | Rationale |
|----------|----------|-----------|
| Semantics: when? | v2.0 (tied to multi-repo) | At 50-200 nodes FTS5 is sufficient; value at 1000+ nodes |
| Languages: order? | Kotlin → Java → Swift → C/C++ → Obj-C | By dogfood project priority (dreamteam) |
| Expo vs React Native? | Distinguish at preset level (already done) | Framework detection for nodes is overkill |
| Route storage? | JSON in `nodes.extra` | Simplicity; no separate table needed |
| Git analysis: depth? | 6 months (configurable) | Balance of speed and usefulness |
| Framework detection: how? | File markers + import analysis side effect | Two levels: fast + accurate |

### Open

| # | Question | Context |
|---|----------|---------|
| 1 | **Multi-repo refs format?** | `@org/repo:REF_ID`? Config in `config.yml`? Git submodules? |
| 2 | **Federation protocol?** | Shared SQLite? JSON API? File-based? |
| 3 | **Plugin format?** | Entry points? Hook-based? Config-driven? |
| 4 | **Embedding model for code?** | Start with bge-small (general-purpose), switch to code-specific if needed? |
| 5 | **Versioning:** | SemVer strict? Affects schema migration story |

---

## 12. Core Strategy Principles

> **Beadloom = data + rules + structure. Agent = intelligence + action.**
> We make data richer, structure explicit, rules enforceable.

> **Context windows solve the volume problem. Beadloom solves the structure problem.**
> More ≠ better. 2K of the right tokens > 500K of raw tokens.

> **Doc Sync is our killer feature. It must work honestly.**
> "5 stale" truth is better than "0 stale" lies.

> **Beadloom is an engineering tool for IT landscapes.**
> Not another vibe-coding gadget, but architecture infrastructure for serious systems.
