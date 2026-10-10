// beadloom:component=site-filter-graph
// Which nodes a set of filters shows.
//
// The visible set is computed as node ids first, and the containers of every
// visible node are added back afterwards. Cytoscape does not draw a child whose
// parent is hidden, so a filter that hid a domain box used to hide every
// feature inside it: `Kind = feature` showed nothing. Adding the ancestors back
// keeps a matching node on the canvas inside the boxes that hold it.

import { childrenOf, subtreeOf, withAncestors } from "../../../shared/lib/index.js";
import { isFlagged } from "../../../entities/graph-nodes/index.js";
import { layerOfNode } from "../../../entities/layers/index.js";

/** The value of a selection filter that does not filter. */
export const ALL = "all";

/** The filters' neutral state, which shows every node. */
export const FILTER_DEFAULTS = Object.freeze({
  kind: ALL,
  domain: ALL,
  layer: ALL,
  violations: false,
  q: "",
});

/** Whether a node's id or label contains the query, ignoring case. */
export function matchesQuery(node, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return [node.id, node.label].some((text) => String(text || "").toLowerCase().includes(needle));
}

/**
 * The ids of the nodes the filters show, with every container of each.
 *
 * The domain filter keeps the domain's whole subtree, not only its direct
 * children; the layer filter compares the layer a node is in, inherited or its
 * own, by the layer's label: its name, said with its rule's where more than one
 * rule is drawn. `parents` is the containment drawn, so the box a scoped rule
 * draws around a layer's parts is kept with them.
 */
export function visibleNodeIds(nodes, filters, { parents, layers }) {
  const inDomain =
    filters.domain !== ALL ? subtreeOf(filters.domain, childrenOf(parents)) : null;
  const matched = nodes.filter(
    (node) =>
      (filters.kind === ALL || node.kind === filters.kind) &&
      (filters.layer === ALL || layerOfNode(node, layers)?.label === filters.layer) &&
      (!inDomain || inDomain.has(node.id)) &&
      (!filters.violations || isFlagged(node)) &&
      matchesQuery(node, filters.q || "")
  );
  return withAncestors(
    matched.map((node) => node.id),
    parents
  );
}

/** Whether any filter differs from its neutral state. */
export function isFiltering(filters) {
  return Object.entries(FILTER_DEFAULTS).some(([key, neutral]) => filters[key] !== neutral);
}
