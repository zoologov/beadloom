# BDL-017: Active Work

## Current Focus
Wave 2 development — integration beads, 5 parallel agents.

## Progress
- [x] PRD — approved
- [x] RFC — approved (with GraphQL + gRPC)
- [x] CONTEXT.md — approved
- [x] PLAN.md — approved (15 beads, 3 waves)
- [x] Beads created (15 beads) + dependencies
- [x] **Wave 1 — COMPLETE** (8/8 beads, 1300 tests, 0 failures)
  - [x] BEAD-01: API Route Extraction — 12 frameworks, 36 tests
  - [x] BEAD-02: Git History Analysis — 4 activity levels, 17 tests
  - [x] BEAD-03: Test Mapping — 5 frameworks, 24 tests
  - [x] BEAD-04: Rule Severity — error/warn, backward compat, 19 tests
  - [x] BEAD-05: MCP why — structured JSON, 7 tests
  - [x] BEAD-06: MCP diff — graph changes, 7 tests
  - [x] BEAD-07: Deep Config — 5 config formats, 20 tests
  - [x] BEAD-08: Cost Metrics — token estimation in status, 12 tests
- [x] **Wave 2 — COMPLETE** (5/5 beads, 1339 tests, 0 failures)
  - [x] BEAD-09: Integrate Routes into Reindex — routes in nodes.extra, ctx shows Routes
  - [x] BEAD-10: Integrate Git Activity into Reindex — activity levels in nodes.extra
  - [x] BEAD-11: Integrate Test Mapping into Reindex — test mappings in nodes.extra
  - [x] BEAD-12: MCP Tool — lint — severity in JSON output, filter param
  - [x] BEAD-13: Integrate Deep Config into Bootstrap — config in root nodes.extra
- [ ] **Wave 3 — in progress (2 beads)**
  - [ ] BEAD-14: Smart Docs Polish with Deep Data [P1]
  - [ ] BEAD-15: E2E Validation + AGENTS.md Update [P0]

## Recent Actions
- 2026-02-16: Epic init. PRD, RFC, CONTEXT, PLAN approved.
- 2026-02-16: Wave 1 completed — 8 beads, 142 new tests, commit 6d2b206.
- 2026-02-16: Wave 2 completed — 5 beads, all integrated. Fixed test_readme_ingestion compat.
- 2026-02-16: Wave 3 started — BEAD-14 + BEAD-15.

## Decisions
1. All new data in `nodes.extra` JSON — no new DB tables
2. GraphQL (schema + code-first) + gRPC included in 10.1
3. Rule severity: `error` (default) | `warn`, backward compatible v1→v2
4. 15 beads in 3 waves, 8-way parallelism in Wave 1
5. Porcelain lint format: 7 fields (severity added)
6. Deep config adds `extra.config` even without README — test updated accordingly

## Blockers
None.
