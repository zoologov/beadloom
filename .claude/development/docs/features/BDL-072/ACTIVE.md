# ACTIVE: BDL-072 — The nightly mutation run judges nothing

> **Last updated:** 2026-09-19 (second pass)
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-95dm` — the nightly announces a dead or red run. `beadloom-ey4m` closed 2026-09-18.
**Goal:** a `mutmut run` that reaches a verdict on a non-zero population, and a nightly whose
silence can no longer be mistaken for success.
**Done when:** both scoring steps print a score instead of `Score: none`, measured on a real run.

## Progress

- [x] Docs folder and the Explore axes (2026-09-18) — 4 seeds, 0 kept nodes, the route recorded
- [x] BRIEF written, `docs quality` clean, beads created
- [x] BRIEF approved by the owner (2026-09-18)
- [x] `beadloom-ey4m` (2026-09-18) — `tests/package_under_test.py` answers both halves; the four
      walking tests read the package through it. Green on the tree (10766 passed, 13 skipped,
      13 xfailed) and green in a clean room over 7 carried files (284 passed, 5 xfailed).
- [x] The nightly's announcement (`beadloom-95dm`, `ea23a6c2`) — both failure shapes, `gh` itself still unmeasured
- [x] Tests (`26de3711`, 43 added) and review — ISSUES: 0 critical, 1 major, 4 minor, 3 nitpick
- [ ] The review's fixes, then the real verdict from a dispatched run

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-3js4` | parent | ready | BDL-072 parent |
| `beadloom-ey4m` | dev-1 | ✓ done | the helper in `tests/` and the four walking tests; verified over a room built from real mutmut 3.7.0 output |
| `beadloom-95dm` | dev-2 | ✓ done | the `announce` job: one labelled issue, both shapes of silence, `gh` itself still unmeasured |
| `beadloom-hz0n` | test | ✓ done | 43 tests: the class guard over the 155 selected files, the 4-site number held over a mutated copy of the real package, and six breaks of the announcement each proven to turn a test red |
| `beadloom-d7qn` | review | ✓ done | three passes: ISSUES (1 major), ISSUES (1 critical, 1 major), then OK. The critical was the locale defect two required legs then proved |
| `beadloom-3js4.1` | fix-dev | ✓ done | the announcement's script reaches bash as a UTF-8 file instead of an argv the locale's codec must hold, and the break harness no longer reads its own failure as the break it planted; measured red then green in a Linux container under `LC_ALL=C` and `LC_ALL=en_US.ISO-8859-1` |
| `beadloom-vd6r` | fix-dev | ✓ done | the concurrency group is scoped by event, so the verify bead's dispatch cannot cancel the schedule and be announced as an outage; the import prune matches mutmut's injected module by name |
| `beadloom-r7eg` | fix-docs | ✓ done | the twenty-second declared room in `cli.md`, and both pages now name the announcement channel |
| `beadloom-e8m4` | verify | In progress | run 35405302194 judged 4151 of 7187 mutants before the runner was shut down; re-dispatch owes a completed score |

## Notes

- The measurement has been dead since 2026-09-10; the scope grew from 6544 to 7187 mutants in that
  time, so the first scored run is a new baseline rather than a comparison.
- `beadloom.__file__` inside a mutmut run points at `mutants/src/beadloom` — the package under test,
  with mutant bodies in it. Resolving the root through the imported package is necessary and not
  sufficient; generated names must be declined as well.
- Removing the failing test from the pool is closed: `tests/test_mutation_runner_scope.py:174`.
