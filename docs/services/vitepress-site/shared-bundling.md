# Shared bundling (component)

A segment of the `shared` layer of the VitePress site's Feature-Sliced layout, `part_of`
[`site-shared`](shared.md). The layout and the layer rule are described in
[the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/bundling/`

---

## Overview

A node's edges drawn as trunks, buses and joins instead of a staircase, rewritten from ELK's own
routes after the layout, so no node or box moves. ELK gives each edge of a node its own port and
channel, and a node with seventy edges leaves its side in a staircase as wide as the graph. The
segment came out of the graph viewer's `lib/` when BDL-080 S2a cut the viewer into slices. What
each rewrite does, and what it was measured to save, is described under "Trunks and buses" in
[the viewer's page](graph-viewer.md).

- `bundles.js` — `bundleRoutes(drawing, overrides)` runs the whole rewrite and returns
  `{ paths, trunks, buses, headRuns }`: every routed edge's route, bundled or as it was, and which
  edges share which. `BUNDLE_OPTIONS` holds the thresholds, among them `trunkDegree` 20,
  `busDegree` 2, `trunkStop` 8, `portShift` 3, `laneReach` 150, `headRun` 20, `headRunStep` 2
  and `headRunClearance` 8; `overrides` replace any of them.
- `bundleDrawing.js` — the drawing being rewritten: its containment, its boxes and each route's
  current version, indexed (`drawingOf`), so every rewrite is checked against the routes as they
  stand. A new segment may not cross a box or run along an edge with no end in common with it
  (`crossesABox`, `runsAlongAnother`).
- `buses.js` — `busesAt`: the edges leaving one side of a node in one direction start from the
  side's middle and share one channel in the first gap.
- `trunks.js` — `trunksOf`: a busy node's edges to one top-level box share one member's route to
  a distribution line just outside that box. Out-trunks are drawn before in-trunks.
- `joins.js` — `joinsAt`: an edge a trunk left in a lane of its own rides the box's main lane out
  past `laneReach`, then turns back to its own route.
- `headRuns.js` — `lengthenHeadRuns`: last, the lines arriving at one point of a node have their
  last bend moved back until the last run is `headRun` long, so an arrowhead fits.
  `lengthenLineEnds` does the same for an overview line drawn along its medoid.

The fallback throughout: an edge keeps its ELK route wherever a new segment would cross a box or
run along an unrelated edge.

## Public API

`shared/bundling/index.js`: `bundleRoutes`, `lengthenLineEnds`.

## Depends on

- `site-shared-geometry` (`gridIndex`, `lineIndex`, `orientationOf`, `segmentRect`).
- `site-shared` (`ids`, for `idRecord`).

Used by `site-overview-map` and `site-graph-viewer`.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `bundles.spec.js`
holds that no node or box moves, the fans keep at most a fifth of ELK's excess steps and busy
nodes leave each side in one channel per direction, importing `shared/bundling/bundles.js` into
the page for its pure cases. `heads.spec.js` holds the head runs, `overview.spec.js` imports
`shared/bundling/headRuns.js` for `lengthenLineEnds`, and `performance.spec.js` times the
bundling of the adopter-sized graph alone (bounds in [the site's page](../vitepress-site.md)).
