# ACTIVE: BDL-050 — CI consolidation

> **Last updated:** 2026-06-11

---

## Current Focus

- **Phase:** dogfood next (BEAD-06) — the feature's own PR validates the live consolidated ci.yml. BEAD-08 (MINOR-1) done.
- **Branch:** `features/BDL-050`.
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-0gwo`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-0gwo.1 | dev — consolidated ci.yml + delete 3 + Node24 | ✓ done (W1) |
| beadloom-0gwo.2 | dev — AI-TW verdict {ok,flagged,infra} | ✓ done (W1) |
| beadloom-0gwo.3 | dev — branch_protection 7-set + GitLab + re-vendor | ✓ done (W2) |
| beadloom-0gwo.4 | test (+22, new-code cov 100%) | ✓ done (W3) |
| beadloom-0gwo.5 | review (PASS-WITH-FIXES: 0 crit/major, 2 minor) | ✓ done (W4) |
| beadloom-0gwo.8 | dev-fix — MINOR-1: derive required contexts from ci.yml, assert == DEFAULT_STATUS_CHECK_CONTEXTS | ✓ done |
| beadloom-0gwo.6 | dogfood | next |
| beadloom-0gwo.7 | tech-writer (incl. MINOR-2: agentic-flow.md `beadloom-gate`→`gate`) | blocked ← 6 |

## Waves

W1 `.1 ∥ .2` ✓ → W2 `.3` ✓ → test `.4` ✓ → review `.5` ✓ → fix `.8` → dogfood `.6` → tech-writer `.7`.

## Key decisions (from PRD/RFC/CONTEXT)

- One `ci.yml` (pull_request→main): gate∥tests∥site-build → ai-techwriter `needs:` all three. deploy-site stays only push:main job.
- **AI-TW Alternative:** verdict {ok,flagged,infra} via tokens>0; exit ok/infra→0, flagged→1; infra → ::warning:: + PR comment. Dead runner/quota must NOT block merges.
- Required = gate, tests×4, site-build, ai-techwriter; branch_protection updated + re-applied; enforce_admins:true kept.
- Drop tests paths filter; remove push:main from gate/tests; Node24-bump all + deploy node 18→22; BDL-049 body 1:1; re-vendor.

## Review findings (.5)

- PASS-WITH-FIXES. Crux dimensions sound (skipped-required ordering; verdict discriminator conservative — publish-fail is hard-red not silent-infra). No BDL-049 regression; deletions safe; contexts match ci.yml; Node24 real.
- MINOR-1 → BEAD-08 (cross-check test). MINOR-2 (agentic-flow.md `beadloom-gate`→`gate`) → tech-writer .7.

## Progress Log

- 2026-06-11: PRD/RFC/CONTEXT/PLAN approved; feature `beadloom-0gwo` + 7 beads + DAG; branch `features/BDL-050`. W1 launched.
- 2026-06-11: **W1 done** (.1 ci.yml consolidation + delete 3 old + Node24 bump + pypi-publish inline; .2 verdict ok/flagged/infra + exit map). Suite 3615; committed.
- 2026-06-11: **W2 done** (.3 branch_protection 7-context set + GitLab verify→docs mirror + templates restructured). Suite 3633; committed.
- 2026-06-11: **W3 done** (.4 test +22, new-code cov 100%). Suite 3653; committed.
- 2026-06-11: **W4 done** (.5 review PASS-WITH-FIXES — 0 crit/major, 2 minor). MINOR-1 → BEAD-08; MINOR-2 → .7.
