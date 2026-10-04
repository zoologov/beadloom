// The environment a case that measures time runs in, and the bound it holds there.
//
// A duration measured in a browser says as much about the machine as about the
// viewer: ELK lays the adopter-sized graph out in 2 to 3 s on an Apple M1 Max,
// and a shared build server without a GPU is slower by an amount that differs
// from runner to runner. A case that measures time therefore states one bound per
// environment, and this module names the environment the run is in:
//
// - `ci`: a build server, where `CI` is set (GitHub Actions sets it, and so may
//   a harness that runs the suite as a build server would). The bounds are wide,
//   because the runner's speed is not known in advance.
// - `local`: anywhere else. The bounds are measured on a developer's machine
//   (each case names the one it was measured on).
//
// BEADLOOM_E2E_ENVIRONMENT names the environment instead, e.g. `ci` on a machine
// slower than the one the local bounds were measured on.

/** The environment variable that names the environment instead of `CI`. */
export const ENVIRONMENT_VARIABLE = "BEADLOOM_E2E_ENVIRONMENT";

/** The environment this run is in: `local` or `ci`, unless named otherwise. */
export const ENVIRONMENT = process.env[ENVIRONMENT_VARIABLE] || (process.env.CI ? "ci" : "local");

/**
 * The bound `bounds`, `{ local, ci }`, states for this run's environment. An
 * environment it states no bound for fails the case, naming the ones it states,
 * rather than holding the run to a bound written for another machine.
 */
export function boundHere(bounds) {
  if (!Object.hasOwn(bounds, ENVIRONMENT)) {
    throw new Error(
      `${ENVIRONMENT_VARIABLE}: no bound is stated for the environment "${ENVIRONMENT}"; ` +
        `the case states one for ${Object.keys(bounds).join(", ")}`
    );
  }
  return bounds[ENVIRONMENT];
}
