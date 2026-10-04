# RFC: BDL-077 — The viewer draws edges like a classic diagram

> **Status:** Approved
> **Created:** 2026-10-03

---

## Overview

The viewer stops drawing Cytoscape's centre-to-centre curves and draws the orthogonal routes ELK
already computes, around every box. On top of those routes it adds three things, all derived from
one ELK layout so that nothing moves: a map-like overview (top-level boxes with one aggregated edge
per pair, opening as the user zooms in), a trunk-and-bus drawing that removes the staircase fans,
and bridges on highlighted edges. Arrange (dragging boxes) is removed, ELK runs in a worker and is
called directly, and the data file does not change.

Every choice below was measured in three probes (`RND.md`): path A/B (renderer), the map probe and
the hub probe, on this repository's graph (130 nodes, 453 drawn edges) and an adopter-sized one
(400–445 nodes, 1,300 edges, hubs up to degree 239).

## Motivation

### Problem

Measured on this repository's graph today: 232 of 453 edges pass through a box they do not connect;
22 edges are more than half shared with another (BDL-076 A2 metric); 9,407 crossings; `cli-commands`
fans its 70 edges into a 36-step staircase, and 41 nodes have more than 5 steps; at the whole-graph
fit the overview is an unreadable cloud and costs 27 ms per frame here and 125 ms at adopter size.

### Solution

| PRD story | What answers it | Measured |
|---|---|---|
| US-1 edges around boxes | ELK's orthogonal sections drawn exactly in Cytoscape | through-box 232 → 0 (except the loops of ruling 2); indistinct 22 → 0 |
| US-2 map overview | one layout, levels derived from it; aggregated routes taken from member routes; unordered pairs, weak edges hidden over a budget | 453 → 37 drawn edges at the overview (≤ 100 at adopter size), box displacement 0 at every level, overview frame 27 → 17 ms (125 → 17 ms at adopter size) |
| US-3 bridges | an overlay on highlighted edges only | finding 29 ms / 208 ms for the whole graph; a highlight set is a small fraction |
| US-4 modes keep working | filters and hide need no re-route; selection opens what it needs | 3.9 ms / 8.9 ms to open a selection's boxes |
| US-5 no staircase | trunk + bus post-processed from ELK's sections | `cli-commands` steps 36 → 1, lanes 70 → 10; excess steps over the graph 403 → 76; no node moves |
| US-6 responsive | ELK in a Web Worker | today 0.5 s / 2.7 s on the main thread |

## Technical Context

### Constraints

- The viewer is JavaScript and Vue 3 in the shipped scaffold (`src/beadloom/site_scaffold/.vitepress/theme/**`),
  laid out by Feature-Sliced Design; each slice is a graph node judged by `site-fsd-layers`.
