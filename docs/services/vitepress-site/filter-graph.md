# Filter graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/features/filter-graph/`

---

## Overview

Decides which nodes the graph viewer shows. The visible set is computed as node ids, and then the
containers of every visible node are added back: Cytoscape does not draw a child whose parent is
hidden, so hiding a domain box used to hide every feature inside it. The domain filter keeps the
domain's whole subtree; the layer filter compares the layer a node is in, own or inherited; the
search box matches the id or the label, ignoring case; "Only flagged" keeps nodes with stale docs or
a lint finding.

## Public API

- `visibleNodeIds(nodes, filters, { parents, layers })` returns a `Set` of ids.
- `FILTER_DEFAULTS`, `ALL`, `matchesQuery(node, query)`, `isFiltering(filters)`.
- `filterOptions(nodes, layers)` returns the choices of each selection filter.
- `FilterControls` (Vue component): props `filters` and `options`, event `change(key, value)`.

## Depends on

- `site-graph-node`, `site-layer` (entities).
- `site-shared`.
