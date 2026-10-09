# Shared (component)

The `shared` layer of the VitePress site's Feature-Sliced layout: the container of its segments.
The layout and the layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/`

---

## Overview

The segments every other layer may use. In Feature-Sliced Design `shared` has segments rather than
slices. This node owns the segments listed below. Since BDL-080 S2a five more are nodes of their
own, each `part_of` this one and tagged `fsd-shared`, so that they import each other as peers
inside one tagged container, which `site-fsd-layers` allows:
[`site-shared-geometry`](shared-geometry.md), [`site-shared-canvas-marks`](shared-canvas-marks.md),
[`site-shared-bundling`](shared-bundling.md), [`site-shared-grid-routing`](shared-grid-routing.md)
and [`site-shared-map-levels`](shared-map-levels.md). Their files came out of the graph viewer. A
segment uses another only through that segment's `index.js`, as every other layer does.

- `lib`: `isBrowser()`, `createJsonResource(path, validate)` (one fetch per file and page load),
  the tree walks `childrenOf`, `withAncestors` and `subtreeOf`, `breadthFirst(start, step,
  maxDepth)`, the walk the neighbourhood and the impact mode both run with a step of their own,
  and `shellQuote(word)`, which quotes a word for a POSIX shell so that a copied command names
  what it shows.
- `theme-tokens`: resolves the VitePress CSS variables to opaque `rgb(...)` through
  `getComputedStyle`, flattening a translucent colour over the background, and `useThemeTokens`
  re-resolves them when VitePress toggles dark mode. Cytoscape rejects `var(...)` and draws its
  fallback grey, `rgb(153,153,153)`, which is why no variable reaches it. Since BDL-080 S1c the
  segment also defines the one tone the VitePress palette has no variable for, the sixth layer
  tone `cyan` (`--bl-c-cyan-1`, `tones.css`, loaded by the segment's `index.js`): `#0e7490` in
  the light theme, 5.4:1 on the canvas, and `#22d3ee` in the dark theme, 9.5:1. The palette's
  brand colour is its indigo unless a project sets it, and its sponsor pink keeps 2.78:1 against
  a tinted box in the dark theme, under the 3:1 a boundary needs. Since BDL-080 S2a it also holds
  `RING_TONES` (`ringTones.js`), the tone of each impact distance ring from the selected node
  outwards (`brand`, `red`, `yellow`, `green`, `purple`, `gray`): the base colours rather than the
  semantic ones, since VitePress defines `warning` as `yellow` and `danger` as `red`. The viewer's
  stylesheet and the impact summary's legend both read them here.
- `cytoscape`: `loadCytoscape()` imports Cytoscape in the browser only, once. It loads Cytoscape
  alone: the layout is not Cytoscape's.
