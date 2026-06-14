# PRD: BDL-052 (EPIC) — Usable doc-flow: tool-agnostic local authoring + Gate enforcement + CI fallback boost

> **Status:** Approved
> **Created:** 2026-06-14
> **Type:** epic
> **Supersedes:** the stub bead `beadloom-parl` ("AI tech-writer speed"); folds the BDL-053 follow-up `beadloom-cugq`.
> **Note:** materially re-scoped from the first draft (the "non-blocking / post-merge" model was rejected in design discussion — see Decisions). Re-approval needed.

---

## Problem

The AI tech-writer is not yet usable in daily team flow, and the doc-freshness invariant isn't formalized as reproducible tooling:

1. **The CI agent was on the merge critical path.** It's a required check running Goose+Qwen on a self-hosted runner (~15min on a wide PR). On EVERY BDL-051 slice we had to `[skip ai-techwriter]` to merge — defeating the point. Root cause of our pain: we deferred all docs to one end-of-epic pass and skipped, instead of authoring docs in-flow per push.
2. **Doc authoring wasn't part of the local loop as a tool.** Docs were treated as an afterthought (a final tech-writer bead) rather than a formalized step the flow always runs before push. The invariant "no merged code without current docs" depended on discipline/memory, not a tool.
3. **The flow is Claude-Code-only.** The agentic flow (`.claude/`) is shipped as Beadloom's philosophy, but it binds to one tool. It must work on the USER's agent — Claude Code, Cursor, etc.
4. **Wide scope + slow CI agent when it does run.** A god-file edit (`cli.py`) drifts ~15 docs (file-level drift detection); the CI agent's per-doc Goose sessions are sequential; CI setup is uncached.

## Impact

Ship the doc-flow as a **stable, reproducible, tool-agnostic set of TOOLS** that guarantees **"no code reaches `main` without current documentation"** by construction — while being fast in daily use. The philosophy: *no methodology an agent must "remember" — only tools that work the same every time.*

The model (settled in discussion):

- **Local authoring is primary, on the user's own agent.** The Beadloom agentic flow (`/task-init → /coordinator → dev → test → review → tech-writer → push → Beadloom Gate`) runs on whatever coding agent the user has (Claude Code, Cursor, …). The **tech-writer step authors docs locally via that agent** — NOT a local Goose+Qwen (Goose+Qwen is the server/CI combo; pointless to stand it up locally when the dev is already in Claude Code/Cursor).
- **The Beadloom Gate is the enforcement tool.** Pre-push, `beadloom ci` (reindex→lint→coverage-lint→sync-check→doctor) runs as a **blocking** hook: a red Gate (incl. doc drift) blocks the push; the **coordinator then runs the tech-writer, re-gates, and only a green Gate proceeds to PR/MR**. An agent literally cannot "forget" docs — the tool won't let the push through.
- **The CI ai-techwriter stays UNCHANGED as a fallback** (BDL-049/050, Goose+Qwen on the self-hosted runner). It runs only when a PR/MR arrives **not passing the Gate** (stale/missing docs slipped through — e.g. an external contributor, or someone who bypassed the local flow); then it fixes them, mandatorily. Because the local Gate makes that rare, the CI agent's latency is rarely hit.
- **Speed for when an agent does run** (local OR CI): tighter scope (only docs whose changed symbols matter) + a faster CI agent (parallel sessions, cached setup).

Success: the daily flow needs no `[skip]`; `main` never holds code without current docs (Gate-enforced both locally + on CI); the flow runs on Claude Code AND Cursor; doc runs are scoped (no god-file fan-out) and the CI fallback is fast when it fires.

## Goals

### Thread A — Formalize the flow as reproducible tools
- [ ] **G1 — The flow is tools, not memory.** Every step (`task-init`, `coordinator`, `dev/test/review/tech-writer`, `push→Gate`) is a formalized, deterministic tool/skill invocation — reproducible for any user, no "remembered methodology". Document + ship it as the standard.
- [ ] **G2 — Pre-push Beadloom Gate hook (blocking).** `beadloom install-hooks` installs a **pre-push** hook running `beadloom ci`; a red Gate blocks the push with a clear, actionable message. (Distinct from the existing pre-commit hook.)
- [ ] **G3 — Coordinator enforcement loop.** `/coordinator` formalizes: dev→test→review→tech-writer→push→Gate; **Gate red → run tech-writer → re-Gate → (green) → PR/MR**. Encoded in the skill (a tool), not agent discipline.

### Thread B — Tool-agnostic local flow
- [ ] **G4 — Run on the user's agent (Claude Code, Cursor, …).** The flow + roles (task-init/coordinator/dev/test/review/tech-writer) work on multiple coding agents, not just `.claude/`. (RFC: AGENTS.md / generic role defs + per-tool adapters; setup scaffolds the right files for the chosen tool.) The local tech-writer is the user's agent performing the tech-writer role — no local Goose+Qwen.

