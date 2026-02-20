# ACTIVE: BDL-025 — Interactive Architecture TUI

> **Last updated:** 2026-02-20
> **Phase:** Wave 2+3 In Progress — BEAD-02, BEAD-03, BEAD-05, BEAD-06 parallel

---

## Summary

Phase 12.10: Interactive Architecture TUI — multi-screen dashboard with graph explorer, debt gauge, file watcher, doc status, keyboard actions.

## Progress

- [x] PRD.md created and approved
- [x] RFC.md created and approved
- [x] CONTEXT.md approved
- [x] PLAN.md approved (10 beads, 7 waves)
- [x] All beads created with dependencies
- [x] Wave 1: BEAD-01 — Data Providers + App Shell (37 tests, all quality checks pass)
- [ ] Wave 2: BEAD-02 + BEAD-03 (parallel) — Dashboard + Graph Tree
- [ ] Wave 3: BEAD-04 + BEAD-05 + BEAD-06 (parallel) — Explorer + DocStatus + FileWatcher
- [ ] Wave 4: BEAD-07 — Keyboard Actions + Overlays
- [ ] Wave 5: BEAD-08 — Test Review
- [ ] Wave 6: BEAD-09 — Code Review
- [ ] Wave 7: BEAD-10 — Documentation

## Beads

- Parent: `beadloom-cjm`
- BEAD-01: `beadloom-cjm.1` (done)
- BEAD-02: `beadloom-cjm.2` (unblocked — ready)
- BEAD-03: `beadloom-cjm.3` (unblocked — ready)
- BEAD-04: `beadloom-cjm.4` (blocked by .2, .3)
- BEAD-05: `beadloom-cjm.5` (unblocked — ready)
- BEAD-06: `beadloom-cjm.6` (unblocked — ready)
- BEAD-07: `beadloom-cjm.7` (blocked by .4, .5, .6)
- BEAD-08: `beadloom-cjm.8` (blocked by .7)
- BEAD-09: `beadloom-cjm.9` (blocked by .8)
- BEAD-10: `beadloom-cjm.10` (blocked by .9)

## BEAD-01 Deliverables

- 7 data providers in `data_providers.py` (Graph, Lint, Sync, Debt, Activity, Why, Context)
- Multi-screen app shell with 3 screens (Dashboard, Explorer, DocStatus)
- Global keybindings: 1/2/3 (screens), q, ?, /, r, l, s, Tab
- `beadloom tui` primary command + `beadloom ui` alias with `--no-watch` flag
- Textual bumped to >=0.80
- 37 tests covering all providers, app shell, screen switching, CLI

## Notes

- Wave 2 beads (.2, .3) and beads .5, .6 are now unblocked
- Sync-check shows expected stale for tui/cli (symbols changed vs preserved baseline)
