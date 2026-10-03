# ACTIVE: BDL-077 — The viewer draws edges like a classic diagram

> **Last updated:** 2026-10-03
> **Phase:** Planning

---

## Current Bead

**Bead:** `beadloom-rcnz` (R&D: ELK routes in Cytoscape, bridges, JointJS and other renderers)
**Goal:** a measured choice of how the viewer draws edges, and a PRD the owner can discuss.
**Done when:** the owner has read the report and the PRD and ruled on its open questions.

## Progress

- [x] R&D, two prototypes in the scratchpad: path A (Cytoscape + ELK routes + bridges) and path B (JointJS core, own SVG from ELK, maxGraph); numbers in `RND.md` (2026-10-03)
- [x] PRD drafted (`PRD.md`, Draft) with five open questions for the owner
- [ ] Owner's discussion and rulings
- [ ] RFC, CONTEXT, PLAN; beads

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-rcnz` | R&D | in progress | measured; awaiting the owner's rulings |

## Notes

- Recommendation in the report: keep Cytoscape and draw ELK's routes (path A); bridges only on highlighted edges; the overview needs fewer edges on screen, not another renderer; own SVG from ELK is the fallback.
- Filed from the R&D: `beadloom-f2we` (the viewer runs a nested elkjs 0.9.3, not the pinned 0.12).
