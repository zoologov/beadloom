# Beadloom: Strategy 3 — Federated Architecture Infrastructure for Multi-Service Landscapes

> **Status:** Vision draft (2026-05-29). Supersedes the "Deferred to STRATEGY-3" backlog in STRATEGY-2.
> **Inputs:** `.claude/development/STRATEGY.md`, `STRATEGY-2.md`, the 2026-05 architecture/code review (`.claude/development/REVIEW.md`), and the maintainer's stated vision.
> **One-line bet:** In the agentic era, agent-generated code grows geometrically. Beadloom becomes the **federated source of truth** that keeps an entire microservices landscape's architecture, boundaries, rules, and documentation **honest and queryable — for every agent and every human, in every repo.**

---

## 1. Strategic Context

**What Strategy 1 & 2 delivered:** a full single-repo Architecture-as-Code platform — graph, Context Oracle, Doc Sync, architecture lint, MCP server, C4 diagrams, debt report, TUI. The single-repo pipeline works.

**The shift Strategy 3 makes:** from a single-repo *tool* to a **federated system-of-record for a microservices landscape** spanning Backend / Frontend / DevOps / Infra. The unit of value is no longer one repo's internal graph — it is the **cross-service contract graph** and a single **"one context for everyone"** that every AI tool and every human shares.

**The honest reckoning (why Phase 0 exists):** the 2026-05 review found Beadloom currently **fails its own checks** — `lint --strict` exits 0 on a graph with 12 real cycles (rules downgraded to `warn`), `doctor` reports a false version drift, `sync-check` cannot reach green even when everything is annotated. **You cannot build distributed enforcement and doc-sync on a core that is not self-honest.** Federation multiplies any dishonesty by N repos. So Strategy 3 opens with a Foundation/Honesty Gate, not a feature.

**The maintainer's goals (verbatim intent):**
- Reduce token spend on grepping and reliance on probabilistic "semantics" for project understanding.
- Achieve **stable** AI understanding via AaC + DocAsCode = a single, stable source of truth.
- **One context for everyone:** all AI agents (Cursor, Claude Code) and manual devs follow the same architecture, rules, and boundaries, with Beadloom as the watcher — tool-agnostic.
- A **VitePress** knowledge base (features, schemas, architecture, integrations, modules) maintained by an **AI tech-writer in CI/CD** with team/human review.
- Beadloom enforces AaC + DocAsCode in **CI/CD**.

---

## 2. North Star & Positioning

**Sharpened positioning:** *federated architecture infrastructure with intent-vs-reality enforcement* — **not** a context-bundle oracle. Context bundles are commoditizing (agents self-index); the durable moat is **intent + enforcement + the diff between intent and reality**, especially across service boundaries.

**Why this is the right bet (validated):** the market window for "compact context for agents" is closing (Cursor/Aider/agents do it natively); the window for "architecture enforcement as an AI guardrail" is *opening* as AI-generated tech debt accumulates. Agents can auto-build a code map (reality); they cannot invent your *intended* architecture, rules, and boundaries (intent). That human/team intent — enforced everywhere — is the moat.

---

## 3. Design Principles (extending Strategy 2)

