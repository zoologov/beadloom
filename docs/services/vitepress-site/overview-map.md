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
  nodes. `PROJECT_PLATE_SIDE` is where the project's plate stands.
- `model/mapTitles.js` — `titleLooks(cy, { nodes, tree, geometry })`, how each title would be
  drawn, which the plan is made with; `titleDresser(looks, planner, tree)`, which dresses the
  nodes with what the plan decided; and `scaleAt(zoom)`, the map's scale, a power of 1.25
  (`SCALE_STEP`) near `1 / zoom`, so a zoom gesture restyles the marks only when it crosses a step.
- `model/aggregateElements.js` — `aggregateElements(cy, { … })`: the element that draws each
  aggregated edge and each node's own line, routed by the plan between two top-level nodes and
  along the medoid of its edges' routes otherwise, with its counts each way, its arrowheads and
  its look in its data. `SAID` is the data a line carries while it says a selection's walk;
  `weigh`, `talliesOf` and `isOwnLine` are the pure helpers the map's extras and tallies read.
- `model/mapExtras.js` — `mapExtras(cy, { … })`: the outward edges of a node under the pointer or
  selected, drawn as themselves where both ends are drawn at their laid-out size and otherwise as
  own lines, the stubs into an open box, and a selection's walk. Each source names the nodes it
  exposes (`expose`, `setWalk`); `FORCED` is the test handle's source, which opens its boxes at
  any zoom.

## Public API

`features/overview-map/index.js`: `SAID`, `aggregateElements`, `isOwnLine`, `talliesOf`,
`weigh`, `FORCED`, `mapExtras`, `scaleAt`, `titleDresser`, `titleLooks`, `overviewPlanner`.

## Depends on

- `site-shared-map-levels`, `site-shared-grid-routing`, `site-shared-geometry`,
  `site-shared-bundling` (`lengthenLineEnds`), `site-shared-canvas-marks`, and `site-shared`
  (`ids`).

Used by `site-graph-viewer` alone.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `overview.spec.js`
holds the overview's routing, titles, plates, grown and broken titles, the plan kept across zoom
and opening, and the calm hover; `map.spec.js` the levels, the budget and marks keeping their
size; `levels.spec.js` own lines on hover and stubs; and `performance.spec.js` times the overview
planning.
