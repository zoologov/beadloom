// What a case needs the served graph to hold, and what it does when the graph holds less.
//
// The suite runs on any built portal, and a correct portal can lack a shape a
// case is written about: a project that declares no layer rule has no layer to
// colour, and a single project's landscape has no contract to walk. A case whose
// subject cannot be chosen from the data it is served says which shape it needs
// with `requireShape`, and the case is skipped with that shape as its reason: the
// run reports what it could not check on this portal instead of failing a portal
// that is correct.
//
// A portal that is meant to hold every shape sets BEADLOOM_E2E_NO_SKIP=1. Under
// it a missing shape fails the case, naming the shape, so a change to the graph
// or to a case's detection that would quietly turn a check into a skip is
// reported as a failure instead.

import { test } from "@playwright/test";

/** The environment variable under which a missing shape fails the case instead of skipping it. */
export const NO_SKIP = "BEADLOOM_E2E_NO_SKIP";

/** The words every skip's reason starts with, so a report can tell a shape's skip from any other. */
export const SKIP_PREFIX = "this portal's graph lacks what the case needs:";

/**
 * Go on when `present`; otherwise skip the running case, naming `lacking`.
 *
 * `lacking` names the shape the served data does not hold, in the words a reader
 * of the report needs to decide whether that is true of the project: "no node
 * has a page under other/", not "precondition failed".
 */
export function requireShape(present, lacking) {
  if (present) return;
  const reason = `${SKIP_PREFIX} ${lacking}`;
  if (process.env[NO_SKIP] === "1") throw new Error(`${NO_SKIP} is set, and ${reason}`);
  test.skip(true, reason);
}

/** Shapes more than one spec needs, each worded as what the served graph lacks. */
export const LACKING = Object.freeze({
  layers:
    "fewer than two declared layers; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml",
  ownLayer: "no node is tagged with a declared layer of its own",
  inheritedLayer: "no node inherits a declared layer through part_of",
  landscape:
    "no contract between two services in the landscape; a single project's landscape is empty without a federation or declared AMQP or GraphQL surfaces",
  landscapeService:
    "no service in the landscape; a single project's landscape is empty without a federation or declared AMQP or GraphQL surfaces",
});
