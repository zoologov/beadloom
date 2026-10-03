# Filter graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/filter-graph/`

---

## Overview

Decides which nodes the graph viewer shows, in each of its two modes.

- **Architecture.** The visible set is computed as node ids, and then the containers of every
  visible node are added back: Cytoscape does not draw a child whose parent is hidden, so hiding a
  domain box used to hide every feature inside it. The domain filter keeps the domain's whole
  subtree; the layer filter compares the name of the layer a node is in, own or inherited; the
  search box matches the id or the label, ignoring case; "Only flagged" keeps the nodes with a
  status (a finding or stale docs).
- **Landscape** (`lib/contractFilters.js`). The filters choose contracts: by protocol, by the health
  of their verdict (problems, healthy or neutral), or down to the problems alone. A service is
  shown when it produces or consumes a shown contract, so a service whose only contract is an
  orphaned consumer still appears among the problems. The viewer hides an edge whose contract is
  not shown, even when both of its services stay. With no filter set, every service is shown.

## Public API

- `visibleNodeIds(nodes, filters, { parents, layers })` returns a `Set` of ids.
- `FILTER_DEFAULTS`, `ALL`, `matchesQuery(node, query)`, `isFiltering(filters)`.
- `filterOptions(nodes, layers)` returns the choices of each selection filter.
- `FilterControls` (Vue component): props `filters` and `options`, event `change(key, value)`.
- `visibleContracts(graph, filters)` returns `{ nodes, contracts }`, the ids of the services and
  the keys of the contracts shown; `CONTRACT_FILTER_DEFAULTS`, `VERDICT_CHOICES`,
  `contractFilterOptions(contracts)`.
- `ContractFilterControls` (Vue component): props `filters` and `options`, event
  `change(key, value)`.

## Depends on

- `site-graph-node`, `site-layer`, `site-landscape-data` (entities).
- `site-shared`.
