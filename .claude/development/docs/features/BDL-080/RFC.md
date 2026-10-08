# RFC: BDL-080 — The portal is a service, and the viewer serves a Feature-Sliced frontend

> **Status:** Draft
> **Created:** 2026-10-08

---

## Overview

Four slices, one PR each. S1 makes `vitepress-site` a service and draws every layer rule. S2
cuts the viewer into FSD slices that are nodes and declares the cohesion rule, in the graph and
in the roles. S3 closes the import resolver's gaps for Vue and React Native, gives `init` an FSD
preset with the FSD rules, and adds two adopter fixtures shaped like the owner's own projects.
S4 makes every number and colour on a card or legend name its population. The version is MINOR:
every change adds, `kind: site` stays accepted, the data file's existing keys keep their meaning.

## Motivation

### Problem

See PRD. The measured facts behind each slice are in `axes.md` and the technical brief of
2026-10-08 (the session's Explore; file:line cited below).

### Solution

The decisions D1–D8 below, each with the alternative it rejects.

## Technical Context

### Constraints

- The declared public API (`docs/guides/public-api.md`) decides the version: adding keys, rules,
  options and an accepted alias is MINOR; changing the meaning of an existing key or value is
  MAJOR. This epic adds only.
- The viewer and the data file ship together from one `docs site`, so a new data key reaches
  the viewer that reads it; `useArchitectureData.js:14` accepts schema versions `[1, 2]`.
- `beadloom waves` serialises by graph node; the cut in S2 is what buys parallelism, so S2's
  node declarations land before any later viewer bead is launched.
- FSD best practice is read from Steiger's `recommended` set (the official FSD linter, which one
  of the owner's projects already runs): `forbidden-imports` (no cross-import inside a layer, no
  upward import), `public-api` (a slice is entered through its `index`), `insignificant-slice`,
  `no-layer-public-api`. Beadloom judges the graph and shows the portal; Steiger stays the
  file-level linter where a project has it.

### Affected Areas

`graph-loader` (kind alias), `rule-engine` (`scope:`, a tag-prefix matcher, two new rule
types), `import-resolver` (aliases, platform suffixes, `.mjs/.cjs`), `site-generation` (the
data file, the Source link, lint totals, debt roll-up), `agent-prime` / `onboarding` (the FSD
preset, rules generation, the role overlays), `site-layer`, `site-graph-viewer`, `site-graph-edge`,
`site-node-card`, `site-filter-graph` (the viewer), the adopter fixtures and the CI matrix.

## Axes

> **Derived by:** six `beadloom impact --section` runs (Explore, 2026-10-08), condensed in `axes.md`; the JavaScript side is not derivable by `beadloom impact` and was read by file.

| Axis | Node | In scope | Why |
|---|---|---|---|
| co-writers | agent-prime, cli-commands, doc-generator, graph-layout, graph-loader, reindex | graph-loader yes (D1); agent-prime yes (D4); doc-generator yes (D1: a skeleton for a service kind); reindex yes (D2: rules index); cli-commands yes (D7 warning); graph-layout no | writers of graph files; the ones the slices change |
| callers | site-generation | yes | D2, D7, D8 |
| callers | ai-techwriter, scope-check, wave-plan | no | read the graph; nothing changes for them |
| callers | reindex (`test_index.py`) | no | card_activity caller only |
| branches | site-generation (`_declared_layer_rule`, `_layer_view`, `_node_dict`, `source_url`, `card_fields`) | yes | D2, D7, D8 |
| branches | onboarding (`detect_preset`, `classify_dir`), agent-prime (`generate_rules`, `bootstrap_project`) | yes | D4 |
| JS (by file) | site-graph-viewer, site-layer, site-graph-edge, site-node-card, site-filter-graph | yes | D2, D3, D8 |
| kind `site` readers | graph-loader, rule-engine (`types.py`), site-generation (pages, nav, view, landscape), doc-generator | yes | D1 |

