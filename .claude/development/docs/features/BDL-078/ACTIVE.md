# ACTIVE: BDL-078 — The viewer looks finished, and five defects are fixed

> **Last updated:** 2026-10-05
> **Phase:** Development

---

## Current Bead

**Bead:** wave 3 — `beadloom-nh7h` ∥ `beadloom-ytcg` (gate owner); then F-jcng, V1 → V2 → V3; T → R → W → P.
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
| `beadloom-ytcg` | F-ytcg | ✓ done | a node named `__proto__` is drawn |
| `beadloom-xv87` | V1 | ✓ done | the base look: `584b9677`, `e152a493`, `562551ed` |
| `beadloom-0gyz` | V2 | in progress | the overview |
| `beadloom-btkd.2` | dev | blocked | a line enters its arrowhead correctly (owner, after V1) |
| `beadloom-hnff` | V3 | blocked | levels |
| `beadloom-lw56` | F-activity | ✓ done | activity by changed lines |
| `beadloom-btkd.1` | dev | ✓ done | activity: boxes among boxes, generated files excluded (owner) |
| `beadloom-nh7h` | F-nh7h | ✓ done | incremental vs fresh import resolution |
| `beadloom-jcng` | F-jcng | ✓ done | manifests as inputs: a go.mod, go.work or Package.swift edit re-resolves the imports it governs; a Go module path with no `/` is imported |
| `beadloom-76mk` | F-76mk | ✓ done | flat Python tests bind |
| `beadloom-stcx` | F-stcx | ✓ done | `vitepress dev` loads |
| `beadloom-q63p` | T | blocked | PRD criteria measured |
| `beadloom-ak1i` | R | blocked | review |
| `beadloom-1hle` | W | blocked | docs |
| `beadloom-hpat` | P | blocked | owner's look, PR |

## Notes

- **Wave 4 closed (2026-10-05):** `beadloom-jcng` `61a2e390` — a changed `go.mod`, `go.work` or `Package.swift` alone re-resolves every stored import; single-segment Go module paths no longer dropped (Go standard-library imports are now stored with no node -> T measures). `beadloom-xv87` (V1) `584b9677`, `e152a493`, `562551ed` — one weight, bridges, junction dots and gradient removed, corner status mark, legends; the layout no longer depends on findings (all 130 nodes moved once; RND probe numbers are on the old layout); Cytoscape's edge path cache off. Gate owner xv87 on the tree at `e152a493`: 13,361 passed, 0 failed; ruff, mypy, lint, doctor clean; Playwright 203 of 203; adopter portals 18 of 18; `beadloom ci` rc 1 on sync-check alone (225 stale pairs -> W). Open from V1, handed to V3 in its bead comments: 34 of 139 arrowheads broken at zoom 0.545; a diagonal unrouted line from a node to its own box. V1's readings for the owner: a followed line keeps the one weight; imports = text colour at 40%; dotted kinds in screen pixels. `beadloom-0gyz` (V2) launched.

- **`beadloom-btkd.1` closed (2026-10-05)** `98d938ee` — boxes rank among boxes, leaves among leaves; lock files (20 names), files git attributes mark generated or binary, and the project's `activity: {exclude: [...]}` patterns count neither lines nor commits. This repository: boxes 7 hot / 4 warm / 1 cool -> 2 / 3 / 7; leaves 3 hot / 24 warm / 56 cool / 21 quiet / 14 dormant -> 9 / 25 / 49 / 21 / 14. Measured on the shared tree: 13,332 passed, only the stale-docs self-check red. Correction: the wave-2 note's "`package-lock.json` is 3,912 of 17,714 lines" was not reproduced — the dev measured 59 of 18,005 in 30 days; the exclusion changes no level here. Six readings (a)-(f) of the ruling are in the bead's comments, for the owner. Incident, recovered: a stray `git stash` held the tree's tracked changes for seconds. `beadloom-jcng` launched beside `beadloom-xv87`.

- **Wave 3 closed (2026-10-05):** `beadloom-nh7h` `80095d60` — an import resolves against the tree's source files, so the incremental and the fresh index agree (`tui -> graph-reads`). `beadloom-ytcg` `05dad0e8` — every record keyed by a node or edge id has no prototype (`idRecord` in `shared/ids`); positions and routes byte-identical over a frozen data file (130 nodes, 453 edges). Gate owner ytcg on the combined tree at `353097b0`: 13,291 passed, 0 failed; ruff, mypy (3.10-3.13), lint, doctor clean; Playwright 205 passed; `beadloom ci` rc 1 on 48 stale pairs from HEAD (31 + 4 + 13) -> W, the run also saw `beadloom-btkd.1`'s uncommitted files. Next: `beadloom-xv87` (V1) launched beside `beadloom-btkd.1`; `beadloom-jcng` waits for `beadloom-btkd.1` (`beadloom waves`: reindex -> git-activity).

- **Wave 2 closed (2026-10-05):** `beadloom-lw56` `15b2e339` — activity by changed lines with relative levels and roll-up; this repository: 0 hot / 11 warm / 103 cold / 16 dormant → 10 hot / 28 warm / 57 cool / 21 quiet / 14 dormant; `infrastructure` 0 → 658 lines (warm). Suite and browser suite green; `beadloom ci` rc 1 on 31 stale pairs → W. For the owner: 7 of the 10 hot nodes are boxes (one population with leaves); lock files count as churn (`package-lock.json` is 3,912 of vitepress-site's 17,714 lines).

- **Wave 1 closed (2026-10-05):** `beadloom-76mk` `27010d00` — flat Python tests bind through `tests: {flat_tests: true}`, which `init` writes for a Python project (opt-in: binding by name stays off by default, per the 2026-09-28 ruling; this repository's 747 bindings unchanged; surfaced to the owner); `init` names unbound test files. `beadloom-stcx` `0c43021c` — the shipped config pre-bundles mermaid and the ELK worker engine; the dev check opens a Mermaid page and the architecture page (both failed before); six adopter portals load under the dev server. Gate owner stcx on the combined tree: 13,246 passed, 0 failed; ruff, mypy, lint clean; `beadloom ci` rc 1 on 13 stale pairs of 76mk → W.

- The branch carries BDL-077's close-out commit `fd3d3f1a`.
