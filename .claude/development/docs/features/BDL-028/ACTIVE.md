# ACTIVE: BDL-028 — TUI Bug Fixes (Phase 12.13)

> **Last updated:** 2026-02-20

---

## Status: COMPLETE

All 4 waves done. All 6 beads closed.

## Completed Waves

### Wave 4: Tech-writer — DONE
| Bead | Task | Result |
|------|------|--------|
| beadloom-atc.6 | UX issues log | Issues #58-60 closed, counter 0 open |

### Wave 3: Review — DONE (OK)
| Bead | Task | Result |
|------|------|--------|
| beadloom-atc.5 | Code review | OK — all fixes correct, thread-safe, well-tested |

### Wave 2: Test — DONE
| Bead | Task | Result |
|------|------|--------|
| beadloom-atc.4 | Regression tests | 10 new edge-case tests added, 347/347 pass |


### Wave 1: Dev (parallel) — DONE
| Bead | Bug | Result |
|------|-----|--------|
| beadloom-atc.1 | #58 Threading quit | Fixed: shutdown flag + try-except in watcher. 5 tests added |
| beadloom-atc.2 | #59 Downstream empty | Fixed: pre-render tree text, cache snapshot in widget |
| beadloom-atc.3 | #60 Explorer state | Fixed: on_screen_resume handler syncs ref_id |

All 333 TUI tests pass after Wave 1.

## Progress Log

- 2026-02-20: PRD Approved, RFC Approved, CONTEXT+PLAN Approved
- 2026-02-20: 6 beads created, DAG configured, Wave 1 starting
- 2026-02-20: Wave 1 complete — all 3 dev beads closed, 333/333 tests pass
- 2026-02-20: Wave 2 starting — BEAD-04 test agent launched
