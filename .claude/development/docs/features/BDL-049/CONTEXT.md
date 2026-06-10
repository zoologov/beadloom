# CONTEXT: BDL-049 — Trunk-based development + PR-triggered AI tech-writer

> **Status:** Approved
> **Created:** 2026-06-10
> **PRD/RFC:** ./PRD.md · ./RFC.md

---

## State

Builds on the shipped BDL-047 + BDL-048:
- **`tools/ai_techwriter/`** — the harness. `cli.py` (`--platform`, `--since`, `--dry-run`); `seams.py` (`GitHubPublisher`/`GitLabPublisher`: `_commit_changes` checkout-b/add/commit, `_push_branch` force-push, `_backfill_pr_url`). We ADD a `pr-branch` publish mode (commit onto the current PR head branch + PR/MR comment) — internals (scope/packet/agent/gate/fixpoint) untouched.
- **`.github/workflows/ai-techwriter.yml`** — currently `on: push: [main,master]` + `workflow_dispatch(since)`, `--since github.event.before`, `concurrency cancel-in-progress:false`. Becomes `on: pull_request` + merge-base `--since` + loop-guard + `cancel-in-progress:true`.
- **`.gitlab-ci.yml`** — currently `rules: $CI_COMMIT_BRANCH==main|master`. Becomes `merge_request_event`.
- **`onboarding/templates/ai_techwriter/{github-workflow,gitlab-ci-job}.yml`** — vendored CI templates (mirror both).
- **`onboarding/templates/agentic_flow/`** (BDL-048) — vendored `.claude/agents/*` + `commands/*` byte-identical to live, drift-guarded. Editing the live `coordinator.md`/`CLAUDE.md` requires re-vendor (`sync_agentic_flow()`).
- **Repo state:** currently direct-push-to-main; no branch protection. This feature flips that.

## Decisions (from PRD/RFC)

- Trigger `on: pull_request → main` (not push); `--since merge-base`; agent commits the refresh **onto the PR head branch** (no orphan doc-PR); loop-guard (`[skip ai-techwriter]` + author `beadloom-ai-techwriter`, workflow early-skip step); `cancel-in-progress: true`.
- Branch protection on `main` via `gh api` (PR required, CI a required check, `enforce_admins:false`, 0 required reviews — owner-mergeable).
- Trunk-based coordinator flow vendored + re-vendored; this changes how WE work (feature branch + one PR per epic).
- Same-repo PRs only (forks out of scope); `workflow_dispatch` kept (branch-PR path).

## Code standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter. pytest + pytest-cov (≥80% changed). ruff. mypy --strict (no `Any`/`# type: ignore` w/o reason). DDD boundaries (`lint --strict`). No bare except, no `import *`, no mutable defaults, no `print()`/`breakpoint()`. Shell: `cp/mv/rm` with `-f`.
- New code: harness publish mode → `tools/ai_techwriter/`; CI configs → `.github/`+`.gitlab-ci.yml`+templates; flow → vendored `.claude/` + `templates/agentic_flow/`.

## Constraints / invariants

- Beadloom green on its own `beadloom ci` + full pytest after each wave.
- BDL-048 **drift-guard must stay green** — re-vendor after editing live `.claude/` or the CI templates.
- Harness unit tests mock `gh`/`glab`/git (no network); the dogfood (a real `features/BDL-049` PR) is the end-to-end proof.
- Loop-guard MUST prevent the agent's own push from re-triggering (verified in the dogfood: agent commit → no 2nd run).
- Anonymize third-party project names in committed artifacts.

## Definition of done

All G1–G10 met; AI tech-writer runs once per PR, commits the refresh into the PR branch, `--since merge-base`, loop-guard works, `main` is branch-protected with CI a required check; trunk-based flow vendored + re-vendored (drift-guard green); dogfood-proven on a real `features/BDL-049` PR (one run, no orphan PR, main green, direct push rejected); docs/CHANGELOG/ROADMAP updated; suite + `beadloom ci` green.
