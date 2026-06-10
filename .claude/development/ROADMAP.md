# Beadloom Roadmap (post-v1.10.0)

> The single forward-looking planning doc. Pure engineering debt & bugs live in `BDL-UX-Issues.md` (cross-referenced).
> Built from a revision of the historical strategy/review docs (now under `archive/`) + a spot-check of REVIEW-2 against HEAD.
> Baseline: v1.10.0, 91.6% coverage, mypy --strict clean, `sync-check` 0 stale.
> Item format: **[Pn] Name** — what/why. _Source; verification status._

---

## Vision & fit (the north-star that drives prioritization)

Beadloom is an **honest, effective tool**, not a marketing product. Market / hype / external-stranger adoption are **explicitly not goals**. Priorities are ranked by usefulness to two uses only:

- **(a) Solo multi-agent dev flow** — the stack **Claude Code + Beadloom + Beads + GitHub**. The #1 value: stably building large/complex projects solo + an AI fleet. Dogfooded on a complex private project (`Product-B`, anonymized). → **agentic cluster = P0**.
- **(b) Team of solos** — each member runs the same solo-flow on their own service/microservice, all federated into one product. This is the federation / landscape use-case. → **integration-map-with-data = P1**.

**Prioritization rule:** every P0/P1 item must serve (a) or (b). Items that serve only adoption/market (marketplace publish, VS Code extension, marketing guides, non-scale semantic search, plugin ecosystem) are consciously demoted to P3 and flagged "off-north-star".

---

## 0. Sequencing principles (from STRATEGY-3 §3/§6)

1. **One end-to-end thread at a time, made honest before the next.** The #1 risk is single-maintainer capacity — do not spread fronts.
2. **Honest ≠ complete; dogfood = acceptance.** Every shippable keeps Beadloom green on its own `doctor / lint --strict / sync-check / ci`. A published lie is worse than a missing feature.
3. **Intent-vs-reality is the moat, not context bundles** (context is commoditizing).
4. **Federation multiplies dishonesty by N repos** — single-repo honesty is a prerequisite for cross-repo depth.
5. **Tool-agnostic: a canonical source → generated thin adapters; CI is the only true enforcement point.**
6. **Lifecycle-aware / draft-then-review** — code-inferred nodes start unverified; conflicts are flagged, not silently decided.
7. **Universal** (paradigm/product/language-agnostic).
8. **Thin slice + dogfood** before broadening.
9. **Semantics are tied to scale** (1000+ nodes), not single-repo.
10. **Bet on top-tier models + tools — no model tiering.** Stable doc/agent quality is the priority; downgrading model grades risks drift and coverage gaps. Beadloom deliberately runs its agentic features on top-tier models.

**Moat:** the only free/MIT/self-hosted tool delivering the *bundle* federated-contracts + polyglot-enforcement + doc-sync + agentic maintenance loop + honest-by-construction portal. The integration of the whole loop is what's defensible.

---

## P0 — Agentic cluster (serves north-star "a": solo multi-agent flow)

> Internal order: F4.1 first (most scoped; exercises the Goose+Beadloom-MCP pairing), then packaging generalizes it. One "agentics" thread, not three parallel ones.

