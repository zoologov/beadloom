// beadloom:component=site-filter-graph
// Which services and contracts the landscape's filters show.
//
// The landscape filters contracts, by protocol and by the health of their
// verdict, or down to the problems alone. A service is shown when it produces
// or consumes a contract that is shown, so a service whose only contract is an
// orphaned consumer with no edge still appears among the problems. With no
// filter set, every service is shown, whether or not it has a contract.

import { HEALTH, healthOf, takesPart } from "../../../entities/landscape-data/index.js";
import { ALL } from "./visibleIds.js";

/** The landscape filters' neutral state, which shows everything. */
export const CONTRACT_FILTER_DEFAULTS = Object.freeze({
  protocol: ALL,
  verdict: ALL,
  problems: false,
});

/** The verdict filter's choices: a health, or all of them. */
export const VERDICT_CHOICES = Object.freeze([
  { value: ALL, label: "all" },
  { value: HEALTH.broken, label: "problems" },
  { value: HEALTH.healthy, label: "healthy" },
  { value: HEALTH.neutral, label: "neutral" },
]);

function shows(contract, filters) {
  const health = healthOf(contract.verdict);
  return (
    (filters.protocol === ALL || contract.protocol === filters.protocol) &&
    (filters.verdict === ALL || health === filters.verdict) &&
    (!filters.problems || health === HEALTH.broken)
  );
}

function isFiltering(filters) {
  return Object.entries(CONTRACT_FILTER_DEFAULTS).some(([key, neutral]) => filters[key] !== neutral);
}

/** `{ nodes, contracts }`: the ids of the services shown, and the keys of the contracts shown. */
export function visibleContracts(graph, filters) {
  const contracts = graph.contracts.filter((contract) => shows(contract, filters));
  const keys = new Set(contracts.map((contract) => contract.contract_key));
  const nodes = isFiltering(filters)
    ? graph.nodes.filter((node) => contracts.some((contract) => takesPart(contract, node.id)))
    : graph.nodes;
  return { nodes: new Set(nodes.map((node) => node.id)), contracts: keys };
}

/** `{ protocols }`: the protocols the contracts declare, `all` first. */
export function contractFilterOptions(contracts) {
  const protocols = new Set(contracts.map((contract) => contract.protocol).filter(Boolean));
  return { protocols: [ALL, ...[...protocols].sort()] };
}
