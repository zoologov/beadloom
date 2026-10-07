// beadloom:component=site-select-neighbourhood
// A selected node's neighbourhood: what it reaches, what reaches it, or both; a selected box's, from everything it holds.
//
// "Both" is the union of the outgoing walk and the incoming walk, not a walk
// that may turn round at every step. A turning walk would reach the other
// dependents of every shared dependency, and at depth 2 almost everything
// depends on the same few nodes, so it would show nearly the whole graph.

import { breadthFirst } from "../../../shared/lib/index.js";
import { depthLimit } from "../model/options.js";

function along(map) {
  return (id) => map.get(id) || [];
}

/**
 * The neighbourhood of `focus`: `{ distances, edges }`.
 *
 * `adjacency` is `{ out, in }` from `adjacencyOf`; `depth` and `dir` are the
 * control's values. `distances` maps each node in the neighbourhood to its
 * fewest steps from `focus`; `edges` holds the keys of the edges walked.
 */
export function neighbourhoodOf(focus, adjacency, { depth, dir }) {
  const limit = depthLimit(depth);
  const walks = [];
  if (dir !== "in") walks.push(breadthFirst(focus, along(adjacency.out), limit));
  if (dir !== "out") walks.push(breadthFirst(focus, along(adjacency.in), limit));
  const distances = new Map();
  const edges = new Set();
  for (const walk of walks) {
    for (const [id, distance] of walk.distances) {
      distances.set(id, Math.min(distance, distances.get(id) ?? Infinity));
    }
    for (const key of walk.edges) edges.add(key);
  }
  return { distances, edges };
}

/**
 * `adjacency` read with box `box` standing for everything in `inside` (the box
 * and what it holds at any depth): the box's edges are every edge with exactly
 * one end inside it, but for an edge onto a box of `holders`, which hold it and
 * are no neighbour of it; a walk that comes back to a node inside stops there,
 * since the box was reached at the start.
 */
function aroundBox(box, inside, holders, adjacency) {
  const leaving = (map) => {
    const out = [];
    for (const id of inside) for (const step of map.get(id) || []) if (!inside.has(step.id) && !holders.has(step.id)) out.push(step);
    return out;
  };
  const read = (map) => {
    const own = leaving(map);
    return { get: (id) => (id === box ? own : (map.get(id) || []).filter((step) => !inside.has(step.id))) };
  };
  return { out: read(adjacency.out), in: read(adjacency.in) };
}

/**
 * The neighbourhood of box `box`, which holds `inside` (itself included) and is
 * held by `holders`: the neighbourhood of one node whose edges are every edge
 * crossing the box's border to a node that does not hold it, `{ distances,
 * edges }` as `neighbourhoodOf` gives them. The nodes inside are not on the
 * walk: they are what was selected.
 */
export function boxNeighbourhoodOf(box, inside, holders, adjacency, options) {
  return neighbourhoodOf(box, aroundBox(box, inside, holders, adjacency), options);
}
