# PLAN: BDL-028 — TUI Bug Fixes (Phase 12.13)

> **Status:** Done
> **Created:** 2026-02-20

---

## Beads Structure

```
BDL-028 [feature] — TUI Bug Fixes (Phase 12.13)
├── BEAD-01 [bug/dev]  — Fix #58: Threading error on quit
├── BEAD-02 [bug/dev]  — Fix #59: Explorer downstream dependents always empty
├── BEAD-03 [bug/dev]  — Fix #60: Explorer broken after early empty visit
├── BEAD-04 [task/test] — Regression tests for all 3 fixes
├── BEAD-05 [task/review] — Code review
└── BEAD-06 [task/tech-writer] — Update UX issues log + docs
```

## Dependencies (DAG)

```
BEAD-01 ──┐
BEAD-02 ──┼──> BEAD-04 (test) ──> BEAD-05 (review) ──> BEAD-06 (tech-writer)
BEAD-03 ──┘
```

## Waves

### Wave 1: Dev (parallel)
- **BEAD-01** [/dev]: Fix file watcher shutdown — add shutdown flag + try-except in `post_message()`
- **BEAD-02** [/dev]: Fix downstream dependents rendering pipeline in `DependencyPathWidget`
- **BEAD-03** [/dev]: Fix Explorer screen state — add `on_screen_resume` hook

All 3 are independent — can run in parallel.

### Wave 2: Test
- **BEAD-04** [/test]: Regression tests for #58, #59, #60

Depends on all dev beads completing.

### Wave 3: Review
- **BEAD-05** [/review]: Code review of all changes

Depends on BEAD-04.

### Wave 4: Tech-writer
- **BEAD-06** [/tech-writer]: Close issues #58-60 in BDL-UX-Issues.md, update CHANGELOG

Depends on BEAD-05.

## Acceptance Criteria

- [ ] No `RuntimeError` on quit (#58)
- [ ] Downstream dependents display correctly (#59)
- [ ] Explorer works regardless of visit order (#60)
- [ ] All existing TUI tests pass (234+)
- [ ] New regression tests for each fix
- [ ] `beadloom sync-check` passes
- [ ] `beadloom lint --strict` passes
- [ ] Issues #58-60 closed in BDL-UX-Issues.md
