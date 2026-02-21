# BRIEF: BDL-033 — v1.8.0 Release Finalization

> **Type:** chore
> **Status:** Approved
> **Created:** 2026-02-21

---

## Problem

v1.8.0 was partially prepared (BDL-031: CHANGELOG, README, docs) and tagged, but never truly released:

1. **Version not bumped** — `__init__.py` still says `1.7.0`, CLAUDE.md says `1.7.0`
2. **BDL-032 changes missed** — Enhanced Architecture Rules (NodeMatcher exclude, rules.yml v3, 9 rules, forbid_import) landed after the v1.8.0 tag
3. **CHANGELOG incomplete** — BDL-032 items (NodeMatcher exclude filter, rules.yml v3, forbid_import rules, skill instruction updates) not listed
4. **STRATEGY-2.md missing BDL-032** — No phase entry for Enhanced Architecture Rules work
5. **Stale v1.8.0 tag** — tag points to pre-BDL-032 commit, needs to be recreated
6. **Project docs may be stale** — README, architecture.md, getting-started.md, CONTRIBUTING.md, SECURITY.md need review for accuracy with current 1.8.0 scope

## Solution

Systematic release finalization:

1. **BEAD-01: Version bump + CHANGELOG** — bump `__init__.py` to `1.8.0`, update CLAUDE.md version, add BDL-032 entries to CHANGELOG
2. **BEAD-02: README.md update** — verify English README reflects all v1.8.0 features (NodeMatcher exclude, 9 rules, tags)
3. **BEAD-03: README.ru.md update** — sync Russian README with English version
4. **BEAD-04: architecture.md + getting-started.md** — verify technical docs accuracy
5. **BEAD-05: CONTRIBUTING.md + SECURITY.md** — verify project structure, MCP tools count, CLI commands count
6. **BEAD-06: STRATEGY-2.md update** — add BDL-032 phase entry (Enhanced Architecture Rules dogfooding)
7. **BEAD-07: Review verification** — final review of all changes

## Beads

| ID | Name | Priority | Status |
|----|------|----------|--------|
| BEAD-01 | Version bump + CHANGELOG | P0 | Pending |
| BEAD-02 | README.md update | P0 | Pending |
| BEAD-03 | README.ru.md update | P0 | Pending |
| BEAD-04 | architecture.md + getting-started.md | P1 | Pending |
| BEAD-05 | CONTRIBUTING.md + SECURITY.md | P1 | Pending |
| BEAD-06 | STRATEGY-2.md update | P1 | Pending |
| BEAD-07 | Review verification | P1 | Pending |

## Acceptance Criteria

- [ ] `__init__.py` version is `1.8.0`
- [ ] CLAUDE.md auto-section shows `1.8.0`
- [ ] CHANGELOG.md includes BDL-032 entries
- [ ] README.md and README.ru.md are accurate and in sync
- [ ] architecture.md and getting-started.md reflect v1.8.0 state
- [ ] CONTRIBUTING.md and SECURITY.md have correct counts
- [ ] STRATEGY-2.md has BDL-032 phase entry
- [ ] `beadloom sync-check` clean
- [ ] `beadloom lint --strict` — 0 errors
- [ ] All tests pass
- [ ] v1.8.0 tag recreated at final commit
