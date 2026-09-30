// beadloom:component=site-landscape-data
// What a contract's verdict means for the landscape, and which contracts are declared.
//
// A verdict falls into one of three kinds of health, as the landscape data
// file's generator buckets it (`landscape_view._health_class`): broken, neutral
// or healthy. A drifting contract is broken, and is also told apart from the
// other broken ones, because drift is a warning that has not yet broken a
// consumer. A contract is declared when its protocol is one the reconciler
// reads a surface for; any other is a plain dependency with no protocol at all.
//
// A contract is verified when its verdict compared what the consumer reads with
// what the producer declares. The generator states what decided each verdict as
// `verdict_basis` (`surface`, `presence` or `lifecycle`), because a GraphQL
// comparison by name leaves no other trace in the file. A service that takes
// part in a broken contract, or in one that is not broken and not verified,
// runs a risk when something it depends on changes.

/** The three kinds of health. */
export const HEALTH = Object.freeze({ healthy: "healthy", broken: "broken", neutral: "neutral" });

/** The verdicts that are not healthy, by the health they fall into. */
const UNHEALTHY = Object.freeze({
  drift: HEALTH.broken,
  breaking: HEALTH.broken,
  orphaned_consumer: HEALTH.broken,
  undeclared_producer: HEALTH.broken,
  undeclared: HEALTH.broken,
  expected: HEALTH.neutral,
  external: HEALTH.neutral,
  dead: HEALTH.neutral,
  unmapped: HEALTH.neutral,
});

/** The verdict of a contract that drifts: broken, and drawn apart. */
export const DRIFT = "drift";

/** The protocols whose surface the reconciler reads. */
export const DECLARED_PROTOCOLS = Object.freeze(["amqp", "graphql"]);

/** The health a verdict falls into; a verdict the table does not name is healthy. */
export function healthOf(verdict) {
  return UNHEALTHY[String(verdict || "").toLowerCase()] || HEALTH.healthy;
}

/** How a contract edge looks: its health, or `drift` for a drifting contract. */
export function lookOf(verdict) {
  return String(verdict || "").toLowerCase() === DRIFT ? DRIFT : healthOf(verdict);
}

/** Whether a contract is declared in a protocol the reconciler reads (never "unknown"). */
export function isDeclaredContract(contract) {
  return Boolean(contract) && DECLARED_PROTOCOLS.includes(String(contract.protocol || ""));
}

/** Whether `id` produces or consumes `contract`. */
export function takesPart(contract, id) {
  return (contract.producers || []).includes(id) || (contract.consumers || []).includes(id);
}

/** The label a contract with no declared protocol is counted under. */
export const PLAIN_DEPENDENCY = "plain dependency";

/** The protocol a contract is counted under: its declared protocol, or a plain dependency. */
export function protocolLabelOf(contract) {
  return isDeclaredContract(contract) ? contract.protocol : PLAIN_DEPENDENCY;
}

/** The verdict basis of a verdict that compared both sides' declared surface. */
const SURFACE_BASIS = "surface";

/** Whether the contract's verdict compared its surface; a file that does not say is not verified. */
export function isVerifiedContract(contract) {
  return contract?.verdict_basis === SURFACE_BASIS;
}

/** The risks a service's contracts carry, by the label the impact list shows. */
export const CONTRACT_RISKS = Object.freeze({
  broken: "broken contract",
  unverified: "unverified contract",
});

/**
 * The risks `id` runs through the contracts it takes part in, on either side:
 * a broken contract, and one that is neither broken nor verified. Each label
 * appears once, in the order of `CONTRACT_RISKS`.
 */
export function contractRisksOf(id, contracts) {
  let broken = false;
  let unverified = false;
  for (const contract of contracts || []) {
    if (!takesPart(contract, id)) continue;
    if (healthOf(contract.verdict) === HEALTH.broken) broken = true;
    else if (!isVerifiedContract(contract)) unverified = true;
  }
  const risks = [];
  if (broken) risks.push(CONTRACT_RISKS.broken);
  if (unverified) risks.push(CONTRACT_RISKS.unverified);
  return risks;
}
