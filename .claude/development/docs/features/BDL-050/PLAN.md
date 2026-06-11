# PLAN: BDL-050 — CI consolidation

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-050` (feature) — CI consolidation.

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| .1 | dev | **Consolidated `ci.yml`** — new `.github/workflows/ci.yml` on `pull_request→main` (+dispatch) with jobs `gate`∥`tests`(3.10–3.13, no paths filter)∥`site-build`(docs site + vitepress build) and `ai-techwriter` `needs:[gate,tests,site-build]` (full BDL-049 body 1:1: loop-guard, AI_TW_PAT checkout, merge-base `--since`, `--target pr-branch`, PR_URL, cancel-in-progress). DELETE `beadloom-gate.yml`/`tests.yml`/`ai-techwriter.yml`. Node24-bump actions across `ci.yml` + `deploy-site.yml` (node 18→22). | — |
| .2 | dev | **AI-TW verdict (Alternative)** — `runner.py` computes `verdict {ok,flagged,infra}` (discriminator `tokens>0`: agent produced output ⇒ flagged on unclean docs; `tokens==0` ⇒ infra); `cli.py` exit ok/infra→0, flagged→1, + `::warning::` annotation + best-effort PR comment on infra. Split the blanket `result.flagged`. | — |
| .3 | dev | **Branch protection + GitLab + re-vendor** — `branch_protection.DEFAULT_STATUS_CHECK_CONTEXTS` → `gate,tests (3.10..3.13),site-build,ai-techwriter`; `.gitlab-ci.yml` consolidated `verify`→`docs` stages with `needs`; re-vendor `templates/ai_techwriter/*` (drift-guard green). | .1, .2 |
| .4 | test | pytest: ci.yml structure (yaml-valid, `needs`, no push:main, Node24 tags, 4 job names), verdict classification (ok/flagged/infra → exit 0/1 + annotation, tokens>0 boundary), branch_protection 7-context set, GitLab mirror, drift-guard. ≥80% changed. | .1,.2,.3 |
| .5 | review | quality/architecture/honesty — needs-ordering correctness, skipped-required reasoning, verdict discriminator (no silent infra-misclass of real failures), no BDL-049 regression, owner-not-locked-out. | .4 |
| .6 | dogfood | the feature's own PR + a follow-up: confirm **red gate ⇒ ai-techwriter skipped ⇒ PR blocked**; **all-green ⇒ ai-techwriter runs ⇒ verdict gates**; tokens NOT spent on a red PR; `deploy-site` only on merge; no Node20 warnings; re-apply branch protection + verify mergeability under the new check names. Friction → `BDL-UX-Issues.md`. | .5 |
| .7 | tech-writer | update ai-techwriter + agentic-flow guides (consolidated CI, verdict semantics) + CHANGELOG + ROADMAP; close `beadloom-wozp` + `beadloom-t7vn`. | .6 |

## Dependencies / DAG

```
.1 ─┬─> .3 ─┐
.2 ─┴───────┴─> .4(test) ─> .5(review) ─> .6(dogfood) ─> .7(tech-writer)
```
(.3 needs .1's job names + .2's verdict; .1 ∥ .2 are disjoint files.)

## Waves

- **W1 (parallel):** `.1` (ci.yml + delete + Node24) ∥ `.2` (verdict classification in the harness) — disjoint (`.github/`+`deploy-site` vs `tools/ai_techwriter/`).
- **W2:** `.3` (branch_protection + GitLab + re-vendor, ← .1 + .2).
- **W3:** `.4` test. **W4:** `.5` review. **W5:** `.6` dogfood. **W6:** `.7` tech-writer.

Work on `features/BDL-050`; commit per wave; one PR to main (gated by the NEW `ci.yml` — eat our own dog food). Beadloom green on `beadloom ci` + pytest after each wave.

## Acceptance (maps to goals)

- **G1** ← .1 (ci.yml + needs). **G2** ← .1 (tests no paths). **G3** ← .1 (site-build job). **G4** ← .3 (branch protection). **G5** ← .1 (push:main removed). **G6** ← .1 (Node24). **G7** ← .1/.3 (BDL-049 1:1 + re-vendor) + **AI-TW Alternative** ← .2. **G8** ← .6 (dogfood) + .7 (docs).
