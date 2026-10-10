// beadloom:component=site-shared-bundling
// A bus on each side of a node: the edges that leave it one way share one channel in the first gap.
//
// ELK gives each edge of a node a port and a channel of its own, so a node's
// fan leaves its side at as many points as it has edges and turns at as many
// heights. A bus starts every edge that leaves one side in one direction from
// the middle of that side, drops it to one channel, the nearest one ELK already
// used in the first gap that no other edge runs along, and lets it leave the
// bus where its own lane begins. The gap ends at the nearest box over any place
// the channel runs to, a lane's as well as a port's: a channel past the border of
// a box the bus reaches would take an edge to that box past it and back into it.
// A box near the ports ends it too, within `gapReach` of them; one off to the side
// of a lane far out does not, or a box hundreds of units away would hold the
// channel a few units under the node, across the head of a line arriving there.
// When two nodes face one gap, an edge between them keeps the channel the busier
// node's bus gave it, and the other node's bus takes it along its own channel
// first.
//
// Every edge of a bus runs along its channel for a while: a lane that begins
// right below the side's middle would take its edge straight down through the
// channel to turn further out, a second channel, so the bus's port moves off it.
// The port moves off an edge that does not end at the node, too: a box's own
// child can send an edge out through the middle of the box's side, and every
// edge of a bus starting there would run along it, so none would join.
// An edge whose lane cannot be reached along the channel, a box or an unrelated
// edge in the way, leaves the bus at its own port's place instead, as an edge
// that drops further does, and keeps its route only when that fails too.

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
  sharesAnEnd,
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
 * lies over the span `[px1, px2]`, `reach` either side of it included, or the
 * border of a box that holds it. Only `depth` units out are searched; past that
 * the gap counts as open.
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
 * The first gap over every place the bus runs above: its ports, and the lanes of
 * the edges that turn in the gap, `turnsIn(gap)`, since the channel runs out to
 * each of them. A box over a lane, the edge's own target among them, ends the
 * gap as one over a port does: a channel past its border would take that edge
 * past the box and back into it. The span only widens, so the gap only narrows,
 * until no edge left turning in it widens the span further.
 */
function gapOver(ports, gapOf, turnsIn) {
  let span = [Math.min(...ports), Math.max(...ports)];
  for (;;) {
    const gap = gapOf(span);
    const lanes = turnsIn(gap).map(({ route }) => route[2].x);
    const wider = [Math.min(span[0], ...lanes), Math.max(span[1], ...lanes)];
    if (wider[0] === span[0] && wider[1] === span[1]) return gap;
    span = wider;
  }
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
 * Where the bus of `fan` leaves `border`, and its channel: `{ port, channel }`.
 * The port is the side's middle `x`, or `options.portShift` to either side of
 * it: the first of those places that no lane begins nearer to than
 * `options.channelRun` (an edge there would not run along the channel at all)
 * and whose drop to the channel runs along no edge that does not end at `node`
 * (every edge of the bus would start along it). With no such place the first
 * place off the lanes is taken, and with none of those the middle.
 */
function portOf(drawing, node, x, { fan, border, sign, gap, options }) {
  const lanes = fan.map((item) => item.lane);
  const starts = [...lanes, ...fan.map(({ route }) => route[0].x)];
  const atNode = (edge) => edge.source === node || edge.target === node;
  const busAt = (place) => {
    const span = [Math.min(...lanes, place), Math.max(...lanes, place)];
    return { port: { x: place, y: border }, channel: busChannel(drawing, fan, { border, sign, gap, span, options }) };
  };
  const clear = ({ port, channel }) =>
    !runsAlongAnother(drawing, port, { x: port.x, y: channel }, options.alongClearance, atNode);
  const places = [x, x + options.portShift, x - options.portShift].filter((place) =>
    starts.every((start) => Math.abs(start - place) >= options.channelRun)
  );
  let first = null;
  for (const place of places) {
    const bus = busAt(place);
    if (clear(bus)) return bus;
    first ||= bus;
  }
  return first || busAt(x);
}

/**
 * Reroute one edge of `node`'s fan onto its bus, from `port` down to `channel`,
 * along it and on as before; true when it joined. An edge whose first turn lies
 * in the gap runs along the channel to its lane, and failing that, as every other
 * edge does, to its own port's place, to drop to its first turn from there. It
 * stays as it was when every way would cross a box other than its ends' and their
 * holders', or run along an edge with no end in common with it, and when another
 * bus claimed its channel nearer the node than this one.
 */
function joinBus(drawing, node, { edge, route, inGap, claimed }, { port, channel, sign, options }) {
  const down = { x: port.x, y: channel };
  const ways = [];
  if (inGap) ways.push([port, down, { x: route[2].x, y: channel }, { x: route[2].x, y: route[1].y }]);
  // Down to the channel and back would not be a drop: only an edge that turns
  // beyond the channel takes it, or one ELK already dropped past the gap.
  const beyond = sign * (route[1].y - channel) >= NEAR;
  if (beyond || !(inGap || claimed)) ways.push([port, down, { x: route[0].x, y: channel }, route[1]]);
  const nodeAndHolders = drawing.withHolders(node);
  const otherAndHolders = drawing.withHolders(otherEnd(edge, node));
  const allowed = (id) => nodeAndHolders.has(id) || otherAndHolders.has(id);
  const related = (other) => sharesAnEnd(other, edge);
  const fits = (points) =>
    points.every(
      (point, i) =>
        i === 0 ||
        (!crossesABox(drawing, points[i - 1], point, allowed) &&
          !runsAlongAnother(drawing, points[i - 1], point, options.alongClearance, related))
    );
  const points = ways.find(fits);
  if (!points) return false;
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
  const ports = fan.map(({ route }) => route[0].x);
  const depth = Math.max(2 * options.shallowChannel, ...fan.map(({ route }) => sign * (route[1].y - border)));
  // An edge whose first turn lies in the gap joins the bus at its lane; one that
  // drops further first, or whose channel another bus claimed, leaves the bus at
  // its own port's place and keeps its drop to that channel.
  const turnsIn = (gap) => fan.filter((item) => !item.claimed && sign * (item.route[1].y - border) < gap);
  // The reach is kept around the ports; over a lane, only a box right under the channel's run ends the gap.
  const nearPorts = firstGap(drawing, node, border, sign, [Math.min(...ports), Math.max(...ports)], depth, options.gapReach);
  const gapOf = (span) => Math.min(nearPorts, firstGap(drawing, node, border, sign, span, depth, 0));
  const gap = gapOver(ports, gapOf, turnsIn);
  const inGap = new Set(turnsIn(gap));
  for (const item of fan) {
    item.inGap = inGap.has(item);
    item.lane = item.inGap ? item.route[2].x : item.route[0].x;
  }
  const { port, channel } = portOf(drawing, node, centreX(box) + separation, { fan, border, sign, gap, options });

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
