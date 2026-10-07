# RFC: BDL-078 — The viewer looks finished, and five defects are fixed

> **Status:** Approved
> **Created:** 2026-10-05
> **Approval:** delegated by the owner on 2026-10-05 ("Утверждаю, дальше веди сам") after the PRD and its fourteen rulings.

---

## Overview

Three probes (`RND.md`) fixed the design; this RFC turns the owner's rulings into changes. The
viewer keeps BDL-077's single ELK layout, routes and bundles, and changes how things are drawn and
when: one thin line weight, no bridges, no junction dots, no direction gradient, a followed edge on
top with a casing, an overview with its own routing that is calm by default, an open box that keeps
its outward edges aggregated, boxes that open when their nodes are readable, and a zoom to the
selection. The activity metric counts changed lines with levels relative to the project. Five open
defects are fixed alongside.

## Motivation

### Problem
See the PRD: unreadable overview (12 overlapping arrowhead pairs, lanes 0.8 px apart, 13 of 34
lines under titles), broken arrowheads on thick lines, bridges and dots that read as bugs, about
100 lines when one box opens, an activity line that says "cold" on 85 of 130 nodes, and five
defects.

### Solution
| PRD item | Change | Measured in the probes |
|---|---|---|
| Overview | an overview router between fixed boxes, calm by default | head overlaps 12 → 0, min gap 0.8 → 7.1 px, under titles 13 → 0, 18 ms (100 ms at adopter size) |
| Open box | edges drawn between siblings; outward edges stay aggregated | lines in view 114 → 43, max heads per side 13 → 3, nothing moves on opening |
| Marks | one weight, constant heads, one head per shared run, rounded merges, no dots, no bridges | — |
| Activity | changed lines, relative levels, roll-up | today 85 cold / 33 zero / 9 warm / 0 hot |
| Five defects | one bead each | — |

## Technical Context

### Constraints
- BDL-077's constraints stand: one ELK layout from which everything is derived, boxes never move,
  Cytoscape 3.34.1, elkjs 0.12 in a worker, literal colours, FSD, exact pins, the test handle,
  performance bounds per environment.
- The data file stays schema 2; `activity` keeps `commits_30d` and `level` and may gain keys (the
  allow-list in the contract test is extended deliberately, never author data).
- Everything shipped stays project-neutral; the same canvas serves the landscape.
- Cases removed with a feature (bridges, junction dots, the gradient) are removed with it; no bar
  is lowered elsewhere.

### Affected Areas
The viewer widget (`site-graph-viewer`) carries most of the change and is edited by several beads,
so those run one after another. The Python fixes are in separate nodes.

## Axes

> **Derived by:** six `beadloom impact --section` runs (full output and Supplement A in `axes.md`)
> **Seed / Unresolved:** per section in `axes.md`; the JavaScript viewer is not read by `beadloom impact`

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| branches | import-resolver | `graph/import_resolver.py` (45 functions) | none | **yes** | `beadloom-nh7h`: one import resolves differently in an incremental index; `beadloom-jcng`: manifests are inputs of the files they govern |
| callers | reindex | `application/reindex/full.py:80`, `incremental.py:348`, `enrichment.py:131`, `test_index.py:204` | none | **yes** | the incremental path for nh7h and jcng; activity storage; test binding |
| callers | agent-prime | `onboarding/scanner/import_scan.py:82`, `init_flow.py:47`, `bootstrap.py` | none | **yes** | `beadloom-76mk`: init binds flat Python tests and names the unbound |
| branches | test-mapping | `bind_test_file`, `_subject_stem`, `_module_stem`, … | none | **yes** | 76mk: a flat `tests/test_<module>.py` binds to the module it names |
| callers | test-layout | `context_oracle/test_layout.py:264` (defaults `:94-95`, `:145`) | none | **yes** | 76mk: the default kind folders |
| branches | git-activity | `infrastructure/git_activity.py` | none | **yes** | activity by changed lines, relative levels, roll-up, the window off-by-one |
| callers | site-generation | `application/site/architecture_card.py:147`, `:250`, `architecture_view.py:516`; `scaffold.py:210` | none | **yes** | activity keys in the data file; (scaffold only as the owner of the shipped viewer) |
| callers | debt-report | `application/debt_report/collect.py:159`, `:196` | none | **yes** | reads activity levels (`_count_dormant`) — must keep meaning after the change |
| callers | tui | `tui/data_providers.py:297` | 4 — `tui/styles/app.tcss` | **yes** | shows activity; follows the new levels (the stylesheet names level classes) |
| callers | cli-commands | `services/commands/setup.py:1533`, `query.py:21`, `index_ops.py:229` | none | **yes** | init's output names unbound test files; otherwise unchanged |
| callers | context-builder, mutation-scope | `context_oracle/builder.py:383`, `application/mutation_scope/change.py:243` | none | no | read test bindings; a newly bound flat test only adds bindings, no code change |
| co-writers | doc-generator, graph-layout, graph-loader | write graph YAML | none | no | no graph-file change |

