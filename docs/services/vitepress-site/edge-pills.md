# Edge pills (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/edge-pills/`

---

## Overview

The map's counts drawn over the canvas. Cytoscape draws an edge's label with its edge, so the next
edge drawn paints over it; these counts are drawn instead on a canvas of their own, the layer
`pills`, above every line, the followed ones included. The slice came out of the graph viewer's
`model/` when BDL-080 S2a cut the viewer into slices. When a line says its count and where the
pill stands are described under "Counts" in [the viewer's page](graph-viewer.md).

- `model/pillOverlay.js` — `pillOverlay(cy, container, { tokens, map })` returns `{ pills,
  tallies, destroy }`. It draws:
  - **a line's count on a pill**, an opaque rounded label with a thin border in the line's
    colour, at the place `site-shared-geometry`'s `pillStagesOf` finds on its line, worked out
    again only when what is drawn or the step of the map's scale changes. While the pointer rests
    on a node, every other pill is faded, as their lines are;
  - **a closed box's tally**, `in N · out M` in its lower right corner once the box is large
    enough on screen, the edges the budget leaves out included;
  - **a node's "+N"**, the count of its outward edges, on a badge across the middle of its right
    side.

## Public API

`features/edge-pills/index.js`: `pillOverlay`.

## Depends on

- `site-graph-edges` (entities): `headEndsOf`, `headLengthOf` and `routePointsOf`, so a pill
  leaves the arrowheads whole.
- `site-shared-geometry` (`PILL_MARKS`, `pillStagesOf`), `site-shared-map-levels`,
  `site-shared-canvas-marks` (`overlayCanvas`, `IN_FRONT`, `BEHIND`), and `site-shared` (`ids`).

Used by `site-graph-viewer` alone.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `overview.spec.js`
holds the pills and the tallies at the overview and the pure cases of the pill search;
`counts.spec.js` that the "+N", the hover and the click name the same edges on the same lines;
and `metrics.spec.js` that opening a box moves no pill.
