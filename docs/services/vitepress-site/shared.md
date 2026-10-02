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
- `cytoscape`: `loadCytoscape()` imports Cytoscape and the ELK layout in the browser only and
  registers the layout once; `LAYERED_LAYOUT` holds the fixed ELK options and hands each node's
  layer rank to ELK as its partition.
- `echarts`: the lazily loaded ECharts component and the dashboard's palette.
- `ui`: `CopyCommand`, a terminal command shown as code with a button that copies it through the
  Clipboard API. Where the browser refuses, the command's text is selected instead and the button
  says "Selected" rather than claiming a copy.

## Public API

- `shared/lib/index.js`, `shared/theme-tokens/index.js`, `shared/cytoscape/index.js`,
  `shared/echarts/index.js` and `shared/ui/index.js`, one public file per segment.

## Depends on

- Nothing inside the site.

## Tests

`src/beadloom/site_scaffold/e2e/shell-command.spec.js` drives `shellQuote`: a plain word is
left alone, any other is single-quoted, and a source path with a space is quoted in the command
the impact summary copies.
