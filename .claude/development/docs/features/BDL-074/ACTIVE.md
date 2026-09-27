# ACTIVE: BDL-074 — Tests that belong to the graph

> **Last updated:** 2026-09-28
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 1 — `beadloom-l67s` (A1, the chdir and contact guards) and `beadloom-5qgt` (C1, the test index and the binding), in parallel.
**Goal:** the suite stops reaching the repository's live state implicitly, and reindex records test files with a binding derived from where they live.
**Done when:** A1's breakage is measured before its fix and the tracer finds no contact outside `live_repo_reindexed`; C1's `extra["tests"]` comes from the binding with no `mutants/` entry.

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
| `beadloom-l67s` | A1 dev | in progress | chdir and contact guards; 115 tests in 20 files broke before the fix (measured); allowed list 44 entries |
| `beadloom-kixx` | A2 dev | blocked | the self-check snapshot |
| `beadloom-2esy` | A3 dev | blocked | the self-check triage |
| `beadloom-51yx` | B1 dev | blocked | tests/support and the root helper |
| `beadloom-1bd6` | B2 dev | blocked | relocate the 227 clear-node files |
| `beadloom-d0bp` | B3 dev | blocked | relocate acceptance |
| `beadloom-5qgt` | C1 dev | ✓ done | the test index and the binding |
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
