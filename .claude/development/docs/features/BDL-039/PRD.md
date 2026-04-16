# PRD: BDL-039 — F3: Tool-Agnostic Enforcement Everywhere

> **Status:** Approved
> **Created:** 2026-06-01

---

## Problem

F1 gave Beadloom a federated landscape; F2 made the cross-service contract graph detect drift, breaking changes, and orphaned consumers. But detection is not **enforcement**. Today the strongest signals Beadloom produces — a GraphQL `BREAKING`, an active cross-repo `DRIFT`, a stale `AGENTS.md` that sends an agent to write code in the wrong layer — do not *block* anything. `beadloom federate` writes a report and exits `0` no matter how broken the landscape is. The per-repo gate (`beadloom-aac-lint.yml`: reindex + `lint --strict` + `sync-check`) exists, but the **landscape** gate does not, violation output is detection-only (no remediation an agent can act on), and the gate is hand-wired per repo rather than a reusable tool-agnostic component.

STRATEGY-3 principle 7 is explicit: **CI is the only true enforcement point** where every tool (Cursor, Claude Code, manual devs) converges; local rules files are mere hints. As AI agents generate code geometrically, an architecture rule that lives only in a hint file is ignored at scale — only a gate that fails the build holds the line. And principle 7's corollary (the #93 lesson): hand-maintained agent adapters drift, so the agent instructions themselves must be **verified-fresh against the graph**, not just generated once.

## Impact

F3 turns Beadloom from a *describer/detector* into an *enforcer*. Without it, F1/F2's landscape intelligence is advisory — teams and agents can ignore it, and the contract graph's drift signals never stop a bad merge. F3 is the phase where "intent-vs-reality" gains teeth: the landscape gate blocks a cross-service break before it merges, regardless of which tool or human wrote the code. It is also the last enforcement prerequisite before F4 can safely publish a living knowledge base (a dashboard built on an un-enforced, drifting landscape is a published lie).

Success criterion (STRATEGY-3 §"What done looks like"): **a CI gate blocks a boundary violation regardless of which tool (or human) wrote the code** — extended in F3 to also block a cross-service contract break and a drifted agent-config.

## Goals

- [ ] **G1 — Federated landscape gate.** `beadloom federate --fail-on <verdicts>` exits non-zero when the composed landscape contains the named verdicts (e.g. `breaking,drift,orphaned_consumer,undeclared_producer`). A safe default set; `external`/`expected`/`dead`/`unmapped` never fail. This is what lets a hub CI *block* a cross-service break (the F2 signals finally gain teeth).
- [ ] **G2 — Agent-actionable violation output.** Every gated finding (lint boundary violation, sync-check staleness, contract verdict) is emitted not just as "what + where" but with a remediation hint ("edge X→Y violates boundary B; files: …; decouple via …" / "contract C BREAKING; consumer references `field` absent from producer SDL; align or remove"). Machine-readable (JSON) + CI-native (GitHub Actions annotations) so both agents and humans consume it in their channel.
- [ ] **G3 — AgentConfigAsCode.** Extend `sync-check` to track **agent-config ↔ graph/code drift** — the auto-managed sections of `.claude/CLAUDE.md`, `.beadloom/AGENTS.md`, and generated IDE adapters (`.cursor/rules` etc.) must match the current graph (paths, layer names, domain list, rule set). Stale agent-config is a gate failure, the same way stale docs are. Generated adapters become **verified-fresh**, not just generated (principle 7 / #93).
- [ ] **G4 — Reusable tool-agnostic CI integration.** A composite **GitHub Action** (in-repo, referenceable by satellites) that runs the unified gate (reindex → `lint --strict` → `sync-check` → AgentConfigAsCode → optional `federate --fail-on`), plus a documented GitLab CI template. CI is the single convergence point for all tools/humans — the gate is identical whoever (or whatever) triggered it.
- [ ] **G5 — Dogfood (the success criterion).** Wire Beadloom's OWN CI to the F3 gate: (a) the per-repo gate blocks a deliberately-introduced boundary violation in a PR-like run with agent-actionable output; (b) a hub gate run blocks a cross-service `BREAKING`/`DRIFT` (reusing the F2 anonymized scratch landscape); (c) AgentConfigAsCode catches a deliberately-drifted `AGENTS.md`. Capture friction in `BDL-UX-Issues.md`.
- [ ] **G6 — Tech-writer (docs).** Update `docs/guides/ci-setup.md` (the landscape gate, the Action, `--fail-on`, AgentConfigAsCode), the relevant domain/SPEC docs, and CHANGELOG; STRATEGY-3 §F3 → delivered.

## Non-goals (deferred / out of scope)

- **Production artifact plumbing** (GitLab Package Registry / MinIO upload-download of `export` artifacts, registry auth, retention) — F3 ships the *gate* and a *documented* pull-based hub pattern; building the registry infrastructure is the satellites' own ops, not Beadloom code.
- **Full SARIF / GitHub Security-tab integration** — F3 emits JSON + Actions annotations; a formal SARIF report is a follow-up if a user needs the Security tab.
- **AI tech-writer in CI + VitePress knowledge base + dashboard + visual landscape map** — all F4.
- **New adapter *kinds* beyond what `setup-rules`/`setup-mcp` already generate** (Cursor/Windsurf/Cline/MCP) — F3 makes the existing ones verified-fresh, it does not add new targets.
- **REST/OpenAPI + gRPC contract sources** — still deferred (F2 non-goal, unchanged).
- **A hosted/SaaS hub** — federation stays local/CI, pull-based, no service.

## User Stories

### US-1: Block a cross-service break in CI
**As** a landscape maintainer, **I want** the hub CI to fail when `federate` finds a `BREAKING` or active `DRIFT`, **so that** a contract break is caught before merge, not in production.

**Acceptance criteria:**
- [ ] `beadloom federate --fail-on breaking,drift,...` exits non-zero on those verdicts, `0` when clean.
- [ ] `external`/`expected`/`dead`/`unmapped` never trigger a failure (no false gates).
- [ ] The failing output names the exact contract + missing/affected names.

### US-2: A gate that does not care which tool wrote the code
**As** a tech lead, **I want** one CI gate that runs identically for code written by Cursor, Claude Code, or a human, **so that** architecture rules hold regardless of authoring tool.

**Acceptance criteria:**
- [ ] A composite GitHub Action runs reindex → lint → sync-check → AgentConfigAsCode → (optional) federate gate with one non-zero exit on any failure.
- [ ] Beadloom's own CI is wired to it (dogfood).

### US-3: Agent-fixable violations
**As** an AI agent, **I want** a violation to tell me *how to fix it* (files + remediation), **so that** I can act on it without a human translating "cycle detected".

**Acceptance criteria:**
- [ ] Each gated finding carries rule, location(s), why, and a remediation hint, in machine-readable JSON.

### US-4: Agent instructions can't silently drift
**As** a maintainer, **I want** `sync-check` to fail when `AGENTS.md`/`CLAUDE.md` auto-sections no longer match the graph, **so that** agents never read stale instructions and write code in the wrong place.

**Acceptance criteria:**
- [ ] A drifted agent-config (renamed domain, changed layer, stale path) is reported as stale and fails the gate.
- [ ] Regenerating the adapter from the graph clears it.
