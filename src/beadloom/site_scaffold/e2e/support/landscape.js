// The browser tests' own reading of the landscape data file, written independently of the viewer.
//
// The expected sets come from `landscape.data.json` directly: which services a
// filter leaves, a service's one-step neighbourhood along the contracts, and
// what a change to a service reaches over them, with the risks its contracts
// carry. `grownLandscape` serves a larger landscape built on the real one, so
// the impact walk has depth, a cycle, and broken and unverified contracts.

import { expect } from "@playwright/test";
import { waitForViewer } from "./viewer.js";

/** Each verdict's health, as the landscape data file's generator buckets it. */
const BROKEN = ["drift", "breaking", "orphaned_consumer", "undeclared_producer", "undeclared"];
const NEUTRAL = ["expected", "external", "dead", "unmapped"];

/** The health a verdict reads as: `broken`, `neutral` or `healthy`. */
export function healthOf(verdict) {
  const value = String(verdict || "").toLowerCase();
  if (BROKEN.includes(value)) return "broken";
  if (NEUTRAL.includes(value)) return "neutral";
  return "healthy";
}

/** Open the landscape page, optionally with a query string, and wait for the layout. */
export async function openLandscape(page, query = "") {
  await page.goto(`landscape.html${query}`);
  await waitForViewer(page);
}

/** The landscape data file the page was built from. */
export async function landscapeData(request) {
  const response = await request.get("landscape.data.json");
  expect(response.ok()).toBe(true);
  return response.json();
}

/** The ids of the services an edge of `health` touches (every edge when `health` is `all`), sorted. */
export function servicesWithEdges(data, health) {
  const ids = new Set();
  for (const edge of data.edges) {
    if (health !== "all" && healthOf(edge.verdict) !== health) continue;
    ids.add(edge.src);
    ids.add(edge.dst);
  }
  return [...ids].sort();
}

/** A service's one-step neighbourhood along the contracts, both ways: `{ ids, edges }`. */
export function contractNeighbourhood(data, id) {
  const ids = new Set([id]);
  const edges = new Set();
  for (const edge of data.edges) {
    if (edge.src === edge.dst || (edge.src !== id && edge.dst !== id)) continue;
    ids.add(edge.src);
    ids.add(edge.dst);
    edges.add(`produces:${edge.src}->${edge.dst}`);
  }
  return { ids: [...ids].sort(), edges: [...edges].sort() };
}

/** The contracts a service produces or consumes. */
export function contractsOf(data, id) {
  return data.contracts.filter(
    (c) => (c.producers || []).includes(id) || (c.consumers || []).includes(id)
  );
}

/** The protocols whose surface the reconciler reads; any other contract is a plain dependency. */
const DECLARED_PROTOCOLS = ["amqp", "graphql"];

/** The label the impact summary gives a contract's protocol. */
export function protocolLabel(contract) {
  const protocol = String(contract?.protocol || "");
  return DECLARED_PROTOCOLS.includes(protocol) ? protocol : "plain dependency";
}

/**
 * Every service a change to `start` reaches over the contracts: `{ distances }`.
 *
 * A contract edge runs from a producer to a consumer, and the consumer is the
 * one that reads what the producer publishes or calls what it serves, so a
 * change travels along an edge from its source to its target, with no limit.
 */
export function contractImpact(data, start) {
  const next = new Map();
  for (const edge of data.edges) {
    if (edge.src === edge.dst) continue;
    (next.get(edge.src) || next.set(edge.src, []).get(edge.src)).push(edge.dst);
  }
  const distances = new Map([[start, 0]]);
  let frontier = [start];
  for (let depth = 1; frontier.length; depth += 1) {
    const reached = [];
    for (const id of frontier) {
      for (const other of next.get(id) || []) {
        if (distances.has(other)) continue;
        distances.set(other, depth);
        reached.push(other);
      }
    }
    frontier = reached;
  }
  return { distances };
}

/**
 * The risks a service runs through its contracts, sorted: a contract of any
 * side whose verdict is broken, and one that is not broken and whose verdict
 * compared no declared surface (`verdict_basis` other than `surface`, or none).
 */
