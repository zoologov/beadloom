# ACTIVE: BDL-074 — Tests that belong to the graph

> **Last updated:** 2026-09-28
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 8 — `beadloom-2mj3.5` (the doc pairs C3 made stale) and `beadloom-cs2o` (E1, the rule-engine pilot), in parallel.
**Goal:** the tree is green again after C3; the rule engine's tests become the model the rest of the suite follows.
**Done when:** `beadloom ci` rc 0 and the suite green on the combined tree; E1's test count, per-node line coverage and kill rate on a fixed sample have not fallen.

**Wave 7 closed (2026-09-28):** PR #84 squash-merged as `7cbc1874` (9/9 green); main merged back tree-identically; the mutation workflow enabled by the owner and one sample dispatched (run 36373061140). C3 `52e2c8de`, `9d9d99be` — four rules over the suite, each stating its population: test files 386 judged, 184 unbound all exempt by path; features 51 judged, 20 without a bound test (warn); domain unit tests 27 judged, 4 exempt; scenarios 528 judged, 211 in the 40 listed files exempt. The "steps execute the node" half of `scenario_binding` is not implemented (a static stand-in found 59 of 81 pairs; not good enough to be a rule). Gate owner C3 on the tree: 11 149 passed, 2 failed (the rule-engine SPEC table), `beadloom ci` rc 1 (43 stale pairs, docs-audit on `architecture.md`) → docs bead `beadloom-2mj3.5`. PLAN's bead table brought up to the tracker (`27ba08de`); `beadloom-10er` filed to drop PLAN's status column (owner).

**Wave 6 closed — phase B done (2026-09-28):** `beadloom-2mj3.4` `68631e77`, `4e7fde6a` — 39 features in 27 node folders `tests/acceptance/<domain>/<node>/`, 33 step files by node and 4 in `steps/common/`; 524 scenarios before and after. E2 `55ccf52f`, `c88a8dcc` — the shipped `test` role states what a test is; 45 file names carried a work-item id: 22 renamed, 23 exempt with an exit; the project layer gained `.beadloom/flow/roles/test.md`. Gate owner `beadloom-2mj3.4` on the combined tree: 11 081 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0.

**Wave 5 closed (2026-09-28):** B3 `11c2fd22`, `989f26a4` — 39 features, 37 step files to `tests/acceptance/<package>/`, 40 mismatches listed; 524 scenarios before and after. B2 `1ecd4f9e`, `c17ebec9`, `d9db4704` — 198 of 227 relocated (46 unit, 152 integration), all bound to the map's node; 554 test files: 198 bound, 184 unplaced, 172 acceptance or self-check; `ctx rule-engine` 605 tests in 21 files (was 0); per-change selection 202 → 162 files, ≈5.6 min locally (≈9 projected on the runner, under the 10-minute budget, not yet run on CI). Gate owner B2 on the combined tree: 11 061 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0. Owner ruled B3's package level short of the approved layout → `beadloom-2mj3.4`.

**Wave 4 closed (2026-09-28):** PR #83 squash-merged as `4890f28c` (9/9 checks green; owner ruled `db`, `repository`, `mcp-server` into the axes, `f10e67de`); main merged back tree-identically as `7503f4b1`. B1 `2c2cd3d0`, `e7f2c6fb`, `7871c0eb` — `tests/support/` 50 modules; parent-counting files 106 → 0; test-module imports 105 → 1 (exempt with a reason). D1 `61f416cd` — `mutation-per-change`, weekly `mutation-sample` (150), `announce`; workflow still disabled; per-change ≈9 min locally, ≈15 projected, over the 10-minute budget until B2. Docs `e0a5983d` (15 stale → 0). Gate owner B1 on the combined tree: 11 061 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0. Filed outside the epic: `beadloom-xg0y` (clean-room ignores `uv.lock`).

**Wave 3 closed — phase A done (2026-09-27):** C2 `0dafac5d` (the name-guessing mapper retired); docs `2b42264c` (22 stale pairs → 0); A3 `18d6690d`, `9202e70f`. Gate owner A3 on the combined tree: 10 959 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0. 592 self-checks in `tests/self_check/`; allowed list 0; tracer 0 live-index contacts — `beadloom-qq6m` closed. Moved test paths are still named in comments in `.github/workflows/*.yml`, `.beadloom/flow.yml`, two `src/` docstrings and two docs; left to W (`beadloom-7u77`), recorded on `beadloom-2esy`.

