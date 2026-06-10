# PRD: BDL-047 (F4.1) — AI tech-writer in CI

> **Status:** Approved
> **Created:** 2026-06-04
> **Roadmap:** P0 (agentic cluster, serves north-star (a) — solo multi-agent flow)

---

## Problem

Beadloom is **honest-by-construction for detecting** doc drift — `sync-check` reliably flags a doc whose code changed underneath it (symbols/hash/untracked). But the **remediation step is fully manual**: a human must open each drifted doc and rewrite it. The DocAsCode loop is therefore open-ended at "fix":

```
code changes → sync-check: STALE  →  ❌ human rewrites each doc by hand  →  sync-check: 0
```

For the solo multi-agent flow (Claude Code + Beadloom + Beads + GitHub) — Beadloom's #1 value — this is the missing link: the knowledge base does not maintain itself. On an actively developed project (and across a team of solos each owning a service), docs drift faster than a maintainer refreshes them, and a stale knowledge base poisons the context every downstream agent reads.

## Impact

F4.1 closes the loop: an AI agent **repairs the drifted docs automatically, scoped to exactly what `sync-check` flags**, re-checks to a fixpoint, and opens a PR/MR for human review — turning Beadloom from "detects drift" into "keeps the knowledge base alive."

```
code changes → sync-check: STALE  →  🤖 agent repairs ONLY drifted nodes  →  re-check to fixpoint (0)  →  PR for human review
```

