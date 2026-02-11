# Beadloom: Strategy & Improvement Plan

> **Status:** Completed (all 6 development phases delivered)
> **Date:** 2026-02-11
> **Current version:** 1.0.0 (Production/Stable)

---

## 1. Positioning

### Problem statement

IDE indexers (Cursor, Copilot) answer the question **"where is this code?"**
Beadloom answers a different question: **"what is this feature in the context of the entire system, and can I trust the documentation?"**

### Core message

> **IDE searches code. Beadloom manages knowledge.**

### Design principle: Agent-native, not agent-replacement

Beadloom is an **infrastructure layer for agents**, not an agent itself. It provides data (context bundles), structure (graph), tracking (sync state), and rules (constraints). The intelligence comes from whatever agent the developer already uses — Claude Code, Cursor, Codex, etc.

This means:
- **No built-in LLM calls** — Beadloom stays deterministic and free of API key configuration
- **No extra costs** — the agent the developer already pays for does the thinking
- **Vendor-agnostic** — works with any agent that speaks MCP (or reads CLI output)
- **Clean separation** — Beadloom = data + rules, Agent = intelligence + action

Beadloom teaches agents how to work with it via instruction files (`.beadloom/AGENTS.md`), following the pattern established by steveyegge/beads.

### Why this matters

| Pain | Who feels it | How Beadloom solves it |
|------|-------------|----------------------|
| "Nobody understands the full system except 2 people" | Tech Lead / Architect | Knowledge graph makes architecture explicit and queryable |
| "Docs are always outdated, nobody trusts them" | Entire team | Doc Sync Engine detects stale docs on every commit |
| "AI agents hallucinate because they grab random context" | DevEx / Platform Eng | Deterministic graph traversal — same query, same result, every time |
| "New developer needs 2 weeks to understand the system" | Engineering Manager | `beadloom ctx DOMAIN` gives a structured context bundle in seconds |
| "Every agent session starts from scratch" | Individual Developer | MCP server delivers ready-made context — zero search tokens |

### Key differentiator: Deterministic Context

Cursor/Copilot use **probabilistic** semantic search — the LLM decides what's relevant.
Beadloom uses **deterministic** BFS traversal over an explicit graph — the team decides what's relevant.

This means:
- **Reproducible** — same query always returns the same context bundle
- **Auditable** — the graph is YAML in Git, reviewable in PRs
- **Trustworthy** — no "the AI thought this file was relevant but it wasn't"

### Target audience (in priority order)

1. **Tech Lead / Architect** — wants architecture knowledge to live in the repo, not in one person's head
2. **Platform / DevEx Engineer** — builds tooling infrastructure for the team
3. **Individual Developer** — wants to understand unfamiliar code faster and trust documentation

---

## 2. Roadmap

### Phase 1: Foundation & Agent-Native Pivot (v0.3) — DONE

**Goal:** Establish the agent-native architecture and clean up the codebase before building new features.

**Rationale:** These items are foundational — they define how agents interact with Beadloom and won't need revision as features evolve. Do them once, do them now.

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 1.1 | **Rewrite README** — new positioning, one-liners, "Why Beadloom?" section | docs | P0 | S |
| 1.2 | **README.ru.md** — Russian translation | docs | P0 | S |
| 1.3 | **AGENTS.md** — agent instruction file for Beadloom workflows (doc sync, context usage, annotation conventions) | docs+code | P0 | S |
| 1.4 | **Deprecate `--auto` LLM integration** — remove `llm_updater.py` and LLM SDK dependencies | code | P0 | S |
| 1.5 | **Update cli-reference.md** — reflect agent-native workflow, remove LLM config docs | docs | P1 | S |

### Phase 2: Lower the Barrier (v0.4) — DONE

**Goal:** From `pip install` to useful context in under 5 minutes, on any project.

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 2.1 | **Architecture presets** — `beadloom init --preset {monolith,microservices,monorepo}` | feature | P1 | M |
| 2.2 | **Smarter bootstrap** — infer domains from directory structure, detect common patterns (controllers/services/models) | feature | P1 | M |
| 2.3 | **Zero-doc mode** — explicitly support and document "no Markdown files at all" workflow | feature | P1 | S |
| 2.4 | **Interactive bootstrap review** — after auto-generating graph, show it in terminal and let user confirm/edit nodes | feature | P2 | M |

### Phase 3: Team Adoption (v0.5) — DONE

