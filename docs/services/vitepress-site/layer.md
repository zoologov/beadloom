# Layer (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/layer/`

---

## Overview

The layers of the architecture graph, read from the data file rather than named in code. The
layers are the `layer_rank` values that occur, top to bottom, each named by the nodes that declare
that layer. A layer's colour is a theme tone chosen by its position in the order, so a project whose
layers are called differently is coloured the same way.

## Public API

- `layersOf(nodes)` returns `[{ rank, name, tone }]`.
- `layerOfNode(node, layers)`, `layerToneOf(node, layers)`, `LAYER_TONES`, `UNLAYERED_TONE`.
- `LayerLegend` (Vue component): prop `layers`.

## Depends on

- `site-shared`, for the theme variables the legend swatches use.
