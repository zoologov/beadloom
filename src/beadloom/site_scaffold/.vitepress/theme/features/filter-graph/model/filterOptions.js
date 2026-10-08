// beadloom:component=site-filter-graph
// The choices each filter offers, derived from the nodes that are there.

import { ALL } from "../lib/visibleIds.js";

function choices(values) {
  return [ALL, ...Array.from(new Set(values.filter(Boolean))).sort()];
}

/**
 * `{ kinds, domains, layers }`: the values each selection filter offers, `all`
 * first. A layer is offered by its label, which says its rule's name where more
 * than one rule is drawn (`entities/layer`).
 */
export function filterOptions(nodes, layers) {
  return {
    kinds: choices(nodes.map((node) => node.kind)),
    domains: choices(nodes.filter((node) => node.kind === "domain").map((node) => node.id)),
    layers: [ALL, ...layers.map((layer) => layer.label)],
  };
}