**Supplement A (the viewer; sites in `axes.md`):**

| Node | In scope | Why |
|---|---|---|
| site-graph-viewer | **yes** | every visual change; id-keyed maps (ytcg) |
| site-graph-node, site-shared | **yes** | ytcg: id-keyed plain objects; `shared/elk/geometry.js` |
| site-node-card | **yes** | the activity line; outward "+N" needs no card change |
| site-graph-edge | **yes** | edge colours without the gradient, legend entries |
| site-navigate-graph | **yes** | zoom to the selection |
| site-app, site-diagram-viewer, vitepress-site | **yes** | stcx (`config.mjs`, the dev check); specs; docs |
| site-select-neighbourhood, site-impact-view, site-filter-graph, site-url-state | no | unchanged as in BDL-077 (the logic sits in graph-viewer) |

Kept: more than one node → full flow.

## Proposed Solution

### Approach

**V1. The base look (owner rulings 1–5, 10).**
- One line weight on screen at every zoom and level (about 1.35 px), for every edge kind and state;
  kinds differ by colour and dash, never by width. No source-to-target gradient: solid colours
  (imports neutral, other kinds toned, violation in the danger colour).
- Arrowheads at a constant screen size (`arrow-scale` computed per edge from Cytoscape's formula),
  with a straight final run at least as long as the head; one head where lines share their final
  run into a box or node.
- Bridges are removed: `lib/bridges.js`, `bridgePaint.js`, `model/bridgeOverlay.js`, the test-handle
  readers, the spec and the docs go.
- Junction dots are removed; branches join their trunk as rounded merges on the stroke
  (`lib/junctions.js` keeps only what the merge geometry needs).
- A followed edge (hover, a selection's walk) is drawn above everything it crosses, at full
  strength, with a background casing; casings are drawn in one pass and lines in a second on the
  overlay, so bundle members do not cut slits into each other. The kind label shows on hover only.
- Nodes are cards with a thin layer-tone border and a corner status mark (filled for an error or a
  stale document, a ring for warn-only); containers get a thin solid border, a light tint and a
  header inside; legends follow. Text contrast at WCAG AA in both themes.
- Edges from a node to its own container stay loops (ruling 13).

**V2. The overview (rulings 8, 10).**
- `lib/overviewRoutes.js` (new, pure): aggregated edges between top-level ends are routed on a grid
  of tracks about 8 px apart at the fit scale, boxes and outside titles as obstacles with a margin,
  a straight run into each box, bends, crossings and running beside another line priced; lines
  into one box may share their last run and one arrowhead only when they agree on having a head
  there. A line ends on its box's border; an outside title plate is an obstacle only (the probe's
  "arrows in the air" defect).
- The plan is computed once per filter state and cached; it is deterministic for its input.
  Budget: ≤ 50 ms here, ≤ 250 ms at adopter size locally (probe: 18 / 100 ms), with a CI bound set
  as for bundling.
- Calm by default: aggregated lines are light; hovering or selecting a box brings its lines and
  pills forward and fades the rest; a box large enough shows "in N · out M".
- Counts are pills on an overlay canvas, placed on a free run, never overlapping a box, a title or
  another pill (a pill with no free place is dropped; its count shows on hover); no pill for a
  count of 1.
- Titles of closed boxes and of top-level leaf nodes shrink through 14 / 12.5 / 11 / 10 px, then
  sit outside on a plate with a border.

**V3. Levels (rulings 7, 9, 12, 14).**
- An edge is drawn between siblings at the lowest box that holds both ends, as itself only when
  both ends are those children and neither is a box; everything else stays in its pair's aggregated
  line. A pair between top-level ends keeps the overview plan's route and port whether its boxes
  are open or closed, so opening a box moves nothing.
- A node inside an open box shows a "+N" mark for its outward edges not drawn at rest; hovering or
  selecting it draws them (to a closed box: one line; to an open box: the edge on its ELK route) on
  top with a casing, from the node's bus port, and the box-level line they belong to is not drawn
  twice.
- A box opens when its parent is open, it overlaps the viewport and its nodes are readable: a node
  at least 24 px tall on screen (hysteresis 0.8). This replaces the 600 px rule.
- Selecting a node (click, search, URL focus, card link) zooms and pans to its neighbourhood
  (animated, respecting reduced motion); a node page already opens focused.
- Neighbourhood and impact draw only the walk's edges as themselves, on top.

**F-activity.** `git_activity` counts changed lines (added + deleted, `git log --numstat`) per node
over 30 and 90 days alongside commits; a box rolls up its descendants; the 30-day window is exact.
Levels are relative to the project: among nodes with a change in 30 days, the top tenth is `hot`,
the next three tenths `warm`, the rest `cool`; no change in 30 days but some in 90 is `quiet`;
none in 90 is `dormant`. The data file's `activity` gains `lines_30d`; the card says
"N lines changed in 30 days" with the level, and "no change in 30 days" for `quiet`. `debt-report`
keeps counting `dormant`; the TUI follows the new names.

**Five defects.**
- `beadloom-nh7h`: find why the incremental index resolves `tui`'s import to `graph-reads` and a
  fresh one to `application` (Strategy 1 reads `code_symbols` / `file_index`); make both paths
  resolve identically; a test that builds an index both ways and compares every resolved import.
- `beadloom-jcng`: a manifest (`go.mod`, `go.work`, `Package.swift`, a JVM layout change) is an
  input of every file it governs: an incremental reindex re-resolves those files' imports when only
  the manifest changed; the extractor's root-package shortcut for Go is fixed.
- `beadloom-76mk`: a flat `tests/test_<module>.py` binds to the node owning the module it names (by
  name, then by import), and `init` names the test files it could not bind.
- `beadloom-stcx`: the portal's pages load under `vitepress dev` (mermaid's `fastdom` default
  export — `optimizeDeps` or an equivalent in the shipped config), and the dev check loads a page
  with a diagram and the architecture page instead of only booting.
