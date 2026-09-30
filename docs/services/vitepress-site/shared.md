# Shared (component)

A slice of the `shared` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/shared/`

---

## Overview

The segments every other layer may use. In Feature-Sliced Design `shared` has segments rather than
slices, so this is one node, and its segments import one another.

- `lib`: `isBrowser()`, `createJsonResource(path, validate)` (one fetch per file and page load),
  and the tree walks `childrenOf`, `withAncestors` and `subtreeOf`.
- `theme-tokens`: resolves the VitePress CSS variables to opaque `rgb(...)` through
  `getComputedStyle`, flattening a translucent colour over the background, and `useThemeTokens`
  re-resolves them when VitePress toggles dark mode. Cytoscape rejects `var(...)` and draws its
  fallback grey, `rgb(153,153,153)`, which is why no variable reaches it.
- `cytoscape`: `loadCytoscape()` imports Cytoscape and the ELK layout in the browser only and
  registers the layout once; `LAYERED_LAYOUT` holds the fixed ELK options and hands each node's
  layer rank to ELK as its partition.
- `echarts`: the lazily loaded ECharts component and the dashboard's palette.

## Public API

- `shared/lib/index.js`, `shared/theme-tokens/index.js`, `shared/cytoscape/index.js` and
  `shared/echarts/index.js`, one public file per segment.

## Depends on

- Nothing inside the site.