## Proposed Solution

### D1 — `site` is an alias of `service` (S1)

`graph/loader.py:466` normalises the kind through `KIND_ALIASES = {"site": "service"}` (the table
beside `VALID_NODE_KINDS`, `types.py:21`), so every reader of `nodes.kind` — rules, pages, nav,
the view, the landscape, the doc skeleton, the impact boundary — sees `service`; the alias is
reported as an info line. This repository's graph: `vitepress-site.yml` becomes `kind: service`,
`tags: [layer-service]` (as `tui.yml`); the `part_of beadloom`, `consumes` and `produces` edges
already exist. Expected: no new `architecture-layers` finding (the slices share the tagged
container; verify with `lint`). *Rejected:* an alias at each of six readers.

### D2 — every layer rule in the data file, additively (S1)

`architecture_view.py` writes every `layers` rule: a new top-level `layer_rules: [{name,
scope, edge_kind, layers: [{name, rank, tag, token}]}]` and per node `layer_rule` and
`layer_rule_rank`. The existing `layers`, `layer_order`, `layer`, `layer_rank` keep today's
meaning (the first rule by name) so schema stays 2 and no v2 reader changes behaviour. A node's
rule: the rule whose tag the node carries, else the nearest `part_of` ancestor's (the walk of
`layers.py:149-183`). A rule's **scope** is derived — the lowest container holding every node
the rule stratifies — and an optional `scope: <ref_id>` key on the rule names it explicitly
(accepted and ignored today, `loader.py:1196`; validated against ref_ids; written to the rules
index; `layer_reach` restricts to the subtree). `token` is the layer's name. `flagged` is the
union over rules.

The viewer keys a layer by `(rule, rank)`: `layers.js` gains the sixth tone (`brand`), the
legend groups layers per rule, the filter offers rule-qualified names, lanes partition siblings
of one rule, the card names the rule. **Layers as boxes at the overview** (proposed, pending the
owner): for a rule with a scope, the overview draws one box per layer inside the scope's box,
derived from the rule — not graph nodes, no `part_of` edge — so an 81-slice frontend reads as
six boxes that open by readability. *Rejected:* a schema 3 with `layer_rank` re-meant — a
meaning change is MAJOR by the declared API.

### D3 — the viewer cut by cohesion, and the rule that keeps it (S2)

From the import graph of the 43 files (brief Q4), ten slices, every one importing downward:

| Slice | Files | Symbols |
|---|---|---|
| `shared/geometry` (spatialIndex, routeIndex, routes, corners, grownBoxes, aggregateRoutes, pillPoints, pillPlaces) | 8 | 49 |
| `shared/canvas-marks` (canvasMarks, overlayCanvas) | 2 | 11 |
| `shared/bundling` (bundleDrawing, buses, joins, trunks, headRuns, bundles) | 6 | 53 |
| `shared/grid-routing` (overviewGrid, overviewRoutes) | 2 | 28 |
| `shared/map-levels` (levels, mapMarks, loopLines; `GEOMETRY`, `drawnSizeOf`, `rimOf`, `OWN_LINE` move here) | 3 | 48 |
| `entities/graph-edge` (+ heads, lineMarks, edgePalette) | +3 | +29 |
| `features/follow-edge` (followedOverlay, sharedLines) | 2 | 16 |
| `features/overview-map` (overviewPlan, mapTitles, aggregateElements, mapExtras; `FIT_*` moved to shared) | 4 | 18 |
| `features/edge-pills` (pillOverlay) | 1 | 3 |
| `widgets/graph-viewer` (index, GraphViewer.vue, useGraphCanvas, canvasMap, canvasLayout, testHandle, modes, viewerKeys, usePanelId, elements, stylesheet, nodeCorners) | 12 | 66 |

