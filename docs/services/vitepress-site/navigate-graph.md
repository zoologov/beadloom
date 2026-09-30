# Navigate graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/features/navigate-graph/`

---

## Overview

How a reader moves around the graph. `NAVIGATION_OPTIONS` creates the graph with
`autoungrabify`, no box selection and Cytoscape's own selection off. Every node is pannable, which
passes a drag on it through to the viewport, so dragging never moves a node. "Arrange" is the
deliberate gesture for moving nodes: it makes the leaves grabbable, while a drag inside a box still
pans.

## Public API

- `NAVIGATION_OPTIONS`, `ZOOM_STEP`, `FIT_PADDING`.
- `useGraphNavigation(getCy)` returns `arranging`, `applyArrangePolicy()`, `zoomIn()`, `zoomOut()`,
  `fit()`, `centre(id)` and `toggleArrange()`.
- `NavigationControls` (Vue component): prop `arranging`; events `zoom-in`, `zoom-out`, `fit`,
  `centre`, `arrange`.

## Depends on

- Nothing inside the site; Cytoscape is handed in by the caller.
