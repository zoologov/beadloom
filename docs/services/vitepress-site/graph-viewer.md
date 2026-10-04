# Graph viewer (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/graph-viewer/`

---

## Overview

The viewer core, `GraphViewer`. Its root element is the viewer's own space: a toolbar, the canvas
and a collapsible panel, with the legend below them. That element is what goes full screen, so the
embedded view and full screen are one UI. In the page the panel lies over the canvas's right edge;
in full screen it sits beside the canvas.

- **Two modes** (`model/modes.js`). One core draws the architecture graph, from
  `architecture.data.json`, and the landscape of contracts between services, from
  `landscape.data.json`. A mode names only what differs: the data file and how it becomes nodes and
  edges, the filters in its slot of the toolbar and the set they show, what its search finds
  (`searched`), and its impact walk. The mode is the page's prop and the URL does not carry it,
  because the two modes are two pages with two different cards.
- **Layout.** ELK lays the graph out once, in a Web Worker (`site-shared`, `shared/elk`), and
  everything the canvas draws is read from that one layout: nodes, box sizes, routes, bundles,
  the map's levels and the bridges. Until ELK answers, a `role=status` note says "Laying out the
  graph…" over a hidden canvas, and the toolbar keeps working. A layout that fails is reported as
  a `role=alert` note naming the error. The canvas stays hidden, because no node has a place, and
  the filter, neighbourhood, impact and navigation controls sit in a disabled `fieldset`. Panel
  and Full screen act on the viewer, not the graph, and stay on.
- **Selection.** A selected node is the start of a walk. In the neighbourhood the walk goes to the
  chosen depth and direction (`site-select-neighbourhood`); with **Impact** on it goes to
  everything that depends on the node, without a limit, by the mode's walk (`site-impact-view`).
  What the walk leaves out is dimmed, or hidden when the reader asks, and the containers of what
  it reached stay. A selection made anywhere but on the canvas, from the URL, the card or the
  impact list, is framed so that the walk is in view, with any closed box that holds part of it.
- **Panel.** It shows what the page puts in its `panel` slot for the selected node and, in impact
  mode, the impact summary above it. A widget does not import another, so the page composes the
  card. Each viewer gets its own panel id (`usePanelId`), so two viewers on one page do not share
  the toolbar's "Panel" button.
- **Navigation.** No node is grabbable and every node is pannable (`panOnNodes()`, called once the
  graph holds its nodes), so a drag anywhere pans, on a node or inside a box. No control moves a
  node: the routes are read from the layout, and a moved node would leave them behind. The
  toolbar zooms, fits and centres, and fitting and centring leave out the part of the canvas the
  open panel covers. Keys, while focus is in the viewer: `+` and `-` zoom, `0` fits, `f` toggles
  full screen, `Esc` clears the selection.
- **Colours.** The stylesheet (`lib/stylesheet.js`) is built from theme tokens resolved to literal
  `rgb(...)` values and rebuilt when VitePress switches between light and dark. A node's border and
  a box's tint are its layer's colour; a status adds the border `NODE_STATUSES` names. On the
  landscape, which has no layers, a node's border is its health. In impact mode a node's fill takes
  its distance ring's tone and a risky node carries a dashed danger outline. A dimmed node is drawn
  at opacity 0.14. A dimmed edge is drawn opaque in its colour faded towards the background by the
  same share: edges drawn along one trunk at opacity 0.14 would add up to about four fifths of full
  strength.
- **Edges.** One line style per kind, a violation red, dashed and thicker, a broken or drifting
  contract as heavy as a violation with its verdict as a badge, a source end lighter than the
  target end, and a label on hover and on the selected node's edges. Every edge is drawn along
  the route ELK computed (below). An edge from a node into a box that holds it is the exception:
  Cytoscape draws it as a loop inside the box, in the `bezier` style (`CURVE_STYLE`).
- **URL state.** The filters, the selection, depth, direction, dim or hide, and the neighbourhood
  or impact view round-trip through the query string (`site-url-state`). The URL overrides the
  props.

### Routes, measured

