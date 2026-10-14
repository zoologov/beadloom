# Graph edges (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/graph-edges/`

---

## Overview

The edge kinds the viewer draws, how each one looks, and which edges a walk follows.

- **Looks.** `part_of` is nesting, not a line. The drawn kinds each have one line style:
  `depends_on` solid, `uses` dotted, `consumes` and `produces` dashed with their own tones. Every
  line has one weight (BDL-078): kinds differ by colour and dash, never by width, and a dash
  pattern is in pixels on screen (`dashOf(look)`, `DOT_PATTERN` 1.5 / 2.5 px). A line at rest takes
  a share of its tone over the background (`strength`): an import 0.4 of `text1`, a light neutral
  the other kinds stand out from, every other kind 0.82. A `depends_on` edge the layer rule judged
  against the declared direction is a violation, drawn dashed in the full danger colour. A
  landscape contract edge is drawn by its look instead of its kind: healthy, drifting, broken or
  neutral. Each sample is a 1.35 px line in its dash ending in a 6 px head, in the colour the
  canvas gives that style at rest (`colours`, passed by the viewer).
- **The legend is the canvas's** (BDL-080 S4b, S4f). It is derived from the lines drawn at the
  level on the canvas now, not from the data file's edges: `legendKeysOf(styleKeys)` takes the
  style key of every visible line, the map's aggregated lines among them, and returns each style
  once, sorted. The viewer's `useGraphCanvas` notes those keys (`drawnStyles`) after every
  redraw, so the legend names every style the canvas shows at that level and no other. An
  aggregated line that carries edges of one style keeps that style's dash: `uses` is dotted at
  the overview too. One that carries several styles (`SEVERAL_STYLES`, from
  `site-shared-map-levels`) is drawn solid in the colour of the kind it carries most (RFC D8),
  and while such a line is drawn the legend adds an entry of its own (the owner's ruling of
  2026-10-10). Since BDL-082 S2c, by the owner's ruling of 2026-10-11, that is one entry per
  colour such lines are drawn in, `severalKindsOf(key)`: "several kinds, mostly uses at runtime"
  with a solid indigo sample, "several kinds, mostly depends on" with a solid grey one, and
  "several kinds, one of them a violation" where a line carries a violation. The single grey
  sample S4b drew stood for an indigo line it did not look like. `drawnStyles` now holds the
  styles of the lines of one style only and `drawnSeveral` the styles of the lines of several,
  so an entry is drawn exactly while a line in its colour and its dash is; the browser case
  compares the sample's colour and dash with the line's, not the entry's words. At a level that
  draws no such line no such entry is drawn. On this repository's portal the line
  `mcp-server -> doc-sync`, drawn solid indigo, carries two edges, `uses: mcp-server->doc-sync`
  and `depends_on: mcp-server->sync-check`, a tie the first of them decides (measured 2026-10-11).
- **Walks** (`model/adjacency.js`). A neighbourhood follows every drawn kind in the direction its
  arrow points (`adjacencyOf`). The impact walk goes from a node to what depends on it
  (`dependentsOf`), and a table names, per edge kind, the end that depends on the other. In the
  architecture that is the source of `depends_on`, `uses` and `consumes` (`DEPENDENT_ENDS`);
  `produces` is not followed. The landscape passes a table of its own. Only edges between two
  known nodes count, and a loop is left out.
- **Card groups.** `edgeGroupsOf` groups a node's drawn edges by kind and direction, outgoing
  before incoming, with the titles the card shows ("Depends on", "Depended on by", and so on), and
  marks a target when an edge to it is a violation.
- **A box's edges** (`model/boxEdges.js`, BDL-078 `beadloom-btkd.7`). `boxEdgesOf(box, edges,
  parents)` counts a box's edges to the outside as the map draws them, one line per node beside
  it: `{ inside, out, in }`, how many nodes it holds at any depth and, per node its lines reach,
  how many of its drawn edges go out to it and come in from it, in code-unit order. An edge onto a
  box that holds it is not counted. `null` when the box holds no node. The card of a selected box
  reads it.
- **How a line is drawn** (`lib/`, moved here from the graph viewer by BDL-080 S2a). `lineMarks.js`
  holds a line's marks and the size each keeps on screen: one weight (`LINE_MARKS`,
  `lineWidthOf`), a head of one length sized through Cytoscape's arrow formula inverted
  (`arrowScaleOf`, `headLengthOf`, `endHeadLength`), a dash on screen (`dashOnScreen`,
  `dashOffsetOf`) and the corners (`cornerRadiiOf`, `edgeCornerRadiiOf`, `routePointsOf`).
  `heads.js` decides where a drawn line carries an arrowhead: the ends its edges arrive at
  (`headEndsOf`), one head where lines share their last run (`droppedHeadsOf`), a head giving way
  to one too close beside it (`crowdedHeadsOf`, `departuresBeside`) and the room a head stands in
  (`headRoomsOf`, `HEAD_ROOM`). `edgePalette.js` gives each look's colours at rest, followed,
  behind (`BEHIND_SHARE` 0.4) and dimmed (`DIMMED_SHARE` 0.14), from resolved theme tokens
  (`edgePaletteOf`). How the viewer uses them is described under "Lines and arrowheads" in
  [the viewer's page](graph-viewer.md).

## Public API

- `EDGE_STYLES` (each entry with `strength`, and `dash` in pixels for a dashed look),
  `DRAWN_KINDS`, `VIOLATION_KEY`, `CONTAINMENT_KIND`, `DOT_PATTERN`, `contractStyleKey(look)`,
  `dashOf(look)`.
- `isDrawnKind(kind)`, `isViolation(edge)`, `styleKeyOf(edge)`, `legendKeysOf(styleKeys)` (the
  style keys of the lines drawn now; it took the data edges before BDL-080 S4b).
- `NEIGHBOURHOOD_KINDS`, `DEPENDENT_ENDS`, `DEPENDENCY_KINDS`, `edgeKeyOf(edge)`,
  `adjacencyOf(edges, kinds, ids)` returns `{ out, in }`, `dependentsOf(edges, dependentEnds, ids)`,
  `edgeGroupsOf(id, edges)`, `boxEdgesOf(box, edges, parents)`.
- `DIMMED_SHARE`, `edgePaletteOf(tokens)`.
- `HEAD_ROOM`, `NO_SOURCE_HEAD`, `NO_TARGET_HEAD`, `SAME_END`, `crowdedHeadsOf`,
  `departuresBeside`, `droppedHeadsOf`, `headEndsOf`, `headRoomsOf`.
- `LINE_MARKS`, `arrowScaleOf`, `cornerRadiiOf`, `dashOffsetOf`, `dashOnScreen`,
  `edgeCornerRadiiOf`, `endHeadLength`, `headLengthOf`, `lineWidthOf`, `routePointsOf`.
- `EdgeLegend` (Vue component): props `keys`, `colours` (style key -> its rest colour) and
  `several` (the style keys the lines of several kinds drawn now are drawn in; it renders one
  `[data-legend-several="<key>"]` entry per key, in that key's colour, solid). `SEVERAL_KINDS`
  is gone since BDL-082 S2c: `severalKindsOf(key)` in `model/edgeKinds.js` gives the look, which
  the legend imports from inside the slice.

## Depends on

- `site-shared`, for the theme variables the legend samples use and `mixRgb`.
- `site-shared-map-levels` (`AGGREGATE`, `STUB_AT`, `scaleOf`) and `site-shared-geometry`
  (`pathOfSegments`), read by the line marks and the heads.
