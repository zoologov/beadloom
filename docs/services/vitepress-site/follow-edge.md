# Follow edge (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/follow-edge/`

---

## Overview

Following a line through a busy area: the reader sees it whole, drawn again on top of what it
crosses, and lines that share a run end in one arrowhead. The slice came out of the graph viewer's
`model/` when BDL-080 S2a cut the viewer into slices. What a followed line looks like, and why
there are no bridges, is described under "Followed lines" and "Lines and arrowheads" in
[the viewer's page](graph-viewer.md).

- `model/followedOverlay.js` — `followedOverlay(cy, container, { tokens })`: the layer `followed`
  over Cytoscape's canvas (`site-shared-canvas-marks`, `overlayCanvas`). The lines the canvas
  marks as followed (`HIGHLIGHTED_EDGES`: the walk's edges, the edges along the hovered line, the
  lines of the hovered node and the ones brought in front) are drawn again in their full colour
  over a casing in the canvas's background colour, in passes: every casing, then every line, then
  the arrowheads, then the title of each open box a followed line runs through, then the label of
  the edge under the pointer. It returns `{ refresh, followed, labelled, frames, destroy }`;
  `followed()` gives the lines and the passes the test handle reads.
- `model/sharedLines.js` — `sharedLines(cy, paths, { scale })`: the edges along a hovered line
  (every drawn route through the hovered point along the same line, from `site-shared-geometry`'s
  route index), one arrowhead per shared last run with the others ending at its base, a head
  giving way to a neighbour too close on one border, and the room each head has before its last
  corner. It returns `{ refresh, along, droppedHeads }`; `refresh()` is called whenever a filter,
  a selection, a level or the map's scale changes what is drawn.

## Public API

`features/follow-edge/index.js`: `followedOverlay`, `sharedLines`.

## Depends on

- `site-graph-edges` (entities): the line marks and the head rules (`lib/lineMarks.js`,
  `lib/heads.js`).
- `site-shared-canvas-marks`, `site-shared-geometry`, `site-shared-map-levels`, and
  `site-shared` (`theme-tokens`, `mixRgb`).

Used by `site-graph-viewer` alone, which is the cut's intended shape: Steiger's
`fsd/insignificant-slice` is switched off for this reason (see [the site's
page](../vitepress-site.md)).

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `look.spec.js` holds
the followed lines on top over a casing, a label only on hover, and one head per shared last run;
`heads.spec.js` holds every arrowhead whole and clear of other lines; and `bundles.spec.js` that
hovering a shared line names its edges.
