# ACTIVE: BDL-073 — The mutation duty becomes executable

> **Last updated:** 2026-09-25
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 2 — `beadloom-jqoa` (B3, the table), while a dispatched `Mutation` run measures the branch at two children.
**Goal:** the twelve-branch dispatch as one table, proven against B1's twenty cases; and the first run since the kill with two children and the new killers.
**Done when:** B3's done-when in PLAN.md holds, and the dispatched run has either printed both scores or died somewhere the bead records.

## Progress

- [x] Docs folder and the Explore axes (2026-09-20) — 3 seeds, 15 nodes, 5 kept by owner ruling
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-20 .. 2026-09-25)
- [x] Beads created: epic `beadloom-nzlc` + 8, one plan, 7 edges confirmed against the titles; swarm valid, 7 waves
- [x] Wave 1: B1 (`1688c707`, 20 cases; all five survivors killed on the activated mutant) + B2 restated as `--max-children 2` (`a3bf2e2d`) — the ordering premise was withdrawn, see the correction in PRD/RFC
- [ ] Wave 2-3: B3 (the table), B4 (the memo)
- [ ] Wave 4-6: B5 (numbers), B6 (review), B7 (docs)
- [ ] Wave 7: B8 — a dispatched run prints both scores (needs `gh auth refresh -s workflow`)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-nzlc` | epic | ready | BDL-073 parent |
| `beadloom-l2b7` | B1 dev | ✓ done | 20 cases in `tests/test_load_rules_pins_its_codec_and_messages.py`, each of mutants 2, 15, 33, 41 and 233 seen red from inside `mutants/` with `PYTHONPATH=mutants/src` (plus the ten sibling `msg = None` mutants); commit `1688c707`; gate owner: combined tree green, `beadloom ci` rc 0 on Darwin 3.13 |
| `beadloom-7omx` | B2 dev | ✓ done | two children landed; no ordering entry point built — mutmut 3.7.0 already runs covering tests cheapest-first (six mutants, 1.16 s mean, stock); owner decision pending |
| `beadloom-jqoa` | B3 dev | ready | the dispatch becomes a table |
| `beadloom-m19h` | B4 dev | blocked | one parse per init |
| `beadloom-4243` | B5 test | blocked | the numbers the PRD promised |
| `beadloom-8cbm` | B6 review | blocked | no hidden special case, no silent patch |
| `beadloom-xn48` | B7 tech-writer | blocked | SPEC, cli.md, gate-coverage |
| `beadloom-kj8t` | B8 verify | blocked | a dispatched run prints both scores |

## Notes

- A mutant run by hand needs `PYTHONPATH=<repo>/mutants/src`; without it the mutant is never
  activated and a survival is false (measured 2026-09-19).
- The runner's killer stays on `beadloom-5isv`: seven of eight deaths at queue positions 4146-4226,
  one at 3281 after 102 minutes.
