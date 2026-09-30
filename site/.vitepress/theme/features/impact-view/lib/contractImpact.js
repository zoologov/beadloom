// beadloom:component=site-impact-view
// What a change to a service reaches over the landscape's contracts, and what that amounts to.
//
// The walk is the one `impact.js` runs, over the dependents the landscape names
// (`CONTRACT_DEPENDENT_ENDS`): from a service to the consumers of what it
// produces, theirs, and so on, with no limit. The summary is what an estimate
// of a change to a service needs: how many services it reaches, which
// contracts and protocols it crosses on the way, which of those contracts are
// broken, and which reached services run a risk through their contracts. Like
// the architecture's, it is the graph's view: contracts as the reconciler
// recorded them, not a reading of the code on either side.

import {
  CONTRACT_EDGE_KIND,
  HEALTH,
  contractRisksOf,
  protocolLabelOf,
} from "../../../entities/landscape-data/index.js";
import { reachOf, sortedUnique } from "./impact.js";

/** The walk a summary of the landscape reads: contracts, from a producer to its consumers. */
export const CONTRACT_WALK = "contracts";

/** The contract edges the walk took: from a reached service to one it reached. */
function crossedEdges(impact, edges) {
  return edges.filter(
    (edge) =>
      edge.kind === CONTRACT_EDGE_KIND &&
      edge.src !== edge.dst &&
      impact.distances.has(edge.src) &&
      impact.distances.has(edge.dst)
  );
}

/**
 * The summary of an impact walk from `focus` over the landscape.
 *
 * `{ walk, focus, affected, byDistance, contracts, protocols, broken, risky }`:
 * `walk` is `CONTRACT_WALK`; `affected` and `byDistance` are `reachOf`'s;
 * `contracts` are the keys of the contracts the walk crossed, `protocols`
 * their protocols (`protocolLabelOf`), and `broken` the crossed contracts whose
 * verdict is broken, each sorted; `risky` lists `{ id, risks }` for each
 * affected service with a broken or unverified contract (`contractRisksOf`).
 */
export function contractImpactSummary(focus, impact, { edges, contracts }) {
  const { affected, byDistance } = reachOf(focus, impact);
  const crossed = crossedEdges(impact, edges);
  const keys = sortedUnique(crossed.map((edge) => edge.contract));
  const byKey = new Map(contracts.map((contract) => [contract.contract_key, contract]));
  return {
    walk: CONTRACT_WALK,
    focus,
    affected,
    byDistance,
    contracts: keys,
    protocols: sortedUnique(keys.map((key) => protocolLabelOf(byKey.get(key)))),
    broken: sortedUnique(
      crossed.filter((edge) => edge.health === HEALTH.broken).map((edge) => edge.contract)
    ),
    risky: affected
      .map((id) => ({ id, risks: contractRisksOf(id, contracts) }))
      .filter((entry) => entry.risks.length),
  };
}