**Wave 2 closed (2026-09-27):** docs `65a098bc` (36 stale pairs → 0); A2 `596401ab`, `4e6b9c20`. Gate owner A2 on the combined tree: 10 975 passed, 0 failed, 13 skipped, 13 xfailed; `beadloom ci` rc 0. Allowed list 44 → 20; live-index contacts 98 → 1 — the A3 probe that hashes the index bytes, so qq6m stays open until A3.

**Wave 1 closed (2026-09-27):** A1 `8e17362e`, `12ad9f12`; C1 `90c04540`. Gate owner A1 on the combined tree: 10 958 passed, 1 failed (`test_all_new_node_pairs_are_fresh`), `beadloom ci` rc 1 on 36 stale doc pairs from C1's change — not planned for this point, so a docs bead `beadloom-2mj3.1` was added ahead of wave 2.

## Progress

- [x] Docs folder, the Explore axes (6 seeds, 15 nodes) and the measured suite map (`map/`, 2026-09-27)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-28); kept nodes 9
- [x] Beads created: epic `beadloom-2mj3` + 16, one plan, 20 edges confirmed against the titles; swarm valid, 11 waves
- [x] Phase A — isolation and the self-check triage (PR 1 opened 2026-09-27)
- [x] Phase B — layout (PR 2 opened 2026-09-28)
- [ ] Phases C, D, E — binding, rules, per-change mutation, pilot, standards (PR 3)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-2mj3` | epic | ready | BDL-074 parent |
| `beadloom-l67s` | A1 dev | ✓ done | chdir and contact guards; 115 tests in 20 files broke before the fix (measured); allowed list 44 entries |
| `beadloom-kixx` | A2 dev | ✓ done | self-check snapshot replaces `live_repo_reindexed`; allowed list 44 → 20; live-index contacts 98 → 1 (the A3 probe), 0 writers; build ≈5.1 s/session |
| `beadloom-2esy` | A3 dev | ✓ done | 590 traced self-checks: 541 moved + 51 siblings = 592 in `tests/self_check/` (architecture 125, config 206, docs 68, process 193); 4 exact `lint`-leg duplicates removed; 45 kept in place with a reason; allowed list 20 → 0; live-index contacts 1 → 0, `beadloom-qq6m` closed; combined tree 10 959 passed, 0 failed, `beadloom ci` rc 0 |
| `beadloom-51yx` | B1 dev | ✓ done | `tests/support/` 50 modules (18 moved, 31 extracted by subject, `repository_root`); files importing a `test_*.py` module 46 → 1, counting parents 106 → 5 (both remainders D1's, exempt by prefix); lock `self_check/architecture/test_the_suite_shares_helpers_through_support.py`; green in a clean room over 247 files; `2c2cd3d0` |
| `beadloom-1bd6` | B2 dev | ✓ done | 198 of the 227 relocated (27 acceptance = B3, 1 retired, 1 now mixed), no renames; 198 bound to the map's node, 0 mismatches (554 files: 198 bound, 184 unplaced, 172 other); `ctx rule-engine` 605 tests in 21 files; per-change selection 202 → 162 files, select 496 → 297 s locally; 11 088 ids and outcomes identical; `1ecd4f9e`, `c17ebec9`. Gate owner wave 5 on the tree: 11 061 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0 |
| `beadloom-d0bp` | B3 dev | ✓ done | 39 features → `tests/acceptance/<package>/`, 37 step files → `steps/<package>/` (6 packages; no `steps/common/`); 40 features listed, not moved (29 tag-executed-not-primary, 3 tag-not-executed, 5 sibling-matched, 3 not in the map); `rules.yml` glob `tests/acceptance/**/*.feature`; 524 → 524 scenarios, identical; 5 edits in B2's files needed (on the bead), green in a clean room with them (11 016 passed); `11c2fd22` |
| `beadloom-5qgt` | C1 dev | ✓ done | the test index and the binding; 462 test files: 0 bound, 392 unplaced, 70 acceptance |
| `beadloom-2mj3.1` | docs | ✓ done | 36 stale pairs → 0 over 10 refs; test-mapping SPEC rewritten for the binding; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-3z94` | C2 dev | ✓ done | ctx and debt-report read the binding; ctx states the unplaced share (393 of 464 here), debt-report withholds `untested` while files are unplaced; `test_mapper` retired; 22 stale pairs for the docs pass |
| `beadloom-2mj3.2` | docs | ✓ done | 22 stale pairs → 0 over 12 refs; `test_mapper` gone from the docs; `test_placements`, the unplaced line, `test_population` and `count_test_files_by_placement` documented; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-2mj3.4` | dev | ✓ done | 39 features → `tests/acceptance/<domain>/<node>/` (27 node folders, spelled as `docs/`); 37 step files → `steps/<domain>/<node>/` (33) or `steps/common/` (4, two or more nodes); 40 mismatches untouched; hyphenated folders import by file name (pytest), `__init__.py` kept for ruff; 524 → 524 scenarios, identical; `68631e77`. Gate owner wave 6 on the tree: 11 081 passed, 0 failed, 14 skipped, 13 xfailed of 11 108; `beadloom ci` rc 0 |
| `beadloom-2mj3.5` | docs | ✓ done | 43 stale pairs → 0 over 8 refs; rule-engine SPEC states Fifteen rule types with the three suite rules, the unimplemented execution half stated with C3's measurement; `architecture.md` 15 keys / 19 rules; sync-check rc 0, `beadloom ci` rc 0 on the tree |
| `beadloom-kag9` | C3 dev | ✓ done | `test_binding`, `test_import_boundary`, `scenario_binding`, each printing its population (`suite_population`, an advisory); declared as 4 rules: test files 386 judged, 184 unbound all exempt by path (error); features 51 judged, 20 without a bound file (warn, not exempted); domain unit tests 27 judged, 4 files open an index, exempt (error); scenarios 528 in 80 files, 211 in the 40 listed files exempt (error); execution half not judged (static proxy 59 of 81, measured); `52e2c8de`. Gate owner wave 7 on the tree: 11 149 passed, 2 failed (SPEC rule-type table, docs), 14 skipped, 13 xfailed; `beadloom ci` rc 1 on 43 stale pairs + 2 architecture.md facts for the docs pass |
| `beadloom-vr0b` | D1 dev | ✓ done | `beadloom mutation --changed-since/--survivors/--sample-of`; `.github/scripts/mutmut_adapter.py`; `mutation.yml` = `mutation-per-change` (PR) + `mutation-sample` (weekly, 150, seeded) + `announce`; workflow still DISABLED; per-change fallback = the pool while tests are unplaced; one-function change measured ~9 min locally (496 s of it the stats pass), so the 10-min budget waits on B2; clean room 11 016 passed, 0 failed |
| `beadloom-2mj3.3` | docs | ✓ done | 15 stale pairs → 0 over 5 refs (mutation-scope, application, infrastructure, repository, cli-commands); D1's modules, `lies_within`, `get_test_file_bindings` and the three `mutation` options documented; the nightly rewritten as history in `cli.md` and gate-coverage, per-change budget stated as not met; sync-check rc 0 at the fixpoint |
| `beadloom-cs2o` | E1 dev | ✓ done | rule-engine pilot, before → after on one selection: tests 765 → 886, line coverage of `graph/rules/` 95.1% → 96.0%, kill rate on a fixed 600-mutant sample (seed 74) 79.3% [75.9, 82.4] → 82.0% [78.7, 84.9], 0 kills lost; 8 unplaced files split by node or moved (test-binding exemptions −8), unit layer for loader/layer reach/node tags, 10 features rewritten with `Rule:`/Outlines over `tests/support/rule_engine_driver.py` + `rule_engine_vocabulary.py`, 7 moved to `graph/rule-engine/` (scenario exemptions −7); weekly survivors: 11 killed, 4 equivalent; open for the owner: an Outline counts once in lint (522) and runs per row (536); `1f7b8a34`, `20104798`. Gate owner wave 8 on the tree: 11 198 passed, 0 failed, 14 skipped, 13 xfailed; `beadloom ci` rc 0 |
| `beadloom-kug7` | E2 dev | ✓ done | test role core states 8 standards (stack-neutral), Python overlay the layout, project layer `.beadloom/flow/roles/test.md`; recomposed, config-check rc 0; B1's lock green on the relocated tree; new lock `self_check/architecture/test_a_test_file_is_named_by_its_behaviour.py`: 45 of 819 names carried an id (0 in acceptance), 22 renamed, 23 exempt with reason and exit; renamed set 302 ids identical; green in a clean room over 36 files (11 036 passed, 0 failed); `55ccf52f` |
| `beadloom-75pl` | T test | ready | the criteria, measured |
| `beadloom-b9ll` | R review | blocked | review |
| `beadloom-7u77` | W tech-writer | blocked | docs and the testing guide |
| `beadloom-paze` | V verify | blocked | the jobs on CI |

## Notes

- The map is the baseline every invariant is measured against: 457 files, 10 895 tests, 518 s;
  19 files touch the live index; `ctx rule-engine` says 0 tests.
- `beadloom-qq6m` (the shared-index flake) closes when A2's tracer shows 0 contacts with the live index.
