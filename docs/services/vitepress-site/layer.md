# Layer (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/layer/`

---

## Overview

The layers of the architecture graph, read from the data file rather than named in code. A
version 2 file declares the project's layers at its top level, `layers: [{ name, rank, tag,
token }]`, and those names are what the legend, the Layer filter, the card and the impact
summary show. A file that declares none, version 1 among them, gives the layers as the
`layer_rank` values that occur, each named by the `layer` token of a node that declares it. A
layer's colour is a theme tone chosen by its position in the order, so a project whose layers are
called differently is coloured the same way. A node is drawn in its layer's tone: a border in it
over a tint of it at `LAYER_FILL_SHARE` (0.16), leaf or box alike (BDL-078). A node in no layer
takes `UNLAYERED_TONE`, VitePress's `--vp-c-text-2`, and is named `UNLAYERED_NAME` ("no layer");
`hasUnlayeredNode(nodes, layers)` tells the viewer whether any node is drawn that way, in which
case the legend adds a "no layer" item (`data-legend-unlayered`), headed `Layers:` when it is the
only one. The viewer asks it about every node but the box that holds everything, which is the
project's frame whatever its layer.

## Public API

- `layersOf(nodes, declared)` returns `[{ rank, name, tone }]`, top to bottom.
- `layerOfNode(node, layers)`, `layerToneOf(node, layers)`, `LAYER_TONES`, `UNLAYERED_TONE`
  (`text2`), `UNLAYERED_NAME`, `LAYER_FILL_SHARE`, `hasUnlayeredNode(nodes, layers)`.
- `LayerLegend` (Vue component): props `layers` and `unlayered` (Boolean); each sample is a
  swatch drawn as the canvas draws the layer, a border over a tint at `LAYER_FILL_SHARE`.

## Depends on

- `site-shared`, for the theme variables the legend swatches use.
