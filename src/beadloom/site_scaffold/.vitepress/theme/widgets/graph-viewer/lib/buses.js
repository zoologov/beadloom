// beadloom:component=site-graph-viewer
// A bus on each side of a node: the edges that leave it one way share one channel in the first gap.
//
// ELK gives each edge of a node a port and a channel of its own, so a node's
// fan leaves its side at as many points as it has edges and turns at as many
// heights. A bus starts every edge that leaves one side in one direction from
// the middle of that side, drops it to one channel, the nearest one ELK already
// used in the first gap that no other edge runs along, and lets it leave the
// bus where its own lane begins. When two nodes face one gap, an edge between
// them keeps the channel the busier node's bus gave it, and the other node's bus
// takes it along its own channel first.

import {
  NEAR,
  centreX,
  crossesABox,
  directionAt,
  fromNode,
  headFrom,
  near,
  otherEnd,
  runsAlongAnother,
  simplify,
} from "./bundleDrawing.js";

/** The bundled sides of a node: the bottom side leads down, the top one up. */
const SIDES = Object.freeze([
  { side: "bottom", sign: 1 },
  { side: "top", sign: -1 },
]);
const DIRECTIONS = Object.freeze(["out", "in"]);

/**
 * The first gap on one side of `node`: how far from its border the nearest box
 * lies over the span of its ports, or the border of a box that holds it. Only
 * `depth` units out are searched; past that the gap counts as open.
 */
function firstGap(drawing, node, border, sign, [px1, px2], depth, reach) {
  let gap = Infinity;
  const ancestors = drawing.ancestors(node);
  for (const id of ancestors) {
    const box = drawing.boxes[id];
    if (!box) continue;
    const distance = sign * ((sign > 0 ? box.y2 : box.y1) - border);
    if (distance > 0) gap = Math.min(gap, distance);
  }
  const strip = { x1: px1 - reach, x2: px2 + reach, y1: Math.min(border, border + sign * depth), y2: Math.max(border, border + sign * depth) };
  drawing.boxesIn(strip, (id, r) => {
    if (id === node || ancestors.includes(id)) return;
    const distance = sign * ((sign > 0 ? r.y1 : r.y2) - border);
    if (distance > 0 && r.x1 < px2 + reach && r.x2 > px1 - reach) gap = Math.min(gap, distance);
  });
  return gap;
}

/**
 * The edges of `node` that leave `border` in `direction` by dropping to a channel
 * and turning, each `{ edge, route, claimed }`. An edge is claimed when its
 * channel is already the bus of the node at its other end: the two nodes face
 * one gap, and the edge keeps that channel.
 */
function fanOf(drawing, node, border, direction) {
  const fan = [];
  for (const edge of drawing.edgesAt(node)) {
    if (directionAt(edge, node) !== direction) continue;
    const points = drawing.routes.get(edge.id);
    const head = headFrom(edge, node, points, 3);
    if (head.length < 3 || !near(head[0].y, border)) continue;
    if (!near(head[0].x, head[1].x) || !near(head[1].y, head[2].y)) continue;
    const given = drawing.channels.get(edge.id);
    const route = fromNode(edge, node, points);
    fan.push({ edge, route, claimed: Boolean(given && given.node !== node && near(given.y, route[1].y)) });
  }
  return fan;
}

/** The bus channel: the nearest channel of the fan in the first gap that no other edge runs along. */
function busChannel(drawing, fan, { border, sign, gap, span, options }) {
  const own = new Set(fan.map(({ edge }) => edge.id));
  const channels = [...new Set(fan.filter((item) => item.inGap).map(({ route }) => route[1].y))].sort(
    (a, b) => sign * (a - b)
  );
  if (!channels.length) channels.push(border + sign * Math.min(options.shallowChannel, gap / 2));
  const clearance = options.channelClearance;
  const free = (y) => {
    let taken = false;
    drawing.segmentsAlong("horizontal", y, clearance, span[0], span[1], (edge, a, b) => {
      if (taken || own.has(edge.id) || Math.abs(a.y - y) >= clearance) return;
      taken = Math.max(a.x, b.x) > span[0] && Math.min(a.x, b.x) < span[1];
    });
    return !taken;
  };
  return channels.find(free) ?? channels[0];
}

