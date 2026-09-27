# ACTIVE: BDL-074 — Tests that belong to the graph

> **Last updated:** 2026-09-28
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 2 — `beadloom-2mj3.1` (the doc pairs C1 made stale) and `beadloom-kixx` (A2, the self-check snapshot), in parallel; then `beadloom-3z94` (C2), then `beadloom-vr0b` (D1) — those two share `cli-commands`.
**Goal:** the combined tree is green again before new work lands on it, and the 44-entry allowed list starts emptying into a snapshot.
**Done when:** `beadloom ci` rc 0 and `test_all_new_node_pairs_are_fresh` green on the combined tree; A2's snapshot replaces `live_repo_reindexed` and qq6m's tracer shows 0 live-index contacts.

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
| `beadloom-kixx` | A2 dev | in progress | the self-check snapshot |
| `beadloom-2esy` | A3 dev | blocked | the self-check triage |
| `beadloom-51yx` | B1 dev | blocked | tests/support and the root helper |
| `beadloom-1bd6` | B2 dev | blocked | relocate the 227 clear-node files |
| `beadloom-d0bp` | B3 dev | blocked | relocate acceptance |
| `beadloom-5qgt` | C1 dev | ✓ done | the test index and the binding; 462 test files: 0 bound, 392 unplaced, 70 acceptance |
| `beadloom-2mj3.1` | docs | ✓ done | 36 stale pairs → 0 over 10 refs; test-mapping SPEC rewritten for the binding; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-3z94` | C2 dev | ready | ctx and debt-report read the binding |
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
