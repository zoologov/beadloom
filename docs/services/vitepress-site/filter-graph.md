# Filter graph (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/filter-graph/`

---

## Overview

Decides which nodes the graph viewer shows, in each of its two modes.

- **Architecture.** The visible set is computed as node ids, and then the containers of every
  visible node are added back: Cytoscape does not draw a child whose parent is hidden, so hiding a
  domain box used to hide every feature inside it. `parents` is the containment drawn, so the
  box a scoped layer rule draws around a layer's parts is kept with them (BDL-080 S1c). The domain filter keeps the domain's whole
  subtree; the layer filter compares the label of the layer a node is in, own or inherited; the
  search box matches the id or the label, ignoring case; "Only flagged" keeps the nodes with a
  status (a finding or stale docs).
- **The Layer filter names a layer by its rule (BDL-080 S1c, S1e).** It offers every drawn rule's
  layers. A choice is `{ value, text }`: the value is the layer's label, `<rule>: <layer>` where
  more than one rule is drawn and the bare layer name otherwise, and it is what the URL's
  `?layer=` carries. The text is the layer's caption, with the rule's title in place of its name
  where the rule declares one. On this repository the value `site-fsd-layers: widgets` is shown
  as `FSD architecture: widgets`. `FilterControls` renders a choice that is a plain value as
  itself.
- **A link that names a bare layer still filters (BDL-080 S1f).** A link shared from a portal
  that drew one rule names a layer by its bare name (`?layer=domains`), which a portal drawing two
  rules does not offer. `layerChoiceOf(value, layers)` reads such a name as the label of the
  layer of that name, the first rule's by name where two rules share it; a value the filter
  offers is returned as it is, and any other value is left unchanged, so it still filters to
  nothing. The graph viewer settles the filter once the layers are read, and the URL is rewritten
  to the offered value: `?layer=domains` becomes `?layer=architecture-layers%3A%20domains` on this
  repository.
- **Landscape** (`lib/contractFilters.js`). The filters choose contracts: by protocol, by the health
  of their verdict (problems, healthy or neutral), or down to the problems alone. A service is
  shown when it produces or consumes a shown contract, so a service whose only contract is an
  orphaned consumer still appears among the problems. The viewer hides an edge whose contract is
  not shown, even when both of its services stay. With no filter set, every service is shown.

## Public API

- `visibleNodeIds(nodes, filters, { parents, layers })` returns a `Set` of ids.
- `FILTER_DEFAULTS`, `ALL`, `matchesQuery(node, query)`, `isFiltering(filters)`.
- `filterOptions(nodes, layers)` returns `{ kinds, domains, layers }`, `all` first; each
  choice is a value or `{ value, text }`, and a layer is `{ value: label, text: caption }`.
- `layerChoiceOf(value, layers)` returns the Layer filter's value for a value a link names.
- `FilterControls` (Vue component): props `filters` and `options`, event `change(key, value)`;
  each `<option>` takes the choice's value and shows its text.
- `visibleContracts(graph, filters)` returns `{ nodes, contracts }`, the ids of the services and
  the keys of the contracts shown; `CONTRACT_FILTER_DEFAULTS`, `VERDICT_CHOICES`,
  `contractFilterOptions(contracts)`.
- `ContractFilterControls` (Vue component): props `filters` and `options`, event
  `change(key, value)`.

## Depends on

- `site-graph-nodes`, `site-layers`, `site-landscape-data` (entities).
- `site-shared`.
