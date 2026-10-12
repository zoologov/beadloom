# ACTIVE: BDL-082 — FSD by the specification 2.1

> **Last updated:** 2026-10-11
> **Phase:** Development

---

## Current Bead

**Bead:** S2c `beadloom-us5r.1` (viewer layout; S2b closed 2026-10-11); S2a landed `df4d8cc3`; S1 merged (PR #101); S1T landed `49e0df97`, S1a `2ab2a56b`, S1b `2d446b23`; then S1T, S1R, S1W, S1P; S2 after S1's PR.
**Goal:** a spec-following FSD project gets no false finding and every real one; the overlays say the specification.
**Done when:** every PRD goal's *Done when* holds; two PRs merged; MINOR by the public-API guide.

## Progress

- [x] PRD, RFC, CONTEXT, PLAN approved (2026-10-11)
- [x] S1a, S1b landed
- [x] S1T
- [x] S1R; S1W
- [x] S1 PR merged 2026-10-11
- [ ] S2a, S2b landed; S2T; S2R; S2W; S2 PR

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
| `beadloom-us5r.1` | S2c | in progress | launched 2026-10-11 after the owner removed the S2b edge; analysis in a clean room until S2b closes |
| `beadloom-q2el` | S2T | blocked | |
| `beadloom-r8y2` | S2R | blocked | |
| `beadloom-rm5a` | S2W | blocked | |
| `beadloom-iuky` | S2P | blocked | |

## Notes

- 2026-10-11: /task-init done; the measured gaps in `axes.md`; the owner's eight rulings in PRD.md.
- 2026-10-11: PAUSED (owner) during S2b's second half. S2b's first half landed `c126ecff`; the fixture half (vue-fsd 21 nodes, rn-fsd 19) lands with a strict xfail on the shipped browser suite naming S2c `beadloom-us5r.1` — read `beadloom-keki`'s last comment for whether it landed. S2c carries two owner rulings (titles inside boxes; legend samples per colour). Resume: S2c → S2T → S2R → S2W (+ BDL-UX #322) → S2P.
- 2026-10-11: DAG change (owner): S2c no longer depends on S2b; `beadloom waves` 0 serialisations between them; S2c launched while S2b verifies.
- 2026-10-11: an outside static audit's six findings verified and recorded (#317–#322, commit `34213b40`); `beadloom-dlb6` (CI trust boundary) is next right after this work item.