**Goal:** Make Beadloom useful for the whole team, not just the person who set it up.

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 3.1 | **CI integration** — `beadloom sync-check` as GitHub Action / GitLab CI template, posts PR comment with stale docs summary | feature | P0 | M |
| 3.2 | **Architecture health dashboard** in `beadloom status` — % features with docs, % stale docs, undocumented domains, coverage trend | feature | P1 | S |
| 3.3 | **Issue tracker linking** — `beadloom link AUTH-001 https://github.com/org/repo/issues/123` to connect graph nodes to Jira/GitHub/Linear | feature | P2 | S |
| 3.4 | **MCP templates** — ready-made `.mcp.json` snippets for Cursor, Claude Code, Windsurf | docs | P1 | S |

### Phase 4: Performance & Agent-Native Evolution (v0.6) — DONE

**Goal:** Make Beadloom fast, searchable, and fully agent-native — with no LLM API dependency.

**RFC:** [RFC-0005](docs/features/BDL-005/RFC.md) — Accepted

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 4.1 | **L1 cache integration in MCP** — connect existing ContextCache to MCP server for token savings on repeated requests | feature | P0 | S |
| 4.2 | **Incremental reindex** — `file_index` table tracks hashes, only re-process changed files; `--full` for full rebuild | feature | P0 | L |
| 4.3 | **Auto-reindex in MCP** — detect stale index on tool call, auto-trigger incremental reindex before responding | feature | P1 | S |
| 4.4 | **Bundle caching in SQLite** — persistent L2 cache (`bundle_cache` table) survives MCP server restarts | feature | P1 | M |
| 4.5 | **MCP write tools** — `update_node` (modify YAML + SQLite), `mark_synced` (reset sync state), `search` (fuzzy query) | feature | P1 | M |
| 4.6 | **Semantic search** — FTS5 built-in + sqlite-vec/fastembed optional; new `beadloom search` command + MCP tool | feature | P2 | L |
| 4.7 | **Remove LLM API** — delete `--auto` flag entirely, clean up all LLM references | cleanup | P0 | S |
| 4.8 | **AGENTS.md update** — reflect write tools, remove llm_updater references, update file tree | docs | P1 | S |

### Phase 5: Developer Experience (v0.7) — DONE

**Goal:** Make Beadloom a joy to use, not just useful.

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 5.1 | **TUI** — `beadloom ui` interactive terminal dashboard (graph explorer, node details, status overview) | feature | P1 | L |
| 5.2 | **Graph diff** — `beadloom diff` shows what changed in the graph since last commit/tag | feature | P2 | M |
| 5.3 | **`beadloom why REF_ID`** — explain a node's role in the system (upstream/downstream, who depends on it, what breaks if it changes) | feature | P2 | M |
| 5.4 | **Watch mode** — `beadloom watch` auto-reindexes on file changes during development | feature | P3 | M |

### Phase 6: Architecture as Code & Ecosystem (v1.0) — DONE

**Goal:** Beadloom evolves from "architecture documentation" to a full **Architecture as Code** platform — where architecture is not just described, but validated, enforced, and delivered to AI agents as executable constraints.

**Vision:** Today Beadloom **describes** architecture (graph) and **delivers** context (Oracle). Phase 6 adds **enforcement** — making Beadloom the only tool that combines architecture definition, validation, context delivery, and doc sync in a single local-first package. This positions Beadloom as a foundational tool for agentic development: agents receive not just context ("here's how the system works") but also constraints ("here's what you must not violate").

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 6.1 | **Architecture rules & lint** — `beadloom lint` validates code against graph boundaries (e.g., "billing must not import from auth directly") | feature | P0 | L |
| 6.2 | **Constraint language** — declarative rules in YAML alongside the graph (`rules.yml`: allowed/forbidden edges, dependency constraints, naming conventions) | feature | P0 | L |
| 6.3 | **Agent-aware constraints** — MCP `get_context` returns not just context but also active constraints for the node, so agents respect architectural boundaries by design | feature | P1 | M |
| 6.4 | **CI architecture gate** — `beadloom lint` as a CI check that blocks PRs violating architecture rules | feature | P1 | M |
| 6.5 | **Multi-repo support** — federated graphs across repositories | feature | P1 | L |
| 6.6 | **Plugin system** — custom node kinds, edge types, indexers, rule types | feature | P2 | L |
| 6.7 | **Web dashboard** — read-only visualization of the knowledge graph for non-CLI users | feature | P3 | L |

### Phase 7: Messaging & Use-Case Guides (post-development)

