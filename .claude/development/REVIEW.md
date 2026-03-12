# Beadloom — Comprehensive Review

> **Author:** Claude (Opus 4.7), commissioned by the maintainer
> **Date:** 2026-05-28
> **Tone:** brutally honest audit. The goal is usefulness for the product's growth, not compliments.
> **Method:** 3 parallel analysis streams (architecture/code, product/UX, market) + independent verification of the key claims on the live system.
> **Version:** the source declares `1.9.0`; yet `beadloom doctor` itself reports "actual is 1.7.0", and `status` showed `1.8.0` — the first symptom, see §4.5.
>
> **Follow-up (2026-05-29):** After this audit, a strategy discussion clarified that Beadloom's primary goal is an **internal tool for the maintainer's team**, not external-market adoption — which reframes the market/scope critiques in §7–§8. The agreed forward direction (federation-first, opening with a Phase 0 "honesty gate") is captured in `STRATEGY-3.md`. This review is preserved as the original candid snapshot.

---

## 1. Executive Summary

Beadloom is **a technically well-built tool with a strong idea that undermines itself in three ways**: it fails its own checks, has sprawled across five product fronts with zero external audience, and bets on the one feature (compact context for agents) that the market is commoditizing fastest.

The idea — **a deterministic architecture graph as an "oracle" for AI agents + documentation-drift control + an architecture-boundary linter** — is genuinely good and rides the 2025–2026 trend (context engineering, spec-driven development, MCP). Engineering discipline is high: `mypy --strict` passes honestly, zero bare `except`, the DB is indexed, tests exist. But:

- **A tool that sells "architecture boundary enforcement" violates its own rules** — 12 violations (cycles + `infrastructure → domains`) that the maintainer did not fix but **silenced** by downgrading the rules to `severity: warn`. `lint --strict` exits with code `0` on a graph full of cycles. _(Verified live.)_
- **Diagnostic commands lie about themselves:** `doctor` reports a false version drift; `sync-check` flags correctly-annotated files as "untracked" (clean-state ceiling 60%, "workaround: none"). A product whose essence is "we tell you the truth about your code" cannot get itself to a green state.
- **Not a single external user** (7★, 0 forks, 0 issues, one committer), yet 34 epics with PRD/RFC/CONTEXT/PLAN/ACTIVE ceremonies and multi-agent rituals — a process fit for a 10-person team on a one-person project.

### Grades by dimension

| Dimension | Grade | Comment |
|-----------|:-----:|---------|
| Engineering mechanics (types, tests, DB) | **B / B+** | Real discipline, not for show |
| Architecture integrity (dogfood) | **D** | Cycles + `infrastructure` god-package, silenced via `warn` |
| Product quality / positioning | **C** | Blurred message, 4+ personas, sprawl |
| UX maturity | **C−** | ¼ of found bugs are HIGH, silent failures in the core |
| Market position | **split: C− / B+** | Context oracle — late; enforcement — early and promising |
| External adoption | **F** | No proven users besides the author |
| **Idea / potential** | **A−** | Unique combination, defensible wedge |

**Final verdict: C+ as a product today — with B-grade engineering and an A-grade idea buried under scope creep.** Beadloom's problem is not *what to build*, but that it solves the "building" problem and ignores the "earning trust" and "getting adopted" problems.

### Top 3 strengths
1. **Unique combination** of graph + arch-linting + doc-drift + context in a single Python CLI — competitors have the individual features, no one has all of them together.
2. **Human-curated YAML graph = intent, not accident.** Auto-inference (Cursor, Aider, GitNexus) gives "architecture as it turned out"; Beadloom gives "architecture as intended".
3. **Real engineering discipline:** `mypy --strict` clean on 60 files, zero bare `except`, deliberate type boundaries.

### Top 3 risks
1. **Trust collapse via false signals** (sync-check/doctor/lint lie about the product itself) — fatal for a tool whose value is trust.
2. **The premise is eroding:** 1M+ context windows and self-indexing agents (Devin, GitNexus, Codebase-Memory) eat exactly the "context oracle".
3. **Bus factor + scope creep:** one person, expanding surface, **recurring** regressions (the silent "Nodes: 0" was fixed twice).

---

## 2. What Beadloom Is (outline)

