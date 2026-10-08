// beadloom:component=site-layer
// The lane each drawn node takes in the layout: the rank of its layer among the siblings of one rule.
//
// ELK lays the graph out top to bottom and pins a node with a partition into
// that partition's band (`shared/elk`). A rank says where a layer stands only
// beside the other layers of its own rule, so lanes are given per box, to the
// siblings of one rule, and never compare a rank of one rule with a rank of
// another.

import { layerOfNode } from "./layers.js";

/**
 * Each node's lane in the layout, `Map(id => rank)`: the rank of its layer among
 * siblings of one rule. Where a box holds parts of more than one rule, the rule
 * that places most of them gives the lanes, the first in the layers' order on a
 * tie, and the others have none: a rank of one rule says nothing about a rank of
 * another. A layer box has its layer's rank; a file that names one order gives
 * every node its rank, as it always did.
 */
export function lanesOf(nodes, { parents, layers, layerBoxes = [] }) {
  const placed = [
    ...nodes.map((node) => ({ id: node.id, layer: layerOfNode(node, layers), rank: node.layer_rank })),
    ...layerBoxes.map((box) => ({ id: box.id, layer: layers.find((l) => l.rule === box.rule && l.rank === box.rank) })),
  ];
  const lanes = new Map();
  if (!layers.length || layers[0].rule === null) {
    for (const { id, rank } of placed) if (typeof rank === "number") lanes.set(id, rank);
    return lanes;
  }
  const siblings = new Map();
  for (const entry of placed) {
    if (!entry.layer) continue;
    const parent = parents[entry.id] ?? null;
    if (!siblings.has(parent)) siblings.set(parent, []);
    siblings.get(parent).push(entry);
  }
  const order = (rule) => layers.findIndex((layer) => layer.rule === rule);
  for (const group of siblings.values()) {
    const counts = new Map();
    for (const { layer } of group) counts.set(layer.rule, (counts.get(layer.rule) || 0) + 1);
    const [rule] = [...counts].sort(([a, m], [b, n]) => n - m || order(a) - order(b))[0];
    for (const { id, layer } of group) if (layer.rule === rule) lanes.set(id, layer.rank);
  }
  return lanes;
}
