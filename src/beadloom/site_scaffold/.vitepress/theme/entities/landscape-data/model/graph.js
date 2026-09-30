// beadloom:component=site-landscape-data
// The landscape data file read as a graph the viewer draws.
//
// A service is a node; a contract is an edge from each of its producers to
// each of its consumers, which is the direction a `produces` edge points in
// the architecture graph, so the viewer draws and walks it as one. Each edge
// carries its contract's key, its verdict, its health and its look, and a
// broken edge carries its verdict as a badge. The file's contracts come along
// whole, for the card.

import { HEALTH, healthOf, lookOf } from "./contracts.js";

/** The kind a contract edge is drawn and walked as. */
export const CONTRACT_EDGE_KIND = "produces";

/**
 * The end of a contract edge that depends on the other: the consumer, its target.
 *
 * Every protocol reads the same way. An AMQP consumer reads the body of the
 * message its producer publishes, a GraphQL consumer calls the schema its
 * producer serves, and a plain dependency is declared as `consumes` by the
 * consumer; in each, the reconciler's `breaking` verdict is the producer
 * breaking what the consumer reads. So a change to a service reaches the
 * consumers of what it produces, along the edge, and never its producers.
 */
export const CONTRACT_DEPENDENT_ENDS = Object.freeze({ [CONTRACT_EDGE_KIND]: "dst" });

const list = (value) => (Array.isArray(value) ? value : []);

function nodeOf(node) {
  return {
    id: node.id,
    label: node.label || node.id,
    kind: node.kind || "",
    url: node.url || "",
    health: node.health || HEALTH.healthy,
  };
}

function edgeOf(edge) {
  const health = healthOf(edge.verdict);
  const contractEdge = {
    src: edge.src,
    dst: edge.dst,
    kind: CONTRACT_EDGE_KIND,
    contract: edge.contract_key || "",
    verdict: edge.verdict || "",
    health,
    look: lookOf(edge.verdict),
  };
  if (health === HEALTH.broken) contractEdge.badge = String(edge.verdict || "").toUpperCase();
  return contractEdge;
}

/** `{ nodes, edges, contracts }` of a landscape data file; empty lists for a missing one. */
export function landscapeGraphOf(data) {
  return {
    nodes: list(data?.nodes).map(nodeOf),
    edges: list(data?.edges).map(edgeOf),
    contracts: list(data?.contracts),
  };
}
