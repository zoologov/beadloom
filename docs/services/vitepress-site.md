# VitePress site — the portal scaffold

The `vitepress-site` node is the portal scaffold the package ships, under
`src/beadloom/site_scaffold/`, with its theme under `src/beadloom/site_scaffold/.vitepress/theme/`.
`beadloom docs site` writes it into the portal directory beside the content it generates, and it
renders that content: the node pages, `architecture.data.json`, `landscape.data.json` and
`dashboard.data.json`. The node consumes the `site-data` contract, and the root service
`beadloom` produces it. How the generator works and how a project publishes its portal are
described in [the VitePress site guide](../guides/vitepress-site.md); this page describes the
scaffold.

The node is a service of its product, with its own runtime, build and tests. Since BDL-080 S1a it
is declared `kind: service`, `part_of` `beadloom` and tagged `layer-service`, so the rules judge
it, its page is under `services/` and `architecture-layers` places its slices through it. The
spelling `kind: site` is still accepted and read as `service` (the
[graph loader](../domains/graph/components/graph-loader/DOC.md)).

Since BDL-076 B1 the scaffold is package data, so every project gets the same theme from the
installed beadloom, and `site/` in this repository is output only: `/site/` is ignored, and
`docs site --out site` writes this repository's portal the way it writes an adopter's.

## The pages it publishes

`docs site` ([site generation](../domains/application/features/site-generation/SPEC.md)) writes
the pages, in six sidebar sections (`page_map.PAGE_SECTIONS`): the About pages, the dashboard,
the architecture pages, one page per node, the landscape pages, and the project's published
documentation. The scaffold supplies what those pages mount, registered by name in the `app`
layer:

- the architecture page mounts `ArchitectureMap` (`site-architecture-page`), the graph viewer in
  architecture mode with the node card;
- every node page mounts the same `ArchitectureMap` with `focus` set to the node and a depth, so
  it opens on that node's neighbourhood;
- the landscape page mounts `LandscapeMap` (`site-landscape-page`), the viewer in landscape mode;
- the dashboard mounts the panels of `site-dashboard`, among them `PageMap`, which lists the
  pages the run wrote, per section (BDL-080 S4a);
- every page mounts the Mermaid diagram viewer (`site-diagram-viewer`), which adds pan, zoom and
  full screen to each diagram the page rendered, and the footer (`site-powered-by`) at the
  bottom.

The About and documentation pages are Markdown that VitePress renders with the default theme.

## What is scanned

The scaffold lies under `src`, this repository's scan path, so its `.js`, `.mjs` and `.vue` files
are read with the rest of the source. `.vitepress/config.mjs`, `.vitepress/generated.mjs`,
`package.json`, `package-lock.json` and `scripts/` belong to this node through its
`source: src/beadloom/site_scaffold/`.

What the index reads from the theme requires the `languages` extra, which provides the
TypeScript grammar:

- **`.js` files:** functions, `export const` values and imports, including `import()`.
- **`.vue` files:** a `component` symbol named after the file, plus the symbols and imports of
  each `<script>` or `<script setup>` block at their lines in the `.vue` file. The template and
  the style are not read.
- **Relative imports** resolve to the file they name, and so to the slice that owns it: an import
  from one slice's file into another slice's `index.js` is a `depends_on` edge between the two
  slices. Package imports (`vue`, `vitepress`, `cytoscape`) resolve to no node.

Without the `languages` extra, a reindex hashes the theme files and records no symbol and no
import from them. It prints no warning, because the warning fires only when a reindex finds no
symbol at all.

## Layout: Feature-Sliced Design

Since BDL-076 A2 the theme follows Feature-Sliced Design. There are six layers, top to bottom, and
a layer imports only the layers below it. A slice is used only through its public `index.js`, and
it holds `ui`, `model`, `lib` or `api` segments as it needs them. Each slice is its own node
(`component`, tagged with its layer), `part_of` this one, with a short document under
[`vitepress-site/`](vitepress-site/app.md). `app` and `shared` have segments rather than slices:
`app` is one node, and `shared` is the container node `site-shared`, which owns the segments
nobody carved out and holds the five that are nodes of their own (BDL-080 S2a), each `part_of
site-shared` and tagged `fsd-shared`. The theme has twenty-nine such nodes. BDL-080 S2a cut the
viewer into ten slices, eight of them new nodes, so that pieces of work touching disjoint parts of
the viewer can run in parallel on disjoint nodes (RFC D3).