1. **Honest ≠ complete.** Ship with gaps and say "not covered yet / unknown." Never assert "all green" when it isn't. Trust is the product.
2. **Self-consistent.** Beadloom must pass its own `doctor` / `lint --strict` / `sync-check`. Dogfood is the acceptance test, not a nice-to-have.
3. **Federation multiplies trust *and* dishonesty.** Single-repo honesty is a hard prerequisite for any cross-repo feature.
4. **Intent vs Reality is the moat.** Declared graph/contracts vs measured imports/calls. Make the *diff* the product, so the source of truth is self-correcting (the cure for "lying docs").
5. **Hub-and-spoke.** Autonomous per-repo Beadloom instances own their slice; a central aggregator pulls and composes the landscape. Repos remain the source of truth for their own nodes.
6. **Ship + dogfood on the real landscape.** Prove each capability on the maintainer's actual microservices via the thinnest end-to-end thread before broadening.
7. **Tool-agnostic via canonical source → generated thin adapters.** One source (graph + generated AGENTS.md/rules) → thin, *generated* per-tool adapters (`.cursor/rules`, `CLAUDE.md`, MCP). Never hand-maintain adapters (that is how AGENTS.md drifted, #93). **CI is the only true enforcement point** where all tools and manual devs converge; local rules files are *hints*.

---

## 4. Roadmap

### Phase 0 — Foundation / Honesty Gate  ⛔ PREREQUISITE (mostly cheap)

The narrow subset of `BDL-UX-Issues.md` that MUST close before federation work. NOT the whole backlog — gating on the full bootstrap-accuracy program (#80 et al.) would be the "polish forever" trap and contradicts ship-and-dogfood.

| Issue | Why it blocks Strategy 3 |
|-------|--------------------------|
| **#91** (CRITICAL) | Make the rule engine real: fix the `infrastructure` god-package coupling; restore `no-dependency-cycles` / `architecture-layers` to `severity: error`. Cannot federate a linter that does not enforce. |
| **#86 / #88 / #94** | Eliminate silent/empty/swallowed failures. #86 (flow-style YAML → 0 nodes) multiplies with hand-edited per-repo graphs. |
| **#89 / #90** | sync-check must be honest and reach 100%; track markers must work. The entire VitePress/AI-techwriter pipeline (Phase F4) amplifies whatever sync-check says. |
| **#92 / #73 / #93** | doctor + AGENTS.md must tell the truth. AGENTS.md drift undermines tool-agnostic distribution. |
| **#71** | Clean out-of-the-box. Once rules are `error`, every newly federated repo fails its own gate on day one unless bootstrap produces a clean graph. |
| (#96) | Fold test de-brittling into the #91 refactor (193 private-attr assertions will otherwise make it painful). |

**Exit criterion:** `beadloom doctor && beadloom lint --strict && beadloom sync-check` are *honestly* green on Beadloom itself **and** on a freshly bootstrapped real repo.

**Explicitly NOT gated (iterate live during federation):** bootstrap-accuracy program (#74/75/77/78/80/81/82/83/84/85), #95 (perf — only when dogfooding hits it), ergonomics (#72/76/87). INFO/metrics entries (#79/#85/#37) are observations, not closable bugs.

### Phase F1 — Federation Foundation (thinnest real slice)
- **Stable cross-repo node identity** (`@org/repo:NODE`) and a shared node registry.
- **Hub-and-spoke wiring:** central aggregator pulls per-repo graphs; a per-repo Beadloom remains usable standalone.
- **Temporal consistency model:** how stale is repo-B's view from repo-A? ("repo-B graph is N commits behind") — this is doc-sync at the federation level.
- **Dogfood:** central hub + 2 of the maintainer's real services + 1 cross-service edge. This surfaces the real hard problems on a live system, not on paper.

### Phase F2 — Cross-Service Contract Graph  🌟 (the differentiated killer feature)
- **Polyglot contract edges:** OpenAPI, GraphQL schema, protobuf/gRPC, async/event contracts.
- **Intent vs Reality at system level:** declared integration contract vs actual calls → detect drift, breaking changes, orphaned consumers, and "the contract does not match on both sides."
- This is the moat for a microservices org — bigger than any per-repo internal graph.

### Phase F3 — Tool-Agnostic Enforcement Everywhere
- **CI gate** as the universal enforcement point: per-repo gate + aggregated landscape gate.
- **Canonical source → generated thin adapters** for Cursor / Claude Code / MCP (never hand-edited).
- **Agent-actionable violation output:** not "cycle detected" but "edge X→Y violates boundary B; here are the files; here is how to decouple" — fed to the agent in its native channel.

### Phase F4 — Living Knowledge Base + Visual Landscape (DocAsCode + VitePress)

Three deliverables: (1) an AI tech-writer that keeps docs fresh in CI, (2) a VitePress knowledge base + AaC/DocAsCode metrics dashboard, (3) 🌟 the **visual IT-landscape map** — the federated contract graph (F2) rendered as an interactive system map. Hard dependency on **Phase 0** (honesty) and **F2** (the landscape data): a KB/dashboard built on a false-positive sync-check or a toothless lint is a *published lie* — worse than none.

**F4.1 — AI tech-writer in CI (OSS, efficiency-first)**

Efficiency comes from **scoping, not the model**:
- Trigger generation **only for drifted nodes** (sync-check / intent-vs-reality) — patch N nodes, never the whole repo.
- Feed the model Beadloom's **structured `docs polish --json`** (graph + symbols + deps), not raw files → small prompt, better output, a small model suffices.
- Stays compliant with the "no built-in LLM" principle: Beadloom **orchestrates an external model** (API or self-hosted service), it does not bundle weights.

The loop:
```
1. beadloom reindex (incremental)
2. beadloom sync-check --json              → drifted nodes = scope
3. per node: docs polish <node> --json → prompt → model → docs/<node>.md
4. beadloom reindex && sync-check && lint --strict   → verify drift closed (honest ≠ complete guardrail)
5. open PR with the doc diff → team/human review → merge → VitePress builds
```

- **Orchestration:** prefer a thin script shipped as `beadloom docs ai-refresh` (the `docs polish` hook already exists); Aider as an alternative driver. Avoid heavy agent frameworks (LangChain/CrewAI) in CI — latency + nondeterminism for a structured-in→structured-out task.
- **Model tiers:** (1) **hosted small** (Haiku / mini / DeepSeek / Flash) — best runner-resource efficiency, no GPU, $/token bounded by drift-scope; (2) **self-hosted open-weight** (Qwen-Coder / Llama / Mistral 7–14B) via **vLLM / Ollama as a long-lived inference service** (never load weights per job) — fully OSS, private; (3) **hybrid** — local for bulk, escalate to hosted only when the post-check still flags drift.

**F4.2 — VitePress knowledge base + AaC/DocAsCode dashboard**

- VitePress = the **published, versioned, URL-shareable source of truth** for humans AND agents (read MD/URL). Static generator: built in CI, not live — freshness = rebuild on push.
- Content: features, schemas, architecture, integrations, modules; **C4 + Mermaid render natively** (already generated).
- Dashboard (generated MD/JSON per build): lint violations + trend, debt score, doc coverage, stale count, sync-check %, per-service health + landscape rollup; interactive widgets via Vue (filterable tables, charts).
- Thin integration: **`beadloom export --vitepress`** (the natural home for the Strategy-2 `export` stub, 13.3) generates a VitePress-ready `docs/` tree. Beadloom produces, VitePress renders — do not let rendering polish become a scope sink.

**F4.3 — 🌟 Visual IT-landscape map (the federation front-end)**

- An **interactive, clickable system map** of the whole landscape: services as nodes, contract edges (OpenAPI/GraphQL/gRPC/events) between them, drift/health overlays — the visual rendering of the **F2** contract graph (Vue + Cytoscape/D3/Mermaid).
- This is a **web** artifact, not a terminal one — VitePress is the right home and arguably better than the TUI for the landscape view. "One glance, whole system" for humans; structured MD/URL for agents — directly serves "one context for everyone."

**Division of labor — TUI vs VitePress (keep clean, don't duplicate):**
- **TUI** = the engineer's *live, per-repo workstation* (real-time, interactive, over SSH) — "what's happening now."
- **VitePress** = the team's *published, landscape-wide source of truth* (versioned, URL, human + agent readable) — "the agreed state," and the channel for non-TUI users (PMs, new devs, other teams, URL-reading agents).

### Phase F5 — Scale & Extensions (later)
- #95 bundle/cache performance (when dogfooding hits scale).
- Semantic search across the federated graph (Strategy 2 Phase 14).
- DevOps / Infra nodes (Terraform / k8s / pipelines) as a schema extension — added last (most scope-expanding).

---

## 5. What Strategy 3 explicitly does NOT do yet (anti-scope-creep)

- No full bootstrap-accuracy program upfront — improve heuristics *while onboarding real repos*.
- No **live/standalone web app**, no plugin marketplace, no **built-in** LLM. (The F4 VitePress dashboard + landscape map is a *static, CI-generated site*, and the AI tech-writer calls an *external* model — both compliant with Strategy 2's "no built-in LLM / no SaaS" principle.)
- DevOps/Infra graph nodes deferred to F5.
- Semantic layer **frozen** until F1–F4 are solid. (TUI stays as the live per-repo workstation per F4's division of labor; no *new* TUI surface until the federation core is solid.)

---

## 6. The Capacity Reality (the #1 risk)

This is a **platform-scale** ambition (federation × BE/FE/DevOps/Infra + polyglot contracts + AI-techwriter-in-CI + tool-agnostic adapters + an honest core) carried by **one maintainer**. The risk is not technical correctness — it is surface area outrunning the maintainer and trust eroding from half-finished fronts. The only survival strategy: **one end-to-end thread at a time, each made honest before the next, dogfooded on the real landscape.**

---

## 7. Success Metrics

| Phase | Metric |
|-------|--------|
| 0 | Beadloom green on its own `doctor`/`lint --strict`/`sync-check`; a fresh-bootstrapped repo is green out of the box. |
| F1 | `beadloom ctx AUTH` in repo-A shows a dependency on `@repo-B:BILLING`. |
| F2 | Beadloom detects a real contract mismatch between two of the maintainer's services *before it ships*. |
| F3 | CI gate blocks a boundary violation regardless of which tool (or human) wrote the code. |
| F4 | A VitePress KB that stays ≥95% fresh automatically, with human review only on drifted nodes. |

---

## 8. Open Questions

1. **Monorepo workspaces** alongside multi-repo? (Maintainer confirmed multi-repo microservices; confirm whether any monorepo packages also need isolated graphs — Strategy 2 task 13.4.)
2. **Who maintains the per-repo graph** as the team + agents generate code fast? (Determines how urgent "intent vs reality" auto-drift is — likely F2-critical.)
3. **Contract source priority** for F2: OpenAPI first? GraphQL? gRPC/protobuf? events? (Drive by which integrations dominate the maintainer's landscape.)
4. **Hub ownership:** is the central Beadloom repo a separate repo the team owns, and who triggers aggregation (CI cron? on per-repo push?).

---

## 9. Next Step

Run `/task-init` to turn **Phase 0 (Foundation/Honesty Gate)** into the next epic — it is the prerequisite for everything else and is mostly cheap, high-credibility fixes. Federation phases (F1+) become subsequent epics, each proven on a thin live slice before broadening.

> **Process note:** the multi-agent dev process was modernized for Beads 1.0.4 + Claude Code in **BDL-035** (`.claude/agents/*` role subagents, `bd swarm`/`gate`/`merge-slot`, `Agent` tool). Phase 0 (Epic 2) is the first epic executed *through* that modernized process — its real dogfood.