`model/canvasLayout.js` draws the layout as ELK computed it. Every leaf stands at the centre of
its ELK box. Every box is sized to its ELK box (`lib/routes.js`, `compoundSizeOf`), with compound
padding 0 and `compound-sizing-wrt-labels: exclude`, and it is sized again whenever a filter or a
selection changes which of its children are drawn, so a box keeps its place. Every edge but a
loop follows its ELK route: `curve-style: round-segments` with corners rounded at 6 units
(`ROUTE_CORNER_RADIUS`), its ends and corners given relative to its nodes' centres
(`segmentsOf`), with the arrowhead where the route enters the target's box. ELK's input carries
nothing about the canvas, so the architecture page, a node page and full screen share one layout.
It carries nothing about text either: a leaf's size is the stylesheet's 160 by 44 units plus its
border, never its label (`layoutInputOf`), and ELK sizes every box, so the layout depends on the
data file alone. The geometry in the site-e2e trace of 2026-10-04, taken on a Linux runner, is
identical to that of the same data file laid out on macOS (`beadloom-m6k7.7`), and
`layout.spec.js` holds it with the fonts changed.

The routes replaced Cytoscape's `bezier` curves from one node's centre to the other's in BDL-077.
Measured on this repository's graph in headless Chromium on an Apple M1 Max, with the built
portal at 1400 x 900 (`beadloom-5x4g`, `beadloom-m6k7.5`):

