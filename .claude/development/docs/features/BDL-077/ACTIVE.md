# ACTIVE: BDL-077 — The viewer draws edges like a classic diagram

> **Last updated:** 2026-10-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-zaba` (P: the owner's look in a browser, then the PR).
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
| `beadloom-94h4` | E4 | ✓ done | the map |
| `beadloom-a6a6` | E5 | ✓ done | bridges on highlighted edges |
| `beadloom-lb1v` | T | ✓ done | PRD criteria measured |
| `beadloom-m6k7.3` | fix | ✓ done | a box hub is not bundled |
| `beadloom-m6k7.4` | fix | ✓ done | adopter-size leaves over the lane bound |
| `beadloom-87o6` | R | ✓ done | review |
| `beadloom-m6k7.6` | fix | ✓ done | review findings |
| `beadloom-m6k7.5` | fix | ✓ done | two-rank second channel |
| `beadloom-t3pw` | W | ✓ done | docs |
| `beadloom-zaba` | P | in progress | owner's look, PR |

## Notes

- **W closed** `44b451eb`: viewer slice docs and the portal guide describe the code as built (routes, trunks and buses, the map, bridges, no Arrange, the performance bounds); stale 61 → 0 (710 pairs); `beadloom ci` rc 0; pytest 0 failed. Left: the `site-shared` node summary does not name the `ids` segment; nine surface-drift warnings.

- **`beadloom-m6k7.5` closed** `df60d928`: the bus measures its first gap over the lanes that turn in it, so no edge drops past its target; ranks 1–6 all 0 over-bound sides and 0 second channels; a case per rank count 1–4. Left: on two ranks one 20-unit edge reads as more than half shared under A2 at every crossing height (a right-angle crossing) — a limit of the metric on very short edges, recorded in CONTEXT and surfaced to the owner.

- **`beadloom-m6k7.6` closed** `60146073`: performance guarded — structural (long tasks during layout, the overview budget) and timed cases with per-environment bounds (local: frame 25 ms, first drawing 7,200 ms, long task 1,000 ms; CI wider, never yet measured on a runner); the budget keeps the 100 heaviest with a name tie-break; a new defect fixed — the pointer on the root box lifted the budget for every box (345 edges at the adopter overview); a failed layout hides the canvas and disables graph controls; 178 browser cases.

- **R closed** `beadloom-87o6`: ISSUES, 0 critical, 1 major — M1 no suite guard for frame time or first render (the reviewer measured the goal holds: first render 4,330 → 3,690 ms here, fit p90 33 → 16.7 ms, 133 → 16.7 at adopter size); minor: ties at the 100 budget can empty the overview; a failed layout shows a stacked canvas; RFC rows named slices that did not change (fixed in RFC); a stale comment; bundling could move to `shared/` (not taken). → `beadloom-m6k7.6`.

- **`beadloom-m6k7.4` closed** `1021f1b9`: the literal hub bound and one channel per side and direction hold for every busy node here and on the three adopter-sized graph shapes the suite draws (18/17/24 over-bound sides → 0; 15/11/13 second-channel sides → 0); excess steps here 36 → 7; no node moved; bundling 36–37 ms at adopter size (budget 50). Levers: incoming trunks, edges in two trunks, bus port shifts and fallbacks, joins. `lanesAt` treats a corner within half a unit of the line as meeting it. RFC D3 updated for the new hub-to-hub rule. Residual: a two-rank graph keeps one second channel → `beadloom-m6k7.5` (P2).

- **`beadloom-m6k7.3` closed** `bde3684c`: every node, box or leaf, gets buses and trunks; a box's loops count in its degree but are never rerouted. `mcp-server` 20 channels / 26 lanes → 1 / 6 (bound 7); every busy node here within its bound; no node moved; through-box 0. `routeMetrics` now treats values within one unit as one lane (Cytoscape reports trunk corners up to half a unit off) — for review. Adopter-size analysis for `.4`: 111 over-bound edges sit in no trunk (hub-to-hub edges the source never trunked), 84 ride the source's trunk and arrive in lanes of their own.

- **T closed** `0bd7ca46`: 28 criteria — 24 MET, 3 NOT MET, 1 not measurable here (frame bounds on CI's machines). NOT MET: the staircase goal — `mcp-server` (a box, 29 edges) leaves in 20 channels and 26 lanes vs 7, because only leaves are bundled (`beadloom-m6k7.3`); at adopter size 15 sides over the lane bound even under the coordinator's reading and 10 nodes with two channels (`beadloom-m6k7.4`) — the reading is withdrawn (CONTEXT); the docs (W). Frame vs main: first render −6% here, −10% at adopter size; fit and zoom ≈ 1 at the 16.7 ms cap in both rooms (today 31/121 ms without a GPU). Not bounded by the PRD, for review: every box opened at zoom 1 at adopter size is slower than today (109 vs 43 ms without a GPU, 31 vs 25 with). 170 browser cases, 4 of them `test.fail` until the two bugs are fixed.

- **E5 closed** `6f0d3bd0`: bridges on hovered and walk edges, none between bundle siblings or with nothing highlighted, skipped under 2 px; finding 4.5 ms here / 26.7 ms at adopter size once per selection; drawing ≤ 0.55 ms per frame; frame time unchanged within ±1.5 ms; 161 browser cases. For the owner's look: the busiest node's full neighbourhood draws 2,225 bridges (about 32 per edge) when every box is open.

- **E4 closed** `c2c62eab`, `6122f46d`, `c6fc16a9`: the map. Overview here 12 boxes and 34 aggregated edges (carrying 277 of 453); at adopter size 79 drawn of 345 pairs (weight ≥ 4; 266 counted as "+N"); box displacement 0 at every level; frame at the fit 39.6 → 16.7 ms here and 162 → 16.7 ms at adopter size (the display cap), zoom ≈ 1 at adopter size 105 → 16.7. Decisions in CONTEXT: an edge with a closed box at one end joins its pair's aggregated edge; a revealed box is drawn open; the default neighbourhood opens its walk unless the node is a hub; search opens its matches; fit ignores labels. 47 existing cases now open every box first (`openEveryBox`); 148 browser cases.

- **`beadloom-m6k7.2` closed** `a5a7b5ab`: `shared/ids` `freshId` keeps ELK's root and Cytoscape's edge ids out of the node id space (ids unchanged when nothing collides); the root found by position; our portal unchanged, the adopter graph's `root` wrapper now drawn at ELK's box. Filed `beadloom-ytcg` (P2, a node id `__proto__` is not drawn).

- **E3 closed** `cf07192c`: trunks and buses; excess steps 396 → 36 here (bound 80), 1,419 → 179 at adopter size; `cli-commands` one channel instead of 36, 9 lanes instead of 69; no node moves; through-box 0; A2 (no common endpoint) 0; 9.9 ms here, 27.7 ms at adopter size; frame time unchanged. The literal hub lane bound fails at adopter size where hubs feed hubs → the bound counts a node's own trunk lanes (CONTEXT, surfaced to the owner). Filed `beadloom-m6k7.2` (a node id `root` collides with ELK's root).

- **E2 closed** `4ceb0f10`: routes drawn along ELK's sections (max deviation 0.005 units here, 0.021 at adopter size); through-box 232 → 0; A2 (no common endpoint) 22 → 0; boxes at ELK's size (padding 0); the canvas size out of ELK's input — node page and full screen read one cached layout (341 ms → 0.3 ms). Watch: frame cost without a GPU rose (fit 31.9 → 38.0 ms here, 119 → 164 at adopter size; zoom 1 at adopter size 43 → 107) — the longer paths, not JavaScript; E3's bundling and E4's map should cut it, T measures with and without a GPU against the PRD bound.

- **`beadloom-m6k7.1` closed** `14750797`: the fault was in the case (VitePress changes the URL before the next page loads, so the case read the previous viewer's handle); a `viewerAfter` helper waits for a different ready handle; reproduced deterministically (4 of 4 before, 8 of 8 after), python fixture 5 of 5 full suites green. Found: the canvas size enters ELK's input (`aspectRatio`, grid-seeded positions) but changes no box with `INCLUDE_CHILDREN` — E2 drops it so one layout per data file holds by construction.

- **E0 closed** `4063628c`: Arrange removed on every page; `panOnNodes()` makes a drag on a node pan; new cases (no control, drag and long press move no node) red first; 108 browser cases. On four adopter fixtures one E1 case flaked ('worker' where 'cache' was expected after a trip to a node page and back; the canvas measured 540 px — a node page's height) → `beadloom-m6k7.1`, fixed before E2.

- **E1 closed** `d9c43d46`: ELK in a Web Worker, elkjs 0.12 direct; positions identical (max 4.5e-13 units); longest main-thread hold 2,943 → 455 ms at adopter size (113 ms while ELK runs), 746 → 180 ms here; one elkjs in the lock (`beadloom-f2we` closed); `cytoscape-elk` and `web-worker` removed; 105 browser cases (4 new). `beadloom ci` rc 1 on 18 stale pairs → W. Filed `beadloom-stcx` (P2, `vitepress dev` crash, pre-existing).

- Filed from the R&D: `beadloom-f2we` (nested elkjs 0.9.3) — closed by E1.
