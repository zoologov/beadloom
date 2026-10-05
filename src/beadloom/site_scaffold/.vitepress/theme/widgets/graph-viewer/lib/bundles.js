// beadloom:component=site-graph-viewer
// A node's edges drawn as a trunk and a bus instead of a staircase, from ELK's own routes.
//
// ELK routes every edge of a node in a channel of its own: a node with seventy
// edges leaves its side at seventy points and turns at thirty-odd heights, a
// staircase as wide as the graph. ELK cannot be told otherwise without moving
// every node (`RND.md`, "Probe: the staircase"), so the routes are rewritten
// after it, and no node or box moves:
//
// - A **bus** on every node: the edges that leave one side of a node in one
//   direction start from the middle of that side and share one channel in the
//   first gap, the nearest one ELK already used that no other edge runs along;
//   each leaves the bus where its own ELK lane begins.
// - A **trunk** on a node with many edges: its edges to one top-level box share
//   one member's route, ELK's own, to a distribution line just outside that box,
//   and each drops off the line where ELK had it enter the box. An edge between
//   two such nodes is in both trunks: its source's out of the source's box, its
//   target's from there on.
// - A **join** where a trunk left such an edge in a lane of its own: it rides
//   the lane most of that box's edges leave in out past the distance a node's
//   lanes are counted at, then turns across to its own route.
// - The **fallback**: an edge keeps its own route wherever a new segment would
//   cross a box or run along an edge that has no end in common with it.
//
// A node is a leaf or a box alike: a box's edges leave its border as a leaf's
// do, and a box with many edges would otherwise leave its side in a staircase as
// wide as a leaf's. A node is busy by the edges it draws, its loops included (a
// box's edges into its own children, a node's into a box that holds it), though
// a loop is never rerouted.
//
// The trunks are drawn first, the ones leading out of a node before the ones
// leading in, then the joins, the busiest nodes first, and the buses on top of
// them, the busiest nodes first (`trunks.js`, `joins.js`, `buses.js`), over one
// drawing whose routes they rewrite (`bundleDrawing.js`). A join is reported
// with the trunks, as the short trunk it is. The layered layout runs downwards, so edges leave a node
// through its top and bottom sides, and those are the sides bundled. Every
// threshold is a parameter (`BUNDLE_OPTIONS`); nothing here knows a project's
// names. Everything is pure: routes in, routes out.

import { idRecord } from "../../../shared/ids/index.js";
import { busesAt } from "./buses.js";
import { drawingOf } from "./bundleDrawing.js";
import { joinsAt } from "./joins.js";
import { trunksOf } from "./trunks.js";

/** What the bundling is tuned by, in layout units unless named otherwise. */
export const BUNDLE_OPTIONS = Object.freeze({
  /** A node, leaf or box, that draws at least this many edges, its loops included, gets trunks. */
  trunkDegree: 20,
  /** A node that draws at least this many edges gets buses: every node that has a fan at all. */
  busDegree: 2,
  /** How far outside its box a trunk's distribution line runs. */
  trunkStop: 8,
  /** How much further out the line moves when another edge or a box is in its way. */
  trunkLineStep: 6,
  /** How many places the line is tried at before the trunk is given up. */
  trunkLineTries: 4,
  /** How far either side of a side's middle the two buses start when a side carries both directions. */
  portSeparation: 8,
  /** How far a bus's port moves off its place when an edge's lane begins right there. */
  portShift: 3,
  /** How far, at least, every edge of a bus runs along its channel. */
  channelRun: 2,
  /** How far either side of a bus's ports a box still ends the first gap. */
  gapReach: 400,
  /** How close another edge may run to a bus channel and leave it free. */
  channelClearance: 6,
  /** How deep a bus runs when ELK used no channel in the first gap. */
  shallowChannel: 10,
  /** How close a new segment may run along an unrelated edge. */
  alongClearance: 3,
  /** How close another edge may run along a distribution line and leave it free. */
  lineClearance: 4,
  /** How far out from a busy node its lanes are counted: a join rides its lane that far, a trunk keeps them there. */
  laneReach: 150,
  /** How far apart the levels lie that a joined edge may turn off its lane at, past `laneReach`. */
  joinStep: 6,
  /** How many such levels are tried before the edge keeps a lane of its own. */
  joinTries: 40,
  /** The side of a cell of the index over the boxes. */
  cellSize: 512,
  /** The width of a band of the index over the routes' segments. */
  bandWidth: 16,
});

/**
 * The routes of a drawing with its fans bundled: `{ paths, trunks, buses }`.
 *
 * `nodes` are `{ id, parent }` (null at a root); `edges` are the routed edges,
 * `{ id, source, target }`, without the ones drawn as loops, and `loops` those,
 * the same way, counted in a node's degree and never rerouted; `boxes` map a node's
 * id to its box `{ x1, y1, x2, y2 }`, and `paths` an edge's id to its route, a
 * polyline of `{ x, y }`. `paths` in the answer holds every routed edge's route,
 * bundled or as it was; `trunks` and `buses` say which edges share which, a
 * join counted with the trunks (its `direction` "both" when its edges lead both
 * ways).
 * `overrides` replace any of `BUNDLE_OPTIONS`.
 */
export function bundleRoutes(drawing, overrides = {}) {
  const options = { ...BUNDLE_OPTIONS, ...overrides };
  const state = drawingOf(drawing, options);
  const hubs = state.nodesWithDegree(options.trunkDegree);
  const busy = new Set(hubs);
  const trunksLeading = (direction) => hubs.flatMap((hub) => trunksOf(state, hub, direction, busy, options));
  const trunks = [...trunksLeading("out"), ...trunksLeading("in")];
  const joins = state.nodesByDegree(options.trunkDegree).flatMap((hub) => joinsAt(state, hub, busy, options));
  const buses = state.nodesByDegree(options.busDegree).flatMap((node) => busesAt(state, node, options));
  return { paths: idRecord(state.routes), trunks: [...trunks, ...joins], buses };
}
