# Shared map levels (component)

A segment of the `shared` layer of the VitePress site's Feature-Sliced layout, `part_of`
[`site-shared`](shared.md). The layout and the layer rule are described in
[the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/map-levels/`

---

## Overview

The map's levels and the sizes its marks keep. The whole-graph view is drawn like a map: a box
is open or closed, a level is a set of open boxes, and nothing is laid out again between levels.
This segment decides which boxes are open, what each node is drawn as and which edges are drawn
between them; the viewer draws the level on Cytoscape (`site-graph-viewer`, `model/canvasMap.js`).
The rules it implements are described under "The map" in [the viewer's page](graph-viewer.md).
The segment came out of the graph viewer when BDL-080 S2a cut the viewer into slices, and four
names moved into it so that the layering is clean: `GEOMETRY`, `drawnSizeOf` and `rimOf` from the
viewer's stylesheet, `FIT_PADDING` and `FIT_MAX_ZOOM` from `site-navigate-graph`, and `OWN_LINE`
from the map's lines.

- `levels.js` — the levels, pure: the containment tree (`boxTreeOf`, `holdersOf`,
  `boxesHolding`, `boxesRevealing`, `isWithinAny`), the sibling rule (`levelOf`), a node's outward
  edges and its own lines (`outwardOf`, `outwardOfOpen`, `ownLinesOf`), the budget (`budgetOf`),
  what is readable opens (`smallestChildOf`, `openInView`, `zoomDrawingOf`), and what a selection
  needs opened (`selectionReveals`). `LEVEL_OPTIONS`: a box opens when its smallest child is at
  least 24 px tall on screen (`readable`) and the zoom is past 1.3 times the whole-graph fit
  (`fitFloor`); it closes below 0.9 of that (`closeShare`); a level draws at most 100 aggregated
  edges (`budget`). The fit those numbers are measured from is `FIT_PADDING` (40 px) and
  `FIT_MAX_ZOOM` (1.5). It also names the classes and data keys the map sets: `COLLAPSED`,
  `PROJECT_BOX`, `STACK_LANES`, `LAYER_BOX`, `AGGREGATE`, `HIDDEN_EDGES`, `MAP_SCALE`, `LOOP_END`,
  `LOOP_OF`, `LOOP_BOX`, `STUB_AT`, `OWN_LINE` and, since BDL-080 S4b, `SEVERAL_STYLES`, the data
  an aggregated edge carries when its edges are drawn in more than one style; and
  `endsOfLine(line)`.
- `mapMarks.js` — the map's marks and the size each keeps on screen, pure: a title tried inside
  its box at 14, 12.5, 11 and 10 px (`MAP_MARKS.titleSizes`), a plate where none fits
  (`plateOf`, `PLATE_SIDES`), a name broken onto two lines (`brokenLabelOf`), the least box that
  holds a title (`titleBoxOf`), a closed box's status mark (`statusMarkOf`, `boxMarkOf`), and the
  data keys `MAP_TITLE`, `MAP_BOX`, `TALLY` and `OUTWARD`. `scaleOf(element)` reads the map's
  scale an element carries.
- `nodeSizes.js` — a node's sizes in layout units (`GEOMETRY`: a card 163 by 47 with its border,
  the room an open box keeps above its children for its title, `boxTitleRoom` 36, and the borders
  and status mark); `drawnSizeOf`, the size a node's shape is drawn at, read from its data as
  the stylesheet sizes it; and `rimOf`, how far its border reaches outside that shape (none for
  the project's frame, whose border is drawn inside). The stylesheet, the layout's title room and the map's titles, pills and corners each
  read one number here.
- `loopLines.js` — `loopLines(cy, geometry, { isLoop, taken })`: an edge from a node to a box
  that holds it drawn square along its ELK route, by a line of its own to an invisible end on the
  box's border, instead of Cytoscape's compound loop across the box.

## Public API

`shared/map-levels/index.js`:

- From `levels.js`: `AGGREGATE`, `COLLAPSED`, `FIT_MAX_ZOOM`, `FIT_PADDING`, `HIDDEN_EDGES`,
  `LAYER_BOX`, `LEVEL_OPTIONS`, `LOOP_BOX`, `LOOP_END`, `LOOP_OF`, `MAP_SCALE`, `OWN_LINE`,
  `PROJECT_BOX`, `SEVERAL_STYLES`, `STACK_LANES`, `STUB_AT`, `boxTreeOf`, `boxesHolding`, `boxesRevealing`,
  `budgetOf`, `endsOfLine`, `holdersOf`, `isWithinAny`, `levelOf`, `openInView`, `outwardOf`,
  `outwardOfOpen`, `ownLinesOf`, `selectionReveals`, `smallestChildOf`, `zoomDrawingOf`.
- `loopLines`.
- From `mapMarks.js`: `MAP_BOX`, `MAP_MARKS`, `MAP_TITLE`, `OUTWARD`, `PLATE_SIDES`, `TALLY`,
  `boxMarkInsetOf`, `boxMarkOf`, `brokenLabelOf`, `mapTitleOf`, `plateLiftOf`, `plateOf`,
  `scaleOf`, `statusMarkInsetOf`, `statusMarkOf`, `titleBoxOf`, `titleOf`.
- From `nodeSizes.js`: `GEOMETRY`, `drawnSizeOf`, `rimOf`.

## Depends on

- `site-shared-geometry` (`pathOf`, `segmentsOf` for the loop lines).
- `site-shared` (`ids`, for `freshId`).

Used by `site-graph-edges`, `site-navigate-graph`, `site-follow-edge`, `site-overview-map`,
`site-edge-pills`, `site-node-card` (`boxTreeOf`) and `site-graph-viewer`. It is the largest
shared segment: 56 owned symbols against the `shared` layer's cohesion limit of 60, measured by
BDL-080 S2d at `d99dfd0e`.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `levels.spec.js`
holds opening by readability, the sibling rule, "+N" and own lines; `map.spec.js` the levels and
the budget, importing `shared/map-levels/levels.js` into the page for `budgetOf`; and
`counts.spec.js` that the "+N", the hover and the click name the same edges.