export function contractRisksOf(data, id) {
  const risks = new Set();
  for (const contract of contractsOf(data, id)) {
    if (healthOf(contract.verdict) === "broken") risks.add("broken contract");
    else if (contract.verdict_basis !== "surface") risks.add("unverified contract");
  }
  return [...risks].sort();
}

/** What the landscape's impact summary must say for `start`, from the data file alone. */
export function expectedContractImpact(data, start) {
  const { distances } = contractImpact(data, start);
  const affected = [...distances.keys()].filter((id) => id !== start).sort();
  const crossedEdges = data.edges.filter((e) => e.src !== e.dst && distances.has(e.src));
  const contracts = [...new Set(crossedEdges.map((e) => e.contract_key))].sort();
  const byKey = new Map(data.contracts.map((c) => [c.contract_key, c]));
  const risks = Object.fromEntries(
    affected.map((id) => [id, contractRisksOf(data, id)]).filter(([, labels]) => labels.length)
  );
  return {
    distances: Object.fromEntries(distances),
    affected,
    contracts,
    protocols: [...new Set(contracts.map((key) => protocolLabel(byKey.get(key))))].sort(),
    broken: [
      ...new Set(crossedEdges.filter((e) => healthOf(e.verdict) === "broken").map((e) => e.contract_key)),
    ].sort(),
    risky: Object.keys(risks).sort(),
    risks,
  };
}

/**
 * A landscape grown from the served one, so the walk has somewhere to go.
 *
 * The file's own services and contracts stay, and seven services join them
 * behind the first contract's consumer: a chain four contracts deep, a
 * contract back into the chain, a producer outside the chain, a broken, a
 * drifting and an unverified contract, and a consumer with no producer.
 * `root` is the producer of the file's first contract, where the walk starts.
 * A landscape with no contract, as a single project serves, is first given
 * one, between two services of its own, so the same walk is grown on it.
 */
export function grownLandscape(data) {
  const contract = (key, protocol, producers, consumers, verdict, basis) => ({
    contract_key: key,
    protocol,
    name: key,
    verdict,
    verdict_basis: basis,
    lifecycle: "active",
    routing: {},
    producers,
    consumers,
    missing: [],
    fields: { exposed: {}, referenced: {} },
    body: { exposed: {}, referenced: {} },
  });
  const first = data.edges[0] ?? { src: "svc-origin", dst: "svc-hub" };
  const hub = first.dst;
  const seeded = data.edges.length
    ? []
    : [contract("amqp:origin/sent:Sent", "amqp", [first.src], [hub], "confirmed", "surface")];
  const added = [
    ...seeded,
    contract("amqp:orders/placed:Placed", "amqp", [hub], ["svc-billing", "svc-mail"], "confirmed", "surface"),
    contract("graphql:Billing", "graphql", ["svc-billing"], ["svc-report"], "breaking", "surface"),
    contract("amqp:report/ready:Ready", "amqp", ["svc-report"], [hub], "confirmed", "presence"),
    contract("graphql:Mail", "graphql", ["svc-mail"], ["svc-audit"], "drift", "presence"),
    contract("amqp:audit/kept:Kept", "amqp", ["svc-audit"], ["svc-archive"], "confirmed", "surface"),
    contract("graphql:Rates", "graphql", ["svc-outside"], ["svc-billing"], "expected", "lifecycle"),
    contract("amqp:archive/asked:Asked", "amqp", [], ["svc-archive"], "orphaned_consumer", "presence"),
  ];
  const grown = structuredClone(data);
  const known = new Set(grown.nodes.map((n) => n.id));
  for (const c of added) {
    grown.contracts.push(c);
    for (const id of [...c.producers, ...c.consumers]) {
      if (known.has(id)) continue;
      known.add(id);
      grown.nodes.push({ id, label: id, kind: "service", group: "services", health: "healthy", url: "" });
    }
    for (const src of c.producers) {
      for (const dst of c.consumers) {
        if (src !== dst) grown.edges.push({ src, dst, verdict: c.verdict, contract_key: c.contract_key });
      }
    }
  }
  return { data: grown, root: first.src, hub };
}

/** Serve `data` in place of the landscape data file on `page`. */
export async function serveLandscape(page, data) {
  await page.route("**/landscape.data.json", (route) => route.fulfill({ json: data }));
}
