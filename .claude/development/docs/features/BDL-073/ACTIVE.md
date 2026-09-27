# ACTIVE: BDL-073 — The mutation duty becomes executable

> **Last updated:** 2026-09-25
> **Phase:** Completed

---

## Current Bead

**Bead:** none — every bead of BDL-073 is closed; merged as `c1bc85ca` (PR #81).

## Progress

- [x] Docs folder and the Explore axes (2026-09-20) — 3 seeds, 15 nodes, 5 kept by owner ruling
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-20 .. 2026-09-25)
- [x] Beads created: epic `beadloom-nzlc` + 8, one plan, 7 edges confirmed against the titles; swarm valid, 7 waves
- [x] Wave 1: B1 (`1688c707`, 20 cases; all five survivors killed on the activated mutant) + B2 restated as `--max-children 2` (`a3bf2e2d`) — the ordering premise was withdrawn, see the correction in PRD/RFC
- [x] Wave 2: B3 (`f5160866`) — `load_rules` 333 → 126 mutants; `forbid_cycles` folded into the table and no `requires_mapping` column, both put to review
- [x] Wave 3: B4 (`ca671a78`) — one parse per init; the memo compares the file's text (owner accepted)
- [x] Wave 4: B5 (`f77975e4`) — load_rules 123/136 killed serially (90.4%), 13 survivors; two children still false-kill; no child above 399 MiB, parent flat ~550 MiB (memory ruled out for the loader on Darwin)
- [x] Wave 5: B6 review OK — main vs HEAD `load_rules` over 1904 generated rules files, 0 differences; 4 minors + 1 nitpick
- [x] F1: the review's minors (added to the DAG 2026-09-26)
- [x] Wave 6: B7 (`a4e2a341`) — four stale pairs to zero; `beadloom ci` rc 0
- [ ] Wave 7: B8 — a dispatched run prints both scores (needs `gh auth refresh -s workflow`)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-nzlc` | epic | ✓ done | BDL-073 parent |
| `beadloom-l2b7` | B1 dev | ✓ done | 20 cases in `tests/test_load_rules_pins_its_codec_and_messages.py`, each of mutants 2, 15, 33, 41 and 233 seen red from inside `mutants/` with `PYTHONPATH=mutants/src` (plus the ten sibling `msg = None` mutants); commit `1688c707`; gate owner: combined tree green, `beadloom ci` rc 0 on Darwin 3.13 |
| `beadloom-7omx` | B2 dev | ✓ done | two children landed; no ordering entry point built — mutmut 3.7.0 already runs covering tests cheapest-first (six mutants, 1.16 s mean, stock); owner decision pending |
| `beadloom-jqoa` | B3 dev | ✓ done | `load_rules` 333 -> 126 mutants (mutmut 3.7.0 `mutate_file_contents`, generation only); one table of eleven mapping keys, `layers` explicit, `forbid_cycles` a table entry; `rules_gen` reads `AUTHORING_KEYS`; full suite green on the tree, Darwin 3.13; four doc pairs stale for `beadloom-xn48` |
| `beadloom-m19h` | B4 dev | ✓ done | one parse per `init` (2 -> 1, both `--yes` and `--bootstrap`); memo keyed on the resolved path and trusted only while the text is unchanged, so a same-size edit inside one timestamp tick is re-parsed; forgotten before every test by an autouse fixture (mutmut fork hazard); 11 tests; suite green on the tree, Darwin 3.13; no new stale pair |
| `beadloom-4243` | B5 test | ✓ done | `load_rules` 136 mutants on HEAD; serial `mutmut run`: 123 killed / 13 survived (90.4%, 2 equivalent + 11 gaps); at two children 128/8 and 126/10 - the difference is false kills; memo: no false survival with or without the fixture; 855 covering tests (827 + 28 new); peak RSS per child 399 MiB, parent flat ~550 MiB - memory ruled out for the loader on Darwin; suite 10857 passed on the tree; coverage 86% / 96%, changed lines 100% |
| `beadloom-8cbm` | B6 review | ✓ done | no hidden special case, no silent patch |
| `beadloom-nzlc.1` | F1 dev | ✓ done | the memo stores a tuple and returns a new list per call (copy 0.078 us vs 13.31 ms parse, measured); mutmut's cheapest-first sort and `-p no:randomly` pinned by `tests/test_mutmut_runs_covering_tests_cheapest_first.py` (green on 3.7.0 and 3.8.0, red on a stand-in); `forget_parsed_rules()` replaces both reaches into `_PARSED`; suite 10869 passed on the tree, Darwin 3.13; no new stale pair |
| `beadloom-xn48` | B7 tech-writer | ✓ done | four stale pairs 4 -> 0 (graph README, rule-engine SPEC, onboarding README, agent-prime SPEC); cli.md + gate-coverage: two children and why, cheapest-first already upstream and pinned, the runner's killer still open (`beadloom-5isv`); commit `a4e2a341`; `beadloom ci` rc 0 on the tree, Darwin; doc-reading tests 957 + acceptance 510 passed |
| `beadloom-kj8t` | B8 verify | ✓ done | a dispatched run prints both scores |

## Notes

- A mutant run by hand needs `PYTHONPATH=<repo>/mutants/src`; without it the mutant is never
  activated and a survival is false (measured 2026-09-19).
- The runner's killer stays on `beadloom-5isv`: seven of eight deaths at queue positions 4146-4226,
  one at 3281 after 102 minutes.

## Outcome

- **Landed (PR #81, `c1bc85ca`):** twenty cases killing the five sampled survivors of `load_rules`; the
  twelve-branch dispatch as one table (333 → 136 mutants; 0 differences from `main` over 1904 generated
  rules files); one parse per `init` through a text-comparing memo returning a fresh list; two mutmut
  children; mutmut's own cheapest-first ordering pinned by a test.
- **Withdrawn mid-flight:** the ordering entry point — mutmut 3.7.0 already orders covering tests.
- **Not achieved, and said so:** the PRD's headline criterion. The verify run on the final head died at
  queue position 4125/6992 after 153 min with the runner's shutdown signal; no aggregate score exists.
- **What the owner decided on 2026-09-27 instead:** retire the whole-scope nightly (workflow disabled,
  issue #79 closed not_planned, `beadloom-5isv` closed as superseded with the killer unidentified) and
  replace it with mutation scoped to each pull request plus a weekly random sample — a new work item.
