# ACTIVE: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Last updated:** 2026-09-30
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-ujzb.3` (K4, data size); then `beadloom-ujzb.4` (W0, docs); then A3 ∥ A4.
**Goal:** the combined tree green with no check weakened, before the selection modes and node pages.
**Done when:** the data file lists tests at their node only; W0 brings every stale pair fresh; `beadloom ci` rc 0.

**Wave 2 closed (2026-09-30):** K1 `beadloom-ujzb.2` `2a3daa08` — the portal's modules in `application/site/` (53 files moved, no shims; `application` 183 → 14 owned symbols, `site-generation` 24 → 193 as a feature; 495 moved tests same ids; `docs site` output identical but for timestamps). K2 `beadloom-oo4m` `0e690d16` — a partly annotated node keeps a pair for every file, the backstop reads every indexed language (site pairs 45 → 64; Python 523 → 526). K3 `beadloom-5o48` `f61c8ab0` — `doc-area-coherence` reads one root per top-level tree when that matches more pairs; back at error, 117 of 126 pairs checked, 0 findings. Gate owner K1 on the combined tree (f61c8ab0): 11 937 passed, 1 failed (`test_all_new_node_pairs_are_fresh`: 18 `site-generation` SPEC pairs → W0), ruff and mypy clean, `lint --strict` 0; `beadloom ci` rc 1 on sync-check only (→ W0).

**Wave 1 closed (2026-09-30):** A1 `beadloom-o2ua` `9daa9d19` — data file v2 (every card field, all edge kinds, the project's layers, a `url` for all 110 nodes; v1 keys kept; symbols' names under `public_symbols`); 145 → 345 KB, mostly test lists repeated at every ancestor (→ K4). A2 `beadloom-iehv` `678942f1`, `20560d14`, `f62243fd` — the core in FSD (`app`/`pages`/`widgets`/`features`/`entities`/`shared`), no dragging by default, real colours in both themes, per-kind edges, layer lanes that ELK now receives, filters that keep ancestors, URL state, full screen holding toolbar, canvas, card and legend; 16 Playwright cases, each red on the old viewer; 17 slice nodes and the `site-fsd-layers` rule (29 edges judged, 0 findings). Combined tree: 11 910 passed, 2 failed (`application` at 183 of 180 symbols → K1); `beadloom ci` rc 1 on 93 stale pairs (→ W0). A2 lowered `doc-area-coherence` to warn, because a second source tree made it judge 0 of 126 pairs; the owner ruled: fix it in the epic (K3) and restore error before PR 1.

**Wave −1 and 0 closed (2026-09-30):** J1 `beadloom-hjr1` `f91f8762` (relative JS/TS imports resolve; 379 edges unchanged); J3 `beadloom-tmxa` `2b00507d` (`.vue` script blocks parsed at their lines; `export const`/`default` as symbols — new kind `variable`, `db` axis row added); J2 `beadloom-g9fb` `09d33310` (a Python import looks only in Python scan paths; the walk-up stops below a scan root; `.vue` imports and literal `import()` extracted); docs `beadloom-ujzb.1` `c797d7d7` (18 stale → 0); A0 step 2 `beadloom-kcwz` `10bb2bfc` (the theme scanned under `vitepress-site`, 80 symbols indexed, 380 edges byte-identical, 0 Python imports into the site; the node's document `docs/services/vitepress-site.md`; Playwright tests under `site/e2e` bind to the node). Gate owner A0 on the combined tree: 11 822 passed, 0 failed; `beadloom ci` rc 0.
- Still true after A0: `ctx` attaches a symbol only through a `beadloom:` annotation, so the theme's symbols show under no node until A2 annotates the slices; `impact` reads Python only (`beadloom-j1ke`, P2); annotating one file of a node drops the sync pairs of its other files because the backstop reads only `*.py` (`beadloom-oo4m`, P1 — A2 annotates whole slices); the git hooks' global `beadloom` lacks the `languages` extra and empties the theme's symbols (`beadloom-v4ql`, P2). Filed outside: `beadloom-95jv` (first full reindex misses an edge).

**Resumed 2026-09-30:** the owner folded the three fixes into BDL-076 before the viewer work (PRD amendment, RFC axes rows `import-resolver` and `code-indexer`, PLAN J1–J3).

**A0 step 1 — measured (2026-09-30, beadloom 7.0.0, the `languages` extra, a `git archive` copy and a separate Vue fixture; details on `beadloom-kcwz`):**
- **`.vue` is not read.** All 10 theme components and the fixture give 0 symbols and 0 imports, `<script setup>` included. `.vue` is a code extension (`application/reindex/models.py:69`) with no parser (`context_oracle/code_indexer.py:246-264`), so it is only hashed. A probe that fed the extracted script blocks to the existing JS parser found 39 functions and 14 package imports: the parser works, and extracting the block is what is missing → `beadloom-tmxa`.
- **`.js` is partly read.** 14 exported functions are read; `export const` and `import()` are not.
- **Relative JS/TS imports are never resolved** (`graph/import_resolver.py:153-155`). None of the theme's 26 relative imports becomes an edge, and on the fixture `why` finds no dependents for an imported composable. This affects every JS/TS adopter → `beadloom-hjr1` (P1 bug).
- **A non-Python scan path creates false edges.** With the theme path added, 1,318 unresolvable Python imports (`typing`, `pathlib`, …) resolve to `vitepress-site` through the resolver's walk-up (`import_resolver.py:737-765`): 103 false `depends_on` edges, and `lint --strict` stays green → `beadloom-g9fb` (P1 bug).
- **What the tools see today:** `ctx` shows none of the theme's functions (no annotations); `impact` says "reads Python source"; `sync-check` sees a `.vue` edit only as a whole-file hash change.

## Progress

- [x] Docs folder, the Explore axes and the facts (`axes.md`, 2026-09-30)
- [x] PRD (with the impact mode), RFC, CONTEXT and PLAN approved (2026-09-30); A0 added by the owner
- [x] Beads created: epic `beadloom-ujzb` + 17 from one plan
- [ ] Slice 1 — the viewer for the team (PR 1)
- [ ] Slice 2 — the portal for adopters (PR 2)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-ujzb` | epic | ready | BDL-076 parent |
| `beadloom-hjr1` | J1 dev | ✓ done | relative JS/TS imports resolve; 379 edges unchanged here |
| `beadloom-g9fb` | J2 dev | ✓ done | no false edges from a foreign scan path; `.vue` imports and `import()` read |
| `beadloom-tmxa` | J3 dev | ✓ done | `.vue` symbols at their lines; `export const`/`default` read; `.vue` imports and `import()` NOT done (resolver file, see bead) |
| `beadloom-ujzb.1` | tech-writer | ✓ done | 6 docs refreshed for J1-J3; sync-check 18 stale → 0 |
| `beadloom-kcwz` | A0 dev | ✓ done | our site under beadloom; `.vue` measured first |
| `beadloom-o2ua` | A1 dev | ✓ done | the data file v2 |
| `beadloom-iehv` | A2 dev | ✓ done | the viewer core |
| `beadloom-ujzb.2` | K1 dev | ✓ done | the portal package |
| `beadloom-oo4m` | K2 dev | ✓ done | JS/Vue sync pairs kept |
| `beadloom-5o48` | K3 dev | ✓ done | `doc-area-coherence`, several trees |
| `beadloom-ujzb.3` | K4 dev | in progress | tests listed at their node only |
| `beadloom-ujzb.4` | W0 docs | blocked | stale pairs of A1, A2, K1–K4 |
| `beadloom-7091` | A3 dev | blocked | neighbourhood, impact, the card |
| `beadloom-k0s6` | A4 dev | blocked | node pages; landscape mode |
| `beadloom-rjp1` | A5 test | blocked | browser tests; `site-e2e` |
| `beadloom-bp8n` | T1 test | blocked | slice 1 criteria |
| `beadloom-arak` | R1 review | blocked | review slice 1 |
| `beadloom-qlii` | W1 tech-writer | blocked | site SPEC, guide, data contract |
| `beadloom-srrn` | P1 PR 1 | blocked | owner's look; PR 1 |
| `beadloom-dfwt` | B1 dev | blocked | scaffold in the wheel |
| `beadloom-qki6` | B2 dev | blocked | our site through the same path |
| `beadloom-hmqn` | B3 test | blocked | adopter fixtures, six stacks |
| `beadloom-19l6` | T2 test | blocked | slice 2 criteria |
| `beadloom-fht7` | R2 review | blocked | review slice 2 |
| `beadloom-ri5a` | W2 tech-writer | blocked | adopter docs |
| `beadloom-la3t` | P2 PR 2 | blocked | owner's look; PR 2 |
