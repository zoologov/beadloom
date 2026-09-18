# ACTIVE: BDL-072 — The nightly mutation run judges nothing

> **Last updated:** 2026-09-18
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-ey4m` — the helper in `tests/` and the four walking tests moved onto it.
**Goal:** a `mutmut run` that reaches a verdict on a non-zero population, and a nightly whose
silence can no longer be mistaken for success.
**Done when:** both scoring steps print a score instead of `Score: none`, measured on a real run.

## Progress

- [x] Docs folder and the Explore axes (2026-09-18) — 4 seeds, 0 kept nodes, the route recorded
- [x] BRIEF written, `docs quality` clean, beads created
- [ ] BRIEF approved by the owner
- [x] `beadloom-ey4m` (2026-09-18) — `tests/package_under_test.py` answers both halves; the four
      walking tests read the package through it. Green on the tree (10766 passed, 13 skipped,
      13 xfailed) and green in a clean room over 7 carried files (284 passed, 5 xfailed).
- [ ] The nightly's announcement (`beadloom-95dm`)
- [ ] Tests, review
- [ ] The real verdict from a dispatched run

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Tracker | Bead | Status | Details |
|---|---|---|---|
| `beadloom-3js4` | parent | Open | BDL-072 parent |
| `beadloom-ey4m` | dev-1 | Closed | the helper in `tests/` and the four walking tests; verified over a room built from real mutmut 3.7.0 output |
| `beadloom-95dm` | dev-2 | Ready | a dead or red nightly announces itself |
| `beadloom-hz0n` | test | Blocked | a guard cannot read a generated mutant again |
| `beadloom-d7qn` | review | Blocked | nothing was merely skipped |
| `beadloom-e8m4` | verify | Blocked | dispatched run, the real numbers |

## Notes

- The measurement has been dead since 2026-09-10; the scope grew from 6544 to 7187 mutants in that
  time, so the first scored run is a new baseline rather than a comparison.
- `beadloom.__file__` inside a mutmut run points at `mutants/src/beadloom` — the package under test,
  with mutant bodies in it. Resolving the root through the imported package is necessary and not
  sufficient; generated names must be declined as well.
- Removing the failing test from the pool is closed: `tests/test_mutation_runner_scope.py:174`.