Beadloom is a Python CLI + MCP server (~25K LOC source, ~48K LOC tests, 7 packages). Operating model:

1. **Graph.** Architecture is described with YAML nodes (`service` / `domain` / `feature`) and edges (`part_of`, `depends_on`) under `.beadloom/_graph/`.
2. **Index.** Code is parsed with tree-sitter (9 languages optional), symbols stored in SQLite + FTS5.
3. **Doc-sync.** Documentation "freshness" is tracked against code (`sync-check`, stale detection).
4. **Linter.** Architecture boundary checks (layers, no cycles, no cross-layer imports).
5. **Context for agents.** `prime` (compact bundle ~9K tokens), `ctx <id>`, `why <id>` (impact analysis), plus MCP tools for IDE agents.
6. **Onboarding.** `init --bootstrap` auto-classifies an existing repository into a graph.

Marketing positioning (a problem in itself — see §4.6/§5): "Context Oracle + Doc Sync Engine" → "Architecture as Code. Context as a Service" → "Architectural Intelligence" → "architecture infrastructure".

---

## 3. Part 1 — Relevance Today and in the Future

### 3.1 The problem — real and timely
The PRD frames the pain honestly and recognizably: agents "spend 80% of tokens searching, not working"; "within a month any index starts lying"; "only two people understand how this works". These are genuine pains of AI-assisted development, and the bet that "the right context + architectural constraints produce better agent output" became consensus by 2026 (spec-driven development, context engineering).

### 3.2 Tailwinds
- **Context engineering / SDD are validated** — exactly the hypothesis Beadloom rests on.
- **MCP became the integration standard** — the MCP server plugs into Claude Code / Cursor / Windsurf without custom work. _But: "being an MCP server" is now table stakes, not differentiation._
- **The "vibe coding" hangover** — accumulating AI tech debt creates demand for tools that *enforce* architecture, not just generate code.
- **Sourcegraph Cody went enterprise-only** (~$59/user/mo), vacating the indie/startup segment of serious code intelligence.

### 3.3 Threats to relevance (by increasing severity)
1. **Growing context windows (1M+).** A slow threat: "lost in the middle" still persists (at 400K+ models noticeably lose the middle), so quality selection still beats "stuff it all in". But as long-context retrieval improves, the need for hand-curated 9K bundles falls.
2. **Self-indexing agents (acute, already arriving in 2026).** Devin indexes the repo before working; Cursor/Windsurf build a semantic index natively; Aider (repo-map with PageRank-style ranking) builds a graph on the fly. If every major agent ships auto-graph construction, Beadloom's manual YAML becomes an *onboarding burden*, not a feature.
3. **Fast OSS clones.** Direct competitors have appeared, like GitNexus and "Codebase-Memory" (tree-sitter KG via MCP) — they can absorb Beadloom's "context bundle" in a single PR.

### 3.4 Relevance verdict — **split**
- The window for **"compact context for agents"** is *closing*: Beadloom loses the race for native context selection to Cursor/agents.
- The window for **"architecture-as-code + enforcement as an AI guardrail"** is *just opening*: as AI tech debt grows, demand for *enforcement* (not visualization) of boundaries will rise, and for Python-DDD teams the mainstream has not occupied this niche.

> ⚠️ **Caveat on market data.** Some specific figures/dates from the web research (exact star counts, adoption percentages, individual sources dated after January 2026) are unverifiable and are given as *direction*, not fact. Product/category names and the general dynamics are reliable; specific metrics — take with a grain of salt.

---

## 4. Part 2 — Design Quality

### 4.1 Architecture and boundaries — **the main problem (P0)**
The tool **does not pass its own linter, and this is hidden.** `beadloom lint --strict` exits with code **0** despite 12 violations. Confirmed live (`EXIT=0`). The cause is twofold:

1. **The violations are real.** `infrastructure/reindex.py:14-16` imports `context_oracle`, `doc_sync`, `graph` at module level; in return `graph/linter.py:98` and `graph/import_resolver.py:820,882` import into `infrastructure.reindex`. The cycle is openly acknowledged in a comment `graph/linter.py:95-96`: *"Lazy import to avoid circular dependency…"*. It was worked around with function-local lazy imports instead of fixing the layers. `infrastructure` is a **god-package**: `reindex.py` (~1296 LOC) orchestrates all domains, so it sits *below* the domains by the layer rule yet *imports* all of them. **The rule is correct — the code is wrong.**
2. **The alarm was silenced.** In `.beadloom/_graph/rules.yml`: `no-dependency-cycles` → `severity: warn` (line 39), `architecture-layers` → `warn` (line 45). `--strict` only fails on `error`, so a graph full of cycles passes.

