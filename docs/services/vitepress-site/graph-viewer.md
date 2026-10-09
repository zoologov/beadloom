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

This page describes the whole drawing, as the reader sees it. Since BDL-080 S2a most of the code
behind it lives in slices of its own, which the widget composes; the paths below name the file
where it lives now, and [Modules](#modules) maps each part to its slice and page.

- **Two modes** (`model/modes.js`). One core draws the architecture graph, from
  `architecture.data.json`, and the landscape of contracts between services, from
  `landscape.data.json`. A mode names only what differs: the data file and how it becomes nodes
  and edges, the filters in its slot of the toolbar and the set they show, what its search finds
  (`searched`), its impact walk, and whether it is layered (`layered`: the architecture is, the
  landscape is not). Since BDL-080 the architecture mode's graph also carries `layerRules`, the
  data file's `layer_rules`, and the mode carries `layerChoiceOf` (`site-filter-graph`): once the
  layers are read, the viewer settles the Layer filter's value through it, so a link naming a
  bare layer (`?layer=domains`) filters on a portal that draws two rules and the URL is rewritten
  to the value the filter offers. The mode is the page's prop and the URL does not carry it,
  because the two modes are two pages with two different cards.
- **Layout.** ELK lays the graph out once, in a Web Worker (`site-shared`, `shared/elk`), and
  everything the canvas draws is read from that one layout: nodes, box sizes, routes, bundles,
  the map's levels and the overview's plan. Until ELK answers, a `role=status` note says "Laying
  out the graph…" over a hidden canvas, and the toolbar keeps working. A layout that fails is
  reported as a `role=alert` note naming the error. The canvas stays hidden, because no node has a
  place, and the filter, neighbourhood, impact and navigation controls sit in a disabled
  `fieldset`. Panel and Full screen act on the viewer, not the graph, and stay on.
  Cytoscape draws no frame while ELK runs: it is held in a batch (`useGraphCanvas.js`,
  `undrawnUntil`), since a frame of the hidden, unplaced adopter-sized graph took 245 ms on
  Darwin arm64. Once ELK answers, drawing the layout (`applyGeometry`) and making the map, which
  plans the overview at its first drawing, take a task each. Between them the page gets a turn of
  its event loop (`scheduler.yield()` where the browser has it, else a `MessageChannel` message),
  with Cytoscape still held. The map's scale is the overview plan's from the first drawing, and
  the whole-graph fit's scale, which reads every element in the graph, is measured only while no
  plan has given one (`canvasMap.js`, `scaleNow`). Together these took the longest task on the
  adopter-sized graph from 603 to 626 ms to 299 to 300 ms on Darwin arm64 (`beadloom-btkd.22`,
  bound in [the site's page](../vitepress-site.md)).
- **Selection.** A selected node is the start of a walk. In the neighbourhood the walk goes to
  the chosen depth and direction (`site-select-neighbourhood`); with **Impact** on it goes to
  everything that depends on the node, without a limit, by the mode's walk (`site-impact-view`).
  What the walk leaves out is dimmed, or hidden when the reader asks, and the containers of what
  it reached stay. Every selection — a tap, the URL, the card, the impact list, a search — is
  framed (BDL-078, owner's ruling 7): the view zooms and pans to the walk, never below the zoom
  at which the node is drawn as itself and readable, in a 350 ms animation unless the reader asks
  for reduced motion (`site-navigate-graph`, `frame`). A selected box is a walk over everything
  it holds taken as one node (`boxNeighbourhoodOf`): it opens at any zoom, is framed whole, keeps
  its contents at full strength and draws its outward edges as the pointer on it does. The one
  exception is a box holding a layer rule's boxes (BDL-080 S1e): it opens only where those boxes
  are readable, also when tapped, because at the zoom that frames it whole their titles would
  stand on plates over each other. Measured on this repository: `vitepress-site` tapped at the
  fit is framed whole at zoom 0.128 and drawn closed, its title inside and its card in the panel;
  zoomed in, it opens at 0.313 with layer boxes 29.7 px tall, and zoomed out it stays open at
  0.250 and closes at 0.200, with no title over another at any step (5 overlaps at 0.128 before).
- **Panel.** It shows what the page puts in its `panel` slot for the selected node and, in impact
  mode, the impact summary above it. A widget does not import another, so the page composes the
  card; the slot passes `parents`, so the card can say what a box holds. Each viewer gets its own
  panel id (`usePanelId`), so two viewers on one page do not share the toolbar's "Panel" button.
  The canvas takes its container's size before a selection is framed, so a panel opened beside it
  in full screen does not leave the walk off-centre.
- **Navigation.** No node is grabbable and every node is pannable (`panOnNodes()`, called once the
  graph holds its nodes), so a drag anywhere pans, on a node or inside a box. No control moves a
  node: the routes are read from the layout, and a moved node would leave them behind. The
  toolbar zooms, fits and centres, and fitting and centring leave out the part of the canvas the
  open panel covers. Keys, while focus is in the viewer: `+` and `-` zoom, `0` fits, `f` toggles
  full screen, `Esc` clears the selection.
- **Layer boxes** (BDL-080 S1c). A layer rule whose scope is a box other than the project's frame
  draws one box per layer inside that box (`site-layers`, `layerBoxesOf`). The viewer draws from
  that containment, `drawnParents`: the elements, the filters' ancestors, and the selection's
  kept nodes, holders and selected box read it. The card and impact read the file's own
  `parents`, because a layer box is no node of the graph. `buildElements` emits each layer box as
  a node carrying `LAYER_BOX` (the rule's name) and marks the scope box `STACK_LANES`, both
  exported from `shared/map-levels/levels.js`. `canvasLayout` passes `stack` to ELK for such a
  box, so its layer boxes stack top to bottom by rank (`site-shared`, `shared/elk`). A layer box
  is titled and toned by its layer, opens by readability, is joined by lines and carries tallies
  and pills like any box, and a tap on it selects nothing. On this repository `vitepress-site`
  opens onto six layer boxes, app, pages, widgets, features, entities and shared. The panel
  slot's `layer-name` is the layer's caption.
- **URL state.** The filters, the selection, depth, direction, dim or hide, and the neighbourhood
  or impact view round-trip through the query string (`site-url-state`). The URL overrides the
  props.

BDL-078 changed how everything is drawn and when, and kept BDL-077's single layout, routes and
bundles: one thin line weight, no bridges, no junction dots and no direction gradient; a followed
line drawn on top over a casing; nodes as cards with a corner status mark; an overview with its
own routing that is calm by default; an open box that keeps its outward edges aggregated; boxes
that open when their nodes are readable; and a zoom to the selection.

### Routes, measured

`model/canvasLayout.js` draws the layout as ELK computed it. Every leaf stands at the centre of
its ELK box. Every box is sized to its ELK box (`shared/geometry/routes.js`, `compoundSizeOf`),
with compound padding 0 and `compound-sizing-wrt-labels: exclude`, and it is sized again whenever
a filter or a selection changes which of its children are drawn, so a box keeps its place. Every
edge follows its ELK route: `curve-style: round-segments`, its ends and corners given relative to
its nodes' centres (`segmentsOf`), with the arrowhead where the route enters the target's box. An
edge from a node to a box that holds it is drawn the same way since BDL-078, square along its
route, by a line of its own to an invisible end on the box's border
(`shared/map-levels/loopLines.js`): Cytoscape would draw it as a compound loop straight across
the box. ELK's input carries nothing about the canvas, so the architecture page, a node page and
full screen share one layout. It carries nothing about text either: a leaf's size is the
stylesheet's 160 by 44 units plus its border, never its label (`layoutInputOf`), and ELK sizes
every box, so the layout depends on the data file alone. The geometry in the site-e2e trace of
2026-10-04, taken on a Linux runner, is identical to that of the same data file laid out on macOS
(`beadloom-m6k7.7`), and `layout.spec.js` holds it with the fonts changed.

The routes replaced Cytoscape's `bezier` curves from one node's centre to the other's in BDL-077.
Measured on this repository's graph in headless Chromium on an Apple M1 Max, with the built
portal at 1400 x 900 (`beadloom-5x4g`, `beadloom-m6k7.5`):

| Measure | `bezier` (before BDL-077) | ELK's routes | Routes with trunks and buses (BDL-077) |
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

### Nodes

The stylesheet (`lib/stylesheet.js`) is built from theme tokens resolved to literal `rgb(...)`
values and rebuilt when VitePress switches between light and dark; no colour is a fallback.

- **A node is a card.** Leaf or box, it is drawn as the legend draws its layer: a thin border in
  its layer's tone over a tint of it (`LAYER_FILL_SHARE`, 0.16, `site-layers`), its title in the
  middle. A node in no layer takes the `text2` tone, and the legend then names "no layer". Its
  corners keep one radius on screen at every zoom, 8 px (`shared/geometry/corners.js`,
  `NODE_CORNER_PX`), a quarter of its shorter side where that is less, and a corner gives way
  where a line ends nearer to it than the radius, so no line stops in the air beside an arc
  (`model/nodeCorners.js`). The overview's boxes have the same rounded corners as the nodes
  (owner, 2026-10-07).
- **Status is a corner mark** (owner's ruling 5): a dot 10 units across in the top right corner,
  filled for an error finding or a stale document, a ring for warn findings only
  (`NODE_STATUSES[s].mark`, `site-graph-nodes`). The border stays its layer's, so a status moves
  nothing.
- **An open box** is a fainter tint of its layer's tone (0.07) inside a thin solid border, its
  title inside at the top. ELK keeps 36 units above a box's children for that title
  (`GEOMETRY.boxTitleRoom`, `shared/elk`, `boxTop`).
- **The box that holds everything** (`PROJECT_BOX`, `is-project`) is the project's frame: a border
  1 px wide on screen in `text3`, which keeps 3:1 against the canvas (3.10:1 light, 3.20:1 dark,
  measured), over a tint of `text1` at 0.05, fainter than any node it holds.
- **Selection and impact.** A selected architecture node keeps its layer tint. Outside the
  neighbourhood or the impact set a node is dimmed (opacity 0.14) or hidden; in impact mode a
  node's fill takes its distance ring's tone and a risky node carries a dashed danger outline. On
  the landscape, which has no layers, a node is a card whose border is its health.

Text reads at WCAG AA against what it is drawn on in both themes, at the overview and at full
detail, and every node's border keeps 3:1 (`look.spec.js`, `metrics.spec.js`).

### Lines and arrowheads

- **One weight** (owner's rulings 4 and 10). Every line is 1.35 px on screen at every zoom,
  whatever its kind, its count or its state (`entities/graph-edges/lib/lineMarks.js`,
  `LINE_MARKS.width`). Kinds differ by colour and dash only. A count is said on a pill, never in
  the width.
- **No gradient** (ruling 3). A line is one colour from end to end; its arrowhead carries the
  direction. At rest a line takes its kind's share of its tone over the background
  (`EDGE_STYLES[k].strength`, `site-graph-edges`): an import is a light neutral, a violation the
  full danger colour. A followed line is drawn in its full tone. A line outside a selection is its
  rest colour faded towards the background at full opacity (`DIMMED_SHARE` 0.14), because edges
  drawn along one trunk at opacity 0.14 would add up to about four fifths of full strength. While
  the pointer rests on a node, every line not its own is faded less (`BEHIND_SHARE` 0.4)
  (`entities/graph-edges/lib/edgePalette.js`).
- **Whole arrowheads.** A head is 6 px long on screen (`LINE_MARKS.head`), sized through
  Cytoscape's own arrow formula inverted (`arrowScaleOf`), and stands on a straight run of its
  own length and half a head more (`stem`). Where a line's run has no room for that, the head is
  drawn shorter, down to 3 px (`smallestHead`, `headLengthAt`); the routes give it the room where
  nothing is in the way (`shared/bundling/headRuns.js`, below). The corner before a headed end is
  rounded only by what its run has to spare, every other corner at 6 px, so a branch leaves its
  trunk in a rounded merge on the stroke (ruling 2). A dashed line's pattern is shifted so a dash
  ends inside the head (`dashOffsetOf`).
- **One head per shared last run** (ruling 10). Lines that reach one end along one final run end
  in one arrowhead: the loudest look draws it (a violation is never hidden under an import's
  head), then an edge of the file before a line of the map's, then the first by id; the others
  end at its base (`entities/graph-edges/lib/heads.js`, `droppedHeadsOf`;
  `features/follow-edge/model/sharedLines.js`). Lines that reach a box side separately keep their
  own heads. Of two heads too close side by side on one border, one gives way and its line ends
  beside the other's head (`crowdedHeadsOf`). A loop keeps its own head.
- **Labels.** Cytoscape draws no edge label but a landscape contract's badge. The kind of the line
  under the pointer is drawn on the layer above (below), and only while it is hovered.

### Trunks and buses

ELK gives each edge of a node its own port and channel, so a node with seventy edges leaves its
side in a staircase as wide as the graph. `shared/bundling/bundles.js` (`bundleRoutes`) rewrites
the routes after the layout, and no node or box moves:

- **Bus** (`shared/bundling/buses.js`), on every node with two or more drawn edges: the edges
  leaving one side in one direction start from the side's middle and share one channel in the
  first gap, the nearest one ELK already used. The gap ends at the nearest box over any place the
  channel runs to, a lane's as well as a port's. The port moves 3 units (`portShift`) off the
  middle when a lane begins there, and when its drop to the channel would run along an edge that
  does not end at the node: a box's own child can send an edge out through the middle of the
  box's side, and then no edge of the bus could start there (`portOf`, `beadloom-m6k7.7`).
- **Trunk** (`shared/bundling/trunks.js`), on a node, leaf or box, with twenty or more drawn
  edges, loops included: its edges to one top-level box share one member's route to a
  distribution line 8 units outside that box, then drop in where ELK had them enter. Out-trunks
  are drawn before in-trunks, and an edge between two busy nodes is in both.
- **Join** (`shared/bundling/joins.js`): an edge a trunk left in a lane of its own rides the
  box's main lane out past 150 units, then turns back to its own route. Each lane is tried as the
  one joined, and failing every lane, a fresh column straight out of the node's side (`joinsAt`).
- **Head run** (`shared/bundling/headRuns.js`, `lengthenHeadRuns`, BDL-078 `beadloom-btkd.2`):
  last, the lines arriving at one point of a node have their last bend moved back along their
  last run, where nothing is in the way, until the run is 20 units long (`headRun`), in steps of
  2 (`headRunStep`), clear of unrelated edges by 8 (`headRunClearance`). ELK ends a line 10 units
  after its last bend, about five pixels where a node is just readable, and a head is six.
  `lengthenLineEnds` does the same for an overview line drawn along its medoid, moving only that
  line (`movable`).
- **Fallback**: an edge keeps its ELK route wherever a new segment would cross a box or run along
  an edge with no end in common with it.

The thresholds are `BUNDLE_OPTIONS`. `shared/bundling/bundleDrawing.js` holds the drawing being
rewritten and `shared/geometry/spatialIndex.js` the grid over boxes and the band index over
segments; a band query stops when its visitor asks and, over a long run, visits only the bands
that hold something. The bundles are kept per layout, so a node page or full screen does not
compute them again. Measured (`beadloom-bcqk`, `beadloom-m6k7.4`): `cli-commands` leaves its
bottom side in one channel and crosses a line 150 units out in nine lanes, nine being its bound,
where ELK's routes took 36 channels and 69 lanes.

Where routes part, the rounded corner of the one that turns is the merge; no dot marks it (ruling
2). On a shared line Cytoscape reports one edge under the pointer; the viewer marks every edge
along that line (`shared/geometry/routeIndex.js`, `routesAlong`; `is-along-hover`), and when the
line carries two or more, a note over the canvas (`data-testid="edge-bundle-note"`) names the
first eight and counts the rest.

### Followed lines

There are no bridges (ruling 1). A followed line — every edge along the hovered line, every line
of the node under the pointer, and every edge of a selection's walk (`HIGHLIGHTED_EDGES`) — is
drawn again on a canvas above Cytoscape's (`features/follow-edge/model/followedOverlay.js`,
`shared/canvas-marks/overlayCanvas.js`), in its full colour, over a casing 2 px wide on each side
(`LINE_MARKS.casing`) in the canvas's background colour that clears what it crosses. The drawing
goes in passes: every casing, then every line, then the arrowheads, then the title of each open
box a followed line runs through, drawn again on a patch of the box's fill so the line runs under
it, then the label of the edge under the pointer. In passes, lines of one bundle do not cut slits
into each other where they part. A followed line is drawn as Cytoscape draws it — the same route,
corners and sizes — and always with its arrowhead. Two layers lie over the canvas, in order:
`followed`, then `pills`.

### The map

The whole-graph view is drawn like a map (`shared/map-levels/levels.js`, `model/canvasMap.js`). A
box is open or closed. A closed box keeps ELK's size and place, is drawn tinted with its title,
and its children are taken out of the graph (`cy.remove`, put back with `restore`). A level is a
set of open boxes and nothing is laid out again, so no box moves between levels.

- **The sibling rule** (ruling 9, `levelOf`, `siblingsOf`). An edge is drawn at the lowest box
  that holds both its ends, between the two children of that box that hold them: as itself only
  when those children are its own ends and neither is a box; otherwise it is carried by one
  aggregated edge per unordered pair of those children. So an open box keeps its outward edges
  aggregated at the box, shows its nodes and the edges among them, and opening it moves no line
  between it and its siblings. This replaces BDL-077's rule that an edge is drawn as itself once
  both ends are drawn. Measured on this repository's graph (RFC probe): lines in view with one
  box open fell from 114 to 43.
- **Aggregated edges.** One per pair, an element of the map's own
  (`features/overview-map/model/aggregateElements.js`) with an arrowhead at each end its edges
  arrive at and its count each way in its data. Between two top-level nodes its route is the
  overview's plan (below), at every level; any other runs along the medoid of its members' ELK
  routes between the two boxes (`shared/geometry/aggregateRoutes.js`), its last run into a closed
  box straightened where it was a short dogleg (`straightenedInto`). It takes a violation's look
  when one of its edges is one. Hovering it shows a note (`data-testid="aggregated-edge-note"`)
  naming its edges each way by their ends.
- **Budget.** A level draws at most 100 aggregated edges (`LEVEL_OPTIONS.budget`): the heaviest,
  ties broken by the pair's ends in code-unit order (`budgetOf`). Each drawn end of a left-out
  edge carries the count (`hiddenEdges`).
- **What is readable opens** (ruling 12, `openInView`). A box opens when the box holding it is
  open, it overlaps the view, the zoom is past 1.3 times the whole-graph fit (`fitFloor`), and
  its smallest child is at least 24 px tall on screen (`readable`); it closes below 0.9 of that
  (`closeShare`). This replaced BDL-077's rule of a box side reaching six hundred pixels, at
  which a box's own cards stood about fifty-five pixels wide and twelve high. The rule runs at
  most once per frame, on viewport changes, and not while the view is animated.
- **What a selection needs opens** (`boxesRevealing`, `selectionReveals`). A selected node is
  drawn as itself with its own edges: every box that holds it opens, and so does the node when it
  is a box. With nothing more asked a selection opens only that, which is what the pointer on the
  node needs, so a click and a hover draw the node's edges on the same lines. Impact, and a
  neighbourhood the reader changed (deeper, one way, the rest hidden), open what every node of
  the walk needs. A selected box opens at any zoom (`forced`), except a box holding a layer
  rule's boxes, which opens where they are readable (`model/canvasMap.js`, BDL-080 S1e). The
  search box opens the boxes that hold its matches. Other filters open nothing, and an aggregated
  edge carries only the edges they show.
- **"+N" and own lines** (the owner's rulings nine and fourteen). A node inside an open box whose
  outward edges a box that holds it carries at rest shows their count as "+N" on a badge across
  the middle of its right side (`outwardOf`; `shared/map-levels/mapMarks.js`, `OUTWARD`). While
  the pointer is on the node, or it is selected, they are drawn on top
  (`features/overview-map/model/mapExtras.js`): each as itself where both ends are drawn at their
  laid-out size, otherwise one own line from the node to each node the other ends are drawn as
  (`ownLinesOf`), along the medoid of their drawn routes. The box-level line they belong to is
  not drawn twice. A line into an open box whose nodes the node's other lines run on into is
  their stub, with no head of its own (`STUB_AT`). The "+N", the hover and the click name the
  same edges (`counts.spec.js`).
- **Loops** (the owner's ruling thirteen). An edge from a node to a box that holds it stays
  drawn, square along its route (`shared/map-levels/loopLines.js`), once both its ends are drawn
  and neither is a closed box. An edge onto the one root box that holds everything is not drawn
  while its other end is inside a closed box.
- **Marks keep their size.** A line's weight, arrowheads and corners, a node's corners, and a
  closed box's title keep one size on screen: each carries the map's scale, a power of 1.25 near
  `1 / zoom` (`features/overview-map/model/mapTitles.js`, `scaleAt`, `SCALE_STEP`), so a zoom
  gesture restyles them only when the zoom crosses a step. A class or data is set only where it
  changes (`shared/canvas-marks/canvasMarks.js`, `setClass`, `giveData`), because Cytoscape 3.34
  restyles an element for every class it is given, changed or not.

The landscape has no boxes, so it has no levels.

### The overview

The overview is the level with every top-level box closed (ruling 8). Its lines are routed
together by the overview's own router (`shared/grid-routing/overviewRoutes.js`, `planOverview`)
at the scale of the whole-graph fit, where the reader sees them, between the fixed top-level
boxes; no box moves.

- **The grid** (`shared/grid-routing/overviewGrid.js`, `gridOf`). Lines run on tracks at least a
  pitch apart, 8 px at the fit (`OVERVIEW_MARKS.pitch`). Each box is an obstacle with a
  half-pitch margin and a halo up to 14 px deep (`halo`) that only its own lines enter, straight
  at it, so a line arrives with a straight run of at least 15 px (`run`). A port lies on the
  straight part of a side, clear of the rounded corners (`sideRange`). The box that holds
  everything is a frame: an outer wall the lines keep inside. A box nearer the frame than half a
  pitch, whose every port runs into a box standing across it, gets a track through the stretch of
  a side nothing covers.
- **The router.** A route costs its length, plus each bend, crossing and run beside another line
  (A* over cells and directions). Lines are routed shortest span first, then each once more. Two
  lines never share a track, except that lines ending at one box that agree on having an
  arrowhead there may share their last run and end in one head. A line no route reaches is routed
  again with each refusal priced; one that still finds none is routed before the lines in its way,
  which are laid again around it, the plan put back as it was when one of them then fails. A line
  nothing can route is drawn along its medoid, its last runs lengthened for its heads
  (`features/overview-map/model/overviewPlan.js`, fallbacks).
- **The plan** (`features/overview-map/model/overviewPlan.js`, `overviewPlanner`) is made from
  the overview whatever level is drawn, and made again only when the edges the filters show, or
  the fit's scale on a resize, change; a line between two top-level nodes keeps the plan's route
  at every level, so a zoom or a box opened moves none of them. A line the budget left out and
  the pointer or a selection now draws is routed around the plan's lines and kept the same way.
- **Titles** (`shared/map-levels/mapMarks.js`, `shared/geometry/grownBoxes.js`,
  `features/overview-map/model/mapTitles.js`). A closed box's or top-level node's title is drawn
  inside its box at 14, 12.5, 11 or 10 px, the largest that fits. Where none fits, a top-level
  box is drawn at the least size that holds the title, centred on its laid-out box and clear of
  every other (`grownBoxesOf`); the lines are routed around the drawn box and on to the laid-out
  one, and zoomed in, the drawn box keeps about its size on screen until the laid-out box is as
  large. Where no such box fits one line, the name is broken onto two at a hyphen, underscore,
  slash, dot, colon or space (`brokenLabelOf`). Only a title neither fits stands on a plate with
  a border, above its box or on the side where it covers nothing (`plateOf`); the router prices a
  plate so no line runs under it and no line ends on it. The project box's title stands on a
  plate above it while its own title would read smaller than 10 px.
- **Calm by default.** Lines at rest are thin and light. Hovering or selecting a box brings its
  lines and pills forward (`is-in-front`) and fades the rest (`is-behind`), and the pointer gone,
  all are back at rest. A closed box large enough on screen says how many edges come in and go out
  in its lower right corner, `in N · out M` (`tallyTextOf`), the ones the budget leaves out
  included.

Measured in the RFC's probe on this repository's graph: overlapping arrowhead pairs 12 → 0, the
minimum gap between parallel lines 0.8 → 7.1 px, lines under a title 13 → 0. The overview is
deferred for a project whose top level does not fit the canvas (ruling 11): its fit is left as it
was.

### Counts

A line's count is drawn on a pill, an opaque rounded label with a thin border in the line's
colour, on a canvas above every line (`features/edge-pills/model/pillOverlay.js`), so no later
line paints over it. A line says its count once it carries more than one edge; a line of the node
under the pointer, a node's own line and a line of a selection's walk say it even when it is one,
so the numbers on the lines a reader is shown for a node add up to the node's count. During a
selection a line says how many of the walk's edges it carries (`SAID`). The place is a free point
on the line, tried every 6 px from the middle out (`shared/geometry/pillPoints.js`,
`candidatesOf`), clear of every node, title, arrowhead and other pill and far enough from the
ends to leave the heads whole (`shared/geometry/pillPlaces.js`, `pillStagesOf`). The pills are
placed in three stages: a node's own lines first, then the lines between top-level things, among
what the top level draws alone, so opening a box moves none of them, then the rest. A line with
no free point has no pill, and its count is in the note shown on hover; a line asked to say its
count says it anyway (`crowded`). A pill is placed once per step of the map's scale.

### Performance

Measured at `6b77893c` (`beadloom-btkd.15`) on this portal and the adopter-sized graph the browser
suite generates, in headless Chromium at 1400 x 900 on Darwin arm64, against the local bounds in
`e2e/support/environment.js`: overview planning 15.1 ms here and 133.1 ms at adopter size (bounds
50 and 250), bundling 40.4 ms (50), the adopter-sized first drawing 6,046 ms (7,200), a zoom step
45.0 / 45.8 ms (60), a hover 29.3 / 32.1 ms (50), and the frame interval while panning 16.7 ms
(25), the display's refresh cap in that run. A hover is drawn once per event in a microtask, so a
`mouseout` and the `mouseover` after it cost one drawing. The CI bounds are set per environment;
see [the site's page](../vitepress-site.md).

### Test handle

Under automation only (`navigator.webdriver`), `window.__beadloomViewer` exposes state for the
browser tests (`model/testHandle.js`). The handle is the last viewer's to install it, and a viewer
that leaves the page removes only its own. Records keyed by a node id have no prototype
(`idRecord`, `site-shared`), so a node named `__proto__` reads like any other; `boxTallies` and
`outwardMarks` answer such a record before the map has drawn a count and after. It reads:

- the canvas: `ready` (false while the view is animated or a change is still to be read),
  `visibleIds`, `selection`, `state`, `positions`, `pan`, `zoom`, `move` (the last move that
  framed a selection or a search, `site-navigate-graph`'s `lastMove()`: `{ animated, from, to,
  frames, done }`, or `null` before any), `boxes` (page coordinates), `nodeBoxes` (drawn boxes,
  graph coordinates), `colours`, `statusLooks` (with `mark`);
- the looks: `nodeLooks` (fill, border and its position, title, status mark, shape, size,
  `cornerRadius`), `lineLooks` (every drawn line: width, dash and `dashOffset`, colour, arrows,
  `arrowScale`, `sourceDistance` / `targetDistance`, `cornerRadii`, `walk`, `dimmed`, `front`,
  `behind`, `forward` / `backward`, `stub`, points), `overlayLayers`, `followed` (`{ edges,
  passes }`, the passes `casings`, `lines`, `heads`, `titles`, `labels`), `frames`,
  `droppedHeads`, `shownEdgeLabels`, `edgeMidpoint`;
- the selection: `neighbourhood`, `dimmedIds`, `rings`, `riskIds`, `impactSummary`;
- the edges of the data file: `drawnEdgeKinds`, `edgeStyle(key)`, `edgeLooks`;
- the layout: `layoutRun` (`{ source, ms }`, `worker` or `cache`), `elkGeometry`, `edgeRoutes`
  (every drawn line: `id`, `key`, ends, `aggregated`, `routed`, `loop`, `points`, `label`; a
  loop's real ends);
- the bundles: `bundles` (`{ ms, routes, trunks, buses, headRuns }`), `hoveredEdges`;
- the map: `openBoxes`, `level` (`{ fitZoom, zoom, scale, extent, open, collapsed }`),
  `aggregatedEdges`, `ownLines`, `outwardMarks` (each node's "+N"), `hiddenEdgeCounts`;
- the overview: `overviewPlan` (`{ ms, unit, routed, failed, grown, broken, plates,
  projectPlate }`), `pills` (`{ pills, dropped }`, each pill `crowded` or not), `titles`,
  `boxTitles`, `boxTallies`.

Since BDL-080 S1c `visibleIds`, `boxes`, `nodeLooks` and the handle's other node readers count
the boxes a scoped layer rule draws among the drawn nodes, beside the file's own.

It takes one action, `revealNodes(ids, { edges })`: with `edges` (the default) it draws every edge
with an end at a revealed node as itself, opening every box that holds one at any zoom; with
`{ edges: false }` it opens the boxes only, as a reader's zoom does; `[]` lets them close. A case
that reads the whole graph at full detail opens every box through it.

`bridges()`, `bridgeFrames()` and `junctions()` were removed with the features (BDL-078).

### Modules

BDL-080 S2a cut the viewer into ten slices so that work on one part of it runs on its own node
(RFC D3). The widget keeps twelve files. The drawing it composes moved into nine other slices:
eight new nodes and the entity `site-graph-edges`. Each moved file kept its name.

What stays in `widgets/graph-viewer/`:

- `index.js` — the public API: `GraphViewer`, `buildElements`, `buildStylesheet`, `CURVE_STYLE`.
- `ui/GraphViewer.vue` — the component: toolbar, canvas, panel and legend, and the wiring of
  every slice below.
- `lib/elements.js` — `buildElements`: the data file as Cytoscape elements, and the boxes a
  scoped layer rule draws (`LAYER_BOX`); a scope box is marked `STACK_LANES`. An edge's id is
  `e<index>:<src>-><dst>` unless a node has that id, then primed (`freshId`).
- `lib/stylesheet.js` — `buildStylesheet(tokens)`, `CURVE_STYLE`. It reads a node's sizes from
  `GEOMETRY`, `drawnSizeOf` and `rimOf`, which moved to `shared/map-levels/nodeSizes.js`.
- `model/useGraphCanvas.js` — the Cytoscape instance: mount, layout, hover, `showOnly`,
  `markSelection`, `reveal`; returns `layingOut`, `layout`, `bundles`, `hoveredEdges`,
  `layoutError`, `pills()`, `tallies()` and `map()`.
- `model/canvasLayout.js` — `layoutInputOf`, `applyGeometry`, `fitCompounds`, `isLoop`; a node's
  `stack` is read from `STACK_LANES`.
- `model/canvasMap.js` — `canvasMap`, the level drawn on Cytoscape. Its parts were split out by
  job in `beadloom-btkd.17` and now live in `site-overview-map`; it re-exports none of their
  names (`beadloom-btkd.20`).
- `model/nodeCorners.js` — corners held at line ends.
- `model/modes.js`, `model/testHandle.js`, `model/usePanelId.js`, `model/viewerKeys.js`.

What moved out, and where:

| Files | Now in | Node |
|-------|--------|------|
| `routes.js`, `corners.js`, `spatialIndex.js`, `routeIndex.js`, `grownBoxes.js`, `aggregateRoutes.js`, `pillPoints.js`, `pillPlaces.js` (were `lib/`) | `shared/geometry/` | [`site-shared-geometry`](shared-geometry.md) |
| `canvasMarks.js`, `overlayCanvas.js` (were `model/`) | `shared/canvas-marks/` | [`site-shared-canvas-marks`](shared-canvas-marks.md) |
| `bundles.js`, `buses.js`, `trunks.js`, `joins.js`, `headRuns.js`, `bundleDrawing.js` (were `lib/`) | `shared/bundling/` | [`site-shared-bundling`](shared-bundling.md) |
| `overviewGrid.js`, `overviewRoutes.js` (were `lib/`) | `shared/grid-routing/` | [`site-shared-grid-routing`](shared-grid-routing.md) |
| `levels.js`, `mapMarks.js` (were `lib/`), `loopLines.js` (was `model/`), and the new `nodeSizes.js` | `shared/map-levels/` | [`site-shared-map-levels`](shared-map-levels.md) |
| `heads.js`, `lineMarks.js`, `edgePalette.js` (were `lib/`) | `entities/graph-edges/lib/` | [`site-graph-edges`](graph-edges.md) |
| `followedOverlay.js`, `sharedLines.js` (were `model/`) | `features/follow-edge/model/` | [`site-follow-edge`](follow-edge.md) |
| `overviewPlan.js`, `mapTitles.js`, `aggregateElements.js`, `mapExtras.js` (were `model/`) | `features/overview-map/model/` | [`site-overview-map`](overview-map.md) |
| `pillOverlay.js` (was `model/`) | `features/edge-pills/model/` | [`site-edge-pills`](edge-pills.md) |

Four names moved with the cut: `GEOMETRY`, `drawnSizeOf` and `rimOf` out of the stylesheet into
`shared/map-levels/nodeSizes.js`; `FIT_PADDING` and `FIT_MAX_ZOOM` out of `site-navigate-graph`
into `shared/map-levels/levels.js`; `OWN_LINE` out of the map's lines into the same file; and
`RING_TONES` out of `site-impact-view` into `shared/theme-tokens` (`site-shared`). The test-handle
dump over nine views was byte-identical before and after the cut (measured by S2a, 3.11 MB).

`lib/bridges.js`, `lib/bridgePaint.js`, `lib/junctions.js`, `model/bridgeOverlay.js` and
`model/bundleOverlay.js` were removed by BDL-078; `routeIndex.js` keeps what a hover needs of the
old junction index.

## Public API

- `GraphViewer` (Vue component). Props: `mode` (`architecture`, the default, or `landscape`),
  `focus`, `depth`, `direction`, `height` (default `640px`). Slot `panel`, shown for the selected
  node, with `node`, `layerName`, `edges`, `layers`, `contracts`, `parents`, `select(id)` and
  `close()`.
- `buildElements(nodes, edges, { parents, layers, layerBoxes })`, `buildStylesheet(tokens)`, `CURVE_STYLE`
  (the fallback curve style of a line the layout did not route).

## Depends on

- `site-filter-graph`, `site-navigate-graph`, `site-select-neighbourhood`, `site-impact-view`,
  `site-fullscreen`, `site-url-state`, `site-follow-edge`, `site-overview-map`, `site-edge-pills`
  (features).
- `site-architecture-data`, `site-landscape-data`, `site-graph-nodes`, `site-graph-edges`,
  `site-layers` (entities).
- `site-shared` (`cytoscape`, `elk`, `ids`, `theme-tokens`, `lib`), `site-shared-geometry`,
  `site-shared-canvas-marks`, `site-shared-bundling`, `site-shared-map-levels`.

## Tests

Fourteen specs are declared on this node. The other Playwright specs drive this widget too, and
each is declared on the slice it tests. Measures that read the drawing are computed from the test
handle by oracles in `e2e/support/`, which import nothing from the theme.

- `e2e/colours.spec.js`: colours in both themes, at the overview and at full detail.
- `e2e/graph-viewer-instances.spec.js`: two viewers on one page, each with its own panel id and
  test handle.
- `e2e/data-ids.spec.js`: nodes named `__proto__`, `constructor`, `toString`, `valueOf` and
  `hasOwnProperty` are laid out, drawn, bundled, opened, selected from the URL, and their counts
  kept by the handle; the counts answer nothing for a name they were not given, before the map
  draws and after.
- `e2e/routes.spec.js`: every edge drawn along its route, a box drawn at ELK's size, routes through
  no box and at most 3% shared on average, one layout for the page, full screen and a node page.
- `e2e/bundles.spec.js`: no node or box moves; the fans keep at most a fifth of ELK's excess steps;
  busy nodes leave each side in one channel per direction within their lane bound; no two
  unrelated edges along one line; hovering a shared line names its edges; a dimmed edge fades in
  colour at opacity 1.
- `e2e/look.spec.js` (support `look.js`): one weight; one head size; whole heads on a straight
  run; one head per shared last run; rounded merges; lines meet nodes clear of their corners; no
  bridge and no junction dot; followed lines on top over a casing, a label only on hover; status
  moves nothing; open-box and project-frame looks; contrast at WCAG AA and 3:1; rounded corners.
- `e2e/heads.spec.js` (support `heads.js`): every arrowhead entered straight, whole and clear of
  other lines at every zoom with every box open and with a node selected, on this portal, the
  portal with two edges more (`support/perturbedGraph.js`) and an adopter-sized graph in no layer
  ranks.
- `e2e/overview.spec.js` (support `overview.js`): the overview's routing, gaps, pills, titles,
  plates, grown and broken titles, the frame, the plan kept across zoom and opening, calm hover,
  tallies, and pure cases of the router and the pill search.
- `e2e/map.spec.js`: the levels, the budget and its counts, a filter composed with the level, the
  root's loops, marks keeping their size, the landscape without levels.
- `e2e/levels.spec.js` (support `levels.js`): opening by readability, the sibling rule, "+N", own
  lines on hover, selection framing and reduced motion, loops square, open-box titles never
  covered.
- `e2e/counts.spec.js` (support `counts.js`): for every node the "+N", the hover and the click name
  the same edges on the same lines; a click on every top-level box frames it whole, open, except
  a box holding a layer rule's boxes, which opens where they are readable, and its card says what
  it holds.
- `e2e/layer-boxes.spec.js` (support `layers.js`, BDL-080): a rule scoped to a box draws one box
  per layer inside it, titled and toned by the layer; the scope opens onto its layer boxes closed,
  titles inside, and a layer box opens once its parts are readable; lines between layers are
  drawn between their boxes; an edge the scoped rule finds against is drawn red between the layer
  boxes and as itself; a tap on the scope at the fit frames it whole and draws its layer boxes
  only once they are readable, with no title over another on the way in and out; a data file
  without every rule's keys draws no layer box.
- `e2e/metrics.spec.js` (support `metrics.js`): every PRD criterion of BDL-078 measured on this
  portal and the adopter-sized graph, including a box's activity reflecting its parts, and since
  BDL-080 the layer boxes' titles at 10 px or more, inside their boxes, on a tap on the scope and
  on a zoom into it.
- `e2e/performance.spec.js`: overview planning, bundling, the adopter-sized first drawing, zoom
  step, hover and frame bounds for the environment (see [the site's page](../vitepress-site.md)).
