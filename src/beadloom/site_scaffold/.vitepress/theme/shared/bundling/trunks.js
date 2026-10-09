// beadloom:component=site-shared-bundling
// A trunk from a busy node to each top-level box: its edges there share one route to a line along the box.
//
// A node with many edges sends several of them into one top-level box, each in
// its own lane across the graph. A trunk draws them along one route, the one of
// them whose first lane leaves nearest the node's middle, ELK's own, up to a
// distribution line just outside the box; there each runs along the line to the
// place where ELK had it enter the box, and on as ELK routed it. The line moves
// further out when another edge runs along it or a box stands across it, and
// the trunk is given up when no place is free.
//
// The trunks leading out of every busy node are drawn first, then the ones
// leading in. An edge between two busy nodes is in both: it leaves its source
// along the source's trunk and, from the line along the source's top-level box
// on, follows the target's. So the route a trunk shares has to be one no other
// trunk runs along: an edge into the hub from elsewhere would share a line with
// edges that have no end in common with it.

import {
  BOX_INSET,
  centreX,
  directionAt,
  fromNode,
  keepsLane,
  near,
  otherEnd,
  runsAlongAnother,
  simplify,
} from "./bundleDrawing.js";

/** Where `route` first enters the rectangle `r` from outside: `{ i, point, side }`, or null. */
function entryInto(route, r) {
  for (let i = 1; i < route.length; i += 1) {
    const a = route[i - 1];
    const b = route[i];
    if (near(a.x, b.x) && a.x > r.x1 && a.x < r.x2) {
      if (a.y <= r.y1 && b.y > r.y1) return { i, point: { x: a.x, y: r.y1 }, side: "top" };
      if (a.y >= r.y2 && b.y < r.y2) return { i, point: { x: a.x, y: r.y2 }, side: "bottom" };
    } else if (near(a.y, b.y) && a.y > r.y1 && a.y < r.y2) {
      if (a.x <= r.x1 && b.x > r.x1) return { i, point: { x: r.x1, y: a.y }, side: "left" };
      if (a.x >= r.x2 && b.x < r.x2) return { i, point: { x: r.x2, y: a.y }, side: "right" };
    }
  }
  return null;
}

/** The side most entries cross, the first named on a tie. */
function busiestSide(entries) {
  const counts = new Map();
  for (const { entry } of entries) counts.set(entry.side, (counts.get(entry.side) || 0) + 1);
  let best = null;
  for (const [side, count] of counts) if (!best || count > counts.get(best)) best = side;
  return best;
}

/** Whether another edge runs along the distribution line, or a box `allowed` does not accept straddles it. */
function lineBlocked(drawing, { line, along, across, lo, hi }, members, allowed, clearance) {
  const rect =
    along === "x"
      ? { x1: lo, x2: hi, y1: line - clearance, y2: line + clearance }
      : { x1: line - clearance, x2: line + clearance, y1: lo, y2: hi };
  let blocked = false;
  const orientation = along === "x" ? "horizontal" : "vertical";
  drawing.segmentsAlong(orientation, line, clearance, lo, hi, (edge, a, b) => {
    if (blocked || members.has(edge.id) || Math.abs(a[across] - line) >= clearance) return;
    blocked = Math.max(a[along], b[along]) > lo && Math.min(a[along], b[along]) < hi;
  });
  if (blocked) return true;
  drawing.boxesIn(rect, (id, q) => {
    if (blocked || allowed(id)) return;
    const [q1, q2, c1, c2] = along === "x" ? [q.x1, q.x2, q.y1, q.y2] : [q.y1, q.y2, q.x1, q.x2];
    blocked = line > c1 + BOX_INSET && line < c2 - BOX_INSET && hi > q1 + BOX_INSET && lo < q2 - BOX_INSET;
  });
  return blocked;
}

/**
 * Whether the route of `item` up to its entry runs along no edge that does not
 * end at `hub`, closer than `options.alongClearance`: every member of the trunk
 * would run along it.
 */