/**
 * Reroute one edge of `node`'s fan onto its bus, from `port` down to `channel`,
 * along it to the edge's lane and on as before; true when it joined. It stays
 * as it was when a new segment would cross a box other than its ends' and their
 * holders', or run along an edge that does not end at `node`, and when another
 * bus claimed its channel nearer the node than this one.
 */
function joinBus(drawing, node, { edge, route, inGap, lane, claimed }, { port, channel, sign, options }) {
  if (claimed && sign * (route[1].y - channel) < NEAR) return false;
  const turn = inGap ? { x: lane, y: route[1].y } : route[1];
  const points = [port, { x: port.x, y: channel }, { x: lane, y: channel }, turn];
  const nodeAndHolders = drawing.withHolders(node);
  const otherAndHolders = drawing.withHolders(otherEnd(edge, node));
  const allowed = (id) => nodeAndHolders.has(id) || otherAndHolders.has(id);
  const atNode = (other) => other.source === node || other.target === node;
  for (let i = 1; i < points.length; i += 1) {
    if (crossesABox(drawing, points[i - 1], points[i], allowed)) return false;
    if (runsAlongAnother(drawing, points[i - 1], points[i], options.alongClearance, atNode)) return false;
  }
  drawing.setRoute(edge, fromNode(edge, node, simplify([...points, ...route.slice(2)])));
  drawing.channels.set(edge.id, { node, y: channel });
  return true;
}

/**
 * The bus on one side of `node` in one direction: its members' routes rewritten,
 * `{ node, side, direction, channel, members }`, or null when fewer than two
 * edges leave that way.
 */
function busOf(drawing, node, { side, sign }, direction, options) {
  const box = drawing.boxes[node];
  const border = sign > 0 ? box.y2 : box.y1;
  const fan = fanOf(drawing, node, border, direction);
  if (fan.length < 2) return null;
  const opposite = drawing
    .edgesAt(node)
    .some(
      (edge) =>
        directionAt(edge, node) !== direction &&
        near(headFrom(edge, node, drawing.routes.get(edge.id), 1)[0].y, border)
    );
  const separation = opposite ? (direction === "out" ? options.portSeparation : -options.portSeparation) : 0;
  const port = { x: centreX(box) + separation, y: border };

  const ports = fan.map(({ route }) => route[0].x);
  const depth = Math.max(2 * options.shallowChannel, ...fan.map(({ route }) => sign * (route[1].y - border)));
  const gap = firstGap(drawing, node, border, sign, [Math.min(...ports), Math.max(...ports)], depth, options.gapReach);
  // An edge whose first turn lies in the gap joins the bus at its lane; one that
  // drops further first, or whose channel another bus claimed, leaves the bus at
  // its own port's place and keeps its drop to that channel.
  for (const item of fan) {
    item.inGap = !item.claimed && sign * (item.route[1].y - border) < gap;
    item.lane = item.inGap ? item.route[2].x : item.route[0].x;
  }
  const lanes = fan.map((item) => item.lane);
  const span = [Math.min(...lanes, port.x), Math.max(...lanes, port.x)];
  const channel = busChannel(drawing, fan, { border, sign, gap, span, options });

  const members = fan
    .filter((item) => joinBus(drawing, node, item, { port, channel, sign, options }))
    .map(({ edge }) => edge.id);
  return members.length ? { node, side, direction, channel, members } : null;
}

/** The buses of `node`, one per side and direction that two edges or more leave by. */
export function busesAt(drawing, node, options) {
  const buses = [];
  for (const side of SIDES) {
    for (const direction of DIRECTIONS) {
      const bus = busOf(drawing, node, side, direction, options);
      if (bus) buses.push(bus);
    }
  }
  return buses;
}