This is the single most damaging fact for the thesis: the product cannot enforce on itself what it sells.

### 4.2 Code quality and type safety — **strong**
- `mypy --strict` (`pyproject.toml:118-126`, `disallow_any_generics`, `warn_return_any`) passes clean on 60 files. Only 14 `# type: ignore` and 9 `cast()` across 25K LOC; 168 `Any` are concentrated at legitimate boundaries (YAML config, MCP protocol).
- **Zero bare `except:`**. The DB is properly indexed (`infrastructure/db.py:171-181`). The context BFS is bounded by `max_nodes`/`max_chunks` (`context_oracle/builder.py:111-208`) — bundles can't blow up.
- Incremental reindex has a genuine fallback to full (`infrastructure/reindex.py:1128-1146`).

### 4.3 Tests and reliability — **volume ≠ depth**
The 1.9:1 test-to-source ratio is **bloat, not coverage**: 2576 test functions but only **4** uses of `parametrize` (bodies are copy-pasted instead of data-driven), and **193 private-attribute accesses (`._foo`)** in tests — brittle, implementation-coupled assertions that will shatter on refactor. `test_tui.py` is 5989 LOC for a TUI (a low-value surface). It looks like chasing `fail_under=80`. The `test_hot_activity` flake was fixed correctly (relative dates), but ~10 date-dependent tests are worth auditing.

### 4.4 Performance and scalability
Fine for small/medium repositories. One bottleneck, but an important one: `_collect_code_symbols` (`builder.py:267`) runs `SELECT * FROM code_symbols` + `json.loads` for **every** symbol on **every** bundle — O(all symbols) per `prime`/`ctx`. The `bundle_cache` table exists, but `build_context` (`builder.py:377`) **does not use it**. Invisible at 506 symbols; at a 50K-symbol monorepo — latency for exactly the users the "oracle" targets.

