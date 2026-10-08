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

/**
 * The Layer filter's value for `value`, as a link names it: `value` itself where
 * the filter offers it. A link shared from a portal that drew one layer rule names
 * a layer by its bare name (`?layer=domains`), which a portal drawing two or more
 * rules offers only said with the rule's (`architecture-layers: domains`): such a
 * name is read as the label of the layer it names, the first rule's by name where
 * two rules have a layer of that name, since `layers` lists the rules by name.
 * Any other value is returned as it is.
 */
export function layerChoiceOf(value, layers) {
  if (value === ALL || layers.some((layer) => layer.label === value)) return value;
  return layers.find((layer) => layer.name === value)?.label ?? value;
}
