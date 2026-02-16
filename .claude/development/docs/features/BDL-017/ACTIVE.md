# BDL-017: Active Work

## Current Focus
EPIC COMPLETE — all 15 beads closed, all 3 waves done.

## Progress
- [x] PRD — approved
- [x] RFC — approved (with GraphQL + gRPC)
- [x] CONTEXT.md — approved
- [x] PLAN.md — approved (15 beads, 3 waves)
- [x] Beads created (15 beads) + dependencies
- [x] **Wave 1 — COMPLETE** (8/8 beads, 142 new tests)
  - [x] BEAD-01: API Route Extraction — 12 frameworks, 36 tests
  - [x] BEAD-02: Git History Analysis — 4 activity levels, 17 tests
  - [x] BEAD-03: Test Mapping — 5 frameworks, 24 tests
  - [x] BEAD-04: Rule Severity — error/warn, backward compat, 19 tests
  - [x] BEAD-05: MCP why — structured JSON, 7 tests
  - [x] BEAD-06: MCP diff — graph changes, 7 tests
  - [x] BEAD-07: Deep Config — 5 config formats, 20 tests
  - [x] BEAD-08: Cost Metrics — token estimation in status, 12 tests
- [x] **Wave 2 — COMPLETE** (5/5 beads)
  - [x] BEAD-09: Integrate Routes into Reindex — routes in nodes.extra
  - [x] BEAD-10: Integrate Git Activity into Reindex — activity levels
  - [x] BEAD-11: Integrate Test Mapping into Reindex — test mappings
  - [x] BEAD-12: MCP Tool — lint — severity in JSON output
  - [x] BEAD-13: Integrate Deep Config into Bootstrap — config in root extra
- [x] **Wave 3 — COMPLETE** (2/2 beads, 1362 total tests, 0 failures)
  - [x] BEAD-14: Smart Docs Polish with Deep Data — 15 tests
  - [x] BEAD-15: E2E Validation + AGENTS.md Update — 8 E2E tests, 13 MCP tools

## Recent Actions
- 2026-02-16: Epic init. PRD, RFC, CONTEXT, PLAN approved.
- 2026-02-16: Wave 1 completed — 8 beads, 142 new tests, commit 6d2b206.
- 2026-02-16: Wave 2 completed — 5 beads, commit cef4379.
- 2026-02-16: Wave 3 completed — BEAD-14 (polish enrichment) + BEAD-15 (E2E + AGENTS.md).
- 2026-02-16: **EPIC CLOSED** — 15/15 beads, 1362 tests, 0 failures. 5 UX issues recorded.

## Decisions
1. All new data in `nodes.extra` JSON — no new DB tables
2. GraphQL (schema + code-first) + gRPC included in 10.1
3. Rule severity: `error` (default) | `warn`, backward compatible v1→v2
4. 15 beads in 3 waves, 8-way parallelism in Wave 1
5. Porcelain lint format: 7 fields (severity added)
6. Deep config adds `extra.config` even without README — test updated accordingly

## Blockers
None — epic complete.
