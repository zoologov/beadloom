// beadloom:component=site-graph-viewer
// A trunk from a busy node to each top-level box: its edges there share one route to a line along the box.
//
// A node with many edges sends several of them into one top-level box, each in
// its own lane across the graph. A trunk draws them along one route, the one of
// them whose first lane leaves nearest the node's middle, ELK's own, up to a
// distribution line just outside the box; there each runs along the line to the
// place where ELK had it enter the box, and on as ELK routed it. The line moves
// further out when another edge runs along it or a box stands across it, and
// the trunk is given up when no place is free. An edge between two busy nodes
// belongs to its source's trunk only.

import { BOX_INSET, centreX, directionAt, fromNode, near, otherEnd, simplify } from "./bundleDrawing.js";

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
    // The trunk is the member whose first lane leaves nearest the hub's middle.
    const laneOf = ({ route }) => (route[1] ?? route[0]).x;
    const trunk = members.reduce((best, item) =>
      Math.abs(laneOf(item) - hubCentre) < Math.abs(laneOf(best) - hubCentre) ? item : best
    );
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
 * The trunks of `hub`: one per top-level box its edges lead to and direction,
 * each `{ node, box, direction, side, members }`. An edge into the hub from
 * another hub in `hubs` is left to that hub's trunk.
 */
export function trunksOf(drawing, hub, hubs, options) {
  const own = drawing.topBox(hub);
  const groups = new Map();
  for (const edge of drawing.edgesAt(hub)) {
    const other = otherEnd(edge, hub);
    const target = drawing.topBox(other);
    if (target === own || target === hub || !drawing.boxes[target]) continue;
    if (edge.target === hub && hubs.has(other)) continue;
    const key = `${directionAt(edge, hub)}\u0000${target}`;
    if (!groups.has(key)) groups.set(key, { target, direction: directionAt(edge, hub), edges: [] });
    groups.get(key).edges.push(edge);
  }
  const trunks = [];
  for (const { target, direction, edges } of groups.values()) {
    if (edges.length < 2) continue;
    const distribution = distributionOf(drawing, hub, edges, target, options);
    if (!distribution) continue;
    const { trunk, members, side } = distribution;
    const shared = [...trunk.route.slice(0, trunk.entry.i), trunk.entry.point];
    for (const { edge, route, entry } of members) {
      const points = simplify([...shared, entry.point, ...route.slice(entry.i)]);
      drawing.setRoute(edge, fromNode(edge, hub, points));
    }
    trunks.push({ node: hub, box: target, direction, side, members: members.map(({ edge }) => edge.id) });
  }
  return trunks;
}
