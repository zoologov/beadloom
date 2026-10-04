# Shared (component)

A slice of the `shared` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/shared/`

---

## Overview

The segments every other layer may use. In Feature-Sliced Design `shared` has segments rather than
slices, so this is one node. A segment uses another only through that segment's `index.js`, as
every other layer does.

- `lib`: `isBrowser()`, `createJsonResource(path, validate)` (one fetch per file and page load),
  the tree walks `childrenOf`, `withAncestors` and `subtreeOf`, `breadthFirst(start, step,
  maxDepth)`, the walk the neighbourhood and the impact mode both run with a step of their own,
  and `shellQuote(word)`, which quotes a word for a POSIX shell so that a copied command names
  what it shows.
- `theme-tokens`: resolves the VitePress CSS variables to opaque `rgb(...)` through
  `getComputedStyle`, flattening a translucent colour over the background, and `useThemeTokens`
  re-resolves them when VitePress toggles dark mode. Cytoscape rejects `var(...)` and draws its
  fallback grey, `rgb(153,153,153)`, which is why no variable reaches it.
- `cytoscape`: `loadCytoscape()` imports Cytoscape in the browser only, once. It loads Cytoscape
  alone: the layout is not Cytoscape's.
- `elk`: the layered layout, run by elkjs 0.12 in a Web Worker so that the page's main thread is
  never held by it. `elkGraphOf({ nodes, edges })` builds the ELK graph with the fixed options
  `LAYERED_OPTIONS` (layered, direction down, orthogonal edge routing, `INCLUDE_CHILDREN`, each
  node's layer rank as its partition) and asks for every box and section in root coordinates
  (`elk.json.shapeCoords` and `elk.json.edgeCoords` set to `ROOT`). Nothing about the canvas is
  handed over, neither its shape nor where a node stands, so the layout depends on the graph
  alone. `layOut(graph)` resolves to `{ geometry, source, ms }`: `geometry` is
  `{ boxes, routes }`, a frozen box `{ x1, y1, x2, y2 }` per node and a route
  `{ source, target, sections }` per edge, each section a polyline of points. `source` is
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
  the data file can collide with them. The segment imports nothing, so a module that runs
  without VitePress can use it. `elk` tells the root apart from the nodes by position, not by
  id.
- `echarts`: the lazily loaded ECharts component and the dashboard's palette.
- `ui`: `CopyCommand`, a terminal command shown as code with a button that copies it through the
  Clipboard API. Where the browser refuses, the command's text is selected instead and the button
  says "Selected" rather than claiming a copy.

## Public API

- `shared/lib/index.js`, `shared/theme-tokens/index.js`, `shared/cytoscape/index.js`,
  `shared/elk/index.js` (`elkGraphOf`, `LAYERED_OPTIONS`, `layOut`, `warmUpLayout`),
  `shared/ids/index.js` (`freshId`), `shared/echarts/index.js` and `shared/ui/index.js`, one
  public file per segment.

## Depends on

- Nothing inside the site.

## Tests

`src/beadloom/site_scaffold/e2e/shell-command.spec.js` drives `shellQuote`: a plain word is
left alone, any other is single-quoted, and a source path with a space is quoted in the command
the impact summary copies.

`src/beadloom/site_scaffold/e2e/layout.spec.js` drives `elk` and `ids`, five cases:

- each leaf is drawn at the centre of its ELK box, every child box lies inside its parent's, and
  every route starts and ends on its own nodes' boxes;
- a graph drawn again (a node page, then back) is answered from the cache and not laid out again;
- the toolbar answers while an adopter-sized graph is laid out, and no main-thread task from the
  data file's arrival until the graph is placed is longer than the environment's bound (Long
  Tasks API, recorded from page start);
- a layout that cannot run (the worker asset refused) is reported as an alert, nothing unplaced is
  drawn, and the controls that act on the graph are off;
- a node named like an id the viewer gives its own things (`root`, `e0:a->b`) still gets its box
  and its routes.
