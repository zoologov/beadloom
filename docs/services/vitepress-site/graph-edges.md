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
  neutral. The legend is derived from the drawn edges, so it cannot list a kind the canvas does
  not show; each sample is a 1.35 px line in its dash ending in a 6 px head, in the colour the
  canvas gives that style at rest (`colours`, passed by the viewer).
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

## Public API

- `EDGE_STYLES` (each entry with `strength`, and `dash` in pixels for a dashed look),
  `DRAWN_KINDS`, `VIOLATION_KEY`, `CONTAINMENT_KIND`, `DOT_PATTERN`, `contractStyleKey(look)`,
  `dashOf(look)`.
- `isDrawnKind(kind)`, `isViolation(edge)`, `styleKeyOf(edge)`, `legendKeysOf(edges)`.
- `NEIGHBOURHOOD_KINDS`, `DEPENDENT_ENDS`, `DEPENDENCY_KINDS`, `edgeKeyOf(edge)`,
  `adjacencyOf(edges, kinds, ids)` returns `{ out, in }`, `dependentsOf(edges, dependentEnds, ids)`,
  `edgeGroupsOf(id, edges)`, `boxEdgesOf(box, edges, parents)`.
- `EdgeLegend` (Vue component): props `keys` and `colours` (style key -> its rest colour).

## Depends on

- `site-shared`, for the theme variables the legend samples use.