| Measure | `bezier` (before BDL-077) | ELK's routes | Routes with trunks and buses (now) |
|---------|---------------------------|--------------|------------------------------------|
| Edges through a box they do not connect | 232 of 453 | 0 of 434 routed | 0 |
| Mean share of an edge's middle shared | 14.4%, against every edge | 1.8% | 1.5% |
| Edges more than half shared | twenty-two | none | none |
| Excess steps of the fans (every node's steps beyond two) | — | 396 | 7 |

A point of an edge's middle 80% is shared when another edge passes within 4 layout units of it
(the BDL-076 A2 metric). The `bezier` figure counted every other edge, including edges that share
an end. The routes count only edges with no common end, because a trunk's edges share a line by
design. A drawn route lies within 0.005 units of the route computed for it (bound 0.5). On the
adopter-sized graph the browser suite generates (about four hundred and fifty nodes and thirteen
hundred drawn edges) the routes run through no box, share 0.27% on average and leave 111 excess
steps of ELK's 1,419.

### Trunks and buses

ELK gives each edge of a node its own port and channel, so a node with seventy edges leaves its
side in a staircase as wide as the graph. `lib/bundles.js` (`bundleRoutes`) rewrites the routes
after the layout, and no node or box moves:

- **Bus** (`lib/buses.js`), on every node with two or more drawn edges: the edges leaving one side
  in one direction start from the side's middle and share one channel in the first gap, the
  nearest one ELK already used. The gap ends at the nearest box over any place the channel runs
  to, a lane's as well as a port's. The port moves 3 units (`portShift`) off the middle when a
  lane begins there, and when its drop to the channel would run along an edge that does not end
  at the node: a box's own child can send an edge out through the middle of the box's side, and
  then no edge of the bus could start there (`portOf`, `beadloom-m6k7.7`).
- **Trunk** (`lib/trunks.js`), on a node, leaf or box, with twenty or more drawn edges, loops
  included: its edges to one top-level box share one member's route to a distribution line 8
  units outside that box, then drop in where ELK had them enter. Out-trunks are drawn before
  in-trunks, and an edge between two busy nodes is in both.
- **Join** (`lib/joins.js`): an edge a trunk left in a lane of its own rides the box's main lane
  out past 150 units, then turns back to its own route.
- **Fallback**: an edge keeps its ELK route wherever a new segment would cross a box or run along
  an edge with no end in common with it.

The thresholds are `BUNDLE_OPTIONS`. `lib/bundleDrawing.js` holds the drawing being rewritten and
`lib/spatialIndex.js` the grid over boxes and the band index over segments. The bundles are kept
per layout, so a node page or full screen does not compute them again. Measured (`beadloom-bcqk`,
`beadloom-m6k7.4`): `cli-commands` leaves its bottom side in one channel and crosses a line 150
units out in nine lanes, nine being its bound, where ELK's routes took 36 channels and 69 lanes.
Bundling takes 13 ms here and about 38 ms on the adopter-sized graph, on the M1 Max; a
GitHub-hosted Ubuntu runner took 186.8 ms for the adopter-sized graph.

`model/bundleOverlay.js` draws a **junction dot** wherever drawn routes part (`lib/junctions.js`),
on a canvas above Cytoscape's (`model/overlayCanvas.js`), found again for the edges drawn now. On
a shared line Cytoscape reports one edge under the pointer. The viewer marks every edge along
that line at the walk's width (`is-along-hover`). When the line carries two or more, a note over the
canvas (`data-testid="edge-bundle-note"`) names the first eight and counts the rest.

### The map

The whole-graph view is drawn like a map (`lib/levels.js`, `model/canvasMap.js`). A box is open
or closed. A closed box keeps ELK's size and place, is drawn tinted with its title, and its
children are taken out of the graph (`cy.remove`, put back with `restore`). A level is a set of
open boxes and nothing is laid out again, so no box moves between levels.

- **Aggregated edges.** An edge both of whose ends are drawn as themselves is drawn as itself.
  Every other edge between two drawn ends is carried by one aggregated edge per unordered pair,
  labelled with its count each way (`3 + 1`), with an arrowhead at each end its edges arrive at.
  Its route is the medoid of its members' ELK routes, clipped between the two boxes
  (`lib/aggregateRoutes.js`). It takes a violation's look when one of its edges is one. Hovering
  it shows a note (`data-testid="aggregated-edge-note"`) naming its count each way by its ends.
- **Budget.** A level draws at most 100 aggregated edges: the heaviest, ties at the cut broken by
  the pair's ends in code-unit order (`budgetOf`). Each drawn end of a left-out edge shows the
  count as `+N` under its title. While the pointer rests on a node or the node is selected, all
  of its edges are drawn. The root box that holds everything exempts nothing, because the pointer
  rests on it wherever it is on no other node.
- **What is in view opens.** A box opens when the box holding it is open, it overlaps the view,
  the zoom is past 1.3 times the whole-graph fit, and its larger side is at least 600 px on
  screen. An open box closes below 80% of that (`openInView`, `LEVEL_OPTIONS`). The rule runs at
  most once per frame, on viewport changes.
- **What a selection needs opens.** A selected node is drawn as itself with its own edges: every
  box that holds it opens, and so does the node when it is a box (`boxesRevealing`). Impact and a
  neighbourhood the reader changed open the boxes of the whole walk. The neutral neighbourhood
  (depth 1, both directions, dimmed) does too, unless the node is a hub with twenty or more drawn
  edges: its neighbours stay inside their closed boxes (`selectionReveals`). The search box opens
  the boxes that hold its matches. Other filters open nothing, and an aggregated edge carries only
  the edges they show.
- **Marks keep their size.** An aggregated edge's width (1.5 px plus 1.1 px per doubling of its
  count), its label and a closed box's title keep one size on screen at any zoom: each carries the
  map's scale, a power of 1.25 near `1 / zoom` (`lib/mapMarks.js`, `scaleAt`). A box too small for
  its title shows it above the box.
- **The root's loops.** An edge onto the one root box that holds everything is not drawn while its
  other end is inside a closed box.

The landscape has no boxes, so it has no levels. Measured on this repository's graph
(`beadloom-94h4`): the whole-graph fit draws twelve top-level nodes and thirty-four aggregated
edges, which carry two hundred and seventy-seven of the four hundred and fifty-three drawn edges.
The mean frame interval while panning at the fit, without a GPU, fell from 39.6 ms to 16.7 ms
here and from 162 ms to 16.7 ms on the adopter-sized graph. 16.7 ms is the display's refresh cap
in that run.

### Bridges

A highlighted edge, one along a hovered line or on a selection's walk (neighbourhood or impact),
hops over every other drawn edge it crosses, original or aggregated (`lib/bridges.js`,
`model/bridgeOverlay.js`). A crossing is a horizontal run of one route through a vertical run of
the other, each at least 0.5 units from its ends, so edges along one line, a junction or a touch
are not crossings. Edges of one trunk or bus carry no bridge between them. When both edges are
highlighted, the horizontal one carries the bridge. With nothing highlighted, no bridge is drawn.

