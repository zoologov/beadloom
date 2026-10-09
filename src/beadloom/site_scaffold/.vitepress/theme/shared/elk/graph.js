// beadloom:component=site-shared
// The ELK graph of a layered drawing: fixed, seedless options, so one graph always gives one layout.
//
// Each node may carry a `partition`, its layer rank, and ELK's partitioning pins
// it into that rank's band from top to bottom (`elk.direction: DOWN`), so the
// lanes follow the declared layers rather than the topology — among the root's
// children only: with `INCLUDE_CHILDREN` ELK reads no partition of a node inside
// a box (measured on elkjs 0.12: three children of one box in partitions 2, 0
// and 1, with no edge between them, are laid out in one row, whether or not the
// box activates partitioning itself). A box that asks for its children to be
// stacked by their partitions (`stack`) therefore gets a lane edge from each
// child of a partition to each child of the next one present: ELK lays the
// graph out with them as with any edge, which puts each partition below the one
// above it whatever the drawn edges say, and they are no edge of the drawing
// (`LANE_EDGE`; `geometry.js` leaves them out of the answer).
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
// Its padding is the margin around the whole drawing. A box of the drawing is
// padded on its own: ELK keeps 12 units between a box's border and its
// children, and a box keeps `boxTop` above them, the room its title is drawn
// in, so no child stands under the title.

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

/** The room ELK keeps between a box's border and its children, in layout units, on every side but the top. */
const BOX_SIDE = 12;

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

/** The mark of an edge laid out only to stack a box's children by partition, which no drawing has. */
export const LANE_EDGE = "lane";

/** ELK's per-node options: the node's lane, when it has one. */
function laneOf(node) {
  return typeof node.partition === "number"
    ? { "elk.partitioning.partition": String(node.partition) }
    : {};
}

/** ELK's padding of a box: `top` above its children, ELK's own room on every other side. */
const boxPaddingOf = (top) => ({ "elk.padding": `[top=${top},left=${BOX_SIDE},bottom=${BOX_SIDE},right=${BOX_SIDE}]` });

/**
 * The lane edges of the boxes in `nodes` that stack their children by partition
 * (`stack`): from each child of a partition to each child of the next partition
 * present, each named so that no node or edge of the drawing has its name.
 */
function laneEdgesOf(nodes, taken) {
  const stacked = new Set(nodes.filter((node) => node.stack).map((node) => node.id));
  const lanes = new Map();
  for (const node of nodes) {
    if (!stacked.has(node.parent) || typeof node.partition !== "number") continue;
    if (!lanes.has(node.parent)) lanes.set(node.parent, new Map());
    const byPartition = lanes.get(node.parent);
    if (!byPartition.has(node.partition)) byPartition.set(node.partition, []);
    byPartition.get(node.partition).push(node.id);
  }
  const edges = [];
  for (const byPartition of lanes.values()) {
    const ordered = [...byPartition].sort(([a], [b]) => a - b).map(([, ids]) => ids);
    for (let k = 1; k < ordered.length; k += 1) {
      for (const source of ordered[k - 1]) {
        for (const target of ordered[k]) {
          const id = freshId(`${LANE_EDGE}:${source}->${target}`, taken);
          taken.add(id);
          edges.push({ id, sources: [source], targets: [target], [LANE_EDGE]: true });
        }
      }
    }
  }
  return edges;
}

/**
 * The ELK graph of `nodes` and `edges`.
 *
 * A node is `{ id, parent, width, height, partition, stack }`: `parent` is the
 * id of the node that contains it, or null; `stack` asks a box to stack its
 * children by partition, top to bottom (`laneEdgesOf`). A node some other node
 * names as its parent is a box, sized by ELK, so its own size is not handed over. An edge is
 * `{ id, source, target }`. `boxTop` is the room each box keeps above its
 * children, in layout units, ELK's own 12 when none is given. Nothing about where
 * the graph will be drawn is handed over, neither the drawing area's shape nor
 * where a node stands now, so the layout depends on the graph alone.
 */
export function elkGraphOf({ nodes, edges, boxTop = BOX_SIDE }) {
  const containers = new Set(nodes.map((node) => node.parent).filter(Boolean));
  const byId = new Map();
  const root = { id: freshId(ROOT_NAME, new Set(nodes.map((node) => node.id))), children: [], edges: [] };
  for (const node of nodes) {
    const shape = { id: node.id, layoutOptions: laneOf(node) };
    if (containers.has(node.id)) Object.assign(shape.layoutOptions, boxPaddingOf(boxTop));
    else Object.assign(shape, { width: node.width, height: node.height });
    byId.set(node.id, shape);
  }
  for (const node of nodes) {
    const parent = (node.parent && byId.get(node.parent)) || root;
    (parent.children ||= []).push(byId.get(node.id));
  }
  for (const edge of edges) {
    root.edges.push({ id: edge.id, sources: [edge.source], targets: [edge.target] });
  }
  const taken = new Set([root.id, ...nodes.map((node) => node.id), ...edges.map((edge) => edge.id)]);
  root.edges.push(...laneEdgesOf(nodes, taken));
  root.layoutOptions = { ...LAYERED_OPTIONS, ...ROOT_COORDINATES };
  return root;
}
