# ACTIVE: BDL-075 — Release 7.0.0 with the documentation current

> **Last updated:** 2026-09-29
> **Phase:** Development

---

## Current Bead

**Bead:** Wave 1 — `beadloom-nxf7` (R1, the version and the change log) and `beadloom-10er` (T1, the PLAN template), in parallel.
**Goal:** 7.0.0 on the tree with its change log; the shipped PLAN template without a status column.
**Done when:** `test_version_surface.py` green, `beadloom ci` rc 0, the suite green; the composed template has no status column.

## Progress

- [x] Docs folder, the Explore axes and the adopter-visible changes (`axes.md`, 2026-09-29)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-29); the PLAN template added to the scope by the owner
- [x] Beads created: epic `beadloom-uk2e` + 7 from one plan, `beadloom-10er` brought under it
- [ ] The release commit (R1, T1, D1–D3, V1, R)
- [ ] PR, merge, publish, verify on the downloaded wheel (P)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-uk2e` | epic | ready | BDL-075 parent |
| `beadloom-nxf7` | R1 dev | done | 7.0.0 on every current-version site and `[7.0.0]` in CHANGELOG; no ignore triple needed; `beadloom-tu41` filed |
| `beadloom-10er` | T1 dev | done | the PLAN template without a status column; BRIEF's twin filed as `beadloom-3nwz` |
| `beadloom-3nwz` | T1b dev | done | the BRIEF template without a status column |
| `beadloom-fdvz` | D1 tech-writer | done | the README pair: the audit's rows fixed and measured on 7.0.0, the section on tests bound to the graph; `readme-pair` 118 blocks, 0 findings |
| `beadloom-n5w5` | D2 tech-writer | done | ROADMAP.md: the audit's 27 rows and M1-M8 resolved (detail in the bead); open work ranked 1-11 in the owner's order; three shipped items moved to 'Shipped since v4.0.0'; federation deferred; every open P0/P1 bug named; `beadloom-txeq` closed |
| `beadloom-o2z4` | D3 tech-writer | done | BDL-UX-Issues.md: Open 133→79, Improvements 20→17, Excluded 7→6, Closed 117→175; no number both open and closed; `beadloom-s34t` filed |
| `beadloom-adbg` | V1 test | ready | the built wheel; the README's steps |
| `beadloom-bz48` | R review | blocked | review |
| `beadloom-vgst` | P publish | blocked | publish and verify |
