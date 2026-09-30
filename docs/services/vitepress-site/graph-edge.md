# Graph edge (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/graph-edge/`

---

## Overview

The edge kinds the viewer draws and how each one looks. `part_of` is nesting, not a line. The
others each have one line style: `depends_on` solid, `uses` dotted, `consumes` and `produces` dashed
with their own tones. A `depends_on` edge the layer rule judged against the declared direction is a
violation, drawn red, dashed and thicker. The legend is derived from the drawn edges, so it cannot
list a kind the canvas does not show.

## Public API

- `EDGE_STYLES`, `VIOLATION_KEY`, `CONTAINMENT_KIND`.
- `isDrawnKind(kind)`, `isViolation(edge)`, `styleKeyOf(edge)`, `legendKeysOf(edges)`.
- `EdgeLegend` (Vue component): prop `keys`.

## Depends on

- `site-shared`, for the theme variables the legend samples use.
