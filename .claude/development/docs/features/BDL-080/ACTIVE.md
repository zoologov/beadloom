# ACTIVE: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Last updated:** 2026-10-08
> **Phase:** Development

---

## Current Bead

**Bead:** S1 — `beadloom-lsev` (S1T); then R, W, PR.
**Goal:** the site a service, every layer rule drawn (S1); then S2, S3, S4.
**Done when:** every PRD goal's *Done when* holds; four PRs merged; a MINOR release.

## Progress

- [x] PRD, RFC, CONTEXT, PLAN approved (2026-10-08)
- [x] S1a, S1b, S1c, S1d landed
- [ ] S1 test, S1e (owner's look), review, docs, PR
- [ ] S2, S3, S4

## Results

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-je0i` | S1a | ✓ done | site is an alias of service: `KIND_ALIASES` in `graph/loader.py` (not `rules/types.py`: a cycle, measured); the doc skeleton applies it too; lint 0 errors, `architecture-layers` judged 381 -> 425 of 434, no finding |
| `beadloom-kgh6` | S1b | ✓ done | `layer_rules` + per node `layer_rule`/`layer_rule_rank` (new `application/site/layer_rules_view.py`); `scope:` parsed, validated, indexed, narrows evaluator/reach/liveness through `layers.within_scope`; site slices placed by `site-fsd-layers` (scope `vitepress-site`), `cli` by `architecture-layers` (scope `beadloom`); lint 0 errors / 69 warnings before and after; existing keys byte-identical |
| `beadloom-i3zs` | S1c | ✓ done | a layer is (rule, rank); legend grouped per rule; filter offers `rule: layer` where two rules are drawn; card names the rule; sixth tone a portal cyan (`brand` is VitePress's indigo); a rule scoped to a box inside the frame draws one box per layer in it (this portal: six in `vitepress-site`), stacked by layout-only lane edges because ELK reads no partition inside a box; one FSD finding drawn red; fixtures drawn alike with and without the new keys; full chromium 317 of 318 (the 318th `diagram-links`, red on HEAD since S1a) |
| `beadloom-af99.1` | S1d | ✓ done | the link writer was right (`/services/vitepress-site`); the case needed a landscape node under `other/`, which this portal no longer holds. It now moves one drawn click target under `/other/` in the page's bundle; new site-generation scenario pins a site node's diagram link under `services/`; diagram-links + landscape + node-page 23 of 23, `BEADLOOM_E2E_NO_SKIP=1` |
| `beadloom-lsev` | S1T | ✓ done | every S1 criterion measured on this portal and the fixtures: all hold; the 14 'unbound' files were scope-check's 'no node owns' count, 0 test files of the branch unbound; +4 test files (own portal as a service by its own rules 13, planted FSD crossing red 2, doctor 3, unreadable rule row 8) and 1 browser case (one rule drawn alike with and without the new keys), each seen red; full tree on the tree: pytest 2,420 + 5,859 + 3,573 + 1,705 (1 failed = stale pairs), chromium 319 of 319, performance 10 of 10, six stacks 86 of 86 |
| `beadloom-af99.2` | S1e | ✓ done | a box holding a layer rule's boxes opens only where they are readable, also when tapped: the site tapped at the fit is framed whole and drawn closed (0.128, layer boxes 12.2 px), opens at 0.313 (29.7 px), 0 title overlaps zooming in and out (5 at 0.128 before); `title:` on a layers rule (loader, index, data file `layer_rules[].title`), legend `DDD architecture (top → bottom):`, filter `FSD architecture: widgets` with the value `site-fsd-layers: widgets`, card `widgets (FSD architecture, its own tag)` |
| `beadloom-m7xq` | S1R | ✓ done | review, bead id only |
| `beadloom-af99.3` | S1f | ✓ done | the first rule's `layer`/`layer_rank` read the tags inside its `scope:`, so a node outside has none and an edge no rule judged carries no `violation` (six fixtures' data files byte-identical; this portal's layer keys and edges identical); a bare `?layer=domains` on a portal of two rules opens on that layer (the first rule's by name where two share the name) and the URL takes the offered value; the evaluator walks a scoped rule's subtree once (`scoped_reach`) |
| `beadloom-af99.4` | S1R2 | in progress | re-review of the fix |
| `beadloom-we9t` | S1W | blocked | docs |
| `beadloom-z30s` | S1P | blocked | PR, merge on green |

## Notes

- **S1f closed (2026-10-09):** `a19505b9` — the first rule's old keys from the tags inside its scope; an edge no rule judged has no `violation` key; the six fixtures byte-identical; a bare `?layer=` resolves to the rule that has it; the scoped subtree walked once. Re-review launched with the bead id only.

- **S1R closed (2026-10-09):** `beadloom-m7xq` = ISSUES, 0 critical, 1 major: when the first layers rule by name declares `scope:`, the old keys are computed against the unscoped tags and an edge no rule judged is written `violation: false` (reviewer's probe; matters for S3's FSD-only projects) -> `beadloom-af99.3`, with the minors (a pre-S1 `?layer=` link on a two-rule portal; `reach_of` narrowing twice). RFC/CONTEXT drift corrected by the coordinator (sixth tone cyan; `KIND_ALIASES` in the loader; `title:` in the API list). The docs list for S1W includes `architecture-data.md` and the CHANGELOG's `[Unreleased]`.

- **S1e closed (2026-10-09):** `46adf178` — a box holding a rule's layer boxes opens only once they are readable, even when selected (the site tapped at the fit: framed whole at 0.128, drawn closed with its title inside; opens at 0.313 with layer titles 10.6-14.8 px; 5 overlaps -> 0); `title:` on a layers rule (loader, index, data file): legend `DDD architecture (top → bottom)` / `FSD architecture (top → bottom)`, filter `FSD architecture: widgets` (URL keeps the name), card `widgets (FSD architecture, its own tag)`. 211 browser cases, fixtures 0 failed, 2,401 pytest. Surfaced: the same plate-over-a-box look exists for context-oracle tapped at the fit (test-mapping's title on a plate over context-builder) — applying the readable rule to every box that holds boxes is the owner's call. 108 stale pairs -> S1W. S1R launched with the bead id only.

- **S1T closed (2026-10-09):** `c242bea5` — every S1 criterion PASS on this portal and the six fixtures (27 pytest cases + 1 Playwright, each red against a planted defect); the '14 unbound test files' were the scope-check's count of paths no node OWNS, not unbound tests — every added test binds by its mirror; 167 unplaced unchanged. Full tree: pytest 2,420 + 5,859 + 3,573 + 1,705 (1 known red); Playwright 319 of 319; performance 10; adopters 86 of 86; `lint --strict` 0 errors; `beadloom ci` rc 1 on 103 stale pairs only. S1e launched.

- **S1d closed (2026-10-08):** `694c831b` — no production defect: the portal links the site under `/services/` everywhere; the `diagram-links` case assumed a landscape node under `other/`, which this portal no longer has; the case now serves its own fixture; a Python scenario holds that a `kind: site` node links under `/services/`. S1T launched (full tree once for the slice; the 14 unbound test files of S1b).

- **S1c closed (2026-10-08):** `c19acf0d` — the site box opens onto six layer boxes (app … shared), coloured and titled by the layer, routes ending on them, rounded; the legend groups layers per rule; the filter offers `rule: layer` names when more than one rule is drawn; the card names the rule; sixth tone the portal's cyan (brand = indigo in VitePress 1.6.4; sponsor pink fails 3:1 in dark); no layer boxes for a rule scoped to the project frame (owner to confirm); lanes: layer boxes stacked by layout-only edges, every box's lanes left as they were (owner's call). Chromium 317 of 318 — `diagram-links` red since S1a -> `beadloom-af99.1`. 103 stale pairs -> S1W. Coordinator's look at light-3-site-open.png: the FSD layers reuse the DDD rule's tones (app purple = services purple) — surfaced to the owner.

- **S1b closed (2026-10-08):** `a20b7df3` — `layer_rules` top-level, per node `layer_rule` / `layer_rule_rank`, `violation` the union over rules; old keys unchanged (schema 2; this portal's old keys and edges byte-identical; six fixtures identical but the new keys); `scope:` on a `layers` rule parsed, validated, indexed, applied through `layers.within_scope`; derived scopes: `architecture-layers` -> `beadloom`, `site-fsd-layers` -> `vitepress-site`; 109 nodes under the first rule, 20 under the FSD rule, 1 under none. Lint identical before/after. 65 stale pairs -> S1W; 14 new test files bind to no node -> S1T. S1c launched.

- **S1a closed (2026-10-08):** `3c798da3` — `KIND_ALIASES`/`canonical_kind` in `graph/loader.py` (not beside `VALID_NODE_KINDS`: the rule engine imports the loader, a cycle); the doc generator reads YAML directly and applies the same table through `onboarding.graph_files`; reindex prints an `[info]` for an alias; `vitepress-site.yml` kind service, `layer-service`; `lint --strict` 0 errors, 70 -> 69 warnings, `architecture-layers` judges 381 -> 425 of 434 edges, no new finding; the own portal page under `services/`. 5,469 passed on the touched packages; sync-check 15 stale pairs -> S1W. S1b launched.

- Epic `beadloom-af99`; branch `features/BDL-080` from `main` at `7b9a9b65` (8.0.0); the branch's first commit is BDL-079's close-out. Later slices' beads are created when the slice starts.
