# PLAN: BDL-049 — Trunk-based development + PR-triggered AI tech-writer

> **Status:** Approved
> **Created:** 2026-06-10
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-049` (feature) — Trunk-based dev + PR-triggered AI tech-writer.

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| .1 | dev | **Harness `pr-branch` publish mode** — `tools/ai_techwriter/{seams,cli}.py`: `--target pr-branch` commits the refresh (docs + run-record) onto the CURRENT PR head branch with a `[skip ai-techwriter]` bot-authored message + posts a PR/MR comment (no new branch/PR); `pr_url` from CI env. Keep the existing branch-PR path for dispatch. Mockable (gh/glab/git), unit-tested. | — |
| .2 | dev | **CI configs + templates** — `.github/workflows/ai-techwriter.yml` → `on: pull_request [opened,synchronize,reopened]→main` + merge-base `--since` + loop-guard step + `cancel-in-progress:true` (remove `push:main`); `.gitlab-ci.yml` → `merge_request_event` mirror; update `templates/ai_techwriter/{github-workflow,gitlab-ci-job}.yml`; re-vendor. | .1 |
| .3 | dev | **Trunk-based flow + branch protection** — update vendored `.claude/commands/coordinator.md` + `CLAUDE.md` §6 Git to feature-branch + one-PR-per-epic + merge-when-green; re-vendor `templates/agentic_flow/` (drift-guard green); add an idempotent branch-protection helper/doc (`gh api`: PR required, CI required check, enforce_admins:false, 0 reviews). | — |
| .4 | test | pytest for .1–.3 (pr-branch publish: commit-to-current + comment + skip-token + pr_url-from-env, gh/glab/git mocked; loop-guard logic; yaml validity of both CI configs; drift-guard for re-vendored templates + agentic_flow). Coverage ≥80% changed. | .1, .2, .3 |
| .5 | review | quality/architecture/honesty (loop-guard correctness, no-auto-merge preserved, merge-base robustness, branch-protection not locking owner, drift-guard). | .4 |
| .6 | dogfood | **Eat our own trunk-based dog food:** a real `features/BDL-049` PR with a deliberate code change that drifts a doc → agent runs ONCE on the PR → commits the doc fix into the PR branch → its push does NOT spawn a 2nd run (loop-guard) → main stays green → direct push to main rejected (branch protection). Capture friction in `BDL-UX-Issues.md`. | .5 |
| .7 | tech-writer | update the AI tech-writer guide + agentic-flow guide (trunk-based/PR model) + CHANGELOG + ROADMAP. | .6 |

## Dependencies / DAG

```
.1 ─> .2 ─┐
          ├─> .4(test) ─> .5(review) ─> .6(dogfood) ─> .7(tech-writer)
.3 ───────┘
```

## Waves

- **W1 (parallel):** `.1` (harness pr-branch mode) ∥ `.3` (trunk-based vendored flow + branch-protection) — disjoint files (`tools/ai_techwriter/` vs vendored `.claude/`/`templates/agentic_flow/`).
- **W2:** `.2` (CI configs + templates, ← .1 for `--target`).
- **W3:** `.4` test (← .1,.2,.3).
- **W4:** `.5` review (← .4).
- **W5:** `.6` dogfood (← .5) — the first real trunk-based PR.
- **W6:** `.7` tech-writer (← .6).

Commit per wave on the (now) feature branch `features/BDL-049`; this epic is itself the first to use the trunk-based model once .1–.3 land (bootstrap note in ACTIVE). Beadloom green on `beadloom ci` + pytest after each wave.

## Acceptance (maps to goals)

- **G1** ← .3 (trunk-based vendored flow). **G2/G3/G8** ← .2 (pull_request trigger + merge-base + cancel). **G4** ← .1 (commit-to-PR-branch). **G5** ← .1 (skip-token) + .2 (guard step). **G6** ← .3 (branch protection). **G7** ← .2 (GitLab MR + templates). **G9** ← .6 (dogfood). **G10** ← .7.
