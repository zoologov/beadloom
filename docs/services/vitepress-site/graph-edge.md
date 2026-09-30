# Graph edge (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/graph-edge/`

---

## Overview

The edge kinds the viewer draws, how each one looks, and which edges a walk follows.

- **Looks.** `part_of` is nesting, not a line. The drawn kinds each have one line style:
  `depends_on` solid, `uses` dotted, `consumes` and `produces` dashed with their own tones. A
  `depends_on` edge the layer rule judged against the declared direction is a violation, drawn
  red, dashed and thicker. A landscape contract edge is drawn by its look instead of its kind:
  healthy, drifting, broken or neutral. The legend is derived from the drawn edges, so it cannot
  list a kind the canvas does not show.
- **Walks** (`model/adjacency.js`). A neighbourhood follows every drawn kind in the direction its
  arrow points (`adjacencyOf`). The impact walk goes from a node to what depends on it
  (`dependentsOf`), and a table names, per edge kind, the end that depends on the other. In the
  architecture that is the source of `depends_on`, `uses` and `consumes` (`DEPENDENT_ENDS`);
  `produces` is not followed. The landscape passes a table of its own. Only edges between two
  known nodes count, and a loop is left out.
- **Card groups.** `edgeGroupsOf` groups a node's drawn edges by kind and direction, outgoing
  before incoming, with the titles the card shows ("Depends on", "Depended on by", and so on), and
  marks a target when an edge to it is a violation.

## Public API

- `EDGE_STYLES`, `DRAWN_KINDS`, `VIOLATION_KEY`, `CONTAINMENT_KIND`, `contractStyleKey(look)`.
- `isDrawnKind(kind)`, `isViolation(edge)`, `styleKeyOf(edge)`, `legendKeysOf(edges)`.
- `NEIGHBOURHOOD_KINDS`, `DEPENDENT_ENDS`, `DEPENDENCY_KINDS`, `edgeKeyOf(edge)`,
  `adjacencyOf(edges, kinds, ids)` returns `{ out, in }`, `dependentsOf(edges, dependentEnds, ids)`,
  `edgeGroupsOf(id, edges)`.
- `EdgeLegend` (Vue component): prop `keys`.

## Depends on

- `site-shared`, for the theme variables the legend samples use.
