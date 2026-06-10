# RFC: BDL-049 — Trunk-based development + PR-triggered AI tech-writer

> **Status:** Approved
> **Created:** 2026-06-10
> **PRD:** ./PRD.md

---

## Summary

Three coordinated changes; the harness internals (scope→packet→agent→gate→fixpoint) are untouched — only the **trigger**, the **`--since` source**, and the **publish target** change:

1. **Trigger:** AI tech-writer fires `on: pull_request` (→ `main`), not `on: push: main`. It runs once per PR against the PR's diff.
2. **Baseline:** `--since $(git merge-base origin/<base> HEAD)` — exactly "what this PR changed".
3. **Publish target:** instead of cutting a NEW branch + `gh pr create`, the agent **commits its doc refresh onto the existing PR head branch** (with a `[skip ai-techwriter]` message) and posts a PR comment. Code + docs become one reviewable PR; no orphan doc-PRs; the human still merges (no auto-merge).

Plus: a **loop-guard** so the agent's own push doesn't re-trigger; `cancel-in-progress: true`; a GitLab `merge_request_event` mirror; the vendored `.claude/` coordinator flow updated to trunk-based + re-vendored; and `main` branch protection with the CI gate as a **required check** (hardens BDL-048 G5).

## Decisions on the open questions

1. **Publish target → commit onto the PR head branch** (not a child PR). The `pull_request` runner already checks out the PR head; the agent commits docs + run-record there + pushes + posts a summary comment. (Reuses BUG-J force/commit machinery, but as a plain commit-on-top of the PR branch.)
2. **Loop-guard → BOTH, belt-and-suspenders.** The agent's refresh commit message starts with `[skip ai-techwriter]` AND is authored by `beadloom-ai-techwriter`. The workflow has an **early guard step**: check the PR head commit (`git log -1 --format='%an%n%s'`); if author is `beadloom-ai-techwriter` OR the subject contains `[skip ai-techwriter]` → exit 0 immediately (skip). Prevents the `synchronize` loop.
3. **`--since` → `git merge-base origin/<base-ref> HEAD`** (robust when the PR branch is behind/ahead of main), with `github.event.pull_request.base.sha` as a fallback. Computed in the workflow, passed via `--since`.
4. **Branch protection → applied via `gh api` + documented.** Require a PR to `main` (no direct push) + the existing CI workflow (`tests` / Beadloom Gate) as a **required status check**. For the solo case, keep it owner-mergeable (no required human reviews, or `required_approving_review_count: 0`); the structure already supports team review later. A small idempotent helper (or documented `gh api` call) sets it; the dogfood verifies a direct push to `main` is rejected.
5. **Coordinator flow change (real, affects how we work):** epics/features run on a short-lived `features/<ISSUE-KEY>` branch; per-wave commits land on that branch; one PR to `main` per epic (or per shippable slice), merged when green + the agent's doc refresh is in. The vendored `.claude/commands/coordinator.md` + the `CLAUDE.md` §6 Git section are updated to describe this and **re-vendored** (BDL-048 drift-guard must stay green).

## Part 1 — Harness: PR-branch publish mode (`tools/ai_techwriter/`)

- New publish **mode** (CLI flag, e.g. `--target pr-branch` vs the existing default `branch-pr`; or auto-detect `GITHUB_HEAD_REF`/`CI_MERGE_REQUEST_*`). In `pr-branch` mode the publisher:
  - commits the refreshed docs + run-record onto the **current** (PR head) branch with message `[skip ai-techwriter] docs: AI tech-writer refresh (N doc(s))` and the bot identity,
  - pushes to that branch (the runner is already on it),
  - posts a **PR/MR comment** summarizing docs refreshed + tokens + gate (flagged or green) instead of opening a new PR,
  - resolves the PR/MR URL from the CI env (`github.event.pull_request.html_url` / `CI_MERGE_REQUEST_*`) for the run-record (`pr_url` now reliably populated — no chicken-and-egg since the PR pre-exists).
- The existing branch-cutting `GitHubPublisher`/`GitLabPublisher` path stays for `workflow_dispatch`/manual use. Add a `PRCommentPublisher`-style seam (or extend the publishers with a `commit_to_current_branch=True` path) — mockable, unit-tested with `gh`/`glab`/git mocked.
- `--since` already exists (BDL-047/G12); the workflow supplies the merge-base.

## Part 2 — CI configs + templates

**GitHub** `.github/workflows/ai-techwriter.yml`:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, master]
  workflow_dispatch: { inputs: { since: {required: false, default: ""} } }
permissions: { contents: write, pull-requests: write }
concurrency:
  group: ai-techwriter-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true        # G8
