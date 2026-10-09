// beadloom:component=site-graph-viewer
// The data file's nodes and edges as Cytoscape elements.
//
// A node carries its layer's tone, its lane and its status as data, and the
// stylesheet maps each value to a resolved colour, so a theme switch restyles the
// graph without rebuilding it. The box a layer rule scoped to a box draws around
// each of its layers' parts (`entities/layers`) is a node here too, no node of the
// file. Containment becomes Cytoscape's `parent`; every other
// drawn kind becomes an edge with its style key. A landscape node carries its
// health, and a landscape edge its contract and, when broken, its badge.
//
// Cytoscape keeps one id space for nodes and edges, and a node's id is the data
// file's, so an edge's id, made here from its place in the file and its ends, is
// chosen against the ids already given (`freshId`): no node can take it.

import { freshId } from "../../../shared/ids/index.js";
import { EDGE_STYLES, edgeKeyOf, isDrawnKind, styleKeyOf } from "../../../entities/graph-edges/index.js";
import { statusOf } from "../../../entities/graph-nodes/index.js";
import { lanesOf, layerToneOf } from "../../../entities/layers/index.js";
import { LAYER_BOX, STACK_LANES } from "../../../shared/map-levels/index.js";

function nodeElement(node, { parents, layers }, lanes, scopes) {
  const data = {
    id: node.id,
    label: node.label || node.id,
    kind: node.kind || "",
    tone: layerToneOf(node, layers),
    status: statusOf(node) || "",
  };
  if (node.health) data.health = node.health;
  // The node's lane in the layout (`entities/layers`, `lanesOf`); a node with none is placed by its edges alone.
  if (lanes.has(node.id)) data.partition = lanes.get(node.id);
  if (parents[node.id]) data.parent = parents[node.id];
  if (scopes.has(node.id)) data[STACK_LANES] = true;
  return { group: "nodes", data };
}

/**
 * The box a scoped rule draws around one layer's parts (`entities/layers`): drawn
 * as a box of the layer's tone, titled by the layer's name, in its layer's lane
 * of its scope, and marked as no node of the file (`LAYER_BOX`).
 */
function layerBoxElement(box, lanes) {
  const data = { id: box.id, label: box.label, kind: "", tone: box.tone, status: "", parent: box.scope, [LAYER_BOX]: box.rule };
  if (lanes.has(box.id)) data.partition = lanes.get(box.id);
  return { group: "nodes", data };
}

function edgeElement(edge, id) {
  const styleKey = styleKeyOf(edge);
  return {
    group: "edges",
    data: {
      id,
      source: edge.src,
      target: edge.dst,
      kind: edge.kind,
      // The edge's key names it in a walk: the selection marks the keys it walked.
      key: edgeKeyOf(edge),
      styleKey,
      label: EDGE_STYLES[styleKey].label,
      ...(edge.contract ? { contract: edge.contract } : {}),
      ...(edge.badge ? { badge: edge.badge } : {}),
    },
  };
}

/**
 * Cytoscape elements for the nodes, the boxes the scoped layer rules draw, and
 * the drawn edges between the nodes. `context` is `{ parents, layers,
 * layerBoxes }`: the containment drawn, the layers, and the layer boxes
 * (`entities/layers`, `layerBoxesOf`), none by default.
 */
export function buildElements(nodes, edges, context) {
  const layerBoxes = context.layerBoxes || [];
  const ids = new Set([...nodes.map((node) => node.id), ...layerBoxes.map((box) => box.id)]);
  const taken = new Set(ids);
  const lanes = lanesOf(nodes, { parents: context.parents, layers: context.layers, layerBoxes });
  const scopes = new Set(layerBoxes.map((box) => box.scope));
  const elements = [
    ...nodes.map((node) => nodeElement(node, context, lanes, scopes)),
    ...layerBoxes.map((box) => layerBoxElement(box, lanes)),
  ];
  edges.forEach((edge, index) => {
    if (isDrawnKind(edge.kind) && ids.has(edge.src) && ids.has(edge.dst)) {
      const id = freshId(`e${index}:${edge.src}->${edge.dst}`, taken);
      taken.add(id);
      elements.push(edgeElement(edge, id));
    }
  });
  return elements;
}
