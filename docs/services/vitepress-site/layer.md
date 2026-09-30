# Layer (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/layer/`

---

## Overview

The layers of the architecture graph, read from the data file rather than named in code. A
version 2 file declares the project's layers at its top level, `layers: [{ name, rank, tag,
token }]`, and those names are what the legend, the Layer filter, the card and the impact
summary show. A file that declares none, version 1 among them, gives the layers as the
`layer_rank` values that occur, each named by the `layer` token of a node that declares it. A
layer's colour is a theme tone chosen by its position in the order, so a project whose layers are
called differently is coloured the same way. A node in no layer is grey.

## Public API

- `layersOf(nodes, declared)` returns `[{ rank, name, tone }]`, top to bottom.
- `layerOfNode(node, layers)`, `layerToneOf(node, layers)`, `LAYER_TONES`, `UNLAYERED_TONE`.
- `LayerLegend` (Vue component): prop `layers`.

## Depends on

- `site-shared`, for the theme variables the legend swatches use.
