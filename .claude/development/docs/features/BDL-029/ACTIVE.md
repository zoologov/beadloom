# ACTIVE: BDL-029 — TUI UX Improvements Phase 12.14

> **Last updated:** 2026-02-21
> **Phase:** Completed

---

## Bead Map

| Bead ID | BEAD | Name | Agent | Status |
|---------|------|------|-------|--------|
| beadloom-j56 | BEAD-01 | Explorer direct navigation key | /dev | Done |
| beadloom-cl1 | BEAD-02 | Fix triangle icon cold start | /dev | Done |
| beadloom-jql | BEAD-03 | Edge count legend [N] | /dev | Done |
| beadloom-wb1 | BEAD-04 | Fix Esc crash ScreenStackError | /dev | Done |
| beadloom-691 | BEAD-05 | Update BDL-UX-Issues.md | /tech-writer | Done |
| beadloom-vy2 | BEAD-06 | Test verification | /test | Done |
| beadloom-jiy | BEAD-07 | Code review | /review | Done |

## Waves

### Wave 1 (dev) — BEADs 01-04 in parallel
- [x] BEAD-01: `e` key for Explorer navigation — 2 tests added
- [x] BEAD-02: triangle icon fix — 1 test added
- [x] BEAD-03: edge count legend — 3 new + 3 updated tests
- [x] BEAD-04: Esc crash fix — 2 tests added

### Wave 2 (docs + test) — after Wave 1
- [x] BEAD-05: update BDL-UX-Issues.md — #58-60 corrected, #61-64 added
- [x] BEAD-06: test verification — 2495 tests pass, 82% coverage

### Wave 3 (review) — after Wave 2
- [x] BEAD-07: code review — Review = OK

## Progress

- Wave 1 completed: all 4 dev beads done, 314 TUI tests pass, ruff + mypy clean
- Wave 2 completed: BDL-UX-Issues.md updated, 2495 total tests pass, 82% coverage
- Wave 3 completed: code review passed, no issues found

## Notes

- Parent bead: beadloom-vcx
- All dev beads were independent, safely parallelized
- BEAD-04 was P1 (crash), others P2
