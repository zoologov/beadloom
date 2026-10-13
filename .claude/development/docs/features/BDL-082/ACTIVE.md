# ACTIVE: BDL-082 — FSD by the specification 2.1

> **Last updated:** 2026-10-11
> **Phase:** Development

---

## Current Bead

**Bead:** S2P `beadloom-iuky` (S2W closed 2026-10-13); S2a landed `df4d8cc3`; S1 merged (PR #101); S1T landed `49e0df97`, S1a `2ab2a56b`, S1b `2d446b23`; then S1T, S1R, S1W, S1P; S2 after S1's PR.
**Goal:** a spec-following FSD project gets no false finding and every real one; the overlays say the specification.
**Done when:** every PRD goal's *Done when* holds; two PRs merged; MINOR by the public-API guide.

## Progress

- [x] PRD, RFC, CONTEXT, PLAN approved (2026-10-11)
- [x] S1a, S1b landed
- [x] S1T
- [x] S1R; S1W
- [x] S1 PR merged 2026-10-11
- [x] S2a, S2b, S2c landed; S2T; S2R (four passes, four fix beads); S2W
- [ ] S2 PR

## Results

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-r15q` | S1a | ✓ done (commit `2ab2a56b`; `edges.extra` `via: @x` / `partly_via` + `not_via`; travels in `export` and the data file; the layer rule accepts it on the layer named `entities` only; the spec's example clean, features/mixed/third/declared as the spec says; `cross_imports.py` shared by both rules) |
| `beadloom-8sml` | S1b | ✓ done |
| `beadloom-wvzg` | S1T | ✓ done (commit `49e0df97`; own probes from the spec's text: goals 1 and 4 hold, 5 holds for the rule until S2a tags it; no probe moved 0 → 1; the alias limit documented; `@x` under `scope:` works; full tree green (unit 2885, integration 5979, acceptance 803, self_check 1093); mutation 93.0%; BDL-UX #316 filed: scope-check reads 0 axis rows from RFC.md) |
| `beadloom-r4ck` | S1R | ✓ done — REVIEW PASSED after one fix cycle (major: three SPECs → S1W `bffa743a`; minors: the container → S1b `52cab093`; RFC D4 corrected) |
| `beadloom-chdr` | S1W | ✓ done (commit `bffa743a`; 46 stale → 0; `ci` rc 0; the version question raised for the owner) |
| `beadloom-chdr` | S1W | ✓ done |  |
| `beadloom-vv3e` | S1P | ✓ done (PR #101 merged `30624370`; required checks green; java leg a flake on re-run; site-e2e at its limit) |
| `beadloom-6e2o` | S2a | ✓ done (commit `df4d8cc3`; groups → `features-auth-login`/`-register`, `register → login` an error; no `pages` check (8 rules); both lists; the rule over six layers; 17-rule header; `unread_code.py` names files without a parser; fixtures unchanged 19/18 nodes) |
| `beadloom-keki` | S2b | ✓ done (commits `c126ecff` + `c7963f7c`; overlays by the spec, Steiger packages as version subjects, harness refuses the pages check; vue-fsd 21 nodes / rc 1 / 3 errors, rn-fsd 19 / rc 0 / 1 warn; slow browser run 143 passed, 2 strict xfails naming S2c; lint 0 errors 69 warnings; 28 known stale pairs) |
| `beadloom-us5r.1` | S2c | ✓ done (commits `8d2f20f6` + `2dbd308b`; eight adopter portals' browser tests 24 passed with no xfail; own suite 369 passed incl. 10 performance cases; unit+integration 8926 passed; ruff, mypy, lint --strict, docs audit clean; `ci` rc 1 only for S2W's 28 stale pairs; not run: acceptance, self_check, mutation, Linux legs) |
| `beadloom-us5r.5` | S2 fix 4 | ✓ done (commit `a721033d`, 9 files; both probes hold: checkout one node of 6 files, auth two slices with `register → login` an error and `helpers.ts` a warning; nested groups unchanged; green in a clean room over 9 files; on the tree fixtures + probes 202 passed, vue-fsd 21/3, rn-fsd 19/1, lint 0 errors; 2 vitepress-site pairs stale from cc0a93a7 → S2W) |
| `beadloom-q2el` | S2T | ✓ done (commit `f8062735`; whole collected suite on the tree 14415 passed / 145 skipped / 13 xfailed / 0 failed, 95% coverage; slow adopter suite 129/129 incl. eight portals with no xfail; spec probes match PRD goals 1–6; vue-fsd 21 nodes / 3 errors, rn-fsd 19 / 1 warning; mutation per change empty, fsd_layout.py 98.2%; `ci` rc 1 on S2W's 28 stale pairs only; 6 tests added; BDL-UX #323, #324 filed) |
| `beadloom-r8y2` | S2R | ✓ done | Major 1 (two prose lines sync-check cannot see) + Minor 4 → S2W; Major 2 (S2c unreviewed) → review widened to S2c, relaunch after the fix bead; Minors 1–3 + nitpick → `beadloom-us5r.2` |
| `beadloom-us5r.2` | S2 fix | ✓ done (commit `db75ab46`, 26 files; green in a clean room over 26 files: ruff, mypy 3.10–3.13, integration 5989, top-level 3570, self_check 1053, unit+acceptance 3770 passed / 1 known room-only failure #311; on the tree fixtures + probes 181 passed, vue-fsd 21/3, rn-fsd 19/1, lint 0 errors; `ci` rc 1 on 13 stale pairs all S2W's; 16 of S2W's pairs re-baselined by editing their documents, text unreviewed — listed on `beadloom-rm5a`) |
| `beadloom-rm5a` | S2W | ✓ done (commit `92e445f8`, 21 files; 15 stale + 16 re-baselined pairs read, stale 15 → 0; on the tree `beadloom ci` rc 0, reindex, sync-check, docs audit, docs quality, lint --strict rc 0, self_check 1099 passed; the Gate did not run pytest, ruff, mypy, lint:fsd; open: the 17-key fact unreadable by docs audit (Debt bead), the MINOR/MAJOR case to measure at the release, #323 to the owner) |
| `beadloom-iuky` | S2P | in progress | 2026-10-13: fresh branch, PR, merge on green |

## Notes

- 2026-10-11: /task-init done; the measured gaps in `axes.md`; the owner's eight rulings in PRD.md.
- 2026-10-11: PAUSED (owner) during S2b's second half. S2b's first half landed `c126ecff`; the fixture half (vue-fsd 21 nodes, rn-fsd 19) lands with a strict xfail on the shipped browser suite naming S2c `beadloom-us5r.1` — read `beadloom-keki`'s last comment for whether it landed. S2c carries two owner rulings (titles inside boxes; legend samples per colour). Resume: S2c → S2T → S2R → S2W (+ BDL-UX #322) → S2P.
- 2026-10-13: RESUMED. S2c's agent resumed for verification and close (checkpoint every 30 min required).
- 2026-10-12: PAUSED (owner). S2c's agent ran 10 h without a checkpoint (process note on the bead); its tree state landed as WIP `8d2f20f6`, bead open. RESUME S2c: slow adopter run with Node 22 (expect vue-fsd and rn-fsd green, strict xfails removed), lint, mypy, `beadloom ci`, fast suite, then COMPLETED + close. ALSO: the pre-commit scope check calls every viewer path `outside-the-declared-axes` — the RFC's `## Axes` never named the viewer nodes (S2c was unplanned); RFC widened 2026-10-13 with section (f): the derivation cannot read JavaScript, the viewer nodes are ruled in by the owner's S2c rulings; the advisory stays until #316 closes.
- 2026-10-11: DAG change (owner): S2c no longer depends on S2b; `beadloom waves` 0 serialisations between them; S2c launched while S2b verifies.
- 2026-10-11: an outside static audit's six findings verified and recorded (#317–#322, commit `34213b40`); `beadloom-dlb6` (CI trust boundary) is next right after this work item.