A bridge erases the highlighted line around the crossing in the colour under it (the background
and the tint of every box around the point), draws the crossed line through the gap, then a half
circle in the highlighted line's colour at that point of its gradient (`lib/bridgePaint.js`). The
hop's radius on screen is the larger of two sizes: both lines' half widths plus 1 px, and the
smaller of 5 px and 4.5 units. Below 2 px it is not drawn, so the whole-graph fit of a full
drawing shows none. Crossings are found only when the highlighted or drawn edges change, never
while the view moves, and a bridge out of view is skipped. Measured (`beadloom-a6a6`): drawing
the bridges costs at most 0.55 ms per frame on average, and finding them takes 4.5 ms for a hub's
neighbourhood here and 26.7 ms on the adopter-sized graph.

### Test handle

Under automation only (`navigator.webdriver`), `window.__beadloomViewer` exposes state for the
browser tests (`model/testHandle.js`). The handle is the last viewer's to install it, and a viewer
that leaves the page removes only its own. It reads:

- the canvas: `ready`, `visibleIds`, `selection`, `state`, `positions` (every node, drawn or
  inside a closed box), `pan`, `zoom`, `boxes` (page coordinates), `nodeBoxes` (drawn boxes,
  graph coordinates), `colours`, `statusLooks`;
- the selection: `neighbourhood`, `dimmedIds`, `rings`, `riskIds`, `impactSummary`;
- the edges of the data file: `drawnEdgeKinds`, `edgeStyle(key)`, `edgeLooks` (arrows, gradient
  stops and their positions, visibility, opacity), `shownEdgeLabels`, `edgeMidpoint`;
- the layout: `layoutRun` (`{ source, ms }`, `worker` or `cache`), `elkGeometry` (ELK's boxes and
  routes), `edgeRoutes` (every drawn edge as drawn: `id`, `key`, ends, `aggregated`, `routed`,
  `loop`, `points`, `label`);
- the bundles: `bundles` (`{ ms, routes, trunks, buses }`), `junctions`, `hoveredEdges`;
- the bridges: `bridges` (per highlighted edge, each crossing with its colours) and
  `bridgeFrames` (`{ findMs, paintMs, frames }`);
- the map: `openBoxes`, `level` (`{ fitZoom, zoom, scale, extent, open, collapsed }`),
  `aggregatedEdges`, `hiddenEdgeCounts`.

It takes one action, `revealNodes(ids)`, which draws the nodes in `ids` as themselves as a
selection does, until it is called again; `[]` lets their boxes close. A case that reads the whole
graph at full detail opens every box through it, because no reader gesture opens every box at
once.

### Modules

- `lib/elements.js` — `buildElements`: the data file as Cytoscape elements. An edge's id is
  `e<index>:<src>-><dst>` unless a node has that id, then primed (`freshId`).
- `lib/stylesheet.js` — `buildStylesheet(tokens)`, `GEOMETRY`, `CURVE_STYLE`,
  `ROUTE_CORNER_RADIUS`; the routed-edge, dimming and map rules.
- `lib/routes.js` — `centreOf`, `pathOf`, `segmentsOf`, `pathOfSegments`, `compoundSizeOf`.
- `lib/bundles.js`, `lib/buses.js`, `lib/trunks.js`, `lib/joins.js`, `lib/junctions.js`,
  `lib/bundleDrawing.js`, `lib/spatialIndex.js` — trunks, buses, joins and junctions.
- `lib/levels.js`, `lib/aggregateRoutes.js`, `lib/mapMarks.js` — the map's levels, aggregated
  routes and marks.
- `lib/bridges.js`, `lib/bridgePaint.js` — where bridges go and how they are painted.
- `model/useGraphCanvas.js` — the Cytoscape instance: mount, layout, hover, `showOnly`,
  `markSelection`, `reveal`, `revealNow`; returns `layingOut`, `layout`, `bundles`,
  `hoveredEdges`, `layoutError`, `junctions()`, `bridges()`, `bridgeFrames()` and `map()`.
