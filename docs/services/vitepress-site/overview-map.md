# Overview map (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/overview-map/`

---

## Overview

The map on the canvas: the overview's plan, the titles at the map's scale, the map's own lines,
and what it draws beyond a level for the pointer, a selection and the test handle. The decisions
are pure and live in `site-shared-map-levels` and `site-shared-grid-routing`; this slice applies
them to Cytoscape. The widget's `model/canvasMap.js` draws a level and calls into it. The slice
came out of the graph viewer's `model/` when BDL-080 S2a cut the viewer into slices. The rules it
draws are described under "The map" and "The overview" in [the viewer's page](graph-viewer.md).

- `model/overviewPlan.js` — `overviewPlanner(cy, { … })` returns `{ current, routeOf, isTop }`:
  the overview's lines routed together by the overview's own router at the scale of the
  whole-graph fit, around the plate of every title too wide for its box, with a top-level node
  too small for its title drawn at the least box that holds it. The plan is made from the
  overview whatever level is drawn and made again only when the edges the filters show, or the
  fit's scale on a resize, change, so a zoom or a box opened moves no line between two top-level
  nodes. `PROJECT_PLATE_SIDE` is where the project's plate stands. Since BDL-080 S4b and S4f:
  - a title on a plate is broken onto two lines where its name breaks, always, and the plan is
    made once (the owner's ruling of 2026-10-10). One node added to a wide box widened the frame
    of this repository's portal, the fit stepped one scale coarser, and three lines between
    other boxes ran under a third box's plate, one line wide (measured by S4b). An overview held
    at the smallest zoom keeps its plates one line wide. `report().broken` names a plated node
    whose plate title is broken too;
  - a node that an edge drawn as itself ends at is drawn larger only by a box that keeps that
    line outside it, its end on the border (`keepsOutside(box, paths)`), at the largest title
    size at which it does so, and is decided after the nodes no such line ends at. Otherwise
    its title, broken onto two lines, is drawn in its laid-out box where it fits there, and
    stands on a plate only where it does not;
  - a plate stands where no line drawn as itself runs under it, since no route moves such a
    line: above its box, then below, then beside it, and only then on a side clear of boxes and
    plates alone, or where it covers the least;
  - the lines keep inside the frame below the band the frame's title is drawn in
    (`routedFrameOf`), since a line routed through that band ran under the title at every zoom
    past the one where it reads inside the frame. The band is the title room less the room ELK
    keeps inside a box's border on its other sides, `BOX_SIDE`, which since BDL-080 S4h
    (`beadloom-af99.16`, the S4 review's M2) is imported from `shared/elk` rather than restated,
    so a change to ELK's padding moves the band with it;
  - `linesOf(id, hidden, broken)` is an input, `titleOf` takes a fourth argument, `broken`, and
    the planner returns `hiddenOf(id)`, how many of a node's lines the overview leaves out.
  Since BDL-080 S4i (`beadloom-af99.17`) the plan's scale is the one the viewer's fit lands on
  once the plan is drawn. The fit measures the drawn shapes, and a box the plan drew larger past
  the project box grew that box on both sides: on the `vue-fsd` portal the laid-out extent of
  812.6 units fitted at 1.25 and the drawn one of 845.1 units at 1.5625, so titles laid out at
  1.25 read 0.868 of their size, and a 10 px title under Linux's wider fonts read 8.57 px, under
  the floor (PR #98's CI). Every box the plan draws larger now keeps within
  `scaleKeepingBoxOf(unit)`, the laid-out extent grown on each side by half of what the fit takes
  before its zoom drops past the least one `scaleAt` gives the unit at (`leastZoomAt`); a title
  that box does not hold is broken or stands on a plate. As a second guard the plan is made
  again at the fit's scale of what it drew (`drawnExtentOf`: the boxes, the grown ones, the
  project box grown around them, every routed and own line), a step coarser each time and at
  most `REFITS` (3) times. Neither this repository's portal nor the two Feature-Sliced fixtures
  needed it, and the test handle reads the same on this portal before and after.
- `model/mapTitles.js` — `titleLooks(cy, { nodes, tree, geometry })`, how each title would be
  drawn, which the plan is made with, now with `linesOf`; `titleDresser(looks, planner, tree,
  geometry)`, which dresses the nodes with what the plan decided, a plate's title broken where
  the plan breaks it; and `scaleAt(zoom)`, the map's scale, a power of 1.25 (`SCALE_STEP`) near
  `1 / zoom`, so a zoom gesture restyles the marks only when it crosses a step. A node the plan
  draws larger keeps its drawn box only while that box covers no line of the file drawn as
  itself into it (`coversOwnLine`, from the map's drawing now). `closedRoomsOf(id, scale)`
  (BDL-080 S4b) is the room a top-level node takes drawn closed, open now or not: its box,
  drawn larger where the plan draws it so, with its border, and its title's plate. The pills of
  the lines between top-level nodes are placed around these rooms, so opening a box moves none
  of them.
- `model/aggregateElements.js` — `aggregateElements(cy, { … })`: the element that draws each
  aggregated edge and each node's own line, routed by the plan between two top-level nodes and
  along the medoid of its edges' routes otherwise, with its counts each way, its arrowheads and
  its look in its data: the style its edges are drawn in most, a violation's whenever one of
  them is one, and since BDL-080 S4b `SEVERAL_STYLES` when they are drawn in more than one,
  which the stylesheet draws solid; a line of one style keeps that style's dash. `SAID` is the
  data a line carries while it says a selection's walk;
  `weigh`, `talliesOf` and `isOwnLine` are the pure helpers the map's extras and tallies read.
- `model/mapExtras.js` — `mapExtras(cy, { … })`: the outward edges of a node under the pointer or
  selected, drawn as themselves where both ends are drawn at their laid-out size and otherwise as
  own lines, the stubs into an open box, and a selection's walk. Since BDL-080 S4f it draws a
  node's edges into an open box the same way (`reaches(id)`, from `reachingOf`), and
  `forcedIds()` names the nodes the test handle reveals with every edge of theirs, which are
  drawn as laid out. Each source names the nodes it exposes (`expose`, `setWalk`); `FORCED` is
  the test handle's source, which opens its boxes at any zoom.

## Public API

`features/overview-map/index.js`: `SAID`, `aggregateElements`, `isOwnLine`, `talliesOf`,
`weigh`, `FORCED`, `mapExtras`, `scaleAt`, `titleDresser`, `titleLooks`, `keepsOutside`
(BDL-080 S4f), `overviewPlanner`.

## Depends on

- `site-shared-map-levels`, `site-shared-grid-routing`, `site-shared-geometry`,
  `site-shared-bundling` (`lengthenLineEnds`), `site-shared-canvas-marks`, and `site-shared`
  (`ids`, and `shared/elk`'s `BOX_SIDE` since BDL-080 S4h).

Used by `site-graph-viewer` alone.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `overview.spec.js`
holds the overview's routing, titles, plates, grown and broken titles, the plan kept across zoom
and opening, and the calm hover; `map.spec.js` the levels, the budget and marks keeping their
size; `levels.spec.js` own lines on hover and stubs; and `performance.spec.js` times the overview
planning.
