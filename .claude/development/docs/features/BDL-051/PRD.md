# PRD: BDL-051 (EPIC) — Beadloom governs itself

> **Status:** Approved
> **Created:** 2026-06-11
> **Type:** epic (3 sub-feature threads, each a trunk-based slice/PR)
> **Roadmap:** raised above BDL-052 (AI tech-writer speed) — graph honesty is the product's core.

---

## Problem

Beadloom's value proposition is **honest, complete architecture-as-code** — yet it does not fully apply that to *itself*. Three concrete gaps (owner-identified):

1. **No clear "feature" definition → domain sprawl.** A graph node is a `feature` only if its code carries `# beadloom:feature=Y` and it's declared in `services.yml`; otherwise a module is attributed to its domain and **dumped into `docs/domains/<X>/README.md`**. Result: `onboarding` has **9 modules but only 2 features** (`doc-generator`, `agent-prime`) — `config_sync` (the config-check engine), `branch_protection` (`setup-branch-protection`), `agentic_flow_setup` (`setup-agentic-flow`), `ai_techwriter_setup` (`setup-ai-techwriter`), `presets`, `config_reader` are real capabilities left **unregistered + invisible**. Nothing flags this; over time every domain becomes a dump. (The existing `domain-size-limit` warn — `graph` 202>200 symbols — is a symptom, not a model.)
2. **The AI tech-writer harness is outside Beadloom's own governance.** `tools/ai_techwriter/` is **structurally invisible** — `.beadloom/config.yml scan_paths: [src]` only — so it has no graph node, no symbols, no `sync-check`, no DDD-boundary lint. Real production code (what *runs* the AI-tech-writer feature) is exempt from the architecture honesty Beadloom sells. Cobbler's children.
3. **The packaged multi-agent flow (BDL-048) isn't actually used by Beadloom.** The MCP process-tools (`task_init`/`bead_context`/`complete_bead`/`checkpoint`) exist but the coordinator shells `bd` directly + edits docs by hand; `checkpoint`/`complete_bead` don't maintain the `ACTIVE.md` bead-status **table** → the systemic ACTIVE-staleness the owner caught across BDL-047..050. Beadloom doesn't dogfood its own flow.

## Impact

Make Beadloom **govern itself**: a clear feature/domain model + a lint that prevents sprawl, the AI-agent harness brought into the graph as a first-class domain, and the project fully adopting its own packaged flow. This (a) raises the product's core promise on its own codebase (the strongest possible dogfood + demo), and (b) makes the architecture graph complete + trustworthy for the team.

**Honest boundary (BDL-048 G4, non-negotiable):** "full migration to the packaged flow" = the coordinator/main-loop **uses** the 4 deterministic MCP process-tools + the `.claude/` flow + the ACTIVE-table fix. **Orchestration (spawning dev/test/review subagents) stays in the main loop** — MCP cannot spawn sub-agents. We do not claim "the flow runs inside MCP."

Success criterion: **(A)** a documented feature/domain definition + a `beadloom lint` rule that flags unregistered-feature / domain-sprawl, with `onboarding` (and every domain audited) re-modeled so no real capability is invisible; **(B)** `src/beadloom/ai_agents/ai_techwriter/` is a graph-tracked domain (symbols, `sync-check`, lint, a SPEC), CI green on the new module path; **(C)** Beadloom's own dev loop runs through the process-tools and `ACTIVE.md` stays current by construction — all dogfooded, all green on the consolidated `ci.yml`.

## Goals

### Thread A — Graph modeling discipline (the core)
- [ ] **G1 — Define "feature" vs "domain-level module"** (documented, e.g. in the architecture doc + the agentic-flow/templates guidance). Domain = a DDD package (`src/beadloom/<pkg>/`). Feature = a cohesive, independently-describable capability with its own `SPEC.md` (typically a CLI command or a distinct subsystem with its own contract). Pure plumbing/shared-helpers stay domain-level **but must appear in the domain README module-list** — never invisible.
- [ ] **G2 — Sprawl / unregistered-feature lint.** A `beadloom lint` rule (in `rules.yml` + `rule_engine`) that flags: a domain with many symbols/modules but few features, AND/OR a module that backs a distinct CLI command (or is otherwise SPEC-worthy) but carries no `# beadloom:feature=`. Output names the candidate(s); severity `warn` (advisory, not a hard CI fail unless configured).
- [ ] **G3 — Re-model `onboarding` + audit all 6 domains.** Register the genuine onboarding features (config-check/config-sync, branch-protection, agentic-flow-setup, ai-techwriter-setup, presets/import as warranted) as feature nodes with SPECs; ensure every remaining module is at least listed in the domain README. Audit `context-oracle`/`doc-sync`/`graph`/`infrastructure`/`application` for the same sprawl; fix or explicitly accept each.

