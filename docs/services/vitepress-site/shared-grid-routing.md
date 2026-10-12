# Shared grid routing (component)

A segment of the `shared` layer of the VitePress site's Feature-Sliced layout, `part_of`
[`site-shared`](shared.md). The layout and the layer rule are described in
[the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/grid-routing/`

---

## Overview

The overview's own router. At the overview every top-level box is closed, and the medoid of a
pair's ELK routes runs beside the next pair's, under a title and into its box after a bend too
close for an arrowhead. So every line between two top-level ends is routed again, all of them
together, between the fixed boxes; no box moves. The segment came out of the graph viewer's
`lib/` when BDL-080 S2a cut the viewer into slices. The rules the router keeps, and what they
were measured to change, are described under "The overview" in [the viewer's page](graph-viewer.md).

- `overviewGrid.js` — `gridOf(boxes, plates, marks, degree, cores, frame)`: the tracks the lines
  run on, at least a pitch apart, each box an obstacle with a half-pitch margin and a halo only
  its own lines enter, straight at it, and each box's ports on the straight part of a side, clear
  of its rounded corners (`sideRange`, read from `site-shared-geometry`'s `cornerRadiusOf`). The
  box that holds everything is a frame the lines keep inside.
- `overviewRoutes.js` — `planOverview(input, marks)`: A* over the cells and the direction a line
  enters them in, a route costing its length plus each bend, crossing and run beside another
  line, and a title's plate priced so high that a line runs under one only where no other way
  reaches its box. Lines are routed shortest span first and then each once more. Two lines never
  share a track, except that lines ending at one box that agree on having an arrowhead there may
  share their last run. `OVERVIEW_MARKS` holds the sizes at the fit: `pitch` 8, `halo` 14, `run`
  15, `corner` 6, `head` 6, `between` 2.

  **A line drawn as itself keeps its head (BDL-080 S4f).** A fixed line, one the level draws as
  itself and no route moves, is marked on the grid (`markFixed`) on the tracks within reach of
  it and, where a planned line crossing it would run under an arrowhead, on the tracks on each
  side of it as well: on a box's stem, and along its own last run, `run` back from its tip.
  A planned line crosses it there only on the second, relaxed routing, priced as
  `FIXED_HEAD_REFUSALS` (8) refusals, since a head shrunk or crossed reads worse than a detour
  through halos and margins. Measured: before it, a crossing a few pixels from a tip left a
  head of a planned line at 3.57 px on one portal; at a price of 3 refusals a line still
  crossed a fixed line 10 layout units from its tip, and at 8 it went round.

  **Since BDL-082 S2c** (`beadloom-us5r.1`) the plan routes every edge drawn as itself between
  two top-level nodes too, so fixed lines are rare: a loop. Two rules came with it. A box drawn
  larger keeps a port through the middle of its laid-out box however near a corner of the drawn
  box that stands (`sideRange`): a laid-out box 9 px wide standing at the side of the box drawn
  around it had the corner's arc cover every track through it, and no port on that axis, so the
  five lines of the `tui` box on this repository's graph with two edges more found no route; the
  drawn box's corner takes the room the line's end leaves it, as any node's does. And the input
  takes `reserved`, the points where an edge of the file ends on the border of a top-level box
  itself, as ELK routes it, and no port lies within a pixel of one (`clearOfReserved`,
  `RESERVED_REACH`): ELK brings such an edge into the middle of the box's side and a track runs
  through every side's middle, so a planned line ended at the very point where a selected
  node's edge drawn as itself, 8 layout units after a bend, shared its arrowhead (measured: a
  bend 4.09 px behind a head of 2.99 px at zoom 0.545). A reach of half a pitch took ports a
  crowded box needed and left a line unrouted, so it is one pixel.

## Public API

`shared/grid-routing/index.js`: `OVERVIEW_MARKS`, `planOverview`.

## Depends on

- `site-shared-geometry` (`cornerRadiusOf`).

Used by `site-overview-map`, which runs the router on the canvas.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `overview.spec.js`
holds the overview's routing, gaps and plates on this portal, and runs pure cases of the router
by importing `shared/grid-routing/overviewRoutes.js` into the page. `performance.spec.js` times
the planning on this portal and the adopter-sized graph.
