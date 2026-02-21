# ACTIVE: BDL-033 — v1.8.0 Release Finalization

> **Last updated:** 2026-02-21
> **Phase:** Completed

---

## Bead Map

| Bead ID | BEAD | Name | Agent | Status |
|---------|------|------|-------|--------|
| beadloom-puf.1 | BEAD-01 | Version bump + CHANGELOG | /dev | Done |
| beadloom-puf.2 | BEAD-02 | README.md + README.ru.md update | /tech-writer | Done |
| beadloom-puf.3 | BEAD-03 | README.ru.md update | /tech-writer | Done (by BEAD-02) |
| beadloom-puf.4 | BEAD-04 | architecture.md + getting-started.md | /tech-writer | Done |
| beadloom-puf.5 | BEAD-05 | CONTRIBUTING.md + SECURITY.md | /tech-writer | Done |
| beadloom-puf.6 | BEAD-06 | STRATEGY-2.md update | /dev | Done |
| beadloom-puf.7 | BEAD-07 | Review verification | /review | Done |

## Waves

### Wave 1 — BEAD-01 + BEAD-02 + BEAD-06 (parallel)
- [x] BEAD-01: Version bumped to 1.8.0 in __init__.py + CLAUDE.md, CHANGELOG updated with BDL-032 entries
- [x] BEAD-02: README.md + README.ru.md updated (rules v3 tags, exclude filter, rule type keywords)
- [x] BEAD-06: STRATEGY-2.md updated with Phase 12.13 (Enhanced Architecture Rules)

### Wave 2 — BEAD-03 + BEAD-04 + BEAD-05 (parallel)
- [x] BEAD-03: Covered by BEAD-02 (both READMEs updated in one pass)
- [x] BEAD-04: architecture.md — NodeMatcher exclude documented; getting-started.md already accurate
- [x] BEAD-05: SECURITY.md — fixed MCP tool name + supported versions table; CONTRIBUTING.md already accurate

### Wave 3 — BEAD-07 (review)
- [x] BEAD-07: Review passed after fix cycle (3 issues found and fixed)

## Results

- BEAD-01: version 1.8.0, CHANGELOG +5 Added +3 Changed entries for BDL-032, test count 2537
- BEAD-02: README.md+README.ru.md — rules v3 tags block, exclude filter, corrected YAML keywords, MCP tool get_debt_report
- BEAD-03: covered by BEAD-02
- BEAD-04: architecture.md — NodeMatcher exclude field documented in Rules Engine section
- BEAD-05: SECURITY.md — docs_audit→get_debt_report, supported versions updated to 1.x
- BEAD-06: Phase 12.13 added to STRATEGY-2.md, status line updated
- BEAD-07: Review passed — 3 issues fixed (version tests, MCP tool name in READMEs), 2537 tests pass

## Notes

- Parent bead: beadloom-puf
- v1.8.0 tag exists at ff06a26 (pre-BDL-032), needs recreation
- Review found `docs_audit` listed as MCP tool in READMEs but actual name is `get_debt_report` — fixed
