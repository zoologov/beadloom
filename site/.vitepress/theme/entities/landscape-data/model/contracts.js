// beadloom:component=site-landscape-data
// What a contract's verdict means for the landscape, and which contracts are declared.
//
// A verdict falls into one of three kinds of health, as the landscape data
// file's generator buckets it (`landscape_view._health_class`): broken, neutral
// or healthy. A drifting contract is broken, and is also told apart from the
// other broken ones, because drift is a warning that has not yet broken a
// consumer. A contract is declared when its protocol is one the reconciler
// reads a surface for; any other is a plain dependency with no protocol at all.

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