### Thread C — Scope precision (shared by local + CI)
- [ ] **G5 — Changed-symbol → doc mapping.** Narrow the stale set from "changed *file* → all its doc pairs" to "doc references a *changed symbol*" (Beadloom `code_symbols`), conservative fallback (ambiguous → include). Kills the god-file fan-out for BOTH the local agent and the CI agent.

### Thread D — CI fallback agent boost (keep it, make it fast)
- [ ] **G6 — Parallel per-doc sessions.** Replace `runner._repair_each_doc`'s sequential loop with bounded concurrent Goose sessions (~3, configurable), 429/5xx back-off, $30-plan-aware.
- [ ] **G7 — Cache CI setup.** `setup-uv` cache + hash-keyed Beadloom index cache (skip reindex on hit) to cut the fixed ~2-4min on the self-hosted runner.

### Thread E — Folded fix + docs
- [ ] **G8 — Hook over-staging (`beadloom-cugq`).** `beadloom active-sync --stage` stages only its reconciled paths; both hook templates use it.
- [ ] **G9 — Docs/CHANGELOG/ROADMAP + adopter guide** for the formalized flow, the pre-push Gate, tool-agnostic setup, the scope/parallel/cache knobs, and the local-primary / CI-fallback model.

## Non-goals (out of scope)

- **Retiring or rewriting the CI ai-techwriter** — it stays as-is (fallback); we only ADD the parallel/cache boosts.
- **A local Goose+Qwen install** — local authoring uses the user's existing agent; Goose+Qwen is server/CI-only.
- **Making the Gate non-blocking / async docs on main** — explicitly rejected: the invariant "no code without docs in main" is hard, enforced by the blocking Gate.
- **Dropping extended thinking / switching the model** — quality-first; the Qwen choice is settled (BDL-050).
- **Multi-agent expansion of `ai_agents`** (reviewer-bot etc.) — future.

## Open architecture questions (→ resolved in the RFC)

1. **Tool-agnostic mechanism:** how do non-Claude agents (Cursor, …) consume the flow? `AGENTS.md` + generic role/skill defs + per-tool adapters scaffolded by `setup`? How much is genuinely portable vs Claude-Code-specific (subagents, slash skills)? Define a minimum viable cross-tool contract.
2. **Pre-push Gate ergonomics:** `beadloom ci` on every push (reindex+lint+sync-check+doctor) — fast enough to block on? Scope to changed refs? Interaction with the existing pre-commit hook (avoid double-running).
3. **Coordinator loop encoding:** how to formalize "Gate red → tech-writer → re-Gate" deterministically in `/coordinator` so it's tool-driven, not memory-driven — across tools (Thread B).
4. **Symbol-level scope:** can `code_symbols` per-symbol hashes attribute drift to changed symbols today, or is a new signal needed? Under-scoping risk + fallback.
5. **CI parallelism + cache:** safe concurrency under the $30 plan (429 back-off, VPS RAM); index-cache keying to avoid staleness.
6. **Slice order:** likely A/B (formalize + tool-agnostic + pre-push gate) first (the philosophy), C (scope) next (shared win), D (CI boost) after, E folded/last.

## User stories

### US-1: Docs can't be forgotten
As a developer, if I try to push code whose docs are stale, the Beadloom Gate blocks the push and the flow runs the tech-writer — so `main` never gets undocumented code, without me having to remember.

### US-2: My own agent, any tool
As a Cursor (or Claude Code) user, the Beadloom flow + tech-writer role run on MY agent — I don't install a separate LLM stack locally.

### US-3: Small edit = small doc run
As a developer, a one-symbol change to a god-file refreshes only the genuinely-affected doc(s), not 15 pages — locally and on CI.

### US-4: The CI net is fast when it fires
As a maintainer, on the rare PR that bypassed the local flow, the CI fallback agent fixes docs quickly (parallel + cached), not in ~15min.

## Acceptance criteria

- The flow is documented + shipped as deterministic tools; no routine `[skip ai-techwriter]`.
- A pre-push `beadloom ci` hook blocks pushes with a red Gate; the coordinator loop drives Gate-red→tech-writer→re-Gate→PR.
- The flow runs on Claude Code AND at least one more tool (Cursor) via a tool-agnostic mechanism.
- A god-file one-symbol edit scopes to only the affected doc(s) (measured vs the old fan-out).
- The CI fallback agent runs concurrently + cached; it fires only on a non-Gate-passing PR.
- `beadloom active-sync --stage` stages only its reconciled paths.
- Doc quality preserved (spot-check vs BDL-050 baseline); full `beadloom ci` + `ci.yml` green per slice.