**Steiger on our own scaffold** (owner, 2026-10-08): `@feature-sliced/steiger` with its
`recommended` set is added to the scaffold's `package.json` (`npm run lint:fsd` over
`.vitepress/theme`), green after the cut — the file-level proof that the ten slices are FSD —
and it runs where `ruff` runs: in the CI `site-build` job and in the STACK completion commands,
with the Gate's verdict naming it among what the Gate did not run (the Gate judges graph and
documents; the style linters are the suite's). The FSD preset writes the same `lint:fsd` script
for an adopter whose project has no Steiger yet.

Four moves make the layering clean: `GEOMETRY`/`drawnSizeOf`/`rimOf` out of `stylesheet.js`,
`FIT_*` out of `navigate-graph`, `OWN_LINE` out of `aggregateElements`, `RING_TONES` out of
`impact-view` (a widget file imports a feature today). Each slice is a graph node (`component`,
its FSD tag, source its directory); `shared` segments are `part_of site-shared` (tagged
`fsd-shared`) so same-layer peers are legal under `site-fsd-layers` (the tagged-container rule,
`layers.py:225`). Playwright is unchanged in count; the test-handle dump over 9 views is
byte-identical before and after (the method of btkd.17).

**The cohesion rule.** FSD gives shape, not numbers: a `check` rule per FSD tag (`for: {kind:
component, tag: fsd-widgets}`, `max_symbols`) — the matcher gains a `tag_prefix:` so one rule
covers `fsd-*` (new, optional key) — calibrated on this repository after the cut (the widget at
66 → limit 80 for widgets, 60 for the rest, re-measured by S2 and stated in `rules.yml`); the
shape rule (`slice_shape`: a slice's top-level directories are among `ui model lib api config`
plus its `index`) is a new rule type in S3 with the other FSD rules. **The roles:** the `fsd`
overlay's mapping becomes slice → `component` tagged with its layer, `part_of` the frontend
service; `shared` and `app` hold segments as components; the cohesion rule and the public-API
rule are stated in `dev`, `review`, `explore`; the `ddd` overlay gains the same cohesion
paragraph for Python packages (neither overlay states it today).

### D4 — `init` for FSD (S3)