**Goal:** Tell the story of the finished product. Write guides and demos that reflect the final UX.

**Rationale:** Use-case guides describe real workflows with real output. Writing them before features stabilize means rewriting them after every phase. The README (positioning) is done — it doesn't describe features. Guides and demos should wait until the product is stable.

| # | Item | Type | Priority | Effort |
|---|------|------|----------|--------|
| 7.1 | **Use-case guide: "Onboarding a new developer in 1 day"** | docs | P1 | S |
| 7.2 | **Use-case guide: "Multi-agent workflow with Beadloom + Claude Code"** | docs | P1 | S |
| 7.3 | **Use-case guide: "Keeping docs alive in a fast-moving codebase"** | docs | P1 | S |
| 7.4 | **Quick demo GIF/asciicast** for README | docs | P1 | S |
| 7.5 | **Update README.ru.md** to match any README changes from development phases | docs | P1 | S |

---

## 3. README Rewrite Plan (COMPLETED)

README rewritten in commits `f9933d3` and `c9b5d49`. See README.md and README.ru.md.

---

## 4. Feature Details

### 4.1 Architecture Presets (Phase 2)

**Problem:** `beadloom init --bootstrap` generates a flat list of "service" nodes from directory structure. This is a starting point, but lacks architectural meaning.

**Solution:** Presets provide opinionated graph templates for common architectures:

```bash
beadloom init --preset monolith
# Generates: domains (inferred from top-level dirs), features (from subdirs),
# a single "core" service node, entity nodes from model files

beadloom init --preset microservices
# Generates: service nodes (one per service dir), domain groupings,
# API boundary nodes, shared entity detection

beadloom init --preset monorepo
# Generates: package nodes, dependency edges (from package.json/pyproject.toml),
# shared library nodes, app-level domain grouping
```

Each preset includes:
- Node generation rules (what becomes a domain, service, feature, entity)
- Edge inference rules (how to detect relationships)
- A README template for the generated graph explaining conventions
- Suggested annotation patterns for the codebase

### 4.2 CI Integration (Phase 3)

**Problem:** `beadloom sync-check` works locally but isn't integrated into team workflows.

**Solution:** GitHub Action + GitLab CI template:

```yaml
# .github/workflows/beadloom-sync.yml
name: Doc Sync Check
on: [pull_request]
jobs:
  sync-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: beadloom/sync-check-action@v1
        with:
          comment: true  # Posts stale docs summary as PR comment
          fail-on-stale: false  # Or true to block merge
```

PR comment example:
```
📚 Beadloom Doc Sync Report

2 stale documents detected:
- docs/domains/auth/features/AUTH-001/SPEC.md — code changed in src/auth/login.py (3 days ago)
- docs/domains/billing/README.md — code changed in src/billing/invoice.py (1 week ago)

Run `beadloom sync-update AUTH-001` to review and update.
```

### 4.3 TUI (Phase 4)

**Problem:** Graph exploration requires mental model building from CLI text output.

**Solution:** `beadloom ui` — interactive terminal dashboard built with Textual:

```
┌─ Beadloom ──────────────────────────────────────────────┐
│ ┌─ Domains ─────────┐ ┌─ auth (domain) ───────────────┐ │
│ │ > auth          ◉  │ │ Features: 3  Services: 2     │ │
│ │   billing       ◉  │ │ Doc coverage: 67%  Stale: 1  │ │
│ │   notifications ○  │ │                               │ │
│ │   payments      ◉  │ │ Nodes:                        │ │
│ │                    │ │   AUTH-001 login       ◉ docs │ │
│ │ ◉ = has docs       │ │   AUTH-002 oauth       ◉ docs │ │
│ │ ○ = no docs        │ │   AUTH-003 2fa         ○      │ │
│ │                    │ │   user-service     [service]  │ │
│ │                    │ │   session-service  [service]  │ │
│ └────────────────────┘ └───────────────────────────────┘ │
│ ┌─ Graph ──────────────────────────────────────────────┐ │
│ │  auth ──part_of──> user-service ──uses──> sessions   │ │
│ │    └──depends_on──> billing                          │ │
│ └──────────────────────────────────────────────────────┘ │
│ [Enter] View context  [/] Search  [g] Full graph  [q] Quit│
└─────────────────────────────────────────────────────────┘
```

Technology: **Textual** (Python TUI framework, same ecosystem, rich rendering).

### 4.4 Architecture as Code (Phase 5)

