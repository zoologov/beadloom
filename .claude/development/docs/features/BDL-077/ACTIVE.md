# ACTIVE: BDL-077 — The viewer draws edges like a classic diagram

> **Last updated:** 2026-10-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-7y2i` (E1, ELK in a worker); then `beadloom-nvux` (E0, Arrange removed) — serialised by `beadloom waves` (shared node `site-app`); then E2 → E3 → E4 → E5 → T → R → W → P.
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
| `beadloom-7y2i` | E1 | in progress | ELK in a worker, elkjs 0.12 direct |
| `beadloom-nvux` | E0 | ready | Arrange removed |
| `beadloom-5x4g` | E2 | blocked | routes drawn exactly |
| `beadloom-bcqk` | E3 | blocked | trunk and bus |
| `beadloom-94h4` | E4 | blocked | the map |
| `beadloom-a6a6` | E5 | blocked | bridges on highlighted edges |
| `beadloom-lb1v` | T | blocked | PRD criteria measured |
| `beadloom-87o6` | R | blocked | review |
| `beadloom-t3pw` | W | blocked | docs |
| `beadloom-zaba` | P | blocked | owner's look, PR |

## Notes

- Filed from the R&D: `beadloom-f2we` (nested elkjs 0.9.3) — closed by E1.
