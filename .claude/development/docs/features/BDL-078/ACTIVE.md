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
| `beadloom-xv87` | V1 | in progress | the base look |
| `beadloom-0gyz` | V2 | blocked | the overview |
| `beadloom-hnff` | V3 | blocked | levels |
| `beadloom-lw56` | F-activity | ✓ done | activity by changed lines |
| `beadloom-btkd.1` | dev | in progress | activity: boxes among boxes, generated files excluded (owner) |
| `beadloom-nh7h` | F-nh7h | ✓ done | incremental vs fresh import resolution |
| `beadloom-jcng` | F-jcng | ready | manifests as inputs |
| `beadloom-76mk` | F-76mk | ✓ done | flat Python tests bind |
| `beadloom-stcx` | F-stcx | ✓ done | `vitepress dev` loads |
| `beadloom-q63p` | T | blocked | PRD criteria measured |
| `beadloom-ak1i` | R | blocked | review |
| `beadloom-1hle` | W | blocked | docs |
| `beadloom-hpat` | P | blocked | owner's look, PR |

## Notes

- **Wave 3 closed (2026-10-05):** `beadloom-nh7h` `80095d60` — an import resolves against the tree's source files, so the incremental and the fresh index agree (`tui -> graph-reads`). `beadloom-ytcg` `05dad0e8` — every record keyed by a node or edge id has no prototype (`idRecord` in `shared/ids`); positions and routes byte-identical over a frozen data file (130 nodes, 453 edges). Gate owner ytcg on the combined tree at `353097b0`: 13,291 passed, 0 failed; ruff, mypy (3.10-3.13), lint, doctor clean; Playwright 205 passed; `beadloom ci` rc 1 on 48 stale pairs from HEAD (31 + 4 + 13) -> W, the run also saw `beadloom-btkd.1`'s uncommitted files. Next: `beadloom-xv87` (V1) launched beside `beadloom-btkd.1`; `beadloom-jcng` waits for `beadloom-btkd.1` (`beadloom waves`: reindex -> git-activity).

- **Wave 2 closed (2026-10-05):** `beadloom-lw56` `15b2e339` — activity by changed lines with relative levels and roll-up; this repository: 0 hot / 11 warm / 103 cold / 16 dormant → 10 hot / 28 warm / 57 cool / 21 quiet / 14 dormant; `infrastructure` 0 → 658 lines (warm). Suite and browser suite green; `beadloom ci` rc 1 on 31 stale pairs → W. For the owner: 7 of the 10 hot nodes are boxes (one population with leaves); lock files count as churn (`package-lock.json` is 3,912 of vitepress-site's 17,714 lines).

- **Wave 1 closed (2026-10-05):** `beadloom-76mk` `27010d00` — flat Python tests bind through `tests: {flat_tests: true}`, which `init` writes for a Python project (opt-in: binding by name stays off by default, per the 2026-09-28 ruling; this repository's 747 bindings unchanged; surfaced to the owner); `init` names unbound test files. `beadloom-stcx` `0c43021c` — the shipped config pre-bundles mermaid and the ELK worker engine; the dev check opens a Mermaid page and the architecture page (both failed before); six adopter portals load under the dev server. Gate owner stcx on the combined tree: 13,246 passed, 0 failed; ruff, mypy, lint clean; `beadloom ci` rc 1 on 13 stale pairs of 76mk → W.

- The branch carries BDL-077's close-out commit `fd3d3f1a`.
