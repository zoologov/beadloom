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
8. **Lifecycle-aware accuracy (real codebases are messy).** Real repos carry dead, deprecated, planned, and stale-named code that misleads naive inference (validated on the F1 landscape: stale `MYSQL_*` env names while the DB is PostgreSQL; a BIM-viewer adapter present-but-unused; a core↔file-service event bridge declared-but-unbuilt; SMTP/feature-flags real-but-unmapped). Three mandates:
   - **(a) Lifecycle status on every node AND edge:** `active | planned | deprecated | dead`.
   - **(b) Three-valued intent-vs-reality** (extends principle 4): `active`+present = OK; `active`+absent = **DRIFT**; `planned`+absent = expected; `deprecated`+present = **cleanup candidate**; **undeclared**+present = **UNDECLARED** (code uses it, graph doesn't — catches the "missed SMTP/feature-flags" class).
   - **(c) Draft-then-review bootstrap, never blind auto-trust.** Code-inferred nodes/edges start `unverified`; a human/agent confirms status. Conflicts (e.g. PostgreSQL-vs-MySQL naming) are **flagged for review, not silently decided.**
   This is the answer to "messy/legacy code must not degrade Beadloom's accuracy." See `F1-landscape-analysis.md` §4bis.
9. **Universal across paradigms, products, and languages (the federation must not assume one ontology).** Beadloom federates repos that do **not** share an architectural style, a product boundary, or a language. **Two landscape scopes, both first-class:**
   - **Product-landscape** — one standalone product, federated across its own back / front / infra / integrations (this is the F1 core-monolith case).
   - **Company-landscape** — an organization with **several products**, *some integrated with each other (cross-product contracts), some fully standalone islands*. The company view composes multiple product-landscapes; cross-product edges exist only where products actually integrate, and standalone products coexist without forced linkage.

   Validated on a real second product — **Product-B** (anonymized; a separate **private** product in its own repo): mobile app (React Native/Expo, **FSD** layers `page/feature/entity/shared` + Clean Architecture), a microservice backend, a broker, GraphQL, DB, integrations, and a possible future web client. It is a *standalone* product-landscape today — not a satellite of the core-monolith one — and a candidate member of a future company-landscape. Three mandates:
   - **(a) Paradigm-agnostic kind/rule model.** The graph + rule engine must carry **arbitrary `kind`/`edge_kind`** (DDD `domain/service` *and* FSD `page/feature/entity/repository`) and rule forms beyond ours (`deny from→to` filtered by `domain` not just `kind`, `unless_edge` exceptions, `require has_edge_to`). `export`/`federate` MUST round-trip unknown kinds without loss or rejection (cf. F1 dogfood #101, where a `CHECK` wrongly forbade `produces/consumes`).
   - **(b) Nested landscape model, not one global hub.** A hub aggregates a single product-landscape *or* composes several into a company-landscape. Products/satellites that share **no** contract MUST NOT produce mutual `UNDECLARED` noise; cross-product contract edges appear only where integration is real. Federation supports N independent landscapes and their company-level rollup.
   - **(c) Language-neutral contract identity.** Cross-paradigm contracts (a TS client consuming a backend's GraphQL/AMQP) resolve on the **contract name** (GraphQL operation/type, AMQP message type) — never a language-specific code symbol. `FederatedRef` + `contract_key` must be language-neutral by design.
   Product-B's own (anonymized) refactoring strategy is the source for the FSD/Clean-Architecture details this principle is validated against. (Third-party/personal projects used to dogfood Beadloom are **always anonymized** in committed artifacts — see the anonymization rule in memory.)

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

### Phase F1 — Federation Foundation (thinnest real slice)  ✅ DELIVERED (thin slice, BDL-037, 2026-06-01)

> **Status: delivered (thin slice).** Shipped `@repo:ref_id` cross-repo identity, the `lifecycle` field (active|planned|deprecated|dead), `beadloom export` (deterministic artifact schema v1), and `beadloom federate` (hub aggregation with three-valued intent-vs-reality `EdgeVerdict`s, both-sides AMQP contract reconciliation, per-satellite staleness). Dogfooded end-to-end on the real core-monolith ↔ integration-service RabbitMQ contract — all 4 message types confirmed both-sides (UX #104). Thin-slice scope held: AMQP only, manual aggregation (no CI wiring / SaaS hub), no VitePress. Follow-ups → F2 (contract graph), F3 (CI/tool-agnostic), F4 (visual landscape). See `docs/domains/graph/features/federation/SPEC.md`.

- **Stable cross-repo node identity** (`@org/repo:NODE`) and a shared node registry.
- **Hub-and-spoke wiring:** central aggregator pulls per-repo graphs; a per-repo Beadloom remains usable standalone.
- **Temporal consistency model:** how stale is repo-B's view from repo-A? ("repo-B graph is N commits behind") — this is doc-sync at the federation level.
- **Dogfood (confirmed slice):** central hub + **core-monolith + integration-service** + their **RabbitMQ contract edge** (`start_plan_version_upload`/`ensure_plans_folder_path` ↔ `*_completed`) — the one contract confirmed on both sides. Surfaces the real hard problems on a live system, not on paper. (file-service↔core is the planned-edge follow-up; see `F1-landscape-analysis.md` §7.)

### Phase F2 — Cross-Service Contract Graph  ✅ DELIVERED (BDL-038, 2026-06-01)  🌟 (the differentiated killer feature)

> **Status: delivered.** Shipped the first-class cross-service contract graph: a `Contract` model (`graph/contracts.py`) keyed by a protocol-prefixed, **language-neutral** `contract_key` — AMQP exchange identity (`amqp:<exchange>/<routing>:<message_type>`) + GraphQL SDL (`graphql:<schema>`, `graph/sdl.py`); contract-level intent-vs-reality `ContractVerdict`s (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL` / `DEAD` / `EXPECTED`) with a **presence-based** breaking-change check (consumer `references ⊄` producer `exposed`); the `external`/`unmapped` lifecycle (U4); nested product-vs-company landscapes (U5); and paradigm-agnostic node/edge kinds (U1). Version bumps EXPORT 1→2 / FEDERATION 1→2 / DB SCHEMA 3→4, all backward-compatible. Contract-level `DRIFT` is intentionally subsumed by `ORPHANED_CONSUMER`/`UNDECLARED_PRODUCER`; `DRIFT` stays the edge-level signal. **F2 success metric met (§7): a real contract mismatch caught before it ships** — dogfooded on the real landscape, a real GraphQL `BREAKING` was caught (a consumer-referenced field absent from the producer's current SDL surface, resolved cross-language by contract name), and a separate FSD-architecture product (anonymized) round-tripped through `export`/`federate` with zero kind loss, its native bridges classified `EXTERNAL` (not DRIFT), and zero cross-pollution as a contract-less member of a company-landscape run. All U1–U5 universality requirements satisfied. Follow-ups → F3 (CI gating / tool-agnostic enforcement), F4 (visual landscape map). REST/OpenAPI + gRPC contracts remain deferred. See `docs/domains/graph/features/federation/SPEC.md`.

- **Contract-source priority (from F1 analysis):** **AMQP/event message types first** (the dominant internal fabric on the real landscape; declared sources already exist in `*/openspec/specs/*rabbitmq*`), then **GraphQL SDL** (the monolith's `schema.graphql` + Hive), then **REST/OpenAPI** (runtime-generated, no static files — lowest priority).
- **Lifecycle-tagged contract edges** (principle 8): each cross-service edge carries `active | planned | deprecated | dead` + protocol + contract-file + a "confirmed both-sides?" flag.
- **Three-valued Intent vs Reality at system level:** declared contract vs both-sides reality → `active`+present = OK; `active`+absent = **DRIFT** / "contract doesn't match on both sides"; `planned`+absent = expected (e.g. the core↔file-service bridge); `deprecated`+present = cleanup candidate; **undeclared**+present = orphaned/UNDECLARED consumer. Detects drift, breaking changes, orphaned consumers.
- This is the moat for a microservices org — bigger than any per-repo internal graph.

**Universality requirements (from the Product-B second landscape — principle 9; design these into the F2 schema *before* building the contract graph on top):**
- **U1 — Paradigm-agnostic round-trip.** `export`/`federate` carry arbitrary `kind`/`edge_kind` (FSD `page/feature/entity/repository` alongside DDD `domain/service`) with **zero loss or rejection**. Acceptance: a freshly bootstrapped FSD repo's nodes survive `export → federate` intact. Run this as a **preventive dogfood on Product-B's mobile graph** early in F2.
- **U2 — GraphQL SDL contract with client-as-consumer.** Beyond AMQP: a frontend/mobile client declares `consumes @backend:GraphQLSchema`, the backend `produces schema.graphql`; both-sides reconciliation + breaking-change/orphaned-consumer detection. First appearance of UI clients as contract consumers (F1 had Python-on-both-sides only).
- **U3 — Language-neutral `contract_key`/`FederatedRef`.** Contracts resolve on the contract name (GraphQL op/type, AMQP message type), never a code symbol — so a TS↔backend edge resolves across the language boundary.
- **U4 — `external`/`unmapped` lifecycle for non-indexed nodes.** Native bridges (Swift/Kotlin/ObjC++/C++ in Product-B's `modules/`, not scanned) and other present-but-unmapped nodes are tagged `external`/`unmapped`, **not** dropped into DRIFT/UNDECLARED. Extends principle 8.
- **U5 — Nested landscapes (product + company scope).** Product-B is a **separate product-landscape/hub**, not a satellite of the core-monolith landscape. `federate` supports both a single product-landscape and a company-landscape that composes several products (cross-product edges only where integration is real); contract-less products/satellites never cross-pollute verdicts.

**F2 tech-writer wave — README positioning rewrite (RELEASE GATE).** The current `README.md`/`README.ru.md` lead with single-repo *"Architecture as Code / Context as a Service"* (the commoditizing context-oracle framing). By the **next release** the product positioning MUST shift to the §2 sharpened line — *federated architecture infrastructure with intent-vs-reality enforcement* — with a proper **federation headline section** (cross-service contract graph, drift detection, landscape view) once F2 makes it real and no longer over-promises. Tier-1 (2026-06-01) already landed the honest interim: `export`/`federate` in the CLI table + a thin-slice federation feature bullet + factual-drift fixes (cli 29→31, edge 63→73). The headline rewrite is a **named deliverable of the F2 tech-writer bead** — do not ship the next release without it. (Owner directive 2026-06-01.) **✅ LANDED (BDL-038 BEAD-11, 2026-06-01):** both `README.md` / `README.ru.md` now lead with *"Federated architecture infrastructure with intent-vs-reality enforcement"* + a Federation headline section (cross-service contract graph, AMQP + GraphQL verdicts, nested landscapes), with an explicit honest-scope note (REST/gRPC + CI gating + visual map = future). Owner-gated for final positioning approval.

### Phase F3 — Tool-Agnostic Enforcement Everywhere
- **CI gate** as the universal enforcement point: per-repo gate + aggregated landscape gate.
- **Canonical source → generated thin adapters** for Cursor / Claude Code / MCP (never hand-edited).
- **Agent-actionable violation output:** not "cycle detected" but "edge X→Y violates boundary B; here are the files; here is how to decouple" — fed to the agent in its native channel.
- **AgentConfigAsCode — extend sync-check to the agent instructions, not just docs.** Product-B's "config-parity / zero-drift rule" (from its refactoring strategy) treats stale `CLAUDE.md`/`AGENTS.md`/`commands` as a *process bug* — agents read drifted instructions and write code in the wrong place. Make `sync-check` track **agent-config ↔ code/graph drift** (paths, layer names, role protocols), the same way it tracks doc↔code drift. Natural extension of principle 7 (the generated-adapter discipline that #93 was about): the adapters become *verified-fresh*, not just generated. Federated CI then asserts each satellite's instructions match its own graph.

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
4. attest baseline (mark_synced) for reviewed pairs
5. beadloom reindex && sync-check && lint --strict   → verify drift closed (honest ≠ complete guardrail)
6. open PR with the doc diff → team/human review → merge → VitePress builds
```

> **Loop invariant (learned in the BDL-UX#99 dogfood, 2026-06-01): sync-check must be re-run *after* attest, not before.** Staleness reasons have priority: `hash_changed`/`symbols_changed` mask `untracked_files` (source-coverage gaps) on the same pair. Clearing the high-priority reasons (via `mark_synced`) **surfaces second-order gaps** that were invisible in the initial scan — e.g. a sibling source file missing its `# beadloom:domain=` annotation. The loop is therefore not single-pass: iterate steps 4–5 until sync-check is *stably* 0, treating each newly surfaced reason as fresh scope. `docs ai-refresh` must encode this re-check-to-fixpoint, or it will report a false "0" after the first pass.

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

**Resolved during F1 discovery (2026-05-31, owner-confirmed — see `F1-landscape-analysis.md` §8):**
- ✅ **Contract source priority (was Q3):** **AMQP/event message types first**, then GraphQL SDL, then REST.
- ✅ **Hub ownership (was Q4):** a **new dedicated repo**; aggregation **via CI/CD, pull-based** (satellites publish commit-SHA-tagged `beadloom export` artifacts to GitLab Package Registry / MinIO; hub CI pulls + composes + validates + publishes). On-push from satellites + nightly cron.
- ✅ **F1 first slice:** **core-monolith ↔ integration-service** (RabbitMQ, the one both-sides-confirmed contract).

**Resolved 2026-06-01 (owner-confirmed):**
- ✅ **Multiple products + two landscape scopes (was the implicit single-landscape assumption):** Beadloom must be **universal** across (1) a **product-landscape** — one standalone product across its back/front/infra/integrations, and (2) a **company-landscape** — several products, some integrated via cross-product contracts, some standalone islands. Confirmed second product: **Product-B** (anonymized; a separate private product — mobile RN/Expo FSD + microservice backend + broker + GraphQL + DB + integrations + possible future web). It is **not** a satellite of the core-monolith landscape; it is a standalone product-landscape and a future company-landscape member. → encoded as **principle 9** + F2 requirements **U1–U5**. Product-B becomes the **second dogfood landscape** for F2 (proves paradigm-agnosticism on a real FSD repo, not just on paper).

**Still open:**
1. **Monorepo workspaces** alongside multi-repo? (Confirmed multi-repo microservices; no monorepo packages identified among the 4 repos so far — revisit if one appears. Strategy 2 task 13.4.)
2. **Who maintains the per-repo graph** as the team + agents generate code fast? (Drives how urgent the principle-8 lifecycle/draft-review tooling is — likely F1/F2-critical.)
3. **Hub artifact schema & CI cadence detail:** exact `beadloom export` federation format + trigger wiring — an F1 design task.
4. **UNDECLARED sweep:** complete the landscape (SMTP, feature-flags already found unmapped; verify error-tracking / video / secrets-manager / directory / Redis-pubsub; BIM-viewer adapter = `deprecated`) so nothing is missed — the owner's explicit "don't miss anything" requirement.
5. **Actualize Product-B's own refactoring strategy** to the modernized process (it still references the retired `commands/dev|review|test|tech-writer.md` slash-role model; Beadloom now uses `agents/*` subagents + `swarm`/`gate`). When Beadloom is initialized there (its Phase 7), install the **new** process, not the old one. Separate task (owner-flagged).

---

## 9. Next Step

Run `/task-init` to turn **Phase 0 (Foundation/Honesty Gate)** into the next epic — it is the prerequisite for everything else and is mostly cheap, high-credibility fixes. Federation phases (F1+) become subsequent epics, each proven on a thin live slice before broadening.

> **Process note:** the multi-agent dev process was modernized for Beads 1.0.4 + Claude Code in **BDL-035** (`.claude/agents/*` role subagents, `bd swarm`/`gate`/`merge-slot`, `Agent` tool). Phase 0 (Epic 2) is the first epic executed *through* that modernized process — its real dogfood.
