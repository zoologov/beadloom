// beadloom:component=site-impact-view
// Everything that depends on a node, and what that reach amounts to.
//
// The walk goes backwards along the dependency kinds with no depth limit:
// from the selected node to its dependents, theirs, and so on. The summary is
// what an estimate needs: how many nodes, which domains and services hold them,
// which layer boundaries the walked edges cross, and which nodes are a risk.
// It is the graph's view — edges from imports and declarations — and says
// nothing about how the code behind a node uses what it imports.

import { breadthFirst } from "../../../shared/lib/index.js";
import { containerOfKind, risksOf } from "../../../entities/graph-node/index.js";
import { DEPENDENCY_KINDS } from "../../../entities/graph-edge/index.js";
import { layerOfNode } from "../../../entities/layer/index.js";

/** The node kinds the summary groups the affected nodes by. */
const DOMAIN_KIND = "domain";
const SERVICE_KIND = "service";

/** `{ distances, edges }`: every dependent of `focus`, by its fewest steps, and the edges walked. */
export function impactOf(focus, adjacency) {
  return breadthFirst(focus, (id) => adjacency.in.get(id) || []);
}

function sortedUnique(values) {
  return [...new Set(values.filter(Boolean))].sort();
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
    if (!from || !to || from.rank === to.rank) continue;
    const key = `${from.rank}->${to.rank}`;
    const entry = counts.get(key) || { from: from.name, to: to.name, fromRank: from.rank, toRank: to.rank, count: 0 };
    entry.count += 1;
    counts.set(key, entry);
  }
  return [...counts.values()].sort((a, b) => a.fromRank - b.fromRank || a.toRank - b.toRank);
}

/**
 * The summary of an impact walk from `focus`.
 *
 * `{ focus, affected, byDistance, domains, services, boundaries, risky }`:
 * `affected` is every dependent, sorted, without `focus`; `byDistance` groups
 * them as `[{ distance, ids }]`; `boundaries` counts each crossing between two
 * layers as `{ from, to, fromRank, toRank, count }`; `risky` lists
 * `{ id, risks }` for each affected node that carries a risk.
 */
export function impactSummary(focus, impact, { nodeById, parents, layers, edges }) {
  const affected = [...impact.distances.keys()].filter((id) => id !== focus).sort();
  const groups = new Map();
  for (const id of affected) {
    const distance = impact.distances.get(id);
    if (!groups.has(distance)) groups.set(distance, []);
    groups.get(distance).push(id);
  }
  const nearest = (kind) =>
    sortedUnique(affected.map((id) => containerOfKind(id, kind, nodeById, parents)));
  return {
    focus,
    affected,
    byDistance: [...groups].sort(([a], [b]) => a - b).map(([distance, ids]) => ({ distance, ids })),
    domains: nearest(DOMAIN_KIND),
    services: nearest(SERVICE_KIND),
    boundaries: boundariesOf(impact.distances, edges, nodeById, layers),
    risky: affected
      .map((id) => ({ id, risks: risksOf(nodeById.get(id)) }))
      .filter((entry) => entry.risks.length),
  };
}
