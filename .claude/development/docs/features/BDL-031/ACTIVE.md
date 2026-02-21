# ACTIVE: BDL-031 — v1.8.0 Release Preparation

> **Last updated:** 2026-02-21
> **Phase:** Completed

---

## Bead Map

| Bead ID | BEAD | Name | Agent | Status |
|---------|------|------|-------|--------|
| beadloom-m1c.1 | BEAD-01 | Version bump + CHANGELOG | /tech-writer | Done |
| beadloom-m1c.2 | BEAD-02 | README.md + README.ru.md | /tech-writer | Done |
| beadloom-m1c.3 | BEAD-03 | architecture.md + getting-started.md | /tech-writer | Done |
| beadloom-m1c.4 | BEAD-04 | CONTRIBUTING.md + SECURITY.md | /tech-writer | Done |
| beadloom-m1c.5 | BEAD-05 | STRATEGY-2.md status update | /tech-writer | Done |
| beadloom-m1c.6 | BEAD-06 | CLAUDE.md refresh + validation | /tech-writer | Done |
| beadloom-m1c.7 | BEAD-07 | Review — final verification | /review | Pending |

## Waves

### Wave 1 — BEAD-01 (version bump)
- [x] BEAD-01: Version bump + CHANGELOG completion

### Wave 2 — BEAD-02..06 (parallel tech-writers)
- [x] BEAD-02: README.md + README.ru.md
- [x] BEAD-03: architecture.md + getting-started.md
- [x] BEAD-04: CONTRIBUTING.md + SECURITY.md
- [x] BEAD-05: STRATEGY-2.md
- [x] BEAD-06: CLAUDE.md refresh + AGENTS.md fix

### Wave 3 — BEAD-07 (review)
- [x] BEAD-07: Final verification — Review = OK

## Results

- BEAD-01: Version bumped to 1.8.0, CHANGELOG rewritten (all 8 deliverables)
- BEAD-02: README.md + README.ru.md updated (MCP 14, CLI 29, nodes 23, edges 63, 3 new features)
- BEAD-03: architecture.md + getting-started.md updated (counts, graph_snapshots table, docs audit)
- BEAD-04: CONTRIBUTING.md + SECURITY.md updated (29 commands, 14 tools, 12 read + 2 write)
- BEAD-05: STRATEGY-2.md all v1.8 phases marked DONE, version 1.8.0, revision 12
- BEAD-06: CLAUDE.md refreshed, AGENTS.md fixed (deduplicated, added get_debt_report tool)
- BEAD-07: Review = OK, 2527 tests pass, docs audit 47→38 stale, all validation clean

## Notes

- Parent bead: beadloom-m1c
- Ground truth from `beadloom docs audit`: 29 CLI commands, 14 MCP tools, 23 nodes, 63 edges, version 1.7.0 -> 1.8.0
- 47 commits since v1.7.0 across BDL-023 through BDL-030
