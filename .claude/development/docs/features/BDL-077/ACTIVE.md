# ACTIVE: BDL-077 — The viewer draws edges like a classic diagram

> **Last updated:** 2026-10-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-m6k7.1` (a flaky E1 case on adopter portals); then E2 → E3 → E4 → E5 → T → R → W → P.
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
| `beadloom-m6k7.1` | fix | in progress | flaky layout-cache case on adopter portals |
| `beadloom-5x4g` | E2 | blocked | routes drawn exactly |
| `beadloom-bcqk` | E3 | blocked | trunk and bus |
| `beadloom-94h4` | E4 | blocked | the map |
| `beadloom-a6a6` | E5 | blocked | bridges on highlighted edges |
| `beadloom-lb1v` | T | blocked | PRD criteria measured |
| `beadloom-87o6` | R | blocked | review |
| `beadloom-t3pw` | W | blocked | docs |
| `beadloom-zaba` | P | blocked | owner's look, PR |

## Notes

- **E0 closed** `4063628c`: Arrange removed on every page; `panOnNodes()` makes a drag on a node pan; new cases (no control, drag and long press move no node) red first; 108 browser cases. On four adopter fixtures one E1 case flaked ('worker' where 'cache' was expected after a trip to a node page and back; the canvas measured 540 px — a node page's height) → `beadloom-m6k7.1`, fixed before E2.

- **E1 closed** `d9c43d46`: ELK in a Web Worker, elkjs 0.12 direct; positions identical (max 4.5e-13 units); longest main-thread hold 2,943 → 455 ms at adopter size (113 ms while ELK runs), 746 → 180 ms here; one elkjs in the lock (`beadloom-f2we` closed); `cytoscape-elk` and `web-worker` removed; 105 browser cases (4 new). `beadloom ci` rc 1 on 18 stale pairs → W. Filed `beadloom-stcx` (P2, `vitepress dev` crash, pre-existing).

- Filed from the R&D: `beadloom-f2we` (nested elkjs 0.9.3) — closed by E1.