- **[P0] ✅ F4.1 — AI tech-writer in CI, on Goose. SHIPPED (BDL-047, 2026-06-10).** Closed scoped loop: `sync-check` detects drift → the **Goose agent** (Qwen3.7-Plus) repairs ONLY the drifted nodes (tool-use: `beadloom ctx/why`, reading neighbouring code/diffs) → re-check to fixpoint → PR/MR for review. Runs on **push to main/master** (+ manual). Dual-platform (GitHub Actions + GitLab CI) on a self-hosted VPS runner; dogfood-proven (refresh PR merged). Stack: **Goose + Qwen3.7-Plus (external API) + Beadloom** (Beads is NOT in the F4.1 runtime). Delivered: the deterministic harness `tools/ai_techwriter/`; `beadloom sync-check --since <ref>` (fresh-checkout/per-push drift); non-interactive `beadloom sync-update --yes/--all` (closes UX #106); `beadloom setup-ai-techwriter --platform {github,gitlab}` + a hardened `provision-runner.sh`; the G9 honest run-record + dashboard widget (tokens = fact, $ = labeled estimate); the getting-started guide.
  - **Decision: Goose, not a thin script.** Good docs need dynamic code exploration (not one-shot); Goose is the substrate for a future Beadloom-agent fleet; MCP-native = direct access to Beadloom tools.
  - **CI safety** (non-determinism bounded by the gate): pin Goose version + recipe; constrained tool surface (read-only code + Beadloom + write only to `docs/`); turn/token budget caps; sandboxed job; **no auto-merge** — PR only; acceptance = `sync-check`→0 + `beadloom ci`, else retry N / open PR flagged "needs human". The agent's output is a proposal; the deterministic gate is the truth.
  - **Follow-ups surfaced by the epic:**
    - `beadloom ci` / the landscape gate could adopt `--since` (same fresh-clone blindness `sync-check --since` fixed — so the gate also catches per-push drift, not just the AI tech-writer harness).
    - The **GitLab path** is wired + scaffolded but still to be validated end-to-end on the team's private GitLab repo (Beadloom itself is on GitHub; the GitHub path is dogfood-proven).
    - The epic's **own code introduced cli/doc-sync doc drift** (the new `--since` / `--yes` / `setup-ai-techwriter` surface) — a candidate for a wide-`--since` AI-tech-writer run to refresh it (or the manual refresh done in this docs wave).
  - _Source: STRATEGY-3 F4.1; REVIEW-2 §1/§5/§8._
- **[P0] ✅ Agentic-flow packaging. SHIPPED (BDL-048, 2026-06-10).** `beadloom setup-agentic-flow` (setup-* family) scaffolds the proven flow into any repo — `.claude/agents/{dev,test,review,tech-writer}.md` + `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` vendored **byte-identical** to the live flow (drift-guarded) + the per-project `CLAUDE.md` auto-regions; idempotent; `config-check` now drift-checks/restores those flow files. Plus four **MCP process-tools** (catalog 14 → 18): `task_init` (docs folder + valid 4-role bead-DAG), `bead_context` (ctx+why+CONTEXT/ACTIVE+active rules in one call), `complete_bead` (**gate that REFUSES to close on a red `beadloom ci` + tests**, closes on green), `checkpoint` — callable from any MCP client (tool-agnostic via `setup-mcp`), behind the mockable `services/bd_seam.py`. Strengthens north-star (a): the stack is reproducible + tool-agnostic. **Honest boundary:** MCP serves deterministic process-tools, NOT orchestration — the coordinator + Agent-spawn stay Claude-Code-native; `complete_bead` is advisory-strong; the single source of TRUE enforcement remains `beadloom ci` in CI.
  - **Follow-ups / notes:**
    - **MCP `prompts` deferred** (tools-only v1) — porting the coordinator/role personas as MCP prompts is a later optional slice (client support uneven in 2026); the `.claude/` scaffold already delivers those personas Claude-Code-native.
    - The pre-existing lint **WARN `graph` 202 > 200 symbols** is a separate BDL-UX item (not introduced by BDL-048; non-blocking advisory).
    - The scaffolded `CLAUDE.md` version uses Beadloom's `__version__` (per BDL-UX #92).
  - _Source: REVIEW-2 §7/§8._
- **[P0, optional] Flow instrumentation.** Self-metrics (review-rejection rate, fix-cycles/epic, bead cycle-time) → another honest-by-construction showcase. _Source: REVIEW-2 §7. (Model tiering explicitly rejected — see principle 10.)_

**Future agent fleet (rationale for the Goose substrate; NOT built now):** auto-bootstrap reviewer (P1 `unverified`→YAML), UNDECLARED-sweep triager (P1), PR-bot explainer (P2), BREAKING-verdict summarizer. These make the Goose runtime amortizable.

---

## P1 — Integration map with data (serves north-star "b": team / microservices)

> One coherent epic cluster: "see your microservices product and what flows in it." **Field/type pop-ups technically require semantic extraction** — so the viz carries Tier A + AsyncAPI with it (an AMQP message body is not in the code).

- **[P1] Richer landscape viz (Cytoscape/D3) + clickable contracts.** Interactive landscape replacing Mermaid: clickable nodes/edges, **contract pop-up card** (type/routing/protocol/verdict/producer-consumer). The team is actively asking for a good graph view; Mermaid can't do rich pop-ups — that's the argument for D3. _Source: REVIEW-2 §5, BDL-040; team request._
- **[P1] Field-level contract data (what "flows" between services).** The pop-up shows real **fields and types** of the payload: GraphQL **Tier A** (parse SDL to fields/types/args via `graphql-core` behind an optional extra) + AMQP **AsyncAPI/JSON-Schema** body declaration. This is the data-flow / interface map (DFD) the team wants — to understand what data moves between services and systems. Also removes the worst false-CONFIRMED of presence-check. _Source: team request + REVIEW-2 §6.1 (Tier A)._
- **[P1] Live cross-repo `ctx` (F1 honesty debt).** The claimed F1 metric is not actually met: `ctx AUTH` should show `@repo-B:BILLING`, but cross-repo identity lives only in `export/federate`, not in bundles. Directly serves (b): an agent on service A sees the contract with service B. _Source: STRATEGY-2 Ph13.1 / STRATEGY-3 F1-metric._
- **[P1] UNDECLARED sweep + `unverified` lifecycle + review-gated bootstrap.** Accuracy of the team's shared landscape: an automated pass over real-but-undeclared integrations; code-inferred nodes start `unverified`, conflicts flagged (anti-"MySQL-mistake"). The F2 accuracy moat. _Source: F1 §4bis/§8, STRATEGY-3 OQ#4._
- **[P1] Tier C — verdict federation** (`buf breaking` / `graphql-inspector` / Pact `can-i-deploy` → `ContractVerdict`). The real moat: Beadloom unifies Pact+Buf+GraphOS+AMQP into ONE landscape with ONE gate. PoC on one protocol. _Source: REVIEW-2 §6.1/§6.3._
- **[P1] Atomic YAML writes** (temp + `os.replace`). Safety of the graph the whole flow depends on. _Source: STRATEGY-2 Ph15.1._

---

## P2 — Deepen federation + team coordination (serves "b")

- **[P2] Ownership from CODEOWNERS + drift-check.** `owner`/`team` derived from CODEOWNERS/git-blame (not a rotting `catalog-info.yaml`); owner-vs-reality detection. Answers "who to call when a contract breaks." _REVIEW-2 §6.2._
- **[P2] PR-bot / GitHub App.** Inline comment: "edge X→Y violates a layer rule" / "contract Z became BREAKING for @backend". Pairs with F4.1. _REVIEW-2 §5, REVIEW §6.3._
- **[P2] REST/OpenAPI contract source.** The most-requested deferred contract type. _F1 §8, STRATEGY-3 F2._
- **[P2] Federation-MCP server.** Neighbouring-service/contract context to an agent via MCP. _REVIEW-2 §5._
- **[P2] Blast radius:** `beadloom why <contract> --landscape` — who breaks across all repos. _REVIEW-2 §5._
- **[P2] Arch/governance scorecard.** Per-service readiness from existing inputs (lint/debt/doc-freshness/verdicts/cycles). Do NOT pull in Sonar/PagerDuty/SLO. _REVIEW-2 §6.2._
- **[P2] Architecture drift over time (decay report)** on top of snapshot+metrics_history. _REVIEW-2 §5._
- **[P2] Auto-bootstrap graph from code (finish the WIP)** — hybrid "inferred + intent layer", tied to `unverified`. _REVIEW-2 §5._
- **[P2] Schema-migration framework (versioned)** — currently ad-hoc bumps. _STRATEGY-2 Ph15.2._

---

## P3 — Off-north-star / on demand (consciously demoted)

> Serve adoption/market or hygiene, not (a)/(b) directly. Raise only if a concrete need appears.

- **[P3] Import intent from import-linter/ArchUnit/dependency-cruiser** (lower the manual-YAML barrier). _REVIEW §6.6._
- **[P3] Guides & demos** (onboarding/multi-agent/keep-docs-alive + demo). _STRATEGY-1/2 Ph7._
- **[P3] Semantic search** (sqlite-vec/fastembed) — only at scale (1000+ nodes). _STRATEGY-2 Ph14._
- **[P3] Semantic docs audit** (cut `docs audit` false-positives). _STRATEGY-2 Ph14.8._
- **[P3] Misc (market/hygiene/on-demand):** publish GH Action to marketplace · VS Code extension · gRPC/AsyncAPI/proto sources · monorepo workspace · richer-viz beyond P1 · TUI graph view / ASCII graph · plugin system · daemon · pre-commit-framework hook · Bitbucket recipes · property-based tests · perf benchmarks · re-export resolution · CLI "did-you-mean" · code similarity · data-ownership/ER · cross-system user-flow · per-system C4 decomposition · remote graph refs / full federation protocol.

---

## Technical debt & bugfixes (→ tracked in BDL-UX-Issues.md; registry + cross-refs here)

> Pure debt/bugs live in BDL-UX-Issues.md. The repository-layer + connection items gate growth (before large refactors / scale).

**Code (REVIEW-2 §2, verified at HEAD):**
- **[HIGH] Repository layer + connection context-managers (fixes 2 HIGHs at once).** Raw `conn.execute` across **36 files** (incl. `tui/data_providers.py` — presentation reading SQLite); `SELECT ref_id, kind, summary FROM nodes` hardcoded **16×**. `open_db` with **no `with`/`closing` anywhere** → leaks + ResourceWarnings. → `infrastructure/repository.py` + a connection context-manager. _("53 open_db" from the review is off: 27 in src / 232 total; the leak pattern is real.)_
- **[HIGH] N+1 in `doc_sync/engine.py:451-525`** (`check_source_coverage`) + non-indexable `LIKE '%…%'` → quadratic. _Confirmed._
- **[MEDIUM] Cycle detection `rule_engine.py:1141-1209`** — no global visited, `neighbor in path` is O(n), bounded only by `max_depth=10`. → Tarjan/Johnson or WHITE/GREY/BLACK + global visited. _Confirmed (a per-rule `seen_cycles` dedup exists; no global visited)._
- **[MEDIUM] Split god-domains: extract `federation`+`rules` from `graph/`** (6439 lines; clears the graph-202 lint warning); `application/` 233. _Confirmed exactly._
- **[MEDIUM] God-functions:** `cli.py:status` ~283 → `application/status.py`; `scanner.bootstrap_project` ~260; `reindex.incremental_reindex` ~216; `scanner.interactive_init` ~203.
- **[LOW] `Any` concentration in onboarding** (172; doc_generator 49/scanner 25/config_reader 19) → TypedDict; exception swallowing (7×).
- **[P2-debt] Context cache not wired into `build_context`** (`builder.py` `SELECT * FROM code_symbols` per bundle; L2 not called). _REVIEW §4.4._

**Tests (REVIEW-2 §3 / REVIEW §4.3):** ResourceWarnings → conftest yield+finally fixtures; make tree-sitter grammars mandatory in CI (else TS/Go/Rust silently green); parametrization (10 across 3211); private-attribute test coupling (**372** — remove before refactors); TUI smoke tests without asserts; no `pytest-randomly`.

**Docs (REVIEW-2 §4, verified — HIGH):**
- **[HIGH] Rule types:** `getting-started.md:127` + `architecture.md` (×4) list **dataclass names** instead of real YAML keys (`deny, require, forbid, forbid_cycles, forbid_import, layers, check`). `README.md:186` is correct (internal contradiction). → single source of truth.
- `getting-started.md:29` — non-existent flag `--non-interactive` (only `-y/--yes`).
- `architecture.md:9` — "six DDD domains" but lists five.
- `CONTRIBUTING.md` — `your-org` placeholders; no release-process section.

---

## Won't do (anti-scope)

- Built-in LLM / bundled weights (F4.1 = external model only).
- Model tiering / downgrading roles to cheaper models (principle 10 — risks drift/quality gaps).
- Live web app / SaaS hub (the portal is static, CI-generated; federation is a pull-based CI pattern).
- Plugin marketplace.
- DSL/OPA-Rego rules; autofix patches; Slack/Discord; a separate cross-reference report (covered by `why`).
- **Backstage replacement** — instead, **feed Backstage** (emit `catalog-info.yaml`).
- Full bootstrap-accuracy upfront; C# (no dogfood); pattern detection (LLMs do it better); dependency-weight analysis.

---

## Close formally (spec-vs-reality / superseded)

- **`sync-update --auto` + `llm:` config** — built then removed (v0.6), replaced by agent-native MCP write tools. Remove from specs.
- **`init --scope`** — specified (PRD §4.1 / RFC §5.4) but never built. **Decision: not building it.** Superseded by a future Goose-based `init` (an agent with its own scenarios/rules). Remove `--scope` from the spec.
- **BACKLOG.md** is stale (frozen at v1.5.0) — superseded by this ROADMAP; archived.