function ownsItsRoute(drawing, hub, { route, entry }, options) {
  const atHub = (other) => other.source === hub || other.target === hub;
  const shared = [...route.slice(0, entry.i), entry.point];
  for (let i = 1; i < shared.length; i += 1) {
    if (runsAlongAnother(drawing, shared[i - 1], shared[i], options.alongClearance, atHub)) return false;
  }
  return true;
}

/**
 * Where a trunk of `group` (edges of `hub` to the top-level box `target`) meets
 * its distribution line: `{ trunk, members, side, line }`, or null when no
 * place for the line is free.
 */
function distributionOf(drawing, hub, group, target, options) {
  const box = drawing.boxes[target];
  const hubCentre = centreX(drawing.boxes[hub]);
  const targetAndHolders = drawing.withHolders(target);
  const allowed = (id) => id === hub || targetAndHolders.has(id);
  for (let attempt = 0; attempt < options.trunkLineTries; attempt += 1) {
    const out = options.trunkStop + options.trunkLineStep * attempt;
    const r = { x1: box.x1 - out, y1: box.y1 - out, x2: box.x2 + out, y2: box.y2 + out };
    const entries = group
      .map((edge) => {
        const route = fromNode(edge, hub, drawing.routes.get(edge.id));
        return { edge, route, entry: entryInto(route, r) };
      })
      .filter((item) => item.entry);
    if (entries.length < 2) return null;
    const side = busiestSide(entries);
    const members = entries.filter((item) => item.entry.side === side);
    if (members.length < 2) return null;
    // The trunk is the member whose first lane leaves nearest the hub's middle,
    // of the ones whose route to the line no other trunk runs along.
    const laneOf = ({ route }) => (route[1] ?? route[0]).x;
    const trunk = [...members]
      .sort((a, b) => Math.abs(laneOf(a) - hubCentre) - Math.abs(laneOf(b) - hubCentre))
      .find((item) => ownsItsRoute(drawing, hub, item, options));
    if (!trunk) return null;
    const along = side === "top" || side === "bottom" ? "x" : "y";
    const across = along === "x" ? "y" : "x";
    const places = members.map((item) => item.entry.point[along]);
    const line = { line: trunk.entry.point[across], along, across, lo: Math.min(...places), hi: Math.max(...places) };
    const memberIds = new Set(members.map((item) => item.edge.id));
    if (!lineBlocked(drawing, line, memberIds, allowed, options.lineClearance)) return { trunk, members, side, line };
  }
  return null;
}

/**
 * The trunks of `hub` in `direction` ("out" or "in"): one per top-level box its
 * edges lead to that way, each `{ node, box, direction, side, members }`. The
 * trunks leading out are drawn first, so a trunk leading in keeps out an edge
 * from a busy node of `hubs` whose lane, `options.laneReach` out of that node,
 * it would move: the line along that node's box can lie nearer it than that.
 */
export function trunksOf(drawing, hub, direction, hubs, options) {
  const own = drawing.topBox(hub);
  const groups = new Map();
  for (const edge of drawing.edgesAt(hub)) {
    if (directionAt(edge, hub) !== direction) continue;
    const target = drawing.topBox(otherEnd(edge, hub));
    if (target === own || target === hub || !drawing.boxes[target]) continue;
    if (!groups.has(target)) groups.set(target, []);
    groups.get(target).push(edge);
  }
  const trunks = [];
  for (const [target, edges] of groups) {
    if (edges.length < 2) continue;
    const distribution = distributionOf(drawing, hub, edges, target, options);
    if (!distribution) continue;
    const { trunk, members, side } = distribution;
    const shared = [...trunk.route.slice(0, trunk.entry.i), trunk.entry.point];
    const rerouted = members
      .map(({ edge, route, entry }) => ({
        edge,
        points: fromNode(edge, hub, simplify([...shared, entry.point, ...route.slice(entry.i)])),
      }))
      .filter(({ edge, points }) => {
        const other = otherEnd(edge, hub);
        return direction === "out" || !hubs.has(other) || keepsLane(drawing, edge, other, points, options.laneReach);
      });
    if (rerouted.length < 2) continue;
    for (const { edge, points } of rerouted) drawing.setRoute(edge, points);
    trunks.push({ node: hub, box: target, direction, side, members: rerouted.map(({ edge }) => edge.id) });
  }
  return trunks;
}
