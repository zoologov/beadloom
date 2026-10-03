// beadloom:component=site-shared
// A breadth-first walk over a graph given as a step function.
//
// The walk knows nothing of edge kinds or directions: `step(id)` names the
// neighbours of a node as `[{ id, key }]`, where `key` identifies the edge that
// leads there. The neighbourhood and the impact mode both walk with it, each
// with its own step.

/**
 * Walk from `start` up to `maxDepth` steps: `{ distances, edges }`.
 *
 * `distances` maps every reached id to its distance from `start`, which is 0.
 * `edges` holds the key of every edge leaving a node closer than `maxDepth`,
 * so an edge between two reached nodes is in the walk when it was a step of it.
 */
export function breadthFirst(start, step, maxDepth = Infinity) {
  const distances = new Map([[start, 0]]);
  const edges = new Set();
  let frontier = [start];
  let depth = 0;
  while (frontier.length && depth < maxDepth) {
    depth += 1;
    const next = [];
    for (const id of frontier) {
      for (const neighbour of step(id)) {
        edges.add(neighbour.key);
        if (distances.has(neighbour.id)) continue;
        distances.set(neighbour.id, depth);
        next.push(neighbour.id);
      }
    }
    frontier = next;
  }
  return { distances, edges };
}