- `model/canvasLayout.js` — `layoutInputOf`, `applyGeometry`, `fitCompounds`, `isLoop`.
- `model/canvasMap.js` — `canvasMap`, `scaleAt`, `SCALE_STEP`.
- `model/bundleOverlay.js`, `model/bridgeOverlay.js`, `model/overlayCanvas.js` — what is drawn
  above Cytoscape's canvas.
- `model/canvasMarks.js` — the selection and hover class names and `DISTANCE_DATA`, kept apart so
  the test handle loads without the canvas.
- `model/modes.js`, `model/testHandle.js`, `model/usePanelId.js`, `model/viewerKeys.js`.

## Public API

- `GraphViewer` (Vue component). Props: `mode` (`architecture`, the default, or `landscape`),
  `focus`, `depth`, `direction`, `height` (default `640px`). Slot `panel`, shown for the selected
  node, with `node`, `layerName`, `edges`, `layers`, `contracts`, `select(id)` and `close()`.
- `buildElements(nodes, edges, { parents, layers })`, `buildStylesheet(tokens)`, `CURVE_STYLE`
  (the style of a loop, the one edge not drawn along a route).

## Depends on

- `site-filter-graph`, `site-navigate-graph`, `site-select-neighbourhood`, `site-impact-view`,
  `site-fullscreen`, `site-url-state` (features).
- `site-architecture-data`, `site-landscape-data`, `site-graph-node`, `site-graph-edge`,
  `site-layer` (entities).
- `site-shared` (`cytoscape`, `elk`, `ids`, `theme-tokens`, `lib`).

## Tests

Seven specs are declared on this node. The other Playwright specs drive this widget too, and each
is declared on the slice it tests.

- `e2e/colours.spec.js`: colours in both themes, at the overview and at full detail.
- `e2e/graph-viewer-instances.spec.js`: two viewers on one page, each with its own panel id and
  test handle.
- `e2e/routes.spec.js`: on this portal's graph, an adopter-sized graph and the landscape, every
  edge is drawn along its route with its label on it and only an edge into its own box is a loop;
  no routed edge passes through a box it does not connect and none is more than half shared; the
  mean shared share stays at most 3%. Every box is drawn at ELK's size, also when a filter empties
  it; the routes survive a theme switch; the page, full screen and a node page share one layout.
- `e2e/bundles.spec.js`: on this portal's graph and the adopter-sized graph, no node or box moves;
  the fans keep at most a fifth of ELK's excess steps; every route joins its own two boxes at
  right angles from outside them; every node with twenty or more drawn edges leaves each side in one
  channel per direction and crosses a line 150 units out within its lane bound; no two edges with
  no common end run along one line; a junction dot marks exactly where routes part. The
  adopter-sized graph is also drawn in one to four layer ranks. Bundling at adopter size stays
  within its bound for the environment (50 ms locally, 400 ms in CI); a bus starts off the middle
  of a side where an edge of the node's own child crosses it; a box hub whose loop counts in its degree is bundled; dots follow a filter;
  hovering a shared line names its edges; a dimmed edge fades in colour at opacity 1.
- `e2e/map.spec.js`: the overview draws only the top-level boxes and at most 100 aggregated
  edges; arrowheads, counts and routes of aggregated edges; no box moves between levels; the
  budget, its ties and the `+N` counts; the pointer lifts the budget for one box at most; zooming
  opens and closes boxes; a selection, a hub's selection and the search open what they need; a
  filter composes with the level; the root's loops; marks keep their size; a title outside a
  small box; the landscape has no levels.
- `e2e/bridges.spec.js`: every crossing of a highlighted edge bridged in its colour, in both
  themes, checked against a brute-force oracle (`e2e/support/bridges.js`); no bridge with nothing
  highlighted; the cost of a hub's bridges per frame; hover; bundle siblings; a level switch, a
  filter and a hidden neighbourhood; pan and zoom; a theme switch.
- `e2e/performance.spec.js`: the frame interval while panning, and the adopter-sized graph's first
  drawing, within the bound for the environment (see [the site's page](../vitepress-site.md)).