`presets.py`: an `fsd` check before every other (and before the mobile → MONOLITH short-circuit):
`{app, pages, widgets, features, entities, shared}` at the root or under `src/`, at least three
present. The scan: a layer directory is no node; each slice is a `component` tagged
`fsd-<layer>`, `part_of` the frontend service (the root node of a single-app repository, or the
app's node in a monorepo); `app` and `shared` are containers of segment components; **legacy
directories beside the layers (`components`, `hooks`, `stores`, …) become nodes too**, tagged
`fsd-legacy`, outside the layer rule — a graph that ignores half the code lies by omission.
`rules_gen.py` writes the FSD rules: `layers` (six tags, `edge_kind: depends_on`, `scope:` the
frontend service), `slice_public_api` (new rule type over resolved imports: an import whose
resolved target lies under another slice's directory and is not that slice's `index` is a
finding — `fnmatch` cannot express "past index", brief Q5), `slice_shape`, the cohesion
`check`; each with the owner's wording in comments.

### D5 — the resolver (S3, before D4)

`import_resolver.py`: (a) tsconfig `compilerOptions.paths` and `baseUrl` (JSON with comments
tolerated) resolve non-relative specifiers; (b) `imports.aliases:` in `.beadloom/config.yml`
(new key) declares what tsconfig does not carry — Babel `module-resolver`, Vite `resolve.alias`
— read by `init` from `babel.config.js` / `vite.config.*` by a tolerant text scan and written
for the user to confirm; (c) platform-suffix candidates `.ios .android .native .web` before the
plain extension (`:850-856`); (d) `.mjs`/`.cjs` parsed (closes `beadloom-zd4m`); (e) an Expo
module's `expo-module.config.json` yields `uses` edges from the module's TS node to its `ios/`
and `android/` component nodes (Swift/Kotlin already parsed) — the JS ↔ native bridge that no
import carries. Unresolved specifiers stay recorded and counted, as today.

### D6 — two fixtures, shaped like the owner's projects (S3)

`tests/fixtures/site/vue-fsd` (Vite + Pinia + Quasar-like, `.vue` with `<script setup
lang="ts">`, `@/` aliases from tsconfig, FSD with legacy directories beside it) and
`tests/fixtures/site/rn-fsd` (Expo Router `app/`, Expo Modules with `ios/` Swift and `android/`
Kotlin, `.web.tsx` and `.ios.tsx` suffixes, Babel `module-resolver` alias, FSD layers). Both
join `FIXTURES_BY_STACK` and the `site-adopters` matrix (8 legs); the done-criterion is that
`init` writes the nodes, tags and rules — the harness adds nothing (`adopter_portals.py:337-375`
adds layers for the other stacks). Names and content are synthetic; no owner project name
appears.

### D7 — the Source link (S4)

`repository_of` (`repository_link.py:223-245`): after `current_commit_sha`, `git for-each-ref
--contains <sha> refs/remotes`; empty → `pushed: false`, the link's ref becomes the branch's
upstream, else `origin/HEAD`; the data file gains top-level `source_ref: {commit, linked,
pushed}`; the card shows "built from an unpublished commit; links point at <ref>"; `docs site`
warns on stderr beside `_warn_about_the_base`.

### D8 — populations named (S4)

`generate.py:198-226` returns lint totals and the node-less findings; the data file gains
top-level `lint: {errors, warnings, nodes_with_findings, nodeless: [...]}`; the card reads
`Rule findings: none — this project: 0 errors, 70 warnings on 28 nodes`; the project box's card
and the dashboard list the node-less findings. Debt: `architecture_card.py:158-163` adds
`inside: {nodes, score, by_reason}` rolled over `part_of` descendants; the card shows own and
inside. The legend is computed from the canvas: `legendKeysOf` over the elements drawn at the
current level (aggregated lines included, by their style key), not over the data; an aggregated
line of one kind keeps that kind's dash (`stylesheet.js:480-488` drops `line-style: solid` for
one-kind aggregates). A case: at every level, every stroke colour and dash on the canvas has a
legend entry and every entry has a stroke.

### API Changes

All additive (MINOR): `kind: site` accepted as an alias; rule keys `scope:` (layers) and
`tag_prefix:` (matchers); rule types `slice_public_api`, `slice_shape`; config key
`imports.aliases`; data file keys `layer_rules`, `layer_rule`, `layer_rule_rank`, `source_ref`,
`lint`, `debt.inside`; `init` preset `fsd`. The CHANGELOG's next section lists each under Added.

## Alternatives Considered

- **Layer nodes in the graph** (a `part_of` container per layer): rejected in BDL-076 — a
  tagged container makes two widgets importing each other legal; D2 draws layers as boxes
  without nodes instead.
- **One mixed fixture** for Vue and RN: rejected by the owner (two projects, two shapes).
- **Globs for the public-API rule**: `fnmatch` cannot say "past index" (brief Q5); a rule over
  resolved targets is the honest form.
- **Ignoring legacy directories in the FSD preset**, as Steiger's config does: rejected — a
  graph is not a linter; what it does not show, the reader believes absent.

## Risks

- The cut moves 31 files; a behaviour change hides in a moved constant — the byte-identical
  dump over 9 views and the full Playwright suite are the guard.
- The alias scan of `babel.config.js` / `vite.config.ts` is a text scan, not an evaluation —
  `init` writes what it found and says so; the user confirms.
- 81 slices at the overview: the drawn layer boxes depend on the owner's answer to D2's
  question; without them the overview of such a project is the clamped case of ruling 11.

## Open Questions

1. **Layers as drawn boxes at the overview for a scoped rule** (D2) — the coordinator's
   proposal; the owner rules.