- Pinned exact versions; Cytoscape 3.34.1 stays; elkjs 0.12.0 is called directly and `cytoscape-elk`
  is removed. 0.9.3 (today's nested copy) and 0.12 produce the same layout; only the coordinate
  convention differs (0.12 honours `elk.json.shapeCoords/edgeCoords: ROOT`).
- Cytoscape takes literal colours only; theme tokens are resolved at runtime.
- The browser never queries the index; the data file stays schema 2 with every v1 key. Nothing in
  this work item needs a new key: aggregation and levels are computed from `edges` and `part_of`.
- The 101 browser cases read state through `window.__beadloomViewer`; they assert state, not pixels.
- No project vocabulary hard-coded; the same canvas serves the landscape mode.
- CI has no GPU: frame bounds are stated per environment.

### Affected Areas

The viewer only. The Python generator is reached by the derivation but needs no change, because the
data file already carries everything the viewer needs (see the Axes rulings).

## Axes

> **Derived by:** `beadloom impact src/beadloom/application/site/architecture_view.py` over `src/beadloom` (full output and Supplement A in `axes.md`)
> **Seed:** `each_graph_file` (`reads-a-yaml-directory`), `write_yaml_atomic` (`serialises-yaml`), rule `reaches-an-effect-sink`
> **Unresolved:** 5 name-defined-more-than-once, 1 node-owns-unread-files, 16 unresolved-terminator-name; the JSON data file's write and the JavaScript viewer are not read by `beadloom impact`

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | agent-prime | 4 — `onboarding/scanner/bootstrap.py:52` | none | no | writes graph YAML; the viewer change does not touch the graph |
| co-writers | cli-commands | 4 — `services/commands/index_ops.py:229` | none | no | same; no CLI change |
| co-writers | doc-generator | 2 — `onboarding/doc_generator.py:29` | none | no | same |
| co-writers | graph-layout | 1 — `onboarding/graph_layout.py:185` | none | no | lays out YAML files, not the viewer |
| co-writers | graph-loader | 1 — `graph/loader.py:297` | none | no | reads the graph; unchanged |
| co-writers | reindex | 1 — `application/reindex/indexing.py:40` | none | no | unchanged |
| callers | ai-techwriter | 1 — `ai_agents/ai_techwriter/runner.py:110` | 2 — `provision-runner.sh` | no | reaches the seed through YAML, not through the viewer; the shell script is its runner |
| callers | scope-check | 1 — `doc_sync/scope_check.py:262` | none | no | unchanged |
| callers | site-generation | 4 — `application/site/generate.py:514` | none | no | the data file needs no new key: aggregation and levels are computed in the browser from `edges` and `part_of`; it stays an owner of the scaffold the viewer ships in (Supplement rows) |
| callers | wave-plan | 1 — `application/waves/scope.py:127` | none | no | unchanged |
| branches | site-generation | 23 functions of `architecture_view.py` | none | no | no data-file change (as above) |
| branches | ai-techwriter, wave-plan, scope-check | from a caller's seat | as above | no | unchanged |

**Supplement A (the viewer; `axes.md` lists every site and line):**

| Node | Sites | In scope | Why |
|---|---|---|---|
| site-shared | `shared/cytoscape/load.js`, `layout.js`, `index.js` | **yes** | ELK called directly in a worker; `cytoscape-elk` removed |
| site-graph-viewer | `useGraphCanvas.js`, `stylesheet.js`, `elements.js`, `GraphViewer.vue`, `testHandle.js`, `modes.js` | **yes** | routes, bundles, map levels, bridges overlay, new test-handle readers |
| site-navigate-graph | `useGraphNavigation.js`, `NavigationControls.vue` | **yes** | Arrange removed |
| site-select-neighbourhood | `neighbourhood.js` | **yes** | a walk opens the boxes it needs and feeds the bridge set |
| site-impact-view | `impact.js`, `rings.js` | **yes** | same, for impact |
| site-filter-graph | `visibleIds.js` | **yes** | filters compose with levels (a filtered box stays collapsible) |
| site-url-state | `useUrlState.js` | **yes** | the map level is not URL state, but focus must open its boxes on load |
| site-graph-edge | `edgeKinds.js`, `adjacency.js` | **yes** | aggregated-edge style and member counts |
| site-architecture-page, site-landscape-page | `ArchitectureMap.vue`, `LandscapeMap.vue` | **yes** | the same canvas; the landscape gets routes and bridges, no levels (no containers) |
| site-architecture-data | `useArchitectureData.js` | no | schema unchanged |
| vitepress-site | `package.json`, lockfile, `e2e/**`, docs | **yes** | dependency change; Arrange cases removed; new cases |
| site-generation | `architecture_view.py`, its tests | no | no data-file change |

Kept: 11 viewer nodes plus `vitepress-site`; no Python node. Full flow.

## Proposed Solution

### Approach

**D1. ELK in a worker, called directly.** `shared/elk` builds the ELK graph from the data file's nodes,
compounds and drawn edges (the options the viewer uses today: layered, orthogonal routing,
`INCLUDE_CHILDREN`, layer partitions), runs elkjs 0.12 in a Web Worker, and returns positions,
compound boxes and each edge's sections in root coordinates (`shapeCoords`/`edgeCoords: ROOT`). The
page shows a "laying out" state meanwhile and stays responsive. `cytoscape-elk` is removed, which
also removes the nested elkjs 0.9.3 (`beadloom-f2we`). The result is cached per data file in memory
for level switches and mode changes.

**D2. Routes drawn exactly.** Each routed edge gets `curve-style: round-segments` (rounded corners),
`edge-distances: endpoints`, explicit source/target endpoints and per-edge `segment-weights` /
`segment-distances` computed from its sections (path A: within 0.05 units of ELK's here). Every
compound gets `width`/`height` from ELK's box (not only collapsed ones — otherwise a hidden box
walks by up to 244 units) and `compound-sizing-wrt-labels: exclude`. Edges from a node to its own
container stay Cytoscape loops (ruling 2).

**D3. Trunk and bus (the staircase).** A pure post-process over ELK's sections, before drawing:
- **Bus** on every node: the edges leaving one side of a node in one direction start from the middle
  of that side and share the nearest free channel ELK already used in the first gap, then join their
  ELK lanes.
- **Trunk** on nodes with ≥ 20 drawn edges: edges to the same top-level box share one member's route,
  stopping 8 units short of the box border, where a distribution line runs along the border (moved
  6 units out when occupied or blocked); each edge drops in where ELK had it enter.
- **Hub-to-hub** edges ride the source hub's outgoing trunk and may also join the target's incoming trunk (an edge in two trunks), provided the shared route runs along no edge that does not end at the hub; an incoming trunk leaves out an edge whose busy source would lose its lane. *(Changed by `beadloom-m6k7.4`: the source-only rule could not meet the owner's bound.)*
- **Joins:** an edge left in a lane of its own rides its box's main lane out past 150 units, then turns back to its own route.
- **Fallback:** an edge keeps its own ELK route wherever the new segment would cross a box or run
  along an unrelated edge.
- **Junction dots** where two or more routes actually branch, recomputed for the visible set.
Measured: `cli-commands` 70 lanes / 36 steps → 10 lanes / 1 step; excess steps over the graph 403 → 76;
crossings +10.6%; 8 ms here, 100–230 ms at adopter size before a spatial index (budget: ≤ 50 ms
after it).

**D4. The map (levels).** One ELK layout; levels are views of it.
- **Collapsed box:** the same Cytoscape compound, its size locked from ELK, children removed with
  `cy.remove` and restored with `cy.restore` (hiding by `display: none` kept Cytoscape spending
  ~95 ms per frame on hidden elements at adopter size).
- **Aggregated edges:** one per **unordered** pair of drawn boxes (owner, Q1), drawn when at least
  one end is collapsed; arrowheads at each end that has members arriving, and the count split by
  direction in the label and on hover. Its route is the medoid of its members' ELK routes clipped
  from where they leave one box to where they enter the other (1,065 clips, 0 failed; 3–6 ms,
  cached per pair); solid line, width by member count. An edge is drawn as itself only when both
  its ends are drawn as themselves.
- **Weak edges hidden only over a budget (owner, Q1):** when a level would draw more than **100**
  aggregated edges, the aggregated edges below the smallest weight that brings the count within
  100 are not drawn; each box shows how many of its aggregated edges are hidden ("+N"), and hovering
  or selecting a box draws all of its edges. On this repository's graph the budget is never reached
  (the overview draws 37); at adopter size (333 unordered pairs) weight ≥ 3 gives 96.
- **Open-what-is-in-view rule:** a box opens when its parent is open, it overlaps the viewport, the
  zoom is past 1.3× the fit, and its larger side is at least **N = 600 px** on screen; it closes below
  0.8 N. Rule evaluation ≤ 0.2 ms per frame; a switch 2–6 ms.
- **Selection opens its own ancestors** (search, URL focus, card link, node page). Neighbourhood and
  impact open the boxes of their whole walk. A hub's selection alone does not open its neighbours'
  boxes: its edges stay aggregated per box (measured: opening neighbours for `cli-commands` falls
  back to 406 edges).
- **Map marks keep a constant screen size** (aggregated edge width, count label, collapsed box title),
  restyled at zoom steps of ×1.25 (≤ 1.8 ms). A box too small for its title shows the title outside it.
- **Loops onto the root wrapper** are hidden at the overview (4 here) and drawn at full detail.
Measured: overview 37 drawn edges (35 aggregated carrying 277, plus 2 originals); A2 0.001 / 0;
52 crossings; frame 16.7 ms here (27 today), 16.5 ms at adopter size (125 today). Box displacement
0 at every level and switch order.

**D5. Bridges on highlighted edges.** An overlay canvas above Cytoscape, redrawn on its `render`
event, draws a half-circle hop where a highlighted edge (hover, neighbourhood, impact walk) crosses
another drawn edge; crossings between members of one bundle (junctions) are not bridges. Colours
come from the resolved theme tokens; nothing is drawn when no edge is highlighted.

**D6. Arrange removed.** `autoungrabify` stays on for good; the Arrange button, `toggleArrange`,
`applyArrangePolicy` and their cases go. Routes therefore never go stale.

**D7. Landscape mode** uses the same canvas: routes, bus/trunk and bridges apply; it has no
containers, so no levels.

### The PRD criteria this RFC restates (owner, Q3)

- **A2, "no indistinct edge":** an edge in a trunk shares its trunk with its siblings by design
  (58 here). The criterion counts sharing only with an edge that has **no common endpoint**. Under
  that reading: 0.020 / 0 here and 0.004 / 0 at adopter size, as good as plain routes.
- **"Bounded width" for a hub:** the fan's pixel width barely moves (876 → 738), because trunk lanes
  sit where ELK placed them; only a re-layout narrows it, which the PRD excludes. The measurable bound
  is: a node with ≥ 20 drawn edges leaves each side in **one channel per direction**, and its edges
  cross a line 150 units from it in **no more lanes than the number of top-level boxes they lead to,
  plus one per edge into its own box** (`cli-commands`: ≤ 11, measured 10, today 70).

### Changes

| File / Module | Change |
|---|---|
| `shared/elk/` (new, replaces `shared/cytoscape/layout.js` ELK use) | ELK graph builder, worker, result in root coordinates, cache |
| `shared/cytoscape/load.js`, `index.js` | load Cytoscape only; no `cytoscape-elk` |
| `widgets/graph-viewer/lib/routes.js` (new) | sections → segment weights/distances; compound sizes |
| `widgets/graph-viewer/lib/bundles.js` (new) | trunk + bus + fallback + junctions, with a spatial index |
| `widgets/graph-viewer/lib/levels.js` (new) | the level rule, aggregation, medoid routes, remove/restore |
| `widgets/graph-viewer/lib/bridges.js` (new) + overlay in `GraphViewer.vue` | crossing finder for the highlight set, drawing |
| `widgets/graph-viewer/lib/stylesheet.js`, `elements.js` | routed edge rule, aggregated edge and collapsed box styles, map-mark sizing |
| `widgets/graph-viewer/model/useGraphCanvas.js` | worker layout, apply routes, level switching, `showOnly` with levels |
| `widgets/graph-viewer/model/testHandle.js` | readers: `edgeRoutes()`, `level()`, `openBoxes()`, `aggregatedEdges()`, `bridges()`, `junctions()` |
| `features/navigate-graph/**` | Arrange removed |
| `features/select-neighbourhood`, `impact-view`, `url-state` | open the boxes a selection or walk needs |
| `features/filter-graph` | filters compose with levels |
| `entities/graph-edge` | aggregated edge kind and member counts |
| `package.json`, lockfile | `elkjs` 0.12.0 direct; `cytoscape-elk` removed |
| `e2e/**` | Arrange cases removed; new cases per story; metric checks |
| `tests/self_check/docs/test_site_viz_deps.py` | dependency list and `layout.js` assertions follow the change |
| `docs/services/vitepress-site/*`, `docs/guides/vitepress-site.md` | routes, map, bridges, no Arrange |

### API Changes

No Python or CLI change. The viewer's test handle gains the readers above; `positions`, walk and edge
readers keep their meaning. The data file is unchanged (schema 2).

### How the goals are checked in the suite

A Playwright metrics case reads `edgeRoutes()` on this repository's portal and on one adopter fixture
and computes: through-box count, A2 against edges with no common endpoint, steps and lanes per node
with ≥ 20 drawn edges, overview drawn-edge count, box displacement across levels (0). The pure
functions (routes, bundles, levels, bridges) are also driven from the same case with crafted inputs.

## Alternatives Considered

### Replace Cytoscape (JointJS core, maxGraph, own SVG)
Measured in path B. JointJS's manhattan router gave up on 59% of edges and `jumpover` costs 0.6–4.5 s
per selection; maxGraph redraws on every pan (186 ms at adopter size); own SVG measured best but means
writing pan, zoom, pinch, hover and hit-testing ourselves. Rejected now; own SVG stays the fallback if
Cytoscape blocks a goal.

### Re-run ELK per level on the collapsed graph
Measured: boxes move by up to 6,940 units (30,264 at adopter size); every interactive option set
either moved every box, threw with `INCLUDE_CHILDREN`, or timed out. Rejected.

### Our own orthogonal router for aggregated edges
Measured: 1.9 s at adopter size for the overview, 20 s at the next level, segments nudged into boxes.
Rejected.

### `cytoscape-expand-collapse`
Unmaintained (its README says so), shrinks boxes (moves up to 1,885 units), bezier meta-edges.
Rejected; its remove/restore idea is kept.

### ELK-side fixes for the staircase
`mergeEdges`, free or three-sided ports, port alignment, priorities, partitions did nothing or deepened
the staircase; hyperedge ports collapse the fan but move every node and add 13–56% crossings. Rejected
by the PRD's non-goal on layout changes.

### Bridges on every crossing
Measured: 6,295 / 52,498 crossings; up to 500 bridges per screen at zoom 1 read as texture. Rejected by
ruling 3.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Large adopter overview still dense (33 top-level boxes → 443 aggregated edges at adopter size) | High | Med | unordered pairs (333) and the weak-edge budget of 100 (Q1) |
| Shared trunk segments: dimmed edges darken on a trunk; hit-testing a trunk is ambiguous | Med | Med | draw a trunk once per bundle for hit-testing; dim rules per bundle; hover selects the bundle and lists members |
| Junction dots wrong after filter/hide | Med | Med | recompute for the visible set; a metric case for stray/missing dots |
| Bundle post-process too slow at adopter size | Med | Low | spatial index; budget ≤ 50 ms; worker if needed |
| ELK quirks (compound box sizes, loops, an upgrade shifting geometry) | Med | Med | lock box sizes from ELK; exact pin; geometry cases in the suite |
| Frame time without a GPU (CI) 2–3× slower at adopter size | High | Low | per-environment bounds; the overview is cheaper than today's fit |
| Small boxes' titles at the overview | Med | Low | title outside the box below a size |
| Losing Arrange surprises a user who relied on it | Low | Low | owner's ruling; noted in the guide |

## Open Questions

| # | Question | Decision |
|---|---|---|
| Q1 | A large adopter's overview (33 top-level boxes) still draws 443 aggregated edges. | Decided (owner, 2026-10-03): unordered pairs, and weak aggregated edges hidden with a count on the box; the coordinator's refinement — hide only above a budget of 100 drawn aggregated edges, at the smallest weight that fits, and draw all of a box's edges on hover or selection — see D4. |
| Q2 | N for the open rule. | Decided (owner): 600 px. |
| Q3 | The restated A2 and hub-bound criteria replace the PRD's wording. | Decided (owner): yes; the PRD's Goals are amended. |
| Q4 | Loops onto the root wrapper hidden at the overview, drawn at full detail. | Decided (owner): yes. |
