# ACTIVE: BDL-078 — The viewer looks finished, and five defects are fixed

> **Last updated:** 2026-10-05
> **Phase:** Development

---

## Current Bead

**Bead:** wave 1 — the beads `beadloom waves` allows together out of F-ytcg, F-activity, F-nh7h, F-76mk, F-stcx; then V1 → V2 → V3 (one widget, one after another), F-jcng after F-nh7h; then T → R → W → P.
**Goal:** a viewer without visual artefacts, an activity metric that means something, five defects fixed.
**Done when:** every PRD criterion holds in the suite, the owner has looked, the PR is merged on the owner's word.

## Progress

- [x] Explore axes (`axes.md`); three probes (`RND.md`); the owner's fourteen rulings; PRD approved (2026-10-05)
- [x] RFC, CONTEXT, PLAN — approval delegated by the owner ("Утверждаю, дальше веди сам", 2026-10-05)
- [x] Beads: epic `beadloom-btkd`, eight from one plan, five existing defects wired in
- [ ] Development
- [ ] Test, review, docs, the owner's look, PR

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-btkd` | epic | ready | BDL-078 parent |
| `beadloom-ytcg` | F-ytcg | ready | a node named `__proto__` is drawn |
| `beadloom-xv87` | V1 | blocked | the base look |
| `beadloom-0gyz` | V2 | blocked | the overview |
| `beadloom-hnff` | V3 | blocked | levels |
| `beadloom-lw56` | F-activity | ready | activity by changed lines |
| `beadloom-nh7h` | F-nh7h | ready | incremental vs fresh import resolution |
| `beadloom-jcng` | F-jcng | blocked | manifests as inputs |
| `beadloom-76mk` | F-76mk | ready | flat Python tests bind |
| `beadloom-stcx` | F-stcx | ready | `vitepress dev` loads |
| `beadloom-q63p` | T | blocked | PRD criteria measured |
| `beadloom-ak1i` | R | blocked | review |
| `beadloom-1hle` | W | blocked | docs |
| `beadloom-hpat` | P | blocked | owner's look, PR |

## Notes

- The branch carries BDL-077's close-out commit `fd3d3f1a`.