### Thread B — `ai_agents` domain
- [ ] **G4 — Move the harness into the graph.** `tools/ai_techwriter/` → `src/beadloom/ai_agents/ai_techwriter/` (generalized domain `ai_agents` for future CI agents). Annotate (`# beadloom:domain=ai_agents`, `# beadloom:feature=ai-techwriter`), declare nodes in `services.yml`, give it a `SPEC.md`. It is then scanned (under `src/`), gets symbols, `sync-check`, and DDD-boundary lint.
- [ ] **G5 — No regression in the running feature.** Update all imports, the vendored harness assets, and the **`ci.yml` invocation path** (`python -m tools.ai_techwriter` → the new module path) so the AI tech-writer keeps working end-to-end (BDL-049/050 model intact). Add an `ai_agents` boundary rule (what it may import).

### Thread C — Full migration to the packaged flow (dogfood)
- [ ] **G6 — Use the process-tools.** Beadloom's own dev loop adopts `task_init`/`bead_context`/`complete_bead`/`checkpoint` for the deterministic steps (the coordinator calls them instead of hand-rolling `bd` + docs).
- [ ] **G7 — Fix ACTIVE.md maintenance.** `checkpoint` and `complete_bead` update the `ACTIVE.md` bead-status **table** (flip the bead's row) deterministically — not just append a note — closing the systemic staleness. The status table becomes correct by construction.
- [ ] **G8 — Docs/CHANGELOG/ROADMAP** for the above + renumber the speed work to **BDL-052**.

## Non-goals (out of scope)

- **Orchestration in MCP** (sub-agent spawning / main-loop control) — structurally impossible; stays main-loop (BDL-048 G4).
- **Re-litigating the BDL-049/050 CI model** — preserved as-is; B only moves the harness's module path.
- **The AI tech-writer SPEED optimization** — that's **BDL-052** (non-blocking, parallelism, cli.py over-scoping, caching); this epic is about graph honesty + self-adoption, not latency.
- **Model tiering** (principle 10).
- **A universal auto-feature-detector** — the sprawl lint is advisory (flags candidates); a human/agent decides what becomes a feature.

## Open architecture questions (→ resolved in the RFC)

1. **Sprawl-lint heuristic** — symbol/module-count threshold per domain? "module backs a CLI command with no feature=" detection (how to map a module → a Click command)? Severity (warn-only vs configurable).
2. **`ai_agents` placement** — does the vendored-template/`setup-ai-techwriter` story change when the harness lives in `src/` (it currently vendors `tools/ai_techwriter/*.py.txt`)? How does the scaffold ship the harness to adopters now?
3. **Which onboarding modules become features** vs stay domain-level (config_reader/presets borderline) — the concrete re-model list.
4. **Process-tools adoption depth** — do we wire `checkpoint`/`complete_bead` ACTIVE-table maintenance into the MCP tools (code), and/or into the coordinator command (process)? Both?
5. **Slice order + per-slice PRs** — A-definition+lint first (so B/onboarding re-model are checked by it), then B (ai_agents move proves the discipline on a real domain), then onboarding re-model, then C.

## User stories

### US-1: No invisible capabilities
**As** the maintainer, **I want** a clear feature definition + a lint that flags unregistered features/sprawl, **so that** a domain like `onboarding` can't silently accumulate 7 unregistered capabilities in one README.
**Acceptance:** `beadloom lint` flags the onboarding sprawl today; after re-modeling, every real capability is a feature (SPEC) or an explicitly-listed domain module; the lint is clean (or warns only on accepted cases).

### US-2: The AI agent harness is governed like everything else
**As** the maintainer, **I want** the AI tech-writer harness in `src/beadloom/ai_agents/`, **so that** it has graph symbols, sync-check, DDD boundaries, and a SPEC — no exempt production code.
**Acceptance:** `beadloom ctx ai-techwriter` resolves; `sync-check` covers it; `lint --strict` enforces its boundaries; the CI ai-techwriter job runs the new module path and stays green.

### US-3: Beadloom runs on its own packaged flow
**As** the maintainer, **I want** our dev loop to use the MCP process-tools with `ACTIVE.md` kept current by construction, **so that** Beadloom is the first full consumer of its own flow and the status table never goes stale again.
**Acceptance:** `complete_bead`/`checkpoint` maintain the ACTIVE bead-status table; a real BDL-051 slice is driven through the process-tools end-to-end.
