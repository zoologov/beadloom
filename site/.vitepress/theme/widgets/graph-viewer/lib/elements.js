// beadloom:component=site-graph-viewer
// The data file's nodes and edges as Cytoscape elements.
//
// A node carries its layer's tone and its status as data, and the stylesheet
// maps each value to a resolved colour, so a theme switch restyles the graph
// without rebuilding it. Containment becomes Cytoscape's `parent`; every other
// drawn kind becomes an edge with its style key.

import { EDGE_STYLES, isDrawnKind, styleKeyOf } from "../../../entities/graph-edge/index.js";
import { statusOf } from "../../../entities/graph-node/index.js";
import { layerToneOf } from "../../../entities/layer/index.js";

function nodeElement(node, { parents, layers }) {
  const data = {
    id: node.id,
    label: node.label || node.id,
    kind: node.kind || "",
    tone: layerToneOf(node, layers),
    status: statusOf(node) || "",
  };
  // The layer rank is the node's lane in the layout; a node with no rank has none.
  if (typeof node.layer_rank === "number") data.partition = node.layer_rank;
  if (parents[node.id]) data.parent = parents[node.id];
  return { group: "nodes", data };
}

function edgeElement(edge, index) {
  const styleKey = styleKeyOf(edge);
  return {
    group: "edges",
    data: {
      id: `e${index}:${edge.src}->${edge.dst}`,
      source: edge.src,
      target: edge.dst,
      kind: edge.kind,
      styleKey,
      label: EDGE_STYLES[styleKey].label,
    },
  };
}

/** Cytoscape elements for the nodes and the drawn edges between them. */
export function buildElements(nodes, edges, context) {
  const ids = new Set(nodes.map((node) => node.id));
  const elements = nodes.map((node) => nodeElement(node, context));
  edges.forEach((edge, index) => {
    if (isDrawnKind(edge.kind) && ids.has(edge.src) && ids.has(edge.dst)) {
      elements.push(edgeElement(edge, index));
    }
  });
  return elements;
}
