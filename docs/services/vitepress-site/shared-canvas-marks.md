# Shared canvas marks (component)

A segment of the `shared` layer of the VitePress site's Feature-Sliced layout, `part_of`
[`site-shared`](shared.md). The layout and the layer rule are described in
[the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/canvas-marks/`

---

## Overview

What the viewer marks the canvas with, and the canvas it draws on above Cytoscape's. The segment
came out of the graph viewer's `model/` when BDL-080 S2a cut the viewer into slices.

- `canvasMarks.js` — the names a selection and a hover set on the canvas, named once: the classes
  `SELECTION_CLASSES` (removed before the next selection is marked), `HOVERED`, `ALONG_HOVER`,
  `IN_FRONT`, `BEHIND`, the selector `HIGHLIGHTED_EDGES` of every followed edge, and the data key
  `DISTANCE_DATA`. `setClass(element, name, on)` and `giveData(element, values)` set a class or
  data only where it changes the element, because Cytoscape 3.34 restyles an element for every
  class it is given, changed or not. Kept apart from the canvas, these names can be read without
  loading it, which keeps the viewer's test handle loadable on a page of its own.
- `overlayCanvas.js` — `overlayCanvas(container, layer)`: a canvas laid over the container that
  takes no pointer event, for what Cytoscape cannot draw itself. `begin()` sizes it to the
  container at the screen's pixel ratio and wipes what it last drew, `inGraph(cy)` sets its
  context to draw in the graph's coordinates, `drew()` notes that a frame left something on it,
  and `remove()` takes it out of the page. A canvas left empty since it was last wiped is not
  wiped again, so an overlay with nothing to show costs no fill per frame.

## Public API

`shared/canvas-marks/index.js`: `ALONG_HOVER`, `BEHIND`, `DISTANCE_DATA`, `HIGHLIGHTED_EDGES`,
`HOVERED`, `IN_FRONT`, `SELECTION_CLASSES`, `giveData`, `setClass`, `overlayCanvas`.

## Depends on

- Nothing inside the site.

Used by `site-follow-edge`, `site-overview-map`, `site-edge-pills` and `site-graph-viewer`.

## Tests

No spec is declared on this node; the specs of `site-graph-viewer` drive it. `look.spec.js`
reads the followed lines and the overlay layers through the test handle's `overlayLayers` and
`followed`, and `overview.spec.js` the calm hover that `IN_FRONT` and `BEHIND` mark.
