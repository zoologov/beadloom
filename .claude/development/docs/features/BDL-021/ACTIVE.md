# ACTIVE: BDL-021 — v1.7.0: AaC Rules v2, Init Quality, Architecture Intelligence

> **Last updated:** 2026-02-17
> **Phase:** Development — All 14 beads DONE

---

## Current Wave

**Wave:** 3 — COMPLETED (4/4 beads done)

## Wave 1 Results (5/5 done)

| Bead | Goal | Tests |
|------|------|-------|
| BEAD-01 | Node tags/labels + NodeMatcher | 26 |
| BEAD-04 | Circular dependency detection | 27 |
| BEAD-07 | Scan all code directories | 8 |
| BEAD-09 | Root service rule fix | 4 |
| BEAD-05 | Import-based boundary rules | 24 |

## Wave 2 Results (5/6 done)

| Bead | Goal | Status | Tests |
|------|------|--------|-------|
| BEAD-02 | ForbidEdgeRule | Done | 21 |
| BEAD-03 | LayerRule | Done | 8 |
| BEAD-08 | Non-interactive init | Done | 10+ |
| BEAD-12 | Architecture snapshots | Done | 30 |
| BEAD-14 | Enhanced why --reverse | Done | 12+ |
| BEAD-10 | Docs generate in init | Done (Wave 3) | 7 |

## Wave 3 Results (4/4 done)

| Bead | Goal | Status | Tests |
|------|------|--------|-------|
| BEAD-10 | Docs generate in init (retry) | Done (already implemented in Wave 2) | 7 |
| BEAD-06 | CardinalityRule | Done | 13 |
| BEAD-11 | Doc auto-linking | Done | 17 |
| BEAD-13 | Enhanced diff + snapshot integration | Done | 24 |

## Progress

- [x] PRD.md — Approved
- [x] RFC.md — Approved
- [x] CONTEXT.md — Approved
- [x] PLAN.md — Approved
- [x] Epic created (beadloom-j9e)
- [x] 14 beads created with dependencies
- [x] Wave 1 — Foundation (5 beads, 89 tests)
- [x] Wave 2 — Dependent rules + init (5/6 beads, ~81 tests)
- [x] Wave 3 — Final 4 beads (4/4 beads, 54 tests)
- [ ] Wave 4 — Stale docs update, validation, version bump

## Remaining Work

- Stale docs update: 4 domains (context-oracle, graph, onboarding, cli)
- Version bump to 1.7.0
- Total: 1657 tests passing, 0 lint violations

## Notes

- Wave 2: 6 agents crashed iTerm (190GB RAM). Limit to 3-4 agents max.
- Wave 3: BEAD-06 and BEAD-13 agents hit permissions/rate-limit — implemented directly by coordinator.
- BEAD-10 was already implemented in Wave 2 by BEAD-08 agent (interactive_init already had doc generation).
