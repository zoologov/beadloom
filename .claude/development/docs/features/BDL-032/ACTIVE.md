# ACTIVE: BDL-032 — Enhanced Architecture Rules

> **Last updated:** 2026-02-21
> **Phase:** Completed

---

## Bead Map

| Bead ID | BEAD | Name | Agent | Status |
|---------|------|------|-------|--------|
| beadloom-ozw.1 | BEAD-01 | NodeMatcher exclude filter | /dev | Done |
| beadloom-ozw.2 | BEAD-02 | rules.yml v3 upgrade | /dev | Done |
| beadloom-ozw.3 | BEAD-03 | forbid_import verification | /dev | Done |
| beadloom-ozw.4 | BEAD-04 | Test verification | /test | Done |
| beadloom-ozw.5 | BEAD-05 | Code review | /review | Done |
| beadloom-ozw.6 | BEAD-06 | Doc update | /tech-writer | Done |
| beadloom-ozw.7 | BEAD-07 | Stale docs fix (architecture, graph, SPEC) | /tech-writer | Done |

## Waves

### Wave 1 — BEAD-01 (NodeMatcher exclude)
- [x] BEAD-01: Add exclude field to NodeMatcher

### Wave 2 — BEAD-02 (rules.yml upgrade)
- [x] BEAD-02: Upgrade to v3, add 3 new rules (7 total)

### Wave 3 — BEAD-03 (forbid_import)
- [x] BEAD-03: Add and verify forbid_import rules

### Wave 4 — BEAD-04..06 (verification pipeline)
- [x] BEAD-04: Test verification
- [x] BEAD-05: Code review
- [x] BEAD-06: Doc update

## Results

- BEAD-01: NodeMatcher exclude filter added (10 tests, 2537 total pass, ruff+mypy clean)
- BEAD-02: rules.yml v3 with 7 rules, tags in services.yml, lint 0 errors/12 warnings, 2537 tests pass
- BEAD-03: Added 2 forbid_import rules (9 total), no violations found, lint 0 errors/12 warnings, 2537 tests pass
- BEAD-04: Test verification passed — 2537 tests pass, ruff+mypy clean, lint 0 errors/12 warnings
- BEAD-05: Code review passed — no blocking issues found
- BEAD-06: Doc update — AGENTS.md regenerated (4 rules -> 9 rules), beadloom prime verified (9 rules), sync-check clean. 3 UX issues logged (#67-69).
- BEAD-07: Stale docs fix — architecture.md (v1→v3), graph/README.md (NodeMatcher +exclude), rule-engine/SPEC.md (all 7 types + exclude). Skill instructions updated (/dev, /review, /tech-writer) to prevent recurrence.

## Notes

- Parent bead: beadloom-ozw
- Critical path: 01 → 02 → 03 → 04 → 05 → 06
- Layer rule uses severity: warn due to known infra→domain coupling
- Review finding: `forbid` (ForbidEdgeRule) type not exercised — 6/7 rule types covered (non-blocking)
