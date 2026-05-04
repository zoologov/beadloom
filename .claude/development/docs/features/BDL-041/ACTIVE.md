# ACTIVE: BDL-041 — F4.4: Site rendering fixes + dashboard UX

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Ready to start (Wave 1)
- **Epic bead:** `beadloom-fv8` (swarm `beadloom-9t43`)
- **Next bead:** `beadloom-fv8.1` — BEAD-01 dev: Mermaid correctness + generation-time guard (P0)
- **Blockers:** none

## Bead Map (epic `beadloom-fv8`)

| Bead | Role | P | Status | Depends |
|------|------|---|--------|---------|
| .1 Mermaid correctness + generation-time guard | dev | P0 | open (READY) | — |
| .2 diagram pan/zoom/fullscreen | dev | P1 | open (READY) | — |
| .3 dashboard data — trends + recommendations | dev | P1 | open | .1 |
| .4 ECharts dashboard widgets | dev | P1 | open | .2, .3 |
| .5 dogfood + render validation | dev | P1 | open | .1–.4 |
| .6 test — guard + determinism + honest-data + coverage | test | P0 | open | .1–.5 |
| .7 review | review | P0 | open | .6 |
| .8 tech-writer | tech-writer | P1 | open | .7 |

## Waves

- **Wave 1 (dev, P0):** .1 — Mermaid correctness + guard (honest render unblocked).
- **Wave 2 (dev):** .2 (pan/zoom, frontend) + .3 (dashboard data, Python) — disjoint; sequential by default (or .2 via worktree parallel).
- **Wave 3 (dev):** .4 — ECharts widgets (needs theme from .2 + data from .3).
- **Wave 4 (solo dev):** .5 — dogfood + render validation (coordinator runs npm).
- **Wave 5 (test):** .6.
- **Wave 6 (review):** .7 → fix cycle if ISSUES.
- **Wave 7 (tech-writer):** .8.

## Progress Log

- 2026-06-02 — `/task-init` complete (follow-up to F4): PRD / RFC / CONTEXT / PLAN approved; epic `beadloom-fv8` + 8 sub-beads created; DAG wired; swarm `beadloom-9t43` (7 waves); `bd ready` confirms .1 + .2 unblocked.

## Notes / Reminders

- **build green ≠ renders ok** — the generation-time Mermaid guard (BEAD-01) must catch the F4 bug classes in pytest; dogfood (BEAD-05) MUST validate the real render, not just `npm run docs:build` exit 0.
- **Honest by construction** — dashboard numbers + recommendations from the gate code paths; trends only-real-points (no fabrication), ts from storage not `now()`.
- **C4 Rel-drop is safe** — only drop Rels to undeclared nodes (System root); relationship stays in graph + landscape.
- **Pinned frontend** — `echarts`/`vue-echarts`/`svg-pan-zoom` exact versions; committed custom theme.
- **F4 + F4.4 push together** — F4 push paused until render is fixed (a published broken diagram = a published lie).
- node v18 available; coordinator runs `npm` with network approval for the real build/dogfood.
- Re-run sync-check to fixpoint after `mark_synced` (F4.1 co-attachment loop).
