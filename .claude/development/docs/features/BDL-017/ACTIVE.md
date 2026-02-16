# BDL-017: Active Work

## Current Focus
Wave 1 development — 4 parallel agents, 8 beads.

## Progress
- [x] PRD — approved
- [x] RFC — approved (with GraphQL + gRPC)
- [x] CONTEXT.md — approved
- [x] PLAN.md — approved (15 beads, 3 waves)
- [x] ACTIVE.md — created
- [x] Beads created in bd (15 beads)
- [x] Dependencies set up (Wave 2→1, Wave 3→2)
- [x] Committed + pushed
- [ ] **Wave 1 — in progress (4 parallel agents)**
  - [ ] Agent-1: BEAD-01 (API Route Extraction) [P0, L]
  - [ ] Agent-2: BEAD-02 (Git Activity) [P0, M] → BEAD-08 (Metrics) [P2, S]
  - [ ] Agent-3: BEAD-03 (Test Mapping) [P1, M] → BEAD-07 (Config) [P2, S]
  - [ ] Agent-4: BEAD-04 (Severity) [P1, S] → BEAD-05 (MCP why) [P1, S] → BEAD-06 (MCP diff) [P1, S]

## Recent Actions
- 2026-02-16: Epic init started. Explored codebase (Phase 10+11 areas).
- 2026-02-16: PRD approved. RFC approved with GraphQL + gRPC additions.
- 2026-02-16: CONTEXT.md + PLAN.md created.
- 2026-02-16: Wave 1 launched — 8 beads claimed, 4 agents running.

## Decisions
1. All new data in `nodes.extra` JSON — no new DB tables
2. GraphQL (schema + code-first) + gRPC included in 10.1
3. Rule severity: `error` (default) | `warn`, backward compatible v1→v2
4. 15 beads in 3 waves, 8-way parallelism in Wave 1

## Blockers
None.
