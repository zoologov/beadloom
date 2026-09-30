# ACTIVE: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Last updated:** 2026-09-30
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-srrn` (P1: the owner's look in a browser, then PR 1). Serialised, not parallel as PLAN drew it: `beadloom waves` finds both in the shared node `site-app`.
**Goal:** the combined tree green with no check weakened, before the selection modes and node pages.
**A3 closed (2026-09-30):** `beadloom-7091` `60bdf1a4` — neighbourhood (depth 1–5/all, in/out/both, dim or hide), impact mode (incoming over `depends_on`/`uses`/`consumes`, rings, summary, risk marks, the graph-view statement, `why`/`impact` to copy), the node card as `widgets/node-card` with every PRD field; data file gains `repository {url, ref}` from the project's own `origin`. Playwright 29 passed (13 new, each red first); pytest 11 978 passed, 1 failed (`test_all_new_node_pairs_are_fresh`); `beadloom ci` rc 1 on 46 stale pairs → W1 `beadloom-qlii`. Three self-checks now leave out of the `architecture-layers` 90% count the edges another layer rule judges (`site-fsd-layers`); the bar is unchanged — flagged for the owner and R1.

**Done when:** the owner has looked at the viewer and said so; PR 1 is open and green; merged on the owner's word.

**W1 closed (2026-09-30):** `beadloom-qlii` `35343379` — 24 files: the site-generation SPEC as at HEAD, the slice pages, three new pages (neighbourhood, impact view, node card), the user's guide section "The architecture viewer"; stale 69 → 0 (615 pairs), surface re-recorded 590 → 615; pytest 12 107 passed, 0 failed; `beadloom ci` rc 0. Left: 10 surface-drift warnings (the README pair, architecture, getting-started, five guides, cli) — warnings, not stale pairs.

**A6 closed (2026-09-30):** `beadloom-ujzb.6` `de4a4c2b` — impact on the landscape: the same Impact toggle, rings with no depth limit, contracts and protocols crossed, broken contracts on the path, risk per service (broken or unverified contract), `why`/`ctx` to copy. The walk is generalised (`dependentsOf` takes, per edge kind, the end that depends): producer → consumer for amqp, graphql and plain dependency. Each landscape contract gains `verdict_basis`. Playwright 99 passed (7 new or changed, red first); pytest 1 failed (stale pairs); `beadloom ci` rc 1 on 69 stale pairs.

**Residue closed (2026-09-30):** `beadloom-ujzb.10` `52c0bbe3` — the remote reaches the data file only as each node's `source_url`; the top-level `repository` and `project` keys are removed (both unread; `project` leaked `?token=` from a remote's basename); unparseable remotes give no link, never a crash; the author check scans every generated file. 30 tests, each seen red. Filed outside: `beadloom-147x` (P1, `beadloom export` publishes a remote's query or fragment in the repo name). The owner confirmed the removal; a project name, if slice 2 needs one, comes from configuration.

**Re-review closed (2026-09-30):** `beadloom-ujzb.9` — M1 fixed with residue (52 remote forms probed), M2 fixed (no author name or email in any of 279 generated files; three leak mutations went red). Residue → `beadloom-ujzb.10`: a legacy Azure SSH remote gets a wrong link; an IPv6 or bad-port remote crashes `docs site`; `repository.url` is published unread and a malformed remote can put a credential in it; the author-data check reads one file only. My launch range excluded the fix commit by one; the reviewer corrected it.

**Fixes closed (2026-09-30):** `beadloom-ujzb.7` `0bb8ce9a`…`8932ba3e` — M1 the generator writes each node's finished `source_url` per forge (GitHub, GitLab, Bitbucket, Gitea/Codeberg, Azure incl. SSH), none for an unknown host (a self-hosted host waits for B4); M2 `activity` narrowed to `commits_30d` and `level`, pinned; m1–m6 and n1–n4 fixed, each with a test seen red; the 17 browser specs bound to the slices they drive (4 slices honestly at 0). Playwright 93 passed; pytest 12 065 passed, 1 failed (stale pairs); `beadloom ci` rc 1 on 69 stale pairs → W1.

**R1 closed (2026-09-30):** `beadloom-arak` — ISSUES, 0 critical, 3 major. M1: source links use GitHub's route only (dead on Bitbucket, Gitea, Azure; the Azure SSH remote becomes a non-browsable address). M2: the data file publishes git author names (`top_contributors`) for every node, read by no screen. M3: 59 stale pairs (W1). Minor: m1 a cleared node-page selection comes back on reload; m2 the viewer shows layer tag tokens, not the declared names; m3 a URL case that cannot fail; m4 the risk oracle copies the viewer's function; m5 viewer slices marked "no bound tests"; m6 warn findings drawn as violations. Sound: FSD (42 imports all downward), the v1 keys, no HTML injection, CI advisory only, the layer-coverage change.

**T1 closed (2026-09-30):** `beadloom-bp8n` `92f4cae7` — 34 slice-1 criteria met, 1 not met (`beadloom ci` rc 1 on 59 stale pairs → W1), 4 not measurable here (`site-e2e` on GitHub, the nine required checks, the owner's look). 17 tests added, each seen red; one read-only test-handle accessor `edgeLooks()`. Measured, no bound declared: data file 340,621 bytes (gzip 39,790; 31,095 on the wire); first render median 4,314 ms (Cytoscape/ELK chunks arrive at 3.5 s); fitted zoom 0.0515 on the page, 0.083–0.110 in full screen. Open for the owner: the landscape's own card vs the PRD's one card. Filed `beadloom-gvdy` (P2, test fixtures that leak a grammar swap).

**A5 closed (2026-09-30):** `beadloom-rjp1` `7fe2912e` — 55 Playwright cases (39 → 55), each goal mapped to its cases on the bead; 16 new or strengthened cases seen red on one deliberately broken build; the advisory `site-e2e` job in `ci.yml` (after `site-build`, Node 22, report on failure), named in `ADVISORY_JOBS` in the CI self-checks, not a required context. Not covered: direction readable at a glance (the test handle exposes no arrow shape), the 50-name symbol cap. pytest 11 998 passed, 1 failed (stale pairs → W1).

**A4 closed (2026-09-30):** `beadloom-k0s6` `01fadab4` — node pages (every kind, `/other/` included) mount `ArchitectureMap` focused on their node, depth 1, card open, free navigation; the landscape runs on the core with protocol, verdict and problems filters, health borders, resolved colours; a pre-existing bug fixed — no Mermaid click target on the built site was rewritten. Deliberate differences, in CONTEXT: no impact in landscape mode, no edge card, the data mode is the page's prop. Playwright 39 passed (10 new, red first); pytest 11 991 passed, 1 failed (stale pairs); `beadloom ci` rc 1 on 59 stale pairs → W1. `beadloom-ujzb.5` `bf19eeb0`: layer coverage counts any layer rule — 411 of 420 (97.9%); counting one rule only drops it to 372 and the three checks go red.

**W0 closed (2026-09-30):** `beadloom-ujzb.4` `74bc8a95`, `4fb6c1c6`, `23661529` — 13 documents; stale pairs 43 → 0 (590 ok); `docs audit` 0; pytest 0 failed; `beadloom ci` rc 0. `.beadloom/sync-surface.json` re-recorded 568 → 590. The application README was attested whole (89 pairs, 71 sibling pairs marked not verified).

**K4 closed (2026-09-30):** `beadloom-ujzb.3` `efe7bd10` — test files listed at their owning node only, ancestors keep counts and a new `file_count`; 376,794 → 331,941 bytes (gzip 44,755 → 38,711). The tests field was 87 KB, not most of the growth: the largest fields now are edges 63 KB, `public_symbols` 47 KB, tests 42 KB, `activity` 26 KB. Tree: 11 946 passed, 1 failed (the same 18 SPEC pairs → W0); `beadloom ci` rc 1 on sync-check only (43 stale).

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
| `beadloom-ujzb.3` | K4 dev | ✓ done | tests listed at their node only |
| `beadloom-ujzb.4` | W0 docs | ✓ done | stale pairs of A1, A2, K1–K4 |
| `beadloom-7091` | A3 dev | ✓ done | neighbourhood, impact, the card |
| `beadloom-k0s6` | A4 dev | ✓ done | node pages; landscape mode |
| `beadloom-ujzb.5` | test | ✓ done | layer-coverage self-checks, strict (owner) |
| `beadloom-rjp1` | A5 test | ✓ done | browser tests; `site-e2e` |
| `beadloom-bp8n` | T1 test | ✓ done | slice 1 criteria |
| `beadloom-arak` | R1 review | ✓ done | review slice 1 |
| `beadloom-ujzb.7` | fix | ✓ done | R1's findings M1, M2, m1–m6, n1–n5 |
| `beadloom-ujzb.6` | dev | ✓ done | landscape impact mode (owner) |
| `beadloom-ujzb.9` | review | ✓ done | re-review of M1, M2 |
| `beadloom-ujzb.10` | fix | ✓ done | the re-review's residue |
| `beadloom-qlii` | W1 tech-writer | ✓ done | site SPEC, guide, data contract |
| `beadloom-srrn` | P1 PR 1 | in progress | owner's look; PR 1 |
| `beadloom-dfwt` | B1 dev | blocked | scaffold in the wheel |
| `beadloom-qki6` | B2 dev | blocked | our site through the same path |
| `beadloom-hmqn` | B3 test | blocked | adopter fixtures, six stacks |
| `beadloom-ujzb.8` | B4 dev | blocked | self-hosted forge links (owner) |
| `beadloom-19l6` | T2 test | blocked | slice 2 criteria |
| `beadloom-fht7` | R2 review | blocked | review slice 2 |
| `beadloom-ri5a` | W2 tech-writer | blocked | adopter docs |
| `beadloom-la3t` | P2 PR 2 | blocked | owner's look; PR 2 |
