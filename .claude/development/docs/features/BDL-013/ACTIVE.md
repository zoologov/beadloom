# ACTIVE: BDL-013 — Dogfood Beadloom + Agent Instructions + CI

> **Current phase:** COMPLETED
> **Last updated:** 2026-02-14

---

## Completed

- [x] PRD created and approved
- [x] RFC created and approved
- [x] CONTEXT.md created
- [x] PLAN.md created
- [x] ACTIVE.md created
- [x] Epic + 13 beads created in beads CLI
- [x] **Wave 1:** D10 (rules.yml +2 rules), D9 (pre-commit warn), D2 (tests.yml path filters), D12 (.beadloom/README.md + code + tests), D13 (knowledge→architecture rename, 26 files)
- [x] **Wave 2:** D11 (fixed 2 lint violations: self-ref edge + unless_edge exemption)
- [x] **Wave 3:** D3 (CLAUDE.md §2.1), D4 (dev.md dynamic structure), D5 (review.md checklist), D6 (test.md flat layout), D7 (coordinator.md validation)
- [x] **Wave 4:** D8 (deleted AGENTS.md, migrated shell warning to CLAUDE.md)
- [x] **Wave 5:** D1 (beadloom-aac-lint.yml CI workflow)

## Final Verification

- 811 tests pass
- ruff clean, mypy clean
- beadloom lint: 0 violations, 4 rules
- beadloom sync-check: all OK
- beadloom doctor: all OK
