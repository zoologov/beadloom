# ACTIVE: BDL-077 — The viewer draws edges like a classic diagram

> **Last updated:** 2026-10-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-94h4` (E4, the map); then E5 → T → R → W → P.
**Goal:** ELK's routes, a map-like overview, trunks and buses, bridges on highlighted edges — from one layout.
**Done when:** every PRD criterion holds in the suite, the owner has looked, the PR is merged on the owner's word.

## Progress

- [x] R&D (`RND.md`), PRD approved, axes (`axes.md`), probes, RFC approved (2026-10-03)
- [x] CONTEXT and PLAN — approval delegated by the owner ("дальше веди сам согласно claude.md и /coordinator", 2026-10-03)
- [x] Beads: epic `beadloom-m6k7` + 10 from one plan; the R&D bead `beadloom-rcnz` closed
- [ ] Development (E0–E5)
- [ ] Test, review, docs, the owner's look, PR

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-m6k7` | epic | ready | BDL-077 parent |
| `beadloom-rcnz` | R&D | ✓ done | path A/B, map and hub probes |
| `beadloom-7y2i` | E1 | ✓ done | ELK in a worker, elkjs 0.12 direct |
| `beadloom-nvux` | E0 | ✓ done | Arrange removed |
| `beadloom-m6k7.1` | fix | ✓ done | flaky layout-cache case on adopter portals |
| `beadloom-5x4g` | E2 | ✓ done | routes drawn exactly |
| `beadloom-bcqk` | E3 | ✓ done | trunk and bus |
| `beadloom-m6k7.2` | fix | ✓ done | a node id `root` collides with ELK's root |
| `beadloom-94h4` | E4 | in progress | the map |
| `beadloom-a6a6` | E5 | blocked | bridges on highlighted edges |
| `beadloom-lb1v` | T | blocked | PRD criteria measured |
| `beadloom-87o6` | R | blocked | review |
| `beadloom-t3pw` | W | blocked | docs |
| `beadloom-zaba` | P | blocked | owner's look, PR |

## Notes

- **`beadloom-m6k7.2` closed** `a5a7b5ab`: `shared/ids` `freshId` keeps ELK's root and Cytoscape's edge ids out of the node id space (ids unchanged when nothing collides); the root found by position; our portal unchanged, the adopter graph's `root` wrapper now drawn at ELK's box. Filed `beadloom-ytcg` (P2, a node id `__proto__` is not drawn).

- **E3 closed** `cf07192c`: trunks and buses; excess steps 396 → 36 here (bound 80), 1,419 → 179 at adopter size; `cli-commands` one channel instead of 36, 9 lanes instead of 69; no node moves; through-box 0; A2 (no common endpoint) 0; 9.9 ms here, 27.7 ms at adopter size; frame time unchanged. The literal hub lane bound fails at adopter size where hubs feed hubs → the bound counts a node's own trunk lanes (CONTEXT, surfaced to the owner). Filed `beadloom-m6k7.2` (a node id `root` collides with ELK's root).

- **E2 closed** `4ceb0f10`: routes drawn along ELK's sections (max deviation 0.005 units here, 0.021 at adopter size); through-box 232 → 0; A2 (no common endpoint) 22 → 0; boxes at ELK's size (padding 0); the canvas size out of ELK's input — node page and full screen read one cached layout (341 ms → 0.3 ms). Watch: frame cost without a GPU rose (fit 31.9 → 38.0 ms here, 119 → 164 at adopter size; zoom 1 at adopter size 43 → 107) — the longer paths, not JavaScript; E3's bundling and E4's map should cut it, T measures with and without a GPU against the PRD bound.

- **`beadloom-m6k7.1` closed** `14750797`: the fault was in the case (VitePress changes the URL before the next page loads, so the case read the previous viewer's handle); a `viewerAfter` helper waits for a different ready handle; reproduced deterministically (4 of 4 before, 8 of 8 after), python fixture 5 of 5 full suites green. Found: the canvas size enters ELK's input (`aspectRatio`, grid-seeded positions) but changes no box with `INCLUDE_CHILDREN` — E2 drops it so one layout per data file holds by construction.

- **E0 closed** `4063628c`: Arrange removed on every page; `panOnNodes()` makes a drag on a node pan; new cases (no control, drag and long press move no node) red first; 108 browser cases. On four adopter fixtures one E1 case flaked ('worker' where 'cache' was expected after a trip to a node page and back; the canvas measured 540 px — a node page's height) → `beadloom-m6k7.1`, fixed before E2.

- **E1 closed** `d9c43d46`: ELK in a Web Worker, elkjs 0.12 direct; positions identical (max 4.5e-13 units); longest main-thread hold 2,943 → 455 ms at adopter size (113 ms while ELK runs), 746 → 180 ms here; one elkjs in the lock (`beadloom-f2we` closed); `cytoscape-elk` and `web-worker` removed; 105 browser cases (4 new). `beadloom ci` rc 1 on 18 stale pairs → W. Filed `beadloom-stcx` (P2, `vitepress dev` crash, pre-existing).

- Filed from the R&D: `beadloom-f2we` (nested elkjs 0.9.3) — closed by E1.
