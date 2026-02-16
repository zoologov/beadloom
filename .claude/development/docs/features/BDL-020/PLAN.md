# PLAN: BDL-020 — Source Coverage Hierarchy Fix

> **Last updated:** 2026-02-17

---

## Beads

| Bead | Title | Priority | Dependencies |
|------|-------|----------|--------------|
| BEAD-01 | Fix 4 annotation mismatches | P0 | — |
| BEAD-02 | Hierarchy-aware check_source_coverage + tests | P0 | — |
| BEAD-03 | E2E validation on beadloom | P1 | BEAD-01, BEAD-02 |

## DAG

```
BEAD-01 (annotations) ──┐
                         ├──> BEAD-03 (E2E validation)
BEAD-02 (logic + tests) ┘
```

## Wave Plan

| Wave | Beads | Parallel | Agents |
|------|-------|----------|--------|
| Wave 1 | BEAD-01, BEAD-02 | Yes | 2 parallel agents |
| Wave 2 | BEAD-03 | No | 1 agent (coordinator) |

## Estimated Scope

- BEAD-01: 4 one-line annotation edits + reindex
- BEAD-02: ~25 lines new logic in engine.py + 4 unit tests in test_source_coverage.py
- BEAD-03: `beadloom sync-check` → 0 stale, full test suite green

## Critical Path

BEAD-01 + BEAD-02 → BEAD-03 → commit → push