| Layer | Slice (node) | What it is |
|-------|--------------|------------|
| `app` | [`site-app`](vitepress-site/app.md) | The theme: registers the pages and widgets the generated Markdown mounts. |
| `pages` | [`site-architecture-page`](vitepress-site/architecture-page.md) | `ArchitectureMap`: the viewer in architecture mode with the node card, on the architecture page and every node page. |
| `pages` | [`site-landscape-page`](vitepress-site/landscape-page.md) | `LandscapeMap`: the viewer in landscape mode with the service card. |
| `widgets` | [`site-graph-viewer`](vitepress-site/graph-viewer.md) | The viewer core: toolbar, canvas, panel and legend, in two data modes; it composes the slices below into ELK's routes, trunks and buses, the map, the overview's own routing, counts on pills, and followed lines drawn on top. |
| `widgets` | [`site-node-card`](vitepress-site/node-card.md) | The architecture card: everything the data file says about one node. |
| `widgets` | [`site-dashboard`](vitepress-site/dashboard.md) | The dashboard's panels. |
| `widgets` | [`site-diagram-viewer`](vitepress-site/diagram-viewer.md) | Pan, zoom and full screen over Mermaid diagrams. |
| `widgets` | [`site-powered-by`](vitepress-site/powered-by.md) | The footer of every page, "Powered by Beadloom", which `site.powered_by: false` removes. |
| `features` | [`site-filter-graph`](vitepress-site/filter-graph.md) | Which nodes the viewer shows: the architecture's filters and the landscape's. |
| `features` | [`site-select-neighbourhood`](vitepress-site/select-neighbourhood.md) | A selected node's neighbourhood: depth, direction, dim or hide. |
| `features` | [`site-impact-view`](vitepress-site/impact-view.md) | The impact mode: everything that depends on the selected node, and its summary. |
| `features` | [`site-navigate-graph`](vitepress-site/navigate-graph.md) | Pan, zoom, fit and centre; no gesture moves a node. |
| `features` | [`site-fullscreen`](vitepress-site/fullscreen.md) | Full screen with a CSS fallback. |
| `features` | [`site-url-state`](vitepress-site/url-state.md) | A view's state in the query string. |
| `features` | [`site-follow-edge`](vitepress-site/follow-edge.md) | Followed lines drawn again over the canvas, and one arrowhead where lines share their last run. |
| `features` | [`site-overview-map`](vitepress-site/overview-map.md) | The overview's plan on the canvas, the map's titles at its scale, its aggregated and own lines, and what it draws for the pointer and a selection. |
| `features` | [`site-edge-pills`](vitepress-site/edge-pills.md) | The map's counts over the canvas: a line's pill, a closed box's tally, a node's "+N". |
| `entities` | [`site-architecture-data`](vitepress-site/architecture-data.md) | `architecture.data.json` and its schema version. |
| `entities` | [`site-landscape-data`](vitepress-site/landscape-data.md) | `landscape.data.json`, its contracts' health, and which are verified. |
| `entities` | [`site-dashboard-data`](vitepress-site/dashboard-data.md) | `dashboard.data.json`. |
| `entities` | [`site-graph-nodes`](vitepress-site/graph-nodes.md) | A node's status, its risks and its container. |
| `entities` | [`site-graph-edges`](vitepress-site/graph-edges.md) | Edge kinds, their styles, the legend, and which edges a walk follows. |
| `entities` | [`site-layers`](vitepress-site/layers.md) | The declared layers, and their colours. |
| `shared` | [`site-shared`](vitepress-site/shared.md) | The container of the shared segments, and the segments it owns itself: browser checks, JSON loading, tree walks, shell quoting, theme tokens, Cytoscape, the ELK layout in a Web Worker, fresh ids, ECharts and the copy button. |
| `shared` | [`site-shared-geometry`](vitepress-site/shared-geometry.md) | The plane geometry of the drawing: spatial and route indexes, ELK's routes as segments, corner radii, grown boxes, an aggregated line's route, where a pill may stand. |
| `shared` | [`site-shared-canvas-marks`](vitepress-site/shared-canvas-marks.md) | The classes and data a selection and a hover set on the canvas, and a canvas laid over Cytoscape's. |
| `shared` | [`site-shared-bundling`](vitepress-site/shared-bundling.md) | Trunks, buses and joins rewritten from ELK's routes, and the last run lengthened for an arrowhead. |
| `shared` | [`site-shared-grid-routing`](vitepress-site/shared-grid-routing.md) | The overview's own router: a grid of tracks between the top-level boxes, and A* over it. |
| `shared` | [`site-shared-map-levels`](vitepress-site/shared-map-levels.md) | The map's levels, the fit they open past, the marks kept one size on screen, a node's drawn sizes, and loops drawn square. |

