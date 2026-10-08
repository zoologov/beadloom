// beadloom:component=site-filter-graph
// The choices each filter offers, derived from the nodes that are there.

import { ALL } from "../lib/visibleIds.js";

function choices(values) {
  return [ALL, ...Array.from(new Set(values.filter(Boolean))).sort()];
}

/**
 * `{ kinds, domains, layers }`: the choices each selection filter offers, `all`
 * first, each a value or `{ value, text }`. A layer's value is its label, which
 * says its rule's name where more than one rule is drawn, and is what the URL
 * carries; its text is its caption, which says the rule's title where the rule
 * declares one (`entities/layer`).
 */
export function filterOptions(nodes, layers) {
  return {
    kinds: choices(nodes.map((node) => node.kind)),
    domains: choices(nodes.filter((node) => node.kind === "domain").map((node) => node.id)),
    layers: [ALL, ...layers.map((layer) => ({ value: layer.label, text: layer.caption }))],
  };
}
