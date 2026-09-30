# Graph viewer (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/widgets/graph-viewer/`

---

## Overview

The viewer core, `GraphViewer`. Its root element is the viewer's own space: a toolbar, the canvas
and a collapsible panel, with the legend below them. That element is what goes full screen, so the
embedded view and full screen are one UI. In the page the panel lies over the canvas's right edge;
in full screen it sits beside the canvas.

- **Navigation.** Nodes are not grabbable and every node is pannable, so a drag anywhere pans,
  including inside a domain box. "Arrange" makes the leaves draggable. The toolbar zooms, fits and
  centres. Keys, while focus is in the viewer: `+` and `-` zoom, `0` fits, `f` toggles full
  screen, `Esc` clears the selection.
- **Colours.** The stylesheet (`lib/stylesheet.js`) is built from theme tokens resolved to literal
  `rgb(...)` values and rebuilt when VitePress switches between light and dark. A node's border and
  a box's tint are its layer's colour; a stale or violating node gets a warning or danger ring.
- **Edges.** One line style per kind, a violation red, dashed and thicker, a source end lighter
  than the target end, and a label on hover and on the selected node's edges. The curve style is
  `bezier`, chosen by measurement (below).
- **Filters and URL state.** The visible set comes from `filter-graph`; the state (filters, focus,
  depth, direction, mode) round-trips through the query string.
- **Test handle.** Under automation only (`navigator.webdriver`), `window.__beadloomViewer` exposes
  read-only state for the browser tests: visible ids, selection, positions, viewport, resolved
  colours and drawn edge styles (`model/testHandle.js`).

### The curve style, measured

Measured on this repository's graph on 2026-09-30, over every edge the viewer draws and the layout
it produces, sampling 60 points along the middle 80% of each edge and counting a point as shared when
another edge passes within 4 layout units of it:

| Curve style | Mean share of an edge's length shared with another edge | Edges more than half shared |
|-------------|----------------------------------------------------------|-----------------------------|
| `taxi` (vertical) | 0.407 | 119 |
| `taxi` inside a lane, `bezier` across lanes | 0.251 | 73 |
| `straight` | 0.172 | 30 |
| `bezier` | 0.157 | 22 |

`taxi` runs every edge that leaves a node down one trunk, so edges become indistinguishable where
they share it. `bezier` separates them best, and it is the viewer's curve style.

## Public API

- `GraphViewer` (Vue component). Props: `mode` (default `architecture`), `focus`, `depth`,
  `direction`, `height` (default `640px`). The URL query overrides the props. Slot `panel`, with
  `node`, `layerName`, `select(id)` and `close()`, shown for the selected node.
- `buildElements(nodes, edges, { parents, layers })`, `buildStylesheet(tokens)`, `CURVE_STYLE`.

## Depends on

- `site-filter-graph`, `site-navigate-graph`, `site-fullscreen`, `site-url-state` (features).
- `site-architecture-data`, `site-graph-node`, `site-graph-edge`, `site-layer` (entities).
- `site-shared`.

## Tests

The Playwright cases under `site/e2e/` drive this widget on the built architecture page: a pan
inside a domain box moves no node, Arrange, keys and buttons, colours in both themes, edge styles
and the legend, the filters, the URL state and full screen.
