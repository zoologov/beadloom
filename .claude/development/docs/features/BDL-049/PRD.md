# PRD: BDL-049 — Trunk-based development + PR-triggered AI tech-writer

> **Status:** Approved
> **Created:** 2026-06-10
> **Follows:** BDL-047 (AI tech-writer in CI), BDL-048 (agentic-flow packaging).

---

## Problem

The AI tech-writer (BDL-047) triggers `on: push` to `main`. During BDL-047/BDL-048 this produced **excessive, redundant runs and an orphan-PR mess**:

- **13 runs in ~5 hours**, of which **three ran ~1h+ and spent ~768K input tokens each** — because doc-touching commits (my manual tech-writer waves, the agent's own merged PR) re-triggered the agent to refresh docs I was already fixing by hand. Pure duplication.
- The `--since github.event.before` baseline on direct-to-main pushes is ambiguous (covered wide accumulated drift on some pushes) → the expensive wide refreshes.
- **Main goes red between code-landing and the agent's doc-PR merging** (we hit "red Beadloom Gate on main" during the F4.1 dogfood) — drift is detected on main *after* the fact.
- **Orphan doc-PRs pile up:** the agent opened separate doc-PRs (`refresh-12-docs`, `refresh-13-docs`) decoupled from the code that caused the drift; they go stale and must be hand-closed.

Root cause: committing straight to `main` + triggering on every push. Path-filters/skip-tokens would patch the symptoms; the structural fix is **trunk-based development** — short-lived feature branches, a PR to `main` as the integration point, and the agent running **once per PR** against that PR's diff, committing its doc fix **into the same PR**.

## Impact

Adopt trunk-based development with PR-gated integration, and move the AI tech-writer to a **`pull_request`-to-`main`** trigger:

- **Runs once per PR**, not per push → kills the redundant 1h/768K-token re-refreshes.
- **Clean `--since <merge-base>`** baseline = exactly "what this PR's code changed" → no more wide-drift surprises.
- **Main is always green:** drift is caught + fixed on the feature branch *before* merge (branch protection + `beadloom ci` as a required check makes this a hard gate — hardening BDL-048 G5: CI becomes true enforcement, not advisory).
- **No orphan doc-PRs:** the agent commits its refresh **back onto the PR branch**, so code + its doc updates review and merge together in one PR.
- **Aligns with north-star (b)** — "team of solos" requires feature-branch + PR + required-checks anyway.

Success criterion: **a real `features/BDL-049` branch → PR to main → the AI tech-writer runs ONCE on the PR, refreshes only that PR's drifted docs into the PR branch, `beadloom ci` is a required check, main never goes red — dogfood-proven; no per-push runs, no orphan doc-PRs.**

## Goals

- [ ] **G1 — Trunk-based process.** Work happens on short-lived `features/BDL-*` branches; integration to `main` is via PR only. The vendored `.claude/` coordinator flow (BDL-048) is updated to reflect this (work on a feature branch, one PR per epic/feature, merge when green) **and re-vendored** so scaffolded repos get the trunk-based flow too.
- [ ] **G2 — PR-triggered AI tech-writer.** `.github/workflows/ai-techwriter.yml` triggers `on: pull_request` (`opened`, `synchronize`, `reopened`) targeting `main` (+ `workflow_dispatch` as a manual fallback). The `push: branches:[main]` trigger is removed.
- [ ] **G3 — `--since <merge-base>` baseline.** Drift is computed against the PR's merge-base with the base branch (`git merge-base origin/main HEAD`, or the PR base SHA), not `github.event.before`.
- [ ] **G4 — Refresh lands in the PR.** The agent commits its doc refresh **back onto the PR head branch** (reusing the BUG-J force-push) so code + docs are one reviewable unit. No separate/orphan doc-PR. No auto-merge (the human still merges the PR).
- [ ] **G5 — Loop-guard.** The workflow must NOT re-trigger on the agent's own push to the PR branch: skip when the head commit's author is `beadloom-ai-techwriter` OR the commit message contains `[skip ai-techwriter]`. Prevents the `synchronize` infinite loop.
- [ ] **G6 — `beadloom ci` as a required check + branch protection on `main`.** Document + (where do-able via API) configure branch protection: no direct push to `main`, PR required, `beadloom ci` (or the test/lint workflow) a required status check → the gate becomes true enforcement.
- [ ] **G7 — GitLab MR mirror.** `.gitlab-ci.yml` mirrors the model via `merge_request_event` (run on MR to the default branch; commit the refresh to the MR source branch; same loop-guard). Templates updated for both platforms.
- [ ] **G8 — `cancel-in-progress: true`** on the concurrency group (a new commit to a PR cancels the older in-flight run for that PR).
- [ ] **G9 — Dogfood.** Prove it on a real `features/BDL-049` branch: open a PR with a deliberate code change that drifts a doc → the agent runs ONCE on the PR → commits the doc fix into the PR branch → main stays green → merge. No per-push runs, no orphan PRs.
- [ ] **G10 — Docs.** Update the AI tech-writer guide + the agentic-flow guide + CHANGELOG + ROADMAP for the trunk-based / PR-triggered model.

## Non-goals (out of scope)

- **Rewriting the harness internals** (scope/packet/agent/gate/fixpoint stay as-is; only the trigger, the `--since` source, and the publish target change).
- **Auto-merge** — the human still reviews + merges the PR (no change to the no-auto-merge principle).
- **Multi-base / release-branch flows** — single `main` trunk only.
- **Forked-PR support** — same-repo PRs only (solo/team repo; secrets + self-hosted runner are available for same-repo PRs, not forks).
- **Removing `workflow_dispatch`** — kept as a manual fallback.
- **Model tiering** (principle 10).

## Open architecture questions (→ resolved in the RFC)

1. **Publish target on a PR:** commit the refresh to the PR head branch (G4) vs a child PR. → RFC picks branch-commit (G4).
2. **Loop-guard mechanism:** author-name check vs `[skip ai-techwriter]` token vs both, and where (workflow-level `if:` vs inside the harness).
3. **`--since` source on `pull_request`:** `github.event.pull_request.base.sha` vs `git merge-base` — pick the robust one (handles the PR branch being behind main).
4. **Branch protection automation:** configure via `gh api` now vs document-only (owner toggles in UI).
5. **How much of MY coordinator flow changes** (per-wave commits → feature branch; one PR per epic) and the exact vendored-doc edits + re-vendor.

## User stories

### US-1: One agent run per PR, refresh in the PR, main always green
**As** the maintainer, **I want** the AI tech-writer to run once when I open a PR to main and commit its doc fix into that PR, **so that** I stop getting redundant 1h/768K-token re-refreshes and orphan doc-PRs, and `main` never goes red waiting on a separate doc-PR.
**Acceptance:** opening a PR with code that drifts a doc → exactly one agent run → doc fix committed to the PR branch → `beadloom ci` required-check gates the merge → no per-push runs, no orphan PR.

### US-2: Trunk-based flow scaffolded for any repo
**As** a teammate adopting the flow, **I want** the scaffolded `.claude/` coordinator to describe trunk-based + PR-gated integration, **so that** my service uses the same always-green-main model.
**Acceptance:** the vendored coordinator flow reflects feature-branch + PR + required-check; re-vendored (drift-guard green); `setup-agentic-flow` ships it.
