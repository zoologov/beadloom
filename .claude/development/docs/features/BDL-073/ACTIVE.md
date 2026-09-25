# ACTIVE: BDL-073 — The mutation duty becomes executable

> **Last updated:** 2026-09-25
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 1 — `beadloom-l2b7` (B1, the gap tests) and `beadloom-7omx` (B2, the ordered entry point), in parallel.
**Goal:** the five survivor gaps pinned before any refactor, and each mutant's covering tests handed
to pytest cheapest-first.
**Done when:** B1's tests are each red against their mutant and green on the tree; B2's entry point
refuses a mutmut whose patched line moved, and the six-mutant benchmark keeps its verdicts at a mean
time-to-kill of 6 s or less.

## Progress

- [x] Docs folder and the Explore axes (2026-09-20) — 3 seeds, 15 nodes, 5 kept by owner ruling
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-20 .. 2026-09-25)
- [x] Beads created: epic `beadloom-nzlc` + 8, one plan, 7 edges confirmed against the titles; swarm valid, 7 waves
- [ ] Wave 1: B1 + B2
- [ ] Wave 2-3: B3 (the table), B4 (the memo)
- [ ] Wave 4-6: B5 (numbers), B6 (review), B7 (docs)
- [ ] Wave 7: B8 — a dispatched run prints both scores (needs `gh auth refresh -s workflow`)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-nzlc` | epic | ready | BDL-073 parent |
| `beadloom-l2b7` | B1 dev | ready | the five gap tests, written first |
| `beadloom-7omx` | B2 dev | ready | covering tests ordered cheapest-first; two children |
| `beadloom-jqoa` | B3 dev | blocked | the dispatch becomes a table |
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
