// beadloom:component=site-shared
// The ELK graph of a layered drawing: fixed, seedless options, so one graph always gives one layout.
//
// Each node may carry a `partition`, its layer rank, and ELK's partitioning pins
// it into that rank's band from top to bottom (`elk.direction: DOWN`), so the
// lanes follow the declared layers rather than the topology.
// `INCLUDE_CHILDREN` lays out compound parents (a domain's box around its
// features and components) together with their children, and every edge is
// routed orthogonally across the whole hierarchy.
//
// The answer comes back in the graph's own coordinates: `elk.json.shapeCoords`
// and `elk.json.edgeCoords` set to `ROOT` make every box and every edge section
// absolute, rather than relative to the box that contains it.
//
// The root is a graph of ELK's, not a node of the drawing, and its id shares
// ELK's node ids with the drawing's: it is named so that no node has its name.

import { freshId } from "../ids/index.js";

/** The options of the layout, the same for every graph. */
export const LAYERED_OPTIONS = Object.freeze({
  algorithm: "layered",
  "elk.direction": "DOWN",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.hierarchyHandling": "INCLUDE_CHILDREN",
  "elk.partitioning.activate": "true",
  "elk.layered.spacing.nodeNodeBetweenLayers": "70",
  "elk.spacing.nodeNode": "45",
  "elk.padding": "[top=36,left=24,bottom=24,right=24]",
});

/** Every coordinate of the answer in the root's frame. */
const ROOT_COORDINATES = Object.freeze({
  "elk.json.shapeCoords": "ROOT",
  "elk.json.edgeCoords": "ROOT",
});

/**
 * The name the graph's root is given. A node of the drawing may have it too, so
 * the root takes it only when no node does (`freshId`).
 */
const ROOT_NAME = "root";

/** ELK's per-node options: the node's lane, when it has one. */
function laneOf(node) {
  return typeof node.partition === "number"
    ? { "elk.partitioning.partition": String(node.partition) }
    : {};
}

/**
 * The ELK graph of `nodes` and `edges`.
 *
 * A node is `{ id, parent, width, height, partition }`: `parent` is the id of
 * the node that contains it, or null. A node some other node names as its parent
 * is a box, sized by ELK, so its own size is not handed over. An edge is
 * `{ id, source, target }`. Nothing about where the graph will be drawn is
 * handed over, neither the drawing area's shape nor where a node stands now, so
 * the layout depends on the graph alone.
 */
export function elkGraphOf({ nodes, edges }) {
  const containers = new Set(nodes.map((node) => node.parent).filter(Boolean));
  const byId = new Map();
  const root = { id: freshId(ROOT_NAME, new Set(nodes.map((node) => node.id))), children: [], edges: [] };
  for (const node of nodes) {
    const shape = { id: node.id, layoutOptions: laneOf(node) };
    if (!containers.has(node.id)) {
      Object.assign(shape, { width: node.width, height: node.height });
    }
    byId.set(node.id, shape);
  }
  for (const node of nodes) {
    const parent = (node.parent && byId.get(node.parent)) || root;
    (parent.children ||= []).push(byId.get(node.id));
  }
  for (const edge of edges) {
    root.edges.push({ id: edge.id, sources: [edge.source], targets: [edge.target] });
  }
  root.layoutOptions = { ...LAYERED_OPTIONS, ...ROOT_COORDINATES };
  return root;
}
