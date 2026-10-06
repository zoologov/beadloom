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

/**
 * The bounds of the cases that time what a reader's own gesture costs
 * (`performance.spec.js`), in ms, per graph and per environment, beside the
 * bounds each case states for a frame, a first drawing, a plan and a bundling.
 *
 * - `zoomStep`: one press of "Zoom in" from the fit towards a box, from the
 *   press until the viewer holds still again and two frames are drawn, the
 *   median of every step until the box opens.
 * - `hover`: the pointer coming to rest on a node inside an open box, from the
 *   move until two frames are drawn, the median over the nodes in view.
 *
 * Locally (an Apple M-series machine, headless Chromium, no GPU, one browser
 * at work) the viewer took, as medians of three openings on the portal these
 * cases were written on: a zoom step 48 ms on its graph and 149 ms on the
 * adopter-sized one, a hover 53 ms and 236 ms. The viewer before an open box
 * kept its outward edges at the box, measured the same way on the same
 * machine, took 35 and 39 ms for a zoom step and 28 ms for a hover on both
 * graphs. The local bounds hold the cost as it is now with half again as much
 * room, so they catch a change that makes it slower still; whether the cost as
 * it is now is acceptable is not theirs to say. A build server is unmeasured:
 * its bounds take the bundling's measured factor of 4.7, and twice that again.
 */
export const GESTURE_MS = Object.freeze({
  zoomStep: { own: { local: 75, ci: 450 }, adopter: { local: 225, ci: 1400 } },
  hover: { own: { local: 80, ci: 500 }, adopter: { local: 350, ci: 2200 } },
});