- `beadloom-ytcg`: every map keyed by a node id is a `Map` or a null-prototype object; a case with
  nodes named `__proto__`, `constructor`, `toString`, `hasOwnProperty`.

### Changes

| File / Module | Change |
|---|---|
| `widgets/graph-viewer/lib/stylesheet.js`, `mapMarks.js`, entities `graph-edge` | one weight, solid colours, constant heads, card nodes, containers, corner status mark |
| `widgets/graph-viewer/lib/bridges.js`, `bridgePaint.js`, `model/bridgeOverlay.js`, `e2e/bridges.spec.js` | removed |
| `widgets/graph-viewer/lib/junctions.js`, `model/bundleOverlay.js`, `lib/bundleDrawing.js` | no dots; rounded merges; followed edges in two passes |
| `widgets/graph-viewer/lib/overviewRoutes.js` (new), `model/pillOverlay.js` (new), `model/canvasMap.js` | the overview plan, pills, calm by default, shared heads |
| `widgets/graph-viewer/lib/levels.js`, `model/canvasMap.js`, `model/useGraphCanvas.js` | sibling rule, "+N", own edges on hover/selection, opening by node readability |
| `features/navigate-graph` | zoom to the selection |
| legends (`EdgeLegend`, `NodeStatusLegend`, `LayerLegend`) | follow the look |
| `widgets/node-card/ui/NodeCard.vue` | the activity line |
| `infrastructure/git_activity.py`, `application/reindex/enrichment.py`, `application/site/architecture_card.py`, `application/debt_report/collect.py`, `tui/**` | activity by changed lines, relative levels, roll-up |
| `graph/import_resolver.py`, `application/reindex/**` | nh7h, jcng |
| `context_oracle/test_layout.py`, test-mapping, `onboarding/scanner/**`, `services/commands/setup.py` | 76mk |
| `site_scaffold/.vitepress/config.mjs`, `scripts/dev-optimize-check.mjs` | stcx |
| `entities/graph-node`, `shared/lib/tree.js`, `shared/elk/geometry.js`, graph-viewer maps | ytcg |
| `e2e/**`, `tests/**`, `docs/**` | cases per rule (seen red first); docs |

