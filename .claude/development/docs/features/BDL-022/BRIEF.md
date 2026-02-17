# BDL-022: v1.7.0 Documentation Refresh

> **Type:** chore
> **Priority:** P1
> **Status:** Approved
> **Created:** 2026-02-17

## Problem

After completing v1.7.0 (AaC Rules v2 + Init Quality + Architecture Intelligence), public-facing documentation is stale. Key discrepancies:

- **MCP tools:** All docs say "10 tools", actual count is **13** (missing `why`, `diff`, `lint`)
- **CLI commands:** README says "21 commands", actual is **22** (added `snapshot`)
- **Rules engine:** Only `deny`/`require` documented; v1.7.0 added `forbid_edge`, `layer`, `cycle_detection`, `import_boundary`, `cardinality` rule types
- **SECURITY.md:** Says MCP is "read-only" — incorrect since v1.6 added `update_node`/`mark_synced`
- **Init flow:** `--yes`/`--non-interactive` flags not documented
- **STRATEGY-2.md:** Phase 12/12.5/12.6 still marked "Planned", should be "DONE"
- **AGENTS.md/README.md:** Generated files have stale tool lists

## Solution

Systematic doc refresh across 10 files in parallel waves:

### Wave 1 — Core public docs (parallel, 3 agents)
- **BEAD-01:** README.md + README.ru.md — MCP tools, CLI commands, rules examples, feature list
- **BEAD-02:** CONTRIBUTING.md + SECURITY.md — MCP command fix, write ops disclosure
- **BEAD-03:** STRATEGY-2.md — Mark Phases 12, 12.5, 12.6 as DONE, update metrics table

### Wave 2 — Technical docs + generated files (parallel, 3 agents)
- **BEAD-04:** docs/getting-started.md — Init flags, new commands, enhanced `why`
- **BEAD-05:** docs/architecture.md — Rules engine v2 docs, MCP/CLI counts, schema updates
- **BEAD-06:** .beadloom/AGENTS.md + .beadloom/README.md — Regenerate/update tool lists

### Wave 3 — Validation
- **BEAD-07:** Full validation: beadloom reindex, sync-check, lint, doctor. Fix any issues.

## Beads

| Bead | Title | Priority | Depends on |
|------|-------|----------|------------|
| BEAD-01 | Update README.md + README.ru.md | P0 | — |
| BEAD-02 | Update CONTRIBUTING.md + SECURITY.md | P0 | — |
| BEAD-03 | Update STRATEGY-2.md (mark phases done) | P0 | — |
| BEAD-04 | Update docs/getting-started.md | P1 | — |
| BEAD-05 | Update docs/architecture.md | P1 | — |
| BEAD-06 | Update .beadloom/AGENTS.md + .beadloom/README.md | P1 | — |
| BEAD-07 | Final validation + git commit | P0 | BEAD-01..06 |

## Acceptance Criteria

- [ ] All MCP tool counts updated to 13
- [ ] All CLI command counts updated to 22
- [ ] New rule types documented with examples in README
- [ ] SECURITY.md accurately describes MCP write ops
- [ ] STRATEGY-2.md phases 12/12.5/12.6 marked DONE
- [ ] `beadloom sync-check` reports 0 stale
- [ ] `beadloom lint --strict` passes
- [ ] All changes committed and pushed
