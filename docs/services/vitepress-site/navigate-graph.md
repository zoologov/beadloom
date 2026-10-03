# Navigate graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/navigate-graph/`

---

## Overview

How a reader moves around the graph. `NAVIGATION_OPTIONS` creates the graph with
`autoungrabify`, no box selection and Cytoscape's own selection off. Every node is pannable, which
passes a drag on it through to the viewport, so dragging never moves a node. "Arrange" is the
deliberate gesture for moving nodes: it makes the leaves grabbable, while a drag inside a box still
pans.

Fitting and centring leave out the part of the canvas something lies over. In the page the
viewer's panel covers the canvas's right edge, and a graph fitted to the whole canvas would put
what the reader asked for under it, so the caller reports that inset. A fit zooms in no closer
than `FIT_MAX_ZOOM`, so a lone node is framed rather than filling the canvas.

## Public API

- `NAVIGATION_OPTIONS`, `ZOOM_STEP`, `FIT_PADDING`, `FIT_MAX_ZOOM`.
- `useGraphNavigation(getCy, { getInset })` returns `arranging`, `applyArrangePolicy()`,
  `zoomIn()`, `zoomOut()`, `fit(selector)`, `centre(id)` and `toggleArrange()`. `fit` fits the
  visible elements the selector names, or everything visible; `centre` centres on a node, or on
  what is visible when no node is named. `getInset()` returns `{ right }` in pixels.
- `NavigationControls` (Vue component): prop `arranging`; events `zoom-in`, `zoom-out`, `fit`,
  `centre`, `arrange`.

## Depends on

- Nothing inside the site; Cytoscape is handed in by the caller.
