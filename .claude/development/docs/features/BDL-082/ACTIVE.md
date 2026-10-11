# ACTIVE: BDL-082 — FSD by the specification 2.1

> **Last updated:** 2026-10-11
> **Phase:** Development

---

## Current Bead

**Bead:** S1P `beadloom-vv3e` — the S1 PR; S1R passed; S1T landed `49e0df97`, S1a `2ab2a56b`, S1b `2d446b23`; then S1T, S1R, S1W, S1P; S2 after S1's PR.
**Goal:** a spec-following FSD project gets no false finding and every real one; the overlays say the specification.
**Done when:** every PRD goal's *Done when* holds; two PRs merged; MINOR by the public-API guide.

## Progress

- [x] PRD, RFC, CONTEXT, PLAN approved (2026-10-11)
- [x] S1a, S1b landed
- [x] S1T
- [x] S1R; S1W
- [ ] S1 PR
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
| `beadloom-vv3e` | S1P | in progress | PR, merge on green |
| `beadloom-6e2o` | S2a | blocked | |
| `beadloom-keki` | S2b | blocked | |
| `beadloom-q2el` | S2T | blocked | |
| `beadloom-r8y2` | S2R | blocked | |
| `beadloom-rm5a` | S2W | blocked | |
| `beadloom-iuky` | S2P | blocked | |

## Notes

- 2026-10-11: /task-init done; the measured gaps in `axes.md`; the owner's eight rulings in PRD.md.