jobs:
  ai-techwriter:
    runs-on: [self-hosted, ai-techwriter]
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0, ref: ${{ github.event.pull_request.head.ref }} }
      # loop-guard (G5): skip the agent's own commit
      - run: |
          read -r AN < <(git log -1 --format='%an'); SUBJ=$(git log -1 --format='%s')
          if [ "$AN" = "beadloom-ai-techwriter" ] || echo "$SUBJ" | grep -q '\[skip ai-techwriter\]'; then
            echo "skip: agent's own commit"; exit 0
          fi
      - ...uv sync / goose / reindex...
      - run: |
          BASE="${{ github.event.pull_request.base.ref }}"
          since=$(git merge-base "origin/$BASE" HEAD)
          uv run python -m tools.ai_techwriter --platform github --target pr-branch --since "$since"
        env: { QWEN_API_KEY, QWEN_BASE_URL, GH_TOKEN, PR_URL: ${{ github.event.pull_request.html_url }} }
```
(`push: branches:[main]` removed.) `workflow_dispatch` keeps the branch-PR path (no PR context).

**GitLab** `.gitlab-ci.yml`: `rules: - if: $CI_PIPELINE_SOURCE == "merge_request_event"`; `since=$(git merge-base "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME" HEAD)`; `--target pr-branch`; commit to `$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`; same loop-guard on commit author/message. Templates `github-workflow.yml` + `gitlab-ci-job.yml` mirror both.

## Part 3 — Trunk-based coordinator flow (vendored) + branch protection

- Update vendored **`.claude/commands/coordinator.md`** (and `CLAUDE.md` §6 Git): work on `features/<ISSUE-KEY>`; per-wave commits to the branch; open ONE PR to `main`; the PR triggers AI tech-writer + CI; merge when green. **Re-vendor** the `agentic_flow` templates (BDL-048 drift-guard byte-match).
- **Branch protection** on `main`: an idempotent helper / documented `gh api`:
  `PUT /repos/{o}/{r}/branches/main/protection` with `required_status_checks` (the `tests`/gate contexts, `strict: true`), `required_pull_request_reviews: {required_approving_review_count: 0}` (PR required, owner-mergeable), `enforce_admins: false`, `restrictions: null`.

## Component / file impact

| Component | Change | Tested by |
|-----------|--------|-----------|
| `tools/ai_techwriter/seams.py` + `cli.py` | `--target pr-branch` publish mode: commit-to-current-branch + PR/MR comment + `pr_url` from env; loop-guard `[skip ai-techwriter]` message | unit (gh/glab/git mocked) |
| `.github/workflows/ai-techwriter.yml` | pull_request trigger, merge-base `--since`, loop-guard step, `cancel-in-progress` | dogfood + yaml-lint test |
| `.gitlab-ci.yml` | `merge_request_event` mirror | dogfood/manual |
| `onboarding/templates/ai_techwriter/{github-workflow,gitlab-ci-job}.yml` | mirror both | drift-guard |
| vendored `.claude/commands/coordinator.md` + `CLAUDE.md` §6 + `templates/agentic_flow/` | trunk-based flow + re-vendor | drift-guard |
| branch-protection helper/doc (`gh api`) | required check on `main` | dogfood (direct push rejected) |
| docs guides + CHANGELOG + ROADMAP | tech-writer | — |

## Alternatives considered

- **Path-filter + skip-token on `push: main` (the earlier A/B/C patch).** Rejected as primary: treats symptoms (still per-push, still can red-main, still orphan-PR-prone). Trunk-based fixes the cause. (`cancel-in-progress` is kept from it.)
- **Agent opens a child PR into the feature branch.** Rejected: more moving parts + still a second PR; committing onto the PR branch is simpler + atomic.
- **Trigger on feature-branch `push` (not `pull_request`).** Rejected: fires before a PR exists + no clean base; `pull_request` gives the base + the PR to comment on.

## Risks & mitigations

- **`synchronize` loop** from the agent's own push. → loop-guard (author + `[skip ai-techwriter]`), belt-and-suspenders (G5). Dogfood must confirm the agent's commit does NOT spawn a second run.
- **`pull_request` + self-hosted runner + secrets.** Same-repo PRs are trusted (secrets + runner available); forks are out of scope (non-goal). Documented.
- **Solo-dev friction** (PRs add ceremony). → one PR per epic (not per commit); owner-mergeable; the vendored flow makes it the default. Net win: always-green main.
- **Branch protection locking out the owner.** → `enforce_admins: false`, 0 required reviews; verify the owner can still merge.
- **Re-vendor drift** (BDL-048 guard). → re-run the sync after editing the live coordinator flow.

## Rollout

Waves: dev (`.1` harness pr-branch mode → `.2` CI configs+templates+loop-guard → `.3` trunk-based vendored flow + branch-protection helper) → test → review → **dogfood (`.9`/G9: a real `features/BDL-049` PR — agent runs ONCE, commits the doc fix into the PR, no second run from its push, main stays green, direct push to main rejected)** → tech-writer. The dogfood is the first real use of the new model (we eat our own trunk-based dog food). Keep Beadloom green on `beadloom ci` throughout.
