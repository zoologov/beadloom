# Graph viewer (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/graph-viewer/`

---

## Overview

The viewer core, `GraphViewer`. Its root element is the viewer's own space: a toolbar, the canvas
and a collapsible panel, with the legend below them. That element is what goes full screen, so the
embedded view and full screen are one UI. In the page the panel lies over the canvas's right edge;
in full screen it sits beside the canvas.

- **Two modes** (`model/modes.js`). One core draws the architecture graph, from
  `architecture.data.json`, and the landscape of contracts between services, from
  `landscape.data.json`. A mode names only what differs: the data file and how it becomes nodes and
  edges, the filters in its slot of the toolbar and the set they show, and its impact walk. The
  mode is the page's prop and the URL does not carry it, because the two modes are two pages with
  two different cards.
- **Selection.** A selected node is the start of a walk. In the neighbourhood the walk goes to the
  chosen depth and direction (`site-select-neighbourhood`); with **Impact** on it goes to
  everything that depends on the node, without a limit, by the mode's walk (`site-impact-view`).
  What the walk leaves out is dimmed, or hidden when the reader asks, and the containers of what
  it reached stay. A selection made anywhere but on the canvas, from the URL, the card or the
  impact list, is framed so that the walk is in view.
- **Panel.** It shows what the page puts in its `panel` slot for the selected node and, in impact
  mode, the impact summary above it. A widget does not import another, so the page composes the
  card. Each viewer gets its own panel id (`usePanelId`), so two viewers on one page do not share
  the toolbar's "Panel" button.
- **Navigation.** Nodes are not grabbable and every node is pannable, so a drag anywhere pans,
  including inside a domain box. "Arrange" makes the leaves draggable. The toolbar zooms, fits and
  centres, and fitting and centring leave out the part of the canvas the open panel covers. Keys,
  while focus is in the viewer: `+` and `-` zoom, `0` fits, `f` toggles full screen, `Esc` clears
  the selection.
- **Colours.** The stylesheet (`lib/stylesheet.js`) is built from theme tokens resolved to literal
  `rgb(...)` values and rebuilt when VitePress switches between light and dark. A node's border and
  a box's tint are its layer's colour; a status adds the border `NODE_STATUSES` names. On the
  landscape, which has no layers, a node's border is its health. In impact mode a node's fill takes
  its distance ring's tone and a risky node carries a dashed danger outline.
- **Edges.** One line style per kind, a violation red, dashed and thicker, a broken or drifting
  contract as heavy as a violation with its verdict as a badge, a source end lighter than the
  target end, and a label on hover and on the selected node's edges. The curve style is `bezier`,
  chosen by measurement (below).
- **URL state.** The filters, the selection, depth, direction, dim or hide, and the neighbourhood
  or impact view round-trip through the query string (`site-url-state`). The URL overrides the
  props.
- **Test handle.** Under automation only (`navigator.webdriver`), `window.__beadloomViewer` exposes
  read-only state for the browser tests: visible ids, selection and state, positions, viewport,
  resolved colours, node status looks, drawn edge styles and arrows, the neighbourhood, the dimmed
  nodes, the impact rings, risks and summary (`model/testHandle.js`). The handle is the last
  viewer's to install it, and a viewer that leaves the page removes only its own.

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

- `GraphViewer` (Vue component). Props: `mode` (`architecture`, the default, or `landscape`),
  `focus`, `depth`, `direction`, `height` (default `640px`). Slot `panel`, shown for the selected
  node, with `node`, `layerName`, `edges`, `layers`, `contracts`, `select(id)` and `close()`.
- `buildElements(nodes, edges, { parents, layers })`, `buildStylesheet(tokens)`, `CURVE_STYLE`.

## Depends on

- `site-filter-graph`, `site-navigate-graph`, `site-select-neighbourhood`, `site-impact-view`,
  `site-fullscreen`, `site-url-state` (features).
- `site-architecture-data`, `site-landscape-data`, `site-graph-node`, `site-graph-edge`,
  `site-layer` (entities).
- `site-shared`.

## Tests

`src/beadloom/site_scaffold/e2e/colours.spec.js` and
`src/beadloom/site_scaffold/e2e/graph-viewer-instances.spec.js` are declared on this node:
colours in both themes, and two viewers on one page, each with its own panel id and test
handle. The other Playwright specs drive this widget too, and each is declared on the slice it
tests.
