// beadloom:component=site-select-neighbourhood
// A selected node's neighbourhood: what it reaches, what reaches it, or both.
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
