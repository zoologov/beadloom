# ACTIVE: BDL-050 — CI consolidation

> **Last updated:** 2026-06-11

---

## Current Focus

- **Phase:** W1 (parallel) — BEAD-01 (consolidated ci.yml + delete old + Node24) ∥ BEAD-02 (AI-TW verdict classification).
- **Branch:** `features/BDL-050`.
- **Coordinator:** main loop (multi-agent).
- **Parent:** `beadloom-0gwo`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-0gwo.1 | dev — consolidated ci.yml + delete 3 + Node24 | W1 in progress |
| beadloom-0gwo.2 | dev — AI-TW verdict {ok,flagged,infra} | W1 in progress |
| beadloom-0gwo.3 | dev — branch_protection + GitLab + re-vendor | blocked ← 1,2 |
| beadloom-0gwo.4 | test | blocked ← 1,2,3 |
| beadloom-0gwo.5 | review | blocked ← 4 |
| beadloom-0gwo.6 | dogfood | blocked ← 5 |
| beadloom-0gwo.7 | tech-writer | blocked ← 6 |

## Waves

W1 `.1 ∥ .2` → W2 `.3` → test `.4` → review `.5` → dogfood `.6` → tech-writer `.7`.

## Key decisions (from PRD/RFC/CONTEXT)

- One `ci.yml` (pull_request→main): gate∥tests∥site-build → ai-techwriter `needs:` all three. deploy-site stays only push:main job.
- **AI-TW Alternative:** verdict {ok,flagged,infra} via tokens>0; exit ok/infra→0, flagged→1; infra → ::warning:: + PR comment. Dead runner/quota must NOT block merges.
- Required = gate, tests×4, site-build, ai-techwriter; branch_protection updated + re-applied; enforce_admins:true kept.
- Drop tests paths filter; remove push:main from gate/tests; Node24-bump all + deploy node 18→22; BDL-049 body 1:1; re-vendor.

## Progress Log

- 2026-06-11: PRD/RFC/CONTEXT/PLAN approved; feature `beadloom-0gwo` + 7 beads + DAG; branch `features/BDL-050`. W1 launched (.1 ∥ .2).