This node keeps what belongs to no slice: `theme/index.js`, the file VitePress looks for, which
re-exports the `app` layer; `.vitepress/config.mjs`, which reads the identity and the nav
`docs site` generates (`site.generated.mjs`, `config.generated.mjs`) and sets from them the nav
logo (marked to be drawn in the text's colour when it is drawn in `currentColor`), the header's
repository link with its icon, the footer switch and the favicons the identity names;
`public/brand/beadloom-icon.svg`, Beadloom's square icon, its only mark, which the footer draws
and VitePress copies to the site root (Beadloom's favicon, an SVG and a PNG, is package data
under `beadloom/site_favicon/` that `docs site` writes beside it, because a PNG cannot carry the
scaffold's marker); `.vitepress/generated.mjs`,
whose `importGenerated(url)` loads a generated module as `{}` with a warning when it is not there
yet and throws any other load error; `package.json` (`engines.node: >=22`, every dependency
pinned exactly) with its lockfile; and `scripts/`. The shipped config pre-bundles `mermaid` and
the ELK worker engine for the dev server (`vite.optimizeDeps.include`, BDL-078 `beadloom-stcx`),
because under `vitepress dev` mermaid's `fastdom` default export broke every page with a diagram.
`npm run dev-check` (`scripts/dev-optimize-check.mjs`) starts the dev server, loads a page with a
Mermaid diagram and the architecture page in Chromium, and fails on a page error, so it needs
Playwright's Chromium; a slow test runs it on the eight adopter fixtures (the six claimed stacks
and, since BDL-080 S3d, the Feature-Sliced frontends `vue-fsd` and `rn-fsd`). `npm run lint:fsd` runs
Steiger over `.vitepress/theme` with the configuration in `steiger.config.js` (below). The viewer's dependencies are Cytoscape and
elkjs 0.12, which the viewer calls directly in a Web Worker. BDL-077 removed `cytoscape-elk`,
which carried a nested elkjs 0.9 of its own, and `web-worker`, the one ranged pin, whose only
user was elkjs's entry point under `cytoscape-elk`.

**The layer rule.** `site-fsd-layers` in `.beadloom/_graph/rules.yml` declares the six layers by
the tags `fsd-app` to `fsd-shared`, at `error`, titled `FSD architecture`. Each slice carries its layer as its own tag and no
node stands for a layer, so a dependency between two slices of one layer is reported as a
same-layer crossing, which is FSD's rule that slices of a layer do not know each other. `app` is
one node. The five `shared` segments that are nodes import each other, and that is legal: they
are peers inside one tagged container, `site-shared`, which the rule allows (the tagged-container
predicate, `layers.shares_tagged_ancestor`). The edges it judges are the
relative imports between theme files, which resolve to the files they name. The rule declares no
`scope:`; the portal derives `vitepress-site` as its scope, the lowest container of every slice it
places. Since BDL-080 the portal draws this rule beside `architecture-layers`: the slices are
coloured by their FSD layer, the legend has one group per rule, and `vitepress-site` opens onto
six layer boxes, app, pages, widgets, features, entities and shared, stacked top to bottom
([`site-layers`](vitepress-site/layers.md)). An edge either rule finds against is drawn red.

**The other rules over the slices.** Six `check` rules, `site-fsd-cohesion-app` to
`site-fsd-cohesion-shared` (BDL-080 S2b), hold each layer's nodes to a `max_symbols` signal over
the symbols one slice or segment OWNS: 80 for `widgets`, the layer that composes, and 60 for every
other layer, at `warn`. They were calibrated after the cut and re-measured at `d99dfd0e` over the
twenty-nine components: `site-graph-viewer` owns 65, the most of any widget, and `site-shared-map-levels`
owns 56, the most of any other node. `site-fsd-public-api` (`slice_public_api`, `error`) and
`site-fsd-slice-shape` (`slice_shape`, `warn`) judge the `pages`, `widgets`, `features` and
`entities` slices (BDL-080 S2d): an import into a slice from outside it lands on its `index.js`,
and a slice's top holds only its segments and its `index`. Measured by S2d on this repository: 22
slices with a folder source, 55 imports into a slice from outside it, and no finding from either
rule. Neither declares a `scope:`, because a slice rule does not read one; the `fsd-*` tags,
which only the site's components carry, confine them.

**Steiger.** The graph's rules judge slices and the imports between them; Steiger, the
Feature-Sliced Design linter, judges the files (BDL-080 RFC D3). The scaffold's `package.json`
pins `steiger` and `@feature-sliced/steiger-plugin` exactly as development dependencies, and
its script `lint:fsd` runs `steiger .vitepress/theme`. `steiger.config.js`, shipped to every
portal, takes the plugin's `recommended` set and switches exactly one rule off,
`fsd/insignificant-slice`, by the owner's ruling of 2026-10-09 (S2c), with the reason beside the
switch: the theme is cut so that beads touching disjoint nodes run in parallel, not for reuse, so
a feature only the viewer widget uses is the intended shape. `fsd/inconsistent-naming` asked for
plural `entities` slices, so S2c renamed `graph-edge`, `graph-node` and `layer` to `graph-edges`,
`graph-nodes` and `layers`, with their nodes. Over a portal generated from this tree Steiger
reports "No problems found!" (measured by S2c and S2R). CI runs it in the `site-build` job, step
"Lint the theme's slices (Steiger)", after `npm ci` and before the build, and the GitLab mirror
runs it the same way, so `beadloom ci` names "the FSD linter (`npm run lint:fsd`)" under "Not
run by this gate" ([gate coverage](../domains/application/components/gate-coverage/DOC.md)).

## What the tools show

- **`beadloom ctx <slice>`** lists the slice's symbols: every file of every slice carries a
  `// beadloom:component=<slice>` annotation. A slice annotates all of its files or none, because
  a node with some files annotated keeps sync pairs for those files only (`beadloom-oo4m`). The
  annotations bind the source to this repository's graph and do not ship: `docs site` writes each
  file without its annotation-only lines (`beadloom-ujzb.18`).
- **`beadloom sync-check`** holds each slice's document to that slice's files. A change to a
  script block's symbols is reported as `symbols_changed`, and any other edit as `hash_changed`.
- **`beadloom why <slice>`** follows the `depends_on` edges the imports between slices produce.
- **`beadloom impact`** on a theme file answers only the boundary section, because its code axes
  read Python (`beadloom-j1ke`).

## Browser tests

The Playwright tests live under `src/beadloom/site_scaffold/e2e/` and ship with the scaffold, so a
portal written by `docs site` carries them in its `e2e/`. `.beadloom/config.yml` declares
`src/beadloom/site_scaffold/e2e` as a test root and names the `playwright` pattern group. This
node declares the whole directory, and each spec is also declared in the `tests:` list of the one
slice it drives, which is where it binds: a test file binds to one node, and a node does not
inherit its ancestors' tests. The thirty-three specs bind to eighteen slices, fourteen of them to
`site-graph-viewer`. Eleven of the twenty-nine slices declare no spec, so they report no bound
tests: `site-app`, `site-dashboard-data`, `site-landscape-data`, and the slices the viewer's cut
moved its code into (`site-edge-pills`, `site-follow-edge`, `site-overview-map` and the five
`site-shared-*` segments), whose behaviour the specs of `site-graph-viewer` drive.

The tests drive the built portal: `e2e/support/serve.mjs` runs `vitepress build` and then
`vitepress preview`, and refuses to start before `beadloom docs site` has written the content.
Run them from the portal directory with `npm run test:e2e`, on `Node.js 22` or later, after
`npx playwright install chromium`. The base path is read from the generated
`site.generated.mjs`, or from `BEADLOOM_E2E_BASE`. The tests read the viewer's state through its
test handle, `window.__beadloomViewer`, which exists only under automation.

The helpers under `e2e/support/` compute their answers apart from the viewer's code, so a case
does not ask the viewer to grade itself:

- `viewer.js`: `waitForViewer`, `viewerAfter(page, navigate)` (waits for a handle other than the
  one installed before a client-side move, because VitePress pushes the URL before it loads the
  next page) and `openEveryBox(page)`, which a case that reads every node or edge calls first,
  since the overview draws only the top-level boxes. Since BDL-080 `parentMap(data)` returns the
  drawn containment, the layer boxes of a scoped rule included.
- `layers.js` (BDL-080): the specs' own reading of the layers, apart from the viewer's:
  `layerRulesOf`, `layersOfData`, `layerOfNode`, `layerBoxesOf`, `drawnParentMap`,
  `fileParentMap` (the file's own containment), `withoutLayerRules` (a file without the
  every-rule keys) and `withRuleTitles`.
- `adopterGraph.js`: `adopterSizedGraph(served, { layerRanks })`, a seeded graph of about four
  hundred and fifty nodes and thirteen hundred drawn edges made from the served file's
  declarations, given the served layer ranks or `layerRanks` of them, up to `RANK_POSITIONS`
  (four), and without the every-rule keys (`withoutLayerRules`). Its boxes sit inside one root
  box, and ELK reads no partition inside a box (measured by BDL-080 S1c on elkjs 0.12, see
  [`site-shared`](vitepress-site/shared.md)), so the ranks do not pin the boxes to lanes: the
  edges place them. Every case that runs on it carries the tag `ADOPTER_SIZED`
  (`@adopter-sized`), and `BEADLOOM_E2E_NO_ADOPTER_SIZED=1` leaves those cases out of a run, in
  every project (`playwright.config.js` sets the filter, because a `--grep-invert` on the
  command line filters nothing in `chromium`, which `performance` depends on).
- `routeMetrics.js`: deviation from a computed route, edges through boxes and through their own
  ends, the A2 sharing metric, channels, excess steps, lanes at a distance, collinear pairs, and
  `lastBendMovedBack` (a route whose last bend the head-run pass moved back still counts as
  ELK's). Values a unit apart or closer count as one channel or lane.
- `map.js`: what each level draws, derived from the data file (`treeOf`, `drawnAs`, `levelOf`,
  `budgetLeftOut`, `degreesOf`).
- `look.js`, `heads.js`, `overview.js`, `levels.js`, `counts.js`, `metrics.js` (BDL-078): the
  oracles of the look (drawn colours, legend samples, rounded corners, contrast), of whole
  arrowheads (straight runs, overlap as triangles), of the overview (gaps, segments outside the
  frame, titles and plates), of the levels (sibling rule, outward edges), of the counts a node
  and its box say, and of every PRD criterion measured together.
- `perturbedGraph.js`: `withTwoMoreEdges(data)`, the served graph with two edges more, a third
  graph for the arrowhead and title cases.

`support/bridges.js` and `bridges.spec.js` were removed with the bridges (BDL-078).
- `pointer.js`: drags and long presses on a reachable leaf, and every toolbar button pressed.
- `environment.js`: the environment a timed case runs in, and its bound there (below).

**Timed cases.** `playwright.config.js` declares two projects. `chromium` runs every case but the
timed ones, in parallel. `performance` runs `e2e/performance.spec.js` one case at a time, after
`chromium` has finished, and not at all when a `chromium` case fails: a case timed beside other
browsers would time them as well. Playwright reports cases it did not run as skipped with no
reason, which the adopter suite's skip-reason check reads as an unnamed skip. To run it alone:
`npx playwright test -c e2e --project performance --no-deps`. A bound is stated per environment
(`e2e/support/environment.js`). The environment is `ci` when `CI` is set and `local` otherwise,
and `BEADLOOM_E2E_ENVIRONMENT` names it instead. An environment a case states no bound for fails
the case, naming the ones it states.

| Bound | Asserted in | `local` | `ci` |
|-------|-------------|---------|------|
| Mean interval between canvas drawings while panning, at the fit and at zoom 1, on both graphs | `performance.spec.js` | 25 ms | 33.4 ms |
| First drawing of the adopter-sized graph, median of three openings | `performance.spec.js` | 7,200 ms | 15,000 ms |
| Longest main-thread task from the data file's arrival until the graph is placed | `layout.spec.js` | 500 ms | 2,000 ms |
| Rewriting the adopter-sized graph's routes into trunks and buses, alone, median of three | `performance.spec.js` | 50 ms | 400 ms |
| Planning the overview's routes: this portal / the adopter-sized graph | `performance.spec.js` | 50 / 250 ms | 200 / 1,000 ms |
| A zoom step and a hover, on both graphs (`GESTURE_MS`) | `performance.spec.js` | 60 / 50 ms | 560 / 470 ms |

The `local` bounds were calibrated on an Apple M1 Max in headless Chromium without a GPU, where
the viewer measured 16.7 ms per frame and a first drawing of 5,707 to 5,781 ms
(`beadloom-m6k7.6`). The `ci` bounds are wide on purpose: they catch ELK on the main thread or the
whole graph drawn at the fit, not a 15% slowdown. Most were written before a GitHub runner had
measured them. The longest task's `local` bound and the bundling's `ci` bound are the two set from
a runner's measurement (below). Two structural guards hold the same regressions on any
machine: the whole-graph fit draws only the top-level boxes and at most 100 edges, and the pointer
resting anywhere at the overview lifts the budget for one box at most (`map.spec.js`).

**The longest task** (`beadloom-btkd.22`). On PR #94 the python adopter leg, on a GitHub-hosted
Ubuntu runner, measured a 2,427 ms task, over the `ci` bound, on the adopter-sized graph built from
a portal that declares no layers. That one task drew ELK's layout, measured the whole graph's fit
over all 1,745 elements and planned the overview at the first drawing. On Darwin arm64 (headless
Chromium, no GPU, the case alone) the same viewer took 608 to 615 ms in that task, and 2,478 to
2,495 ms with the page's processor slowed four times, so the runner ran this work about four times
slower. The `local` bound is the `ci` bound over that factor, 500 ms, so a task the runner would
hold too long fails on the machine the change is made on. Against it the viewer before the fix
measured 603, 607 and 626 ms. The fix measures the fit only when no plan gives the scale, gives
the page a turn between drawing the layout and making the map, and draws no Cytoscape frame of
the hidden graph meanwhile ([the viewer's page](vitepress-site/graph-viewer.md), Layout). After it
the case measured 299 to 300 ms on that machine and 232 to 234 ms on this portal. Slowed four
times, the work is two tasks of 460 to 471 ms and 1,244 to 1,265 ms. These figures after the fix
were taken on Darwin arm64, not on a runner.

The overview's planning, zoom-step and hover bounds came with BDL-078. Measured at `6b77893c`
on Darwin arm64 (`beadloom-btkd.15`): planning 15.1 ms here and 133.1 ms at adopter size, a zoom
step 45.0 / 45.8 ms, a hover 29.3 / 32.1 ms. The `ci` gesture bounds (560 and 470 ms, about nine
times local) were not measured on a runner when they were set; the bundling's `ci` bound is the
one taken from a runner's measurement. The bundling case moved from `bundles.spec.js` to
`performance.spec.js`, where it runs alone.

The bundling's bound is the one `ci` bound set from a runner's measurement (`beadloom-m6k7.7`).
The bundling took 36 to 39 ms on the M1 Max and 186.8 ms on a GitHub-hosted Ubuntu runner with
two Playwright workers. On the M1 Max with the page's processor slowed four times it took 157 to
161 ms, and slowed five times 196 to 205 ms, so the runner ran it about 4.7 times slower. The
`ci` bound of 400 ms is about twice the runner's measurement. Both bounds still catch the bundling
without its indexes, which took 100 to 230 ms on the M1 Max (`shared/geometry/spatialIndex.js`).

**Any project's graph** (`beadloom-ujzb.17`, `.20`). A case chooses its subject from the data the
portal serves, never by a node id of this repository. A case written about a shape the served
graph does not hold, such as two declared layers, a domain two levels deep or a contract between
two services, calls `requireShape` (`e2e/support/shape.js`) and is skipped with the reason
`this portal's graph lacks what the case needs: <shape>`. With `BEADLOOM_E2E_NO_SKIP=1` such a
case fails instead, naming the shape. No case skips in any other way, which a self-check holds.
Measured on the six adopter fixtures under `tests/fixtures/site/` when the shape skips were
introduced (`beadloom-ujzb.17`, on macOS with `Node.js 22`), all 101 cases ran or skipped by
shape: python 75 passed and 26 skipped, go 88 and 13, typescript 94 and 7, java 78 and 23, kotlin
74 and 27, swift 74 and 27.

**In CI.** The advisory `site-e2e` job runs the suite on this repository's portal after
`site-build`, with `BEADLOOM_E2E_NO_SKIP=1`, so every case runs here, under the `ci` bounds. At
`6b77893c` the suite held 294 cases in the `chromium` project and 10 in `performance`, measured
locally on Darwin arm64 (`beadloom-btkd.15`). On PR #94 (head `038305af`, job 113056037571,
a GitHub-hosted Ubuntu runner, two workers) it ran 318 cases, 308 in `chromium` and 10 in
`performance`: 318 passed and none skipped, in 25.4 minutes. It is not a required check. The
`site-adopters` workflow builds the eight fixtures and runs the suite on each, on pull requests
that change what it tests, weekly on `main` and on demand. It runs in nine legs, one per fixture
and one for the slow tests that build a project of their own (`projects`), reported as the check
runs `site-adopters (python)`, `(go)`, `(typescript)`, `(java)`, `(kotlin)`, `(swift)`,
`(vue-fsd)`, `(rn-fsd)` and `(projects)`; none is a required check. `BEADLOOM_SLOW_PART` names a
leg's part (`beadloom-m6k7.7`). Before the legs were split, the six suites of that time ran one
after another, took about 14 minutes each on the runner, and the job was cancelled at its
60-minute timeout during the third. The cases tagged `@adopter-sized` run on the first stack of
each count of declared layers (python, go, typescript, and since BDL-080 S3d `vue-fsd`, the first
with the six FSD layers `init` writes) and are left out on java, kotlin and swift, which declare
none, like python, and on `rn-fsd`, which declares as many as `vue-fsd`; each would draw the same
graph. At `8dbe844c` the shipped suite was not green on the two FSD portals: S3T measured 7
failing cases on `vue-fsd` and 17 on `rn-fsd` (macOS, `Node.js 22`), viewer layout and
selection cases that S4f (`beadloom-af99.13`) owns. What it tests is its
`paths:` filter, and a self-check holds that filter to every file the slow tests read and every
`src/beadloom` file their `init`, `reindex` and `docs site` steps enter, traced on each fixture in
a fresh interpreter (`beadloom-ujzb.24`).