- `elk`: the layered layout, run by elkjs 0.12 in a Web Worker so that the page's main thread is
  never held by it. `elkGraphOf({ nodes, edges, boxTop })` builds the ELK graph with the fixed options
  `LAYERED_OPTIONS` (layered, direction down, orthogonal edge routing, `INCLUDE_CHILDREN`, each
  node's layer rank as its partition) and asks for every box and section in root coordinates
  (`elk.json.shapeCoords` and `elk.json.edgeCoords` set to `ROOT`). Every box carries its own
  padding, `[top=boxTop, left=12, bottom=12, right=12]`: ELK's own 12 units on three sides and
  `boxTop` above its children, the room its title is drawn in, 12 when none is given (BDL-078
  `beadloom-btkd.6`; the viewer passes 36, `GEOMETRY.boxTitleRoom`), so no child stands under
  an open box's title.

  **Partitions pin lanes among the root's children only.** Measured on elkjs 0.12 by BDL-080
  S1c: with `INCLUDE_CHILDREN`, ELK reads no partition of a node inside a box. Three children of
  one box in partitions 2, 0 and 1, with no edge between them, are laid out in one row, whether or
  not the box activates partitioning itself. On this repository every node is inside the frame
  `beadloom`, so lanes under the frame have only ever come from the edges' topology. A box that
  asks for its children to be stacked (`stack`) therefore gets layout-only lane edges
  (`LANE_EDGE`, `"lane"`) from each child of a partition to each child of the next partition
  present, which puts each partition below the one above it. They are no edge of the drawing:
  `geometry.js` leaves them out of the routes. The viewer asks for `stack` only on a box holding
  a scoped rule's layer boxes, so their number does not grow with a domain's children; five lane
  edges on this repository. Nothing about the canvas is
  handed over, neither its shape nor where a node stands, so the layout depends on the graph
  alone. `layOut(graph)` resolves to `{ geometry, source, ms }`: `geometry` is
  `{ boxes, routes }`, a frozen box `{ x1, y1, x2, y2 }` per node and a route
  `{ source, target, sections }` per edge, each section a polyline of points, both records
  without a prototype (`idRecord`). `source` is
  `worker` when ELK ran for this call and `cache` when the layout was already kept or under way.
  The page keeps the last eight layouts, keyed by the ELK graph, so every viewer of one data
  file (the page, full screen, a node page) shares one layout. One worker serves the page.
  `warmUpLayout()` starts it when a viewer mounts, because loading ELK costs more than a layout:
  1,917 ms from start to ELK's first answer against 420 ms for this repository's layout, measured
  in headless Chromium on an Apple M1 Max (`beadloom-7y2i`). A worker that
  fails to load or dies fails every layout it holds, so a viewer reports the failure rather than
  waiting.
- `ids`: `freshId(base, taken)`, the id for a thing the viewer makes itself: `base`, primed (`'`)
  until no id in `taken` has it. ELK's root graph and Cytoscape's edge ids use it, so no node of
  the data file can collide with them. `idRecord(entries)` (BDL-078 `beadloom-ytcg`) is a record
  without a prototype keyed by the data file's ids: a plain object answers `constructor` or
  `toString` for a key it was never given, and assigning `__proto__` replaces its prototype, so
  a node of that name dropped out of every walk over the object. Every map keyed by a node id in
  the viewer is a `Map` or such a record: the containment map, the layout's boxes and routes, the
  bundling's paths and the test handle's records. The segment imports nothing, so a module that runs
  without VitePress can use it. `elk` tells the root apart from the nodes by position, not by
  id.
- `echarts`: the lazily loaded ECharts component and the dashboard's palette.
- `ui`: `CopyCommand`, a terminal command shown as code with a button that copies it through the
  Clipboard API. Where the browser refuses, the command's text is selected instead and the button
  says "Selected" rather than claiming a copy.

## Public API

- `shared/lib/index.js`, `shared/theme-tokens/index.js`, `shared/cytoscape/index.js`,
  `shared/elk/index.js` (`elkGraphOf`, `LAYERED_OPTIONS`, `layOut`, `warmUpLayout`),
  `shared/ids/index.js` (`freshId`, `idRecord`), `shared/echarts/index.js` and
  `shared/ui/index.js`, one public file per segment.

## Depends on

- Nothing inside the site. The segments it owns import none of the five segment nodes; those
  import `ids` from here (`site-shared-bundling`, `site-shared-map-levels`).

## Tests

`src/beadloom/site_scaffold/e2e/shell-command.spec.js` drives `shellQuote`: a plain word is
left alone, any other is single-quoted, and a source path with a space is quoted in the command
the impact summary copies.

`src/beadloom/site_scaffold/e2e/layout.spec.js` drives `elk` and `ids`, six cases:

- each leaf is drawn at the centre of its ELK box, every child box lies inside its parent's, and
  every route starts and ends on its own nodes' boxes;
- a graph drawn again (a node page, then back) is answered from the cache and not laid out again;
- the layout does not depend on the fonts text is rendered in: with the portal's web fonts refused
  and its font variable set to a monospace family, which sets every node's id at another width,
  every box, position and route is the same (`beadloom-m6k7.7`);
- the toolbar answers while an adopter-sized graph is laid out, and no main-thread task from the
  data file's arrival until the graph is placed is longer than the environment's bound (Long
  Tasks API, recorded from page start);
- a layout that cannot run (the worker asset refused) is reported as an alert, nothing unplaced is
  drawn, and the controls that act on the graph are off;
- a node named like an id the viewer gives its own things (`root`, `e0:a->b`) still gets its box
  and its routes.
