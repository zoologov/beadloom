# ACTIVE: BDL-074 — Tests that belong to the graph

> **Last updated:** 2026-09-28
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 3 — `beadloom-2esy` (A3, the self-check triage) and `beadloom-3z94` (C2, ctx and debt-report read the binding), in parallel; then `beadloom-vr0b` (D1), which shares `cli-commands` with C2. PR 1 opens after A3.
**Goal:** the 547 self-checks sorted by what they guard, Gate duplicates removed, the allowed list emptied; ctx and debt-report stop calling the name-guessing mapper.
**Done when:** the allowed list is empty or each remaining entry names why; qq6m's tracer reads 0; ctx and debt-report read the binding with the four-key shape kept.

**Wave 2 closed (2026-09-27):** docs `65a098bc` (36 stale pairs → 0); A2 `596401ab`, `4e6b9c20`. Gate owner A2 on the combined tree: 10 975 passed, 0 failed, 13 skipped, 13 xfailed; `beadloom ci` rc 0. Allowed list 44 → 20; live-index contacts 98 → 1 — the A3 probe that hashes the index bytes, so qq6m stays open until A3.

**Wave 1 closed (2026-09-27):** A1 `8e17362e`, `12ad9f12`; C1 `90c04540`. Gate owner A1 on the combined tree: 10 958 passed, 1 failed (`test_all_new_node_pairs_are_fresh`), `beadloom ci` rc 1 on 36 stale doc pairs from C1's change — not planned for this point, so a docs bead `beadloom-2mj3.1` was added ahead of wave 2.

## Progress

- [x] Docs folder, the Explore axes (6 seeds, 15 nodes) and the measured suite map (`map/`, 2026-09-27)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-28); kept nodes 9
- [x] Beads created: epic `beadloom-2mj3` + 16, one plan, 20 edges confirmed against the titles; swarm valid, 11 waves
- [ ] Phase A — isolation and the self-check triage (PR 1)
- [ ] Phase B — layout (PR 2)
- [ ] Phases C, D, E — binding, rules, per-change mutation, pilot, standards (PR 3)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-2mj3` | epic | ready | BDL-074 parent |
| `beadloom-l67s` | A1 dev | ✓ done | chdir and contact guards; 115 tests in 20 files broke before the fix (measured); allowed list 44 entries |
| `beadloom-kixx` | A2 dev | ✓ done | self-check snapshot replaces `live_repo_reindexed`; allowed list 44 → 20; live-index contacts 98 → 1 (the A3 probe), 0 writers; build ≈5.1 s/session |
| `beadloom-2esy` | A3 dev | in progress | the self-check triage |
| `beadloom-51yx` | B1 dev | blocked | tests/support and the root helper |
| `beadloom-1bd6` | B2 dev | blocked | relocate the 227 clear-node files |
| `beadloom-d0bp` | B3 dev | blocked | relocate acceptance |
| `beadloom-5qgt` | C1 dev | ✓ done | the test index and the binding; 462 test files: 0 bound, 392 unplaced, 70 acceptance |
| `beadloom-2mj3.1` | docs | ✓ done | 36 stale pairs → 0 over 10 refs; test-mapping SPEC rewritten for the binding; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-3z94` | C2 dev | ✓ done | ctx and debt-report read the binding; ctx states the unplaced share (393 of 464 here), debt-report withholds `untested` while files are unplaced; `test_mapper` retired; 22 stale pairs for the docs pass |
| `beadloom-2mj3.2` | docs | ✓ done | 22 stale pairs → 0 over 12 refs; `test_mapper` gone from the docs; `test_placements`, the unplaced line, `test_population` and `count_test_files_by_placement` documented; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-kag9` | C3 dev | blocked | the three rules |
| `beadloom-vr0b` | D1 dev | ready | mutation per change and the weekly sample |
| `beadloom-cs2o` | E1 dev | blocked | the rule-engine pilot |
| `beadloom-kug7` | E2 dev | blocked | test standards |
| `beadloom-75pl` | T test | blocked | the criteria, measured |
| `beadloom-b9ll` | R review | blocked | review |
| `beadloom-7u77` | W tech-writer | blocked | docs and the testing guide |
| `beadloom-paze` | V verify | blocked | the jobs on CI |

## Notes

- The map is the baseline every invariant is measured against: 457 files, 10 895 tests, 518 s;
  19 files touch the live index; `ctx rule-engine` says 0 tests.
- `beadloom-qq6m` (the shared-index flake) closes when A2's tracer shows 0 contacts with the live index.