### API Changes
- Data file: `activity` gains `lines_30d`; `level` takes the values `hot`, `warm`, `cool`, `quiet`,
  `dormant` (schema stays 2; the viewer shows an unknown level as text).
- Test handle: `bridges()`, `bridgeFrames()`, `junctions()` removed; readers added for the overview
  plan (routes, heads, pills), a node's outward count, and own edges.
- `beadloom init` output: names unbound test files.

### How the goals are checked
Suite cases on this portal and the adopter-sized graph, computed from the handle with an oracle in
`e2e/support/`: head overlaps 0; one head per shared final run; minimum gap between parallel
box-level runs ≥ 5 px at the fit; no line under a title or through a box; one line weight for every
drawn edge; no bridge or dot element; opening a box changes no box-level route or pill; a node in an
open box has no drawn edge leaving the box at rest and exactly its own on hover; a box opens only
when its nodes are ≥ 24 px tall; text contrast; the performance bounds. Python: activity levels on a
fixture repository with a squash-merged history; each defect's test.

## Alternatives Considered

### Tidy the medoid routes (probe V1)
Arrowheads separate, lanes still 0.8 px apart, 13 lines under titles. Rejected.

### Direct curves at the overview (probe V3)
Shortest, but 8 lines through boxes, 9 head overlaps, a hairball at adopter size. Rejected.

### Keep bridges restyled; dots on square joins
Owner's rulings 1 and 2.

### Route every pair with the overview router at every level
650 ms here and 7.9 s at adopter size with one box open. Rejected: only top-level pairs are planned.

### Activity as "merges in 30 days" with retuned thresholds
Still a property of the merge habit; changed lines are not. Owner's ruling 6.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| The overview router is sequential: a filter change re-plans and lines may move | Med | Low | deterministic for its input; cached per filter state |
| Opening by node readability opens many boxes at once on a wide screen | Med | Med | a box must overlap the viewport; measure switch cost; hysteresis |
| Removing bridges and dots removes cases — coverage of "follow one line" must move to the casing rule | Med | Med | cases for draw order and casing replace them |
| Relative activity levels change as the project changes | Low | Low | stated on the card's wording and in the guide |
| Loops at one thin weight dominate an open box | Med | Low | owner looks before merge (ruling 13) |
| CI timings for the new router | Med | Low | per-environment bound, measured on a runner |
| Large change to one widget by several beads | High | Med | serialised beads, each a gate owner with the full suite |

## Open Questions

| # | Question | Decision |
|---|---|---|
| Q1 | The seven look questions and the overview/open-box rules | Decided: the owner's rulings 1–14 in the PRD |
| Q2 | Loops to a node's own container at one weight | Kept (ruling 13); the owner looks before the merge |