**Problem:** Beadloom describes architecture (graph) and delivers context (Oracle), but doesn't enforce architectural rules. Agents receive context about how the system works, but nothing prevents them from violating architectural boundaries. Traditional AaC tools (ArchUnit, Deptrac) enforce rules but don't deliver context to agents. No tool does both.

**Solution:** Turn Beadloom's knowledge graph into an enforceable architecture definition:

**Rules language** (`.beadloom/_graph/rules.yml`):

```yaml
rules:
  - name: billing-auth-boundary
    description: "Billing must not import from auth directly — use events"
    deny:
      from: { kind: service, ref_id: billing }
      to: { kind: service, ref_id: auth }
      edge: imports

  - name: domain-isolation
    description: "Services must not cross domain boundaries without an explicit edge"
    deny:
      from: { kind: service }
      to: { kind: service }
      unless_edge: [depends_on, uses]

  - name: adr-required-for-new-services
    description: "Every new service node must have an associated ADR"
    require:
      for: { kind: service }
      has_edge_to: { kind: adr }
```

**CLI:**

```bash
# Validate code against architecture rules
beadloom lint
# ✗ billing-auth-boundary: src/billing/invoice.py imports src/auth/tokens.py
# ✗ adr-required-for-new-services: service "notifications" has no associated ADR
# 2 violations found

# Validate in CI (exit code 1 on violations)
beadloom lint --strict
```

**Agent-aware constraints** — `get_context("AUTH-001")` returns:

```json
{
  "graph": { ... },
  "docs": [ ... ],
  "code_symbols": [ ... ],
  "constraints": [
    {
      "rule": "billing-auth-boundary",
      "description": "Billing must not import from auth directly — use events",
      "scope": "auth"
    }
  ]
}
```

Agents receive constraints alongside context and can respect them autonomously — without a human reviewer catching violations after the fact.

**Why this is unique:** Existing AaC landscape:

| Tool | Describes | Validates | Delivers to agents | Tracks docs |
|------|-----------|-----------|-------------------|-------------|
| Structurizr (C4) | Yes (DSL) | No | No | No |
| ArchUnit / Deptrac | No | Yes (code tests) | No | No |
| Backstage | Yes (catalog) | No | No | No |
| **Beadloom v1.0** | **Yes (YAML graph)** | **Yes (lint)** | **Yes (MCP + constraints)** | **Yes (Sync Engine)** |

Beadloom becomes the first tool that closes the full loop: **describe → validate → deliver → keep in sync**.

---

## 5. Success Metrics

| Metric | Current | Target (v0.5) | Target (v1.0) |
|--------|---------|---------------|----------------|
| GitHub stars | — | 500 | 2,000 |
| PyPI weekly downloads | — | 200 | 1,000 |
| Time from install to first `ctx` output | ~10 min | < 5 min | < 2 min |
| README "Why?" clarity | weak | strong | strong |
| Use-case guides | 0 | 3 | 5+ |
| CI integration templates | 0 | 2 (GH + GL) | 3+ |

---

## 6. Priority Summary — All Phases Complete

| Phase | Version | Status |
|-------|---------|--------|
| 1 — Foundation | v0.3 | DONE |
| 2 — Lower the Barrier | v0.4 | DONE |
| 3 — Team Adoption | v0.5 | DONE |
| 4 — Performance | v0.6 | DONE |
| 5 — Developer Experience | v0.7 | DONE |
| 6 — Architecture as Code | v1.0 | DONE |
| 7 — Messaging & Guides | post-dev | Planned |

**Current totals:** 18 CLI commands, 8 MCP tools, 653 tests, 21 modules, 4 languages in import resolver.

**Next steps:** See `BACKLOG.md` for deferred work and `STRATEGY-2.md` (planned) for the next roadmap.

---

## Open Questions — Resolved

| # | Question | Answer | Phase |
|---|----------|--------|-------|
| 1 | Presets scope? | 3 presets (monolith, microservices, monorepo) | Phase 2 |
| 2 | TUI framework? | Textual — full-featured, pure-Python, async | Phase 5 |
| 3 | CI action? | Docs recipe with `beadloom sync-check --porcelain` | Phase 3 |
| 4 | Naming? | "Knowledge Graph" (used consistently in docs) | Phase 1 |
| 5 | Pricing model? | Fully open (MIT) | — |
| 6 | AaC rule engine? | YAML deny/require — simple, PR-reviewable | Phase 6 |
| 7 | AaC scope? | Import-boundary validation (Python, TS/JS, Go, Rust) | Phase 6 |
