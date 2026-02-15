# Beadloom: Strategy 2 — Architecture Infrastructure for the AI Agent Era

> **Status:** Approved
> **Date:** 2026-02-15 (revision 2)
> **Current version:** 1.4.0
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

### What's Still Broken

**Three critical problems:**

1. **Bootstrap is shallow** — `Domain: auth (15 files)` tells an agent nothing. No frameworks, entry points, dependencies, routes.

2. **Doc Sync is broken** — sync-check shows "31/31 OK" with 12 real discrepancies (UX Issues #15, #18). Hash-based detection doesn't catch semantic drift. The killer feature doesn't truly work.

3. **4 languages aren't enough** — no Java/Kotlin (Android), Swift (iOS), C/C++ (native modules). Mobile and cross-platform projects get empty nodes.

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

### Phase 8: Smart Bootstrap (v1.5)

**Goal:** `beadloom init` creates a graph with real architectural meaning, not just file counts.

**Metric:** Bootstrapping a 50-module project yields nodes with framework, entry points, key symbols, and dependency edges.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 8.1 | **README/documentation ingestion** — parse README.md, CONTRIBUTING.md; extract project description, tech stack, architecture notes; store as root node metadata | feature | P0 | S |
| 8.2 | **Extended framework detection** — 15+ frameworks by files and imports: FastAPI, Flask, Django, Express, NestJS, Next.js, Vue, Spring Boot, Gin, Actix, **Expo/React Native**, **SwiftUI**, **Jetpack Compose**, **UIKit** | feature | P0 | M |
| 8.3 | **Entry point discovery** — `__main__.py`, `if __name__`, CLI (Click/Typer/argparse), `main()` in Go/Rust/Java/Kotlin, `@main` in Swift, `AppDelegate`/`@UIApplicationMain`, server bootstraps | feature | P0 | M |
| 8.4 | **Import analysis at bootstrap** — run tree-sitter import extraction in `bootstrap_project()`, build `depends_on` edges before reindex; first graph has real dependencies | feature | P0 | L |
| 8.5 | **Contextual node summaries** — replace "Domain: auth (15 files)" with "FastAPI service: auth — JWT auth, 3 routes, 5 public classes" from extracted data | feature | P1 | M |
| 8.6 | **AGENTS.md in bootstrap** — call `generate_agents_md()` from `bootstrap_project()` automatically (fix UX Issue #19) | fix | P1 | S |
| 8.7 | **`service-needs-parent` rule** — auto-generate in `generate_rules()`: every service must have a `part_of` edge | fix | P1 | S |

### Phase 8.5: Doc Sync v2 — Semantic Drift Detection (v1.5)

**Goal:** Doc Sync honestly catches discrepancies between code and documentation, rather than creating a false sense of security.

**Metric:** After changing 3 functions in a module, `sync-check` shows "stale" for the corresponding documentation, even if the doc file hasn't changed between reindexes.

**Fix:** UX Issues #15, #18 — critical product problems.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 8.5.1 | **Symbol-level drift detection** — on reindex, compute `symbols_hash` for each node (hash of sorted `code_symbols` list); store in `sync_state`; on `sync-check` compare current `symbols_hash` vs stored → if code changed but doc didn't, mark as stale | feature | P0 | M |
| 8.5.2 | **`doctor` warns about drift** — "N nodes have code changes since last doc update"; doesn't replace 100% coverage, adds a second layer of verification | feature | P0 | S |
| 8.5.3 | **Symbol diff in `docs polish`** — `generate_polish_data()` includes diff: "added functions X, Y; removed class Z; changed signature W"; agent receives specific update instructions | feature | P0 | M |
| 8.5.4 | **Incremental reindex: graph YAML** — incremental reindex must pick up changes in `services.yml` (fix UX Issue #21) | fix | P0 | M |
| 8.5.5 | **`setup-rules` auto-detect fix** — for Windsurf/Cline, check existing file content, not just presence (fix UX Issue #17) | fix | P2 | S |

### Phase 9: Mobile and Server Languages (v1.5)

**Goal:** Beadloom supports mobile, cross-platform, and server-side development languages. Critical for dogfood project (dreamteam: React Native + Expo + Valhalla C++ + Meshtastic).

**Metric:** `beadloom reindex` on a project with `.kt`, `.swift`, `.cpp`, `.m` files extracts symbols, imports, and dependencies.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 9.1 | **Kotlin** — tree-sitter-kotlin: classes, data classes, annotations (`@Composable`, `@HiltViewModel`), imports; `.kt`, `.kts` | feature | P0 | M |
| 9.2 | **Java** — tree-sitter-java: classes, interfaces, annotations (`@RestController`, `@Service`), imports; `.java` | feature | P0 | M |
| 9.3 | **Swift** — tree-sitter-swift: classes, structs, protocols, `@main`, `import`; `.swift` | feature | P0 | M |
| 9.4 | **C/C++** — tree-sitter-c / tree-sitter-cpp: functions, classes, `#include`; `.h`, `.c`, `.cpp` | feature | P1 | L |
| 9.5 | **Objective-C** — tree-sitter-objc: classes, methods, `#import`, `@interface`; `.m`, `.mm` | feature | P1 | M |

### Phase 10: Deep Code Analysis (v1.6)

**Goal:** Graph nodes become rich contextual objects: routes, activity, tests.

**Metric:** `beadloom ctx AUTH` returns API routes, activity level, test coverage — enough for an agent to start working without reading a single file.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 10.1 | **API surface extraction** — tree-sitter: `@app.route` (Python), `@Get` (TS/NestJS), `@GetMapping` (Java/Kotlin/Spring), `router.Handle` (Go), gRPC defs, GraphQL types; store as node metadata | feature | P0 | L |
| 10.2 | **Git history analysis** — `git log --stat` → commits per module, last_modified, top contributors, churn; nodes get `activity: hot/warm/cold/dormant` + `last_active` | feature | P0 | M |
| 10.3 | **Test mapping** — detect framework (pytest, jest, go test, JUnit, XCTest), map tests to modules by naming + imports; nodes get `test_files`, `coverage_estimate` | feature | P1 | M |
| 10.4 | **Rule severity levels** — `warn` vs `error`; `beadloom lint --strict` fails only on errors; useful for gradual adoption | feature | P1 | S |
| 10.5 | **Smart `docs polish`** — enrich `generate_polish_data()` with metadata from phases 8-10: routes, entry points, activity, tests, symbol diff | feature | P1 | M |

### Phase 11: Agent Infrastructure (v1.6)

**Goal:** Agents have full access to all validation and context tools via MCP and CLI.

**Metric:** An agent can run lint via MCP, get impact analysis (`why`), see graph diff — not just `get_context`.

| # | Task | Type | P | Effort |
|---|------|------|---|--------|
| 11.1 | **MCP tool `lint`** — run `beadloom lint` via MCP; return violations as JSON | feature | P0 | M |
| 11.2 | **MCP tool `why`** — impact analysis via MCP; upstream deps + downstream dependents | feature | P1 | S |
| 11.3 | **MCP tool `diff`** — graph changes since git ref via MCP | feature | P1 | S |
| 11.4 | **Context cost metrics** — `beadloom status` shows "average context bundle size in tokens"; benchmark: Beadloom vs raw grep | feature | P2 | S |
| 11.5 | **Deep config reading** — extract scripts, workspaces, path aliases from pyproject.toml/package.json/tsconfig.json/Cargo.toml/build.gradle/Podfile | feature | P2 | S |

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
v1.5 ──────────────────────────────────────────────────────
│
├── Phase 8 (Smart Bootstrap) ─── no dependencies
│   ├── 8.1 README ingest ──────── standalone
│   ├── 8.2 Framework detection ── standalone
│   ├── 8.3 Entry points ──────── standalone
│   ├── 8.4 Import analysis ───── reuses import_resolver.py
│   ├── 8.5 Contextual summaries ─ depends on 8.1-8.4
│   ├── 8.6 AGENTS.md in bootstrap standalone (fix UX #19)
│   └── 8.7 service-needs-parent ─ standalone
│
├── Phase 8.5 (Doc Sync v2) ──── parallel with Phase 8
│   ├── 8.5.1 Symbol-level drift ─ standalone
│   ├── 8.5.2 Doctor drift warn ── depends on 8.5.1
│   ├── 8.5.3 Symbol diff polish ─ depends on 8.5.1
│   ├── 8.5.4 Incremental fix ──── standalone (fix UX #21)
│   └── 8.5.5 setup-rules fix ──── standalone (fix UX #17)
│
└── Phase 9 (Languages) ──────── parallel with Phases 8, 8.5
    ├── 9.1 Kotlin ───────────── standalone
    ├── 9.2 Java ─────────────── standalone (parallel with 9.1)
    ├── 9.3 Swift ────────────── standalone
    ├── 9.4 C/C++ ────────────── standalone
    └── 9.5 Objective-C ──────── standalone

v1.6 ──────────────────────────────────────────────────────
│
├── Phase 10 (Deep Analysis) ── after Phases 8+9
│   ├── 10.1 API surface ──────── depends on 8.2 (frameworks)
│   ├── 10.2 Git history ──────── standalone
│   ├── 10.3 Test mapping ─────── standalone
│   ├── 10.4 Rule severity ────── standalone
│   └── 10.5 Smart docs polish ── depends on 8.5 + 10.1-10.3
│
└── Phase 11 (Agent Infra) ───── after Phase 8.5
    ├── 11.1 MCP lint ──────────── standalone
    ├── 11.2 MCP why ───────────── standalone
    ├── 11.3 MCP diff ──────────── standalone
    ├── 11.4 Context cost metrics ─ standalone
    └── 11.5 Deep config reading ── standalone

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

| Metric | v1.4 (current) | v1.5 (target) | v1.6 (target) | v1.7 (target) | v2.0 (target) |
|--------|----------------|---------------|---------------|---------------|---------------|
| **Node summaries** | "15 files" | Framework + entry points | + routes, activity | + cross-repo | + cross-repo |
| **First graph edges** | `part_of` only | `part_of` + `depends_on` | + API contracts | + inter-repo | + federated |
| **Doc drift detection** | file-hash only | **symbol-level** | + symbol diff | + cross-repo | + cross-repo |
| **Frameworks** | 4 patterns | 15+ | 15+ with routes | 15+ | + custom |
| **Languages** | 4 | **9** (+Kt, Java, Swift, C/C++, ObjC) | 9 | 9 | 9+ |
| **MCP tools** | 10 | 10 | **13** (+lint, why, diff) | 13 | 13+ |
| **Multi-repo** | No | No | No | **refs** | **federation** |
| **Search** | FTS5 | FTS5 | FTS5 | FTS5 | FTS5 + **semantic** |

---

## 8. Priority Summary

| Phase | Version | Tasks | Effort | Key outcome |
|-------|---------|-------|--------|-------------|
| **8 — Smart Bootstrap** | v1.5 | 7 | M-L | Rich graph from first `init` |
| **8.5 — Doc Sync v2** | v1.5 | 5 | M | Honest drift tracking (fix #15, #18, #21) |
| **9 — Mobile Languages** | v1.5 | 5 | M-L | +Kotlin, Java, Swift, C/C++, Obj-C |
| **10 — Deep Analysis** | v1.6 | 5 | M-L | Routes, activity, tests |
| **11 — Agent Infra** | v1.6 | 5 | M | MCP lint/why/diff, metrics |
| **12 — Cross-System** | v1.7 | 4 | L | Multi-repo refs, export |
| **13 — Full Cross + Semantic** | v2.0 | 7 | L | Federation, semantic search |
| **14 — Quality** | cross-cutting | 5 | M | Atomic writes, migrations |
| **7 — Guides** | parallel | 5 | S | Guides, demos |

**v1.5 priority:** Phases 8 + 8.5 + 9 in parallel. Three critical problems solved in one release.

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
| More languages — Java, Kotlin, Swift, C/C++ (§6a) | Phase 9 | **Elevated to v1.5** |
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

| UX Issue | Where resolved | Phase |
|----------|---------------|-------|
| #15 [HIGH] doctor 100% coverage misleading | Phase 8.5.1 + 8.5.2 | v1.5 |
| #16 [MEDIUM] beadloom's own docs outdated | Manual update (hygiene) | — |
| #17 [LOW] setup-rules auto-detect for Windsurf/Cline | Phase 8.5.5 | v1.5 |
| #18 [HIGH] sync-check "31/31 OK" despite drift | Phase 8.5.1 | v1.5 |
| #19 [MEDIUM] AGENTS.md not in bootstrap | Phase 8.6 | v1.5 |
| #20 [LOW] .beadloom/README.md no auto-update | Low priority; manual | — |
| #21 [HIGH] incremental reindex Nodes: 0 | Phase 8.5.4 | v1.5 |

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
