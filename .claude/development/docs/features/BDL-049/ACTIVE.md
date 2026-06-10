# ACTIVE: BDL-049 — Trunk-based dev + PR-triggered AI tech-writer

> **Last updated:** 2026-06-10

---

## Current Focus

- **Phase:** W1 (parallel) — BEAD-01 (harness pr-branch mode) ∥ BEAD-03 (trunk-based vendored flow + branch protection).
- **Branch:** `features/BDL-049` (this epic bootstraps trunk-based — first work on a feature branch).
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-j72g`

## Bootstrap note

GitHub runs `pull_request` workflows from the BASE branch (main) version → the new trigger goes live only AFTER BDL-049 merges to main. So: build .1–.3 on `features/BDL-049` → one PR to main → merge (transitional; old push-trigger may fire once) → **dogfood (.6) is a SEPARATE post-merge PR** proving the live pull_request model.

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-j72g.1 | dev — harness pr-branch publish mode | W1 in progress |
| beadloom-j72g.2 | dev — CI configs (pull_request) + GitLab MR + templates + re-vendor | blocked ← 1 |
| beadloom-j72g.3 | dev — trunk-based vendored flow + branch protection | W1 in progress |
| beadloom-j72g.4 | test | blocked ← 1,2,3 |
| beadloom-j72g.5 | review | blocked ← 4 |
| beadloom-j72g.6 | dogfood (separate post-merge PR) | blocked ← 5 |
| beadloom-j72g.7 | tech-writer | blocked ← 6 |

## Waves

W1 `.1 ∥ .3` → W2 `.2` → test `.4` → review `.5` → dogfood `.6` → tech-writer `.7`.

## Key decisions (from PRD/RFC/CONTEXT)

- Trigger `on: pull_request → main`; `--since merge-base`; agent commits refresh INTO the PR head branch (no orphan doc-PR); loop-guard (`[skip ai-techwriter]` + author + workflow early-skip); `cancel-in-progress: true`.
- Branch protection on main (PR required, CI required check, owner-mergeable).
- Trunk-based coordinator flow vendored + re-vendored; harness internals untouched.

## Progress Log

- 2026-06-10: PRD/RFC/CONTEXT/PLAN approved; feature `beadloom-j72g` + 7 beads + DAG; branch `features/BDL-049` created. W1 launched (.1 ∥ .3).
- 2026-06-10: **BEAD-01 (.1) DONE.** `--target {branch-pr,pr-branch}` flag (default `branch-pr`, unchanged). New `GitHubPRBranchPublisher`/`GitLabPRBranchPublisher`: commit refresh onto CURRENT PR-head branch (no `checkout -b`), msg starts `[skip ai-techwriter]` + bot identity, plain `git push origin HEAD`, 0-docs→no empty commit, post PR/MR comment (`gh pr comment`/`glab mr note`, NOT create, best-effort), `pr_url` from CI env (`PR_URL` / `CI_MERGE_REQUEST_IID`+`CI_MERGE_REQUEST_PROJECT_URL`). Re-vendored harness (drift-guard green). +21 tests; full suite + ruff + mypy + beadloom validation green.
