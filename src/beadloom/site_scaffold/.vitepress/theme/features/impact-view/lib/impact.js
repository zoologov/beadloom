// beadloom:component=site-impact-view
// Everything that depends on a node, and what that reach amounts to in the architecture.
//
// The walk goes from the selected node to its dependents, theirs, and so on,
// with no depth limit, over a map of dependents the mode builds from its edges
// (`dependentsOf` in `entities/graph-edges`): in the architecture, backwards
// along the dependency kinds. The summary here is what an estimate needs: how
// many nodes, which domains and services hold them, which layer boundaries the
// walked edges cross, and which nodes are a risk. It is the graph's view —
// edges from imports and declarations — and says nothing about how the code
// behind a node uses what it imports. The landscape's summary, over contracts,
// is `contractImpact.js`.

import { breadthFirst } from "../../../shared/lib/index.js";
import { containerOfKind, risksOf } from "../../../entities/graph-nodes/index.js";
import { DEPENDENCY_KINDS } from "../../../entities/graph-edges/index.js";
import { layerOfNode } from "../../../entities/layers/index.js";

/** The node kinds the summary groups the affected nodes by. */
const DOMAIN_KIND = "domain";
const SERVICE_KIND = "service";

/** The walk a summary of the architecture reads: dependencies, from a node to its dependents. */
export const DEPENDENCY_WALK = "dependencies";

/** `{ distances, edges }`: every dependent of `focus` in `dependents`, by its fewest steps, and the edges walked. */
export function impactOf(focus, dependents) {
  return breadthFirst(focus, (id) => dependents.get(id) || []);
}

/** The distinct values that are set, sorted. */
export function sortedUnique(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

/**
 * `{ affected, byDistance }` of an impact walk from `focus`: every node it
 * reached, sorted, without `focus`, and the same ids grouped as
 * `[{ distance, ids }]` from the nearest out.
 */
export function reachOf(focus, impact) {
  const affected = [...impact.distances.keys()].filter((id) => id !== focus).sort();
  const groups = new Map();
  for (const id of affected) {
    const distance = impact.distances.get(id);
    if (!groups.has(distance)) groups.set(distance, []);
    groups.get(distance).push(id);
  }
  const byDistance = [...groups].sort(([a], [b]) => a - b).map(([distance, ids]) => ({ distance, ids }));
  return { affected, byDistance };
}

function boundariesOf(distances, edges, nodeById, layers) {
  const counts = new Map();
  const wanted = new Set(DEPENDENCY_KINDS);
  for (const edge of edges) {
    if (!wanted.has(edge.kind) || edge.src === edge.dst || !distances.has(edge.dst)) continue;
    const dependent = nodeById.get(edge.src);
    const dependency = nodeById.get(edge.dst);
    if (!dependent || !dependency) continue;
    const from = layerOfNode(dependent, layers);
    const to = layerOfNode(dependency, layers);
    if (!from || !to || from === to) continue;
    const key = `${from.key}->${to.key}`;
    const entry = counts.get(key) || { from: from.caption, to: to.caption, fromRank: from.rank, toRank: to.rank, order: [layers.indexOf(from), layers.indexOf(to)], count: 0 };
    entry.count += 1;
    counts.set(key, entry);
  }
  // In the layers' order: every rule's top to bottom, the rules in the file's order.
  return [...counts.values()]
    .sort((a, b) => a.order[0] - b.order[0] || a.order[1] - b.order[1])
    .map(({ order: _order, ...entry }) => entry);
}

/**
 * The summary of an impact walk from `focus` over the architecture.
 *
 * `{ walk, focus, affected, byDistance, domains, services, boundaries, risky }`:
 * `walk` is `DEPENDENCY_WALK`; `affected` and `byDistance` are `reachOf`'s;
 * `boundaries` counts each crossing between two layers as
 * `{ from, to, fromRank, toRank, count }`; `risky` lists `{ id, risks }` for
 * each affected node that carries a risk.
 */
export function impactSummary(focus, impact, { nodeById, parents, layers, edges }) {
  const { affected, byDistance } = reachOf(focus, impact);
  const nearest = (kind) =>
    sortedUnique(affected.map((id) => containerOfKind(id, kind, nodeById, parents)));
  return {
    walk: DEPENDENCY_WALK,
    focus,
    affected,
    byDistance,
    domains: nearest(DOMAIN_KIND),
    services: nearest(SERVICE_KIND),
    boundaries: boundariesOf(impact.distances, edges, nodeById, layers),
    risky: affected
      .map((id) => ({ id, risks: risksOf(nodeById.get(id)) }))
      .filter((entry) => entry.risks.length),
  };
}
