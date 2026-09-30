# ACTIVE: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Last updated:** 2026-09-30
> **Phase:** Development

---

## Current Bead

**Bead:** Wave −1 — `beadloom-hjr1` (J1, relative JS/TS imports) ∥ `beadloom-tmxa` (J3, `.vue` parsed); then `beadloom-g9fb` (J2, no false edges; same resolver as J1). Then A0 step 2 (`beadloom-kcwz`).
**Goal:** beadloom reads JS/TS/Vue honestly, so that the viewer has a truthful graph for a JS/TS adopter and our site can join the graph.
**Done when:** on non-repository fixtures, `why` sees relative-import dependents, `.vue` symbols appear in `ctx` at their lines, and a mixed repository's edge count equals what its imports name; this repository's Python graph is unchanged.

**Resumed 2026-09-30:** the owner folded the three fixes into BDL-076 before the viewer work (PRD amendment, RFC axes rows `import-resolver` and `code-indexer`, PLAN J1–J3).

**A0 step 1 — measured (2026-09-30, beadloom 7.0.0, the `languages` extra, a `git archive` copy and a separate Vue fixture; details on `beadloom-kcwz`):**
- **`.vue` is not read.** All 10 theme components and the fixture give 0 symbols and 0 imports, `<script setup>` included. `.vue` is a code extension (`application/reindex/models.py:69`) with no parser (`context_oracle/code_indexer.py:246-264`), so it is only hashed. A probe that fed the extracted script blocks to the existing JS parser found 39 functions and 14 package imports: the parser works, and extracting the block is what is missing → `beadloom-tmxa`.
- **`.js` is partly read.** 14 exported functions are read; `export const` and `import()` are not.
- **Relative JS/TS imports are never resolved** (`graph/import_resolver.py:153-155`). None of the theme's 26 relative imports becomes an edge, and on the fixture `why` finds no dependents for an imported composable. This affects every JS/TS adopter → `beadloom-hjr1` (P1 bug).
- **A non-Python scan path creates false edges.** With the theme path added, 1,318 unresolvable Python imports (`typing`, `pathlib`, …) resolve to `vitepress-site` through the resolver's walk-up (`import_resolver.py:737-765`): 103 false `depends_on` edges, and `lint --strict` stays green → `beadloom-g9fb` (P1 bug).
- **What the tools see today:** `ctx` shows none of the theme's functions (no annotations); `impact` says "reads Python source"; `sync-check` sees a `.vue` edit only as a whole-file hash change.

**The decision waiting for the owner:** A0 step 2 needs the three beadloom changes above (`.vue` reader, relative JS/TS imports, the resolver walk-up fix). Choose among:
- take them into BDL-076 before the viewer work;
- make them their own work item first;
- or proceed with the viewer and leave the site outside the graph until they land.

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
| `beadloom-kcwz` | A0 dev | in progress | our site under beadloom; `.vue` measured first |
| `beadloom-o2ua` | A1 dev | blocked | the data file v2 |
| `beadloom-iehv` | A2 dev | blocked | the viewer core |
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