This is the agentic-maintenance loop named in STRATEGY-3 as F4.1 and validated by REVIEW-2 as "killer-feature #2 — release first among the agentic features." It is the highest-leverage P0 item: it directly serves north-star (a) and is reusable by north-star (b) (each service's CI keeps its own docs fresh).

**Honesty principle preserved:** the agent's output is a **proposal**. The deterministic gate (`sync-check` → 0 + `beadloom ci`) plus **human PR review** is the source of truth — nothing merges automatically. A doc the gate still calls stale never lands silently.

Success criterion: **on a repo with stale docs (`sync-check` exit 2), one CI run produces a branch + PR in which the drifted docs are refreshed and `sync-check` reports 0 stale — verified by re-running the deterministic gate, with no source code touched and no auto-merge.**

## Goals

- [ ] **G1 — Closed scoped refresh loop.** Given drift (`sync-check` exit 2), the agent repairs **only the docs `sync-check` flags stale** (not a blanket rewrite), then re-checks to a **fixpoint** (re-run `sync-check` after marking synced until stable 0 — the known F4.1 loop-invariant: editing a domain doc re-stales all its pairs).
- [ ] **G2 — Grounded by Beadloom's structured outputs.** The agent scopes + grounds its edits using `sync-check --json` (what drifted + why), `docs polish --format json` (structured enrichment input), and `ctx`/`why` (architecture context) — plus tool-use to read the relevant code/diff. No blind rewriting.
- [ ] **G3 — External top-tier model via Goose.** Goose (MCP-native agent coordinator) drives **Qwen3.7-Plus (external API)**. No bundled LLM, no local model on the runner, **no model tiering** (top-tier only — stable quality).
- [ ] **G4 — Honest + safe by gate, not by trust.** Agent output is a proposal; acceptance = `sync-check` → 0 **and** `beadloom ci` green; **no auto-merge** (PR/MR only). Bounded cost: token/turn budget caps + retry policy; on failure, open the PR flagged "needs human" rather than merge or hang.
- [ ] **G5 — CI-runnable on BOTH GitHub Actions and GitLab CI + VPS runner.** Dual-platform is a deliberate, first-class requirement (the team uses both). The deterministic harness is platform-agnostic (one Python codebase); only the trigger, the secret-naming, and the PR/MR-open step differ per platform (a thin adapter: `gh pr create` vs `glab`/GitLab API). Runs unattended on a self-hosted VPS runner (agentics live where the API key + Goose live); docs-only writes; sandboxed tool surface.
- [ ] **G6 — Dogfood (both platforms).** **GitHub path** dogfooded natively on Beadloom's own repo — refresh a real drift (e.g. doc-debt #130/#131) into a reviewable PR. **GitLab path** validated on the team's private GitLab repo (Beadloom itself is on GitHub). Capture friction in `BDL-UX-Issues.md`.
- [ ] **G7 — Docs.** Guide for setting up + running the AI tech-writer (Goose recipe, secrets, CI workflow, acceptance gate) + CHANGELOG + ROADMAP status.
- [ ] **G8 — Simple opt-in setup (added 2026-06-04).** End-user setup must be low-friction: a `beadloom setup-ai-techwriter` scaffold + a ≤3-step checklist (register VPS runner · add API-key secret · run scaffold + enable workflow). No hand-wiring; the recipe is repo-agnostic. Highest-priority output quality (full reasoning, no think-capping) is the non-negotiable goal of the agent itself.
- [ ] **G9 — Activity + token tracking on the dashboard (added 2026-06-04, variant A).** The harness emits an honest **run-record** per run (real API token usage + docs refreshed + gate result + PR/MR url); a VitePress dashboard **widget** visualizes AI tech-writer activity + token spend over time. **Tokens are fact** (from the API `usage` field); any **$ figure is a clearly-labeled estimate** at the configured rate (honest-by-construction preserved — only real recorded runs, no interpolation).

## Non-goals (out of scope)

- **Rewriting non-drifted docs / prose-quality scoring.** Scope is strictly what `sync-check` flags; no "improve all docs" pass, no AI grading of prose.
- **Touching source code.** Docs-only (`docs/**` + tracked doc files). The agent never edits `src/`.
- **Auto-merge / unattended landing.** Always a PR/MR for human review.
- **Local/bundled model.** External API only (Qwen3.7-Plus); no model on the runner; no model tiering (principle 10).
- **A general agent framework.** Use Goose; we don't build orchestration from scratch.
- **Beads in the runtime pipeline.** Beads is our multi-agent *dev-flow* tracker (and a promising **future** agentic-stack component — Goose + Beadloom + Beads); the F4.1 **runtime** loop is **Goose + Beadloom + Qwen only** and does not use Beads.
- **Semantic-contract / viz work** (that's P1) and **the broader MCP process-tools fleet** (P0 agentic-flow packaging is a *separate* epic; F4.1 may consume process-tools if they exist but does not block on them).

## Open architecture questions (→ resolved in the RFC, per owner's "architecture discussion")

These are the decisions to settle in the RFC, not the PRD:

1. **Goose recipe vs MCP process-tools boundary** — how much of the loop is a Goose recipe (agent + tools + instructions) vs deterministic Python around it (scope from `sync-check --json`, the fixpoint re-check, the PR step). Likely: deterministic harness owns scope + fixpoint + PR; Goose owns the per-doc repair with tool-use.
2. **Model-call boundary** — Goose → Qwen3.7-Plus via OpenAI-compatible/DashScope endpoint; where the API key lives (CI secret on the VPS runner); think-token / cost controls.
3. **Acceptance-gate + retry/budget policy** — exact loop: repair → `sync-check` → (stale? retry up to N) → `beadloom ci` → PR; per-run token/turn budget; failure → PR flagged "needs human".
4. **Scoped-context contract** — exactly which Beadloom outputs feed the agent per doc (`sync-check --json` + `docs polish --format json` + `ctx`/`why`) and the tool surface Goose is allowed (read-only code + Beadloom + write only to `docs/`).
5. **CI topology** — GitHub Actions trigger (nightly? on-merge? manual?) + self-hosted VPS runner setup; how it generalizes to a private service's CI.

## User stories

### US-1: Drift gets repaired without me hand-editing
**As** the solo maintainer, **I want** stale docs to be auto-repaired into a PR when code drifts, **so that** my knowledge base stays alive without manual rewriting.
**Acceptance:**
- [ ] A CI run on a repo with `sync-check` exit 2 produces a branch + PR refreshing the drifted docs; re-run `sync-check` = 0.
- [ ] Only the docs `sync-check` flagged are changed; no source code touched.

### US-2: I trust it because the gate, not the model, decides
**As** the reviewer, **I want** the agent's output gated by `sync-check`→0 + `beadloom ci` and delivered as a PR, **so that** nothing inaccurate merges silently.
**Acceptance:**
- [ ] No auto-merge; a PR/MR is always opened.
- [ ] If the loop can't reach a green gate within the retry/budget, the PR is opened flagged "needs human" (never merged, never hung).

### US-3: It runs on my CI with my model
**As** the operator, **I want** the loop to run on GitHub Actions via a VPS runner against Qwen3.7-Plus, **so that** the agentics run where the API key + Goose live, with bounded cost.
**Acceptance:**
- [ ] A documented workflow runs the loop unattended on the VPS runner with a token/turn budget cap.
