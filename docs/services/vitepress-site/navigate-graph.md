# Navigate graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/navigate-graph/`

---

## Overview

How a reader moves around the graph: pan, zoom, fit and centre. `NAVIGATION_OPTIONS` creates the
graph with `autoungrabify`, no box selection and Cytoscape's own selection off. `panOnNodes()`
makes every node pannable, which passes a drag on it through to the viewport. No node is
grabbable, on any page and by any gesture, because the edges between the nodes are drawn from the
layout: a moved node would leave its routes behind. There is no control that moves nodes (an
earlier "Arrange" button was removed in BDL-077).

Fitting and centring leave out the part of the canvas something lies over. In the page the
viewer's panel covers the canvas's right edge, and a graph fitted to the whole canvas would put
what the reader asked for under it, so the caller reports that inset. A fit zooms in no closer
than `FIT_MAX_ZOOM`, so a lone node is framed rather than filling the canvas. A fit measures the
nodes' shapes and the edges' routes, not their labels or strokes (`shapesBoxOf`): the viewer's
map titles a closed box at a constant size on screen and draws every line at one width on screen,
so in graph units both grow as the view zooms out, and a fit measured with them would depend on
the zoom it was pressed at. The overview's lines run outside every node, which is why routes are
measured too (BDL-078). `fitZoom()` is the zoom a fit of everything visible would take now,
without moving the view; the viewer's map measures how far the reader has zoomed in from it.
Called as `fitZoom({ drawing })`, with a token that changes whenever what is drawn does, it is
measured once per drawing, canvas size and inset, because a zoom or a pan of one drawing moves
no shape (`beadloom-btkd.10`).

**Framing a selection** (BDL-078, owner's ruling 7). `frame({ box, focus, leastZoom },
{ animate })` frames a box in graph coordinates at no less than `leastZoom`, and where it does
not fit at that zoom, centres on `focus` instead. The viewer frames every selection this way, at
the zoom where the selected node is drawn as itself and readable. Animated, the move takes
`FRAME_MS` (350 ms, `ease-in-out-cubic`); a reader whose browser asks for reduced motion
(`prefers-reduced-motion: reduce`) is moved at once.

## Public API

- `NAVIGATION_OPTIONS`, `ZOOM_STEP`, `FIT_PADDING`, `FIT_MAX_ZOOM`.
- `useGraphNavigation(getCy, { getInset })` returns `panOnNodes()`, `zoomIn()`, `zoomOut()`,
  `fit(selector)`, `fitZoom({ drawing })`, `frame({ box, focus, leastZoom }, { animate })` and
  `centre(id)`. `panOnNodes` is called once the graph holds its
  nodes. `fit` fits the visible elements the selector names, or everything visible. `centre`
  centres on a node, or on what is visible when no node is named. `getInset()` returns
  `{ right }` in pixels.
- `NavigationControls` (Vue component): no props; events `zoom-in`, `zoom-out`, `fit`, `centre`.

## Depends on

- Nothing inside the site; Cytoscape is handed in by the caller.

## Tests

`src/beadloom/site_scaffold/e2e/navigation.spec.js`: a drag inside a domain box pans and moves no
node; no page offers a control that moves nodes; on the architecture page and on the landscape a
drag and a long press on a node pan the view and move no node, whatever toolbar button was
pressed before; the keys and the buttons zoom, fit and clear the selection. Framing a selection,
animated and with reduced motion, is held by `levels.spec.js` and `metrics.spec.js` on the
viewer.
