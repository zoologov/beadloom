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
 * The bounds are the cost a reader does not notice, on both graphs: a zoom
 * step within 60 ms and a hover within 50 ms, the order of the viewer before an
 * open box kept its outward edges at the box, which took, measured as these
 * cases measure (an Apple M-series machine, headless Chromium, no GPU, one
 * browser at work, medians of three openings), 35 and 39 ms for a zoom step on
 * this portal's graph and the adopter-sized one and 28 ms for a hover on both.
 * Both gestures are timed to a drawn frame, so a gesture whose work fits in
 * one frame costs two or three frames, 33 to 50 ms, and one whose work spills
 * over a frame costs a frame more. A build server is unmeasured: its bounds
 * take the bundling's measured factor of 4.7, and twice that again.
 */
export const GESTURE_MS = Object.freeze({
  zoomStep: { own: { local: 60, ci: 560 }, adopter: { local: 60, ci: 560 } },
  hover: { own: { local: 50, ci: 470 }, adopter: { local: 50, ci: 470 } },
});
