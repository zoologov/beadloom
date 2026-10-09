# Shared geometry (component)

A segment of the `shared` layer of the VitePress site's Feature-Sliced layout, `part_of`
[`site-shared`](shared.md). The layout and the layer rule are described in
[the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/geometry/`

---

## Overview

The plane geometry of the drawn graph. Every function here is pure: boxes, routes and points in,
numbers, ids or places out. The segment came out of the graph viewer's `lib/` when BDL-080 S2a
cut the viewer into slices (RFC D3). How the viewer uses each part is described in
[the viewer's page](graph-viewer.md).

- `routes.js` — ELK's routes as Cytoscape draws them: `centreOf(box)`, `pathOf(route)`,
  `segmentsOf(path, sourceCentre, targetCentre)` (a route's ends and corners relative to its
  nodes' centres), `pathOfSegments`, and `compoundSizeOf(box, childrenBox, inset, reach)`, which
  gives a compound node ELK's box whether a filter hides its children or not.
- `corners.js` — the radius a node's corners are drawn at: one size on screen,
  `NODE_CORNER_PX` (8 px), a quarter of the shorter side where that is less, and never over a
  line's end (`cornerRadiusOf`, `cornerRoomOf`, the data key `CORNER`).
- `spatialIndex.js` — `gridIndex(cellSize)` files a rectangle under the cells it covers, and
  `lineIndex(band)` files an axis-aligned segment under its orientation and band, so the bundling
  and a hover ask about a small window instead of every box and segment. Without them the
  bundling took 100 to 230 ms at adopter size; with the band index it took 17 ms against 85 ms for
  a cell index (measured in Node.js on an adopter-sized graph, recorded in the file).
- `routeIndex.js` — which drawn routes run through a point along one line (`routeIndexOf`,
  `routesAlong`), read from the routes alone, so a filter that hides a member leaves it out.
- `grownBoxes.js` — the overview's top-level nodes drawn larger than their layout to hold their
  titles: `grownBoxesOf`, `drawnBoxOf`, `crossesAny`, and `pathOutside`, where a line into a
  grown box stops.
- `aggregateRoutes.js` — `aggregateRouteOf(members, fromBox, toBox, closed)`: an aggregated
  line's route, the medoid of its members' ELK routes clipped between the two boxes, its last run
  into a closed box straightened where it was a short dogleg (`straightenedInto`).
- `pillPoints.js` and `pillPlaces.js` — where a line's count may stand: points tried along the
  line from its middle out (`candidatesOf`), and the placement in stages, clear of every node,
  title, arrowhead and other pill (`pillStagesOf`, `PILL_MARKS`: a pill 16 px high, 6 px padding,
  10.5 px text, 3 px gap).

## Public API

`shared/geometry/index.js`:

- `aggregateRouteOf`.
- `CORNER`, `cornerRadiusOf`, `cornerRoomOf`.
- `crossesAny`, `drawnBoxOf`, `grownBoxesOf`, `pathOutside`.
- `PILL_MARKS`, `pillStagesOf`.
- `routeIndexOf`, `routesAlong`.
- `centreOf`, `compoundSizeOf`, `pathOf`, `pathOfSegments`, `segmentsOf`.
- `gridIndex`, `lineIndex`, `orientationOf`, `segmentRect`.

## Depends on

- Nothing inside the site.

Used by `site-shared-bundling`, `site-shared-grid-routing`, `site-shared-map-levels`,
`site-graph-edges`, `site-follow-edge`, `site-overview-map`, `site-edge-pills` and
`site-graph-viewer`.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `routes.spec.js`
holds every edge drawn along its route and a box drawn at ELK's size, `look.spec.js` the rounded
corners, and `overview.spec.js` the grown titles and the pill search, the last by importing
`shared/geometry/pillPoints.js` into the page.