### 4.5 Tech debt and bugs (silent failures — a class of evil of their own)
- **P1 — "Nodes: 0" in incremental reindex.** `incremental_reindex` (`reindex.py:1088-1296`) on the docs/code-only path **does not assign** `result.nodes_loaded`/`edges_loaded`, leaving the default `0`, and the CLI prints it verbatim (`cli.py:288-289`). Data is intact, but the output screams "graph is empty". This is a **recurrence**: the same bug (#21) was already "fixed" in v1.5.0 — and it came back (#88). The foundational step everything depends on has had silent "empty" failures across several releases.
- **P1 — `doctor` lies about the version.** Live: *"Version drift: CLAUDE.md claims 1.9.0, actual is 1.7.0"*, although `__init__.py:3` = `1.9.0`. The cause: `doctor` trusts `importlib.metadata.version()` (stale editable-install metadata) over the source (`infrastructure/doctor.py:274-281`). Plus a bonus inconsistency: *"MCP tool drift: AGENTS.md documents 13 tools, actual is 14"*. A diagnostic that confidently emits a wrong diagnosis erodes trust in *all* of its output.
- **P1 — `sync-check` falsely flags "untracked".** Per the UX log (#89/#90), correctly-annotated, documented files end up in `untracked_files`, clean-state ceiling "Max achievable: 60%", *"Workaround: None"*. A doc-sync engine that **cannot reach green even when the user did everything right** — a hole of trust at its very center.
- **P1 — silent 0-node on flow-style YAML.** Valid YAML `- { src: x, dst: y }` silently yields 0 nodes with no error (UX #86) — the worst class of failure in the graph loader.
- **P2 — broad `except Exception`** for "table doesn't exist yet" (`reindex.py:125,863,926`) should be `sqlite3.OperationalError`; otherwise it swallows real corruption/IO errors and silently returns `{}`.
- **"Broken out of the box":** `init --bootstrap` generates rules that immediately produce lint violations (UX #71) — onboarding fails on its own linter.

### 4.6 Design verdict
Mechanics — **B+**. Architecture integrity — **D**: a product-about-boundaries built with cycles and a god-package, where the alarm was silenced rather than removed. The "silent empty-result failure" class (reindex, YAML, sync-check) is a systemic illness for a tool whose currency is trust.

---

## 5. Part 3 — Prospects

### 5.1 Where Beadloom is genuinely differentiated (defensible wedge)
1. **The combination is unique.** Graph (like Greptile) + boundary enforcement (like import-linter) + doc-drift (like Swimm) + context bundles (like Aider) — all in a single Python CLI. *This* is the moat, not any single feature.
2. **Intent, not accident.** A curated YAML = architecture *as intended*; competitors' auto-graphs = *as it turned out*. Especially valuable for DDD teams — exactly the ones who would invest in such a tool.
3. **Enforcement, not visualization.** Most tools show dependencies; Beadloom *forbids* the disallowed ones. (Once it works on itself.)
4. **Python-specific + local + deterministic.** The same bundle every time, no cloud.

### 5.2 Where Beadloom is being commoditized
Context bundles/`prime`, tree-sitter symbol indexing, doc-drift reminders — all done natively by agents (Cursor/Windsurf/Claude Code) and OSS clones (GitNexus, Codebase-Memory). Beadloom will lose the race on this feature as a flagship.

### 5.3 Competitive map (compact)
- **Agents with native context:** Cursor (semantic index), Aider (repo-map), Claude Code (no index — *consumes* Beadloom via MCP → complementary), Windsurf, Copilot.
- **Code graph / enterprise:** Sourcegraph Cody (went enterprise-only — vacated the market), Greptile (PR review, not context feeding), Glean.
- **Doc-sync:** Swimm owns the "stale docs" narrative; Mintlify. A "vitamin" category.
- **Arch-linting:** ArchUnit (Java), dependency-cruiser (JS), **import-linter (Python — the direct incumbent)**, SonarQube, Structurizr/C4. **Python arch-linting is Beadloom's most defensible ground.**

### 5.4 Prospect risks
- **Technical:** self-inconsistency (lint/doctor/sync-check) → loss of trust; the symbol bottleneck on a monorepo; recurring regressions.
- **Product:** scope creep (5 fronts), blurred positioning, no feedback loop from real users.
- **Market:** the "context oracle" window is closing; fast OSS clones; growing context windows.

### 5.5 Prospects verdict
**Yes, but conditional on a refocus.** The strategic move: less "context oracle for AI" (crowded, commoditizing) — more **"an enforcer of architectural fitness functions that feeds AI agents"** (early, differentiated, the Python niche is open). The YAML graph is not a bug but the mechanism for encoding intent, which survives the agent's own auto-inference.

---

## 6. Part 4 — Killer Features (what to add)

All ideas are tied to the strategic refocus from §5.5 (bet on enforcement + intent), not the commoditized context.

### 6.1 🌟 "Intent vs Reality" — the diff between intent and fact *(flagship)*
Today Beadloom stores the *declared* graph (YAML) and *reads the actual* imports — but does not turn their divergence into a product. Make it the main feature: **"your implementation drifted from the intended architecture — here's where and why"**, in an agent-machine-readable form. No one combines declared-intent + measured-reality + AI-actionable remediation. _Irony as marketing: Beadloom itself currently has 12 such drifts — fix it on yourself and show it in the demo._
**Effort:** medium (the data already exists). **Impact:** defines the category.

### 6.2 CI "architectural fitness gate" with explanation for the agent
`beadloom check --ci` that **fails** on `error`-severity violations and emits not just "cycle" but *agent-actionable* context: "here's the edge, here are the files, here's how to decouple". Turns the linter into a guardrail for AI generation. **Prerequisite: pass it on yourself first** (remove the `warn` silencers, decouple `infrastructure`).
**Effort:** low-medium. **Impact:** high, squarely in the "AI tech debt" trend.

### 6.3 PR-scoped deterministic context + impact (`why` as a product)
"What context *this diff* needs and what it *touches*" — a local, deterministic analog of Greptile, but cloud-free and intent-aware. Embed it in pre-commit / PR comments.
**Effort:** medium. **Impact:** high (a daily workflow).

### 6.4 Trusted doc-drift gate
After fixing the false positives (#89/#90) — `sync-check` reachable to 100%, as a CI gate. Today the "60% ceiling" kills the feature; an honest, 100%-reachable signal makes it valuable.
**Effort:** medium (this is about *honesty*, not volume). **Impact:** restores trust in the core.

### 6.5 Live MCP tools instead of a static `prime`
Let the agent *query* the oracle while working (`why`, `impact`, `ctx`, "may I import X from Y?") — interactively, not one static bundle. This is exactly what auto-indexers can't do: *ask about intent*.
**Effort:** low-medium (MCP already exists). **Impact:** differentiation against self-indexing agents.

### 6.6 Import intent from existing standards
Read `import-linter` / `ArchUnit` / `dependency-cruiser` configs as a rule source — zero onboarding for teams that already describe their boundaries. Removes the main friction (manual YAML).
**Effort:** medium. **Impact:** removes the adoption barrier.

---

## 7. Risk & Recommendation Summary (prioritized)

| Priority | Action | Why | Effort |
|:--------:|--------|-----|:------:|
| **P0** | Decouple `infrastructure` (move reindex orchestration to a `services` layer or invert the dependency) and **remove the `warn` silencers** for cycles/layers | Pass your own `lint --strict`. Without this the product thesis is untenable | High |
| **P0** | Fix "Nodes: 0" (read live totals from the DB, `cli.py:288`), `doctor` version drift (use `__version__`, not `importlib.metadata`), `sync-check` false untracked | Silent/false signals kill trust — that's the product's currency | Low–medium |
| **P0** | Freeze the roadmap (stop STRATEGY-3) until the open HIGH bugs are closed | ¼ of found bugs are HIGH, concentrated in the newest features | — |
| **P1** | Narrow the positioning to **one** sentence and **one** persona (suggested: "an architectural fitness-enforcer for Python-DDD teams that feeds AI agents") | 4+ personas and escalating slogans ("Architectural Intelligence", "infrastructure") = a message that isn't repeatable → no word of mouth | — |
| **P1** | Fix the silent 0-node on flow-style YAML (valid YAML → explicit error or support) | The worst class of failure in the graph loader | Low |
| **P1** | Remove the tests' dependence on private attributes (193 of them) before the P0 refactor | Otherwise the architecture refactor will be hell | Medium |
| **P2** | Cache/index symbols for bundles (`bundle_cache` is unused; full-scan on every `ctx`) | Latency on a monorepo — for the target audience | Medium |
| **P2** | Cut scope creep: the TUI and part of onboarding are freeze candidates | Breadth outran depth; a single person's bandwidth | — |
| **P2** | Make a 30-second demo/asciicast and get **10 external users** | Zero external audience = the roadmap optimizes for the author, not the market | — |

---

## 8. Personal Opinion (direct)

**Should you continue? Yes — but not the way it's going.** An A-level idea, B-level engineering, C-level product execution. Beadloom makes three classic mistakes of a strong solo engineer: (1) building faster than the product can be validated with people; (2) expanding the surface instead of deepening the core; (3) wrapping a solo project in a 10-person team's process.

**The most painful observation:** a product whose sole promised value is *"we tell you the truth about your code and architecture"* **does not tell itself the truth** — `lint` green on cycles, `doctor` lying about the version, `sync-check` not reaching green. This is not cosmetic, it directly contradicts the thesis. Until `beadloom doctor && beadloom lint --strict` are honestly green on Beadloom itself, any skeptic closes the case in two commands.

**What to bet on:** **enforcement and intent**, not context bundles. "Context for agents" is a race won by Cursor and the agents themselves. "Intent vs reality + an architecture gate for the AI-generation era" is land the mainstream hasn't occupied, and which appreciates as AI tech debt accumulates.

**What NOT to do:** don't write STRATEGY-3; don't add a web dashboard / federation / plugins; don't chase "95% bootstrap accuracy" (agents are learning to self-index anyway — that's not your moat). Freeze, fix the honesty, narrow the message, ship a demo, find 10 strangers. One polished, *self-consistent* tool with one sentence beats five half-fronts.

> _(See the 2026-05-29 Follow-up note at the top: the maintainer subsequently chose to pursue federation as an internal-team tool, with an honesty-gate first. The "don't write STRATEGY-3 / don't do federation" advice above was written under the assumption of an external-adoption goal; `STRATEGY-3.md` is the refined plan. The honesty-first recommendation stands either way.)_

---

## 9. Appendix — Evidence Base

### 9.1 Code (verified by reading/running)
- **Self-rule violation:** `beadloom lint --strict` → `EXIT=0`; output contains `no-dependency-cycles:cycle:warn:...`. Downgrades: `.beadloom/_graph/rules.yml:39` (`no-dependency-cycles: warn`), `:45` (`architecture-layers: warn`), `:59` (`domain-size-limit: warn`).
- **Cycle/coupling:** `infrastructure/reindex.py:14-16` (imports domains); `graph/linter.py:98`, `graph/import_resolver.py:820,882` (reverse imports); the acknowledging comment `graph/linter.py:95-96`. `reindex.py` ~1296 LOC (god-package).
- **"Nodes: 0":** `infrastructure/reindex.py:1088-1296` (does not assign `nodes_loaded` on the docs/code-only path) → `services/cli.py:288-289` (prints the default 0). Fallback to full: `reindex.py:1128-1146`.
- **`doctor` version drift (live):** "CLAUDE.md claims 1.9.0, actual is 1.7.0" + "MCP tool drift: 13 vs 14"; source of truth `src/beadloom/__init__.py:3` = `1.9.0`; cause `infrastructure/doctor.py:274-281` (`importlib.metadata`).
- **Symbols:** `context_oracle/builder.py:267` (full-scan + `json.loads` per bundle), `:377` (`bundle_cache` unused), BFS bounds `:111-208`.
- **Broad except:** `infrastructure/reindex.py:125,863,926`.
- **Types/DB:** `pyproject.toml:118-126` (mypy strict), `infrastructure/db.py:171-181` (indexes). `mypy` → "no issues found in 60 source files".
- **Tests:** 2576 test functions, 4× `parametrize`, 193 `._private` accesses, `test_tui.py` ~5989 LOC.

### 9.2 Product/UX (from `.claude/development/`)
- Positioning drift: `PRD.md` ("Context Oracle + Doc Sync Engine") vs `README.md` ("Architecture as Code… Architectural Intelligence") vs `STRATEGY.md`/`STRATEGY-2.md` ("architecture infrastructure… scales to IT landscapes").
- UX log `BDL-UX-Issues.md`: distribution ≈21 HIGH / 41 MEDIUM / 22 LOW / 6 INFO. Key open ones: **#86** (flow-style YAML → 0 nodes), **#88** (incremental reindex → 0 nodes, recurrence of #21/v1.5.0), **#71** (bootstrap → lint violations), **#89/#90** (sync-check false untracked, "Max 60%, workaround: none"; inert `beadloom:track`), **#73** (doctor false drift), **#37/#79/#80/#85** (bootstrap accuracy 35–80%, the 95% target not built).
- Roadmap: `STRATEGY.md` (7 phases "v1.0 DONE") → `STRATEGY-2.md` (phases 8–14) → `BACKLOG.md` (dominant status "Deferred to STRATEGY-3"). PRD non-goals (web UI, embeddings, multi-repo) are now on the roadmap.
- Adoption: ~7★, 0 forks, 0 issues, one committer (per stream B; exact counts — with a grain of salt).
- Process: 34 epics (`docs/features/BDL-001..034`), up to 5 ceremony docs per epic, multi-agent rituals in `.claude/CLAUDE.md`.

### 9.3 Market (web research — direction, metrics discounted)
Competitors by category: native agent context (Cursor, Aider repo-map, Claude Code, Windsurf, Copilot); code graph/enterprise (Sourcegraph Cody — enterprise-only pivot, Greptile, Glean); doc-sync (Swimm, Mintlify); arch-linting (ArchUnit/Java, dependency-cruiser/JS, **import-linter/Python**, SonarQube, Structurizr); OSS context-oracle clones (GitNexus, "Codebase-Memory"). Trends: MCP standardization (tailwind, but table stakes), spec-driven/context-engineering (validate the premise), growing 1M+ windows (a slow threat, "lost in the middle" still holds retrieval's value), self-indexing agents (an acute threat to the context feature specifically).

> Specific figures (stars, adoption percentages, individual sources dated after Jan 2026) were produced by stream C from the web and are **not** independently verified — use as a reference, not as fact.
