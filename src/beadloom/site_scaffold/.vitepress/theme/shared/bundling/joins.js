// beadloom:component=site-shared-bundling
// A busy node's edges to one top-level box leave it along one line, where the trunks left them in lanes of their own.
//
// A trunk gathers a busy node's edges to one top-level box along one route,
// but not every such edge gets into it: a trunk takes the edges that enter the
// box from one side only, it shares a route no other trunk runs along, and it
// is given up when no line along the box is free. Each edge left out leaves the
// node in a lane of its own, and the node's side reads as a staircase again.
//
// So, after the trunks, an edge to one top-level box that leaves a side of a
// busy node in a lane of its own is joined to the lane most of that box's edges
// leave in: it runs along that lane's route out past the distance a node's
// lanes are counted at (`laneReach`), turns across at a level where both routes
// run straight, and goes on along its own route. The turn and the route it rides
// cross no box but its ends' and their holders' and run along no edge that has
// no end in common with it, the turn keeps as clear of a box's border as of such
// an edge, and the edge keeps the lane it leaves its other end in when that end
// is busy too. The level is the nearest one that fits past the lane's first
// corner, so that the bus drawn afterwards (`buses.js`) keeps the two together;
// failing that, the farthest one before that corner, where the bus keeps them
// together when the corner lies past its gap. Where an edge cannot join that
// lane — it runs beside an edge of another node's that has no end in common with
// the edge — the other lanes are tried in turn, and the one most edges join is
// taken; where every lane runs beside such an edge, the edges ride a lane of
// their own, a column straight out of the node's side, past the distance and
// back to their own routes. An edge no level fits keeps its lane, and an edge
// into the node's own top-level box keeps its own by design.

import {
  NEAR,
  ONE_LANE,
  crossesABox,
  fromNode,
  headFrom,
  keepsLane,
  laneAt,
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

/**
 * Where `route` first meets the level `y`, across a vertical run and away from
 * its corners: `{ i, x }`, `i` the index of the run's end; or null.
 */
function crossingAt(route, y) {
  for (let i = 1; i < route.length; i += 1) {
    const a = route[i - 1];
    const b = route[i];
    if ((a.y - y) * (b.y - y) > 0) continue;
    if (!near(a.x, b.x) || Math.abs(a.y - y) < NEAR || Math.abs(b.y - y) < NEAR) return null;
    return { i, x: a.x };
  }
  return null;
}

/**
 * Whether the turn from `a` to `b`, a level run, passes closer than `clearance`
 * along the border of a box `allowed` does not accept: the level is free of
 * boxes, but one drawn a fraction of a unit off it would graze a box.
 */
function turnHugsABox(drawing, a, b, allowed, clearance) {
  return [-clearance, clearance].some((offset) =>
    crossesABox(drawing, { x: a.x, y: a.y + offset }, { x: b.x, y: b.y + offset }, allowed)
  );
}

/**
 * The levels an edge may turn off the lane `carrier` takes at, past `reach`:
 * past the lane's first corner as well, nearest first, then along the lane's
 * first run, farthest first.
 */
function levelsOf(carrier, { reach, sign }, options) {
  const corner = carrier.route[1].y;
  const levels = [];
  const from = sign * (corner - reach) > 0 ? corner : reach;
  for (let step = 1; step <= options.joinTries; step += 1) levels.push(from + sign * step * options.joinStep);
  for (let y = corner - sign * options.joinStep; sign * (y - reach) > 0; y -= sign * options.joinStep) levels.push(y);
  return levels;
}

/**
 * The route that joins `item` (`{ edge, route }`, its route read from `node`) to
 * the route of `carrier`, turning off it at one of `levels`, or null when none
 * fits. `busy` holds the busy nodes, whose lanes the join keeps.
 */
function joinOf(drawing, node, item, carrier, levels, busy, options) {
  const ends = [drawing.withHolders(item.edge.source), drawing.withHolders(item.edge.target)];
  const allowed = (id) => ends.some((holders) => holders.has(id));
  const related = (other) => sharesAnEnd(other, item.edge);
  const far = otherEnd(item.edge, node);
  for (const y of levels) {
    const along = crossingAt(carrier.route, y);
    const own = crossingAt(item.route, y);
    if (!along || !own) continue;
    const head = [...carrier.route.slice(0, along.i), { x: along.x, y }, { x: own.x, y }];
    const fits = head.every(
      (point, i) =>
        i === 0 ||
        (!crossesABox(drawing, head[i - 1], point, allowed) &&
          !runsAlongAnother(drawing, head[i - 1], point, options.alongClearance, related))
    );
    if (!fits || turnHugsABox(drawing, { x: along.x, y }, { x: own.x, y }, allowed, options.alongClearance)) continue;
    const points = fromNode(item.edge, node, simplify([...head, ...item.route.slice(own.i)]));
    if (busy.has(far) && !keepsLane(drawing, item.edge, far, points, options.laneReach)) continue;
    return points;
  }
  return null;
}

/**
 * The joins of `items` to the lane `main`: `[{ item, points }]`, those that fit.
 * The items of one group share the node, so no join stands in another's way.
 */
function joinsTo(drawing, node, items, main, context, options) {
  const levels = levelsOf(main, context, options);
  return items.map((item) => ({ item, points: joinOf(drawing, node, item, main, levels, context.busy, options) })).filter(({ points }) => points);
}

/**
 * A lane of the group's own, for edges each of whose lanes runs beside an edge
 * that has no end in common with the others: a column straight out of the node's
 * side, tried from the side's middle outwards, that every edge of `items` rides
 * past the reach and leaves at a level where it turns back to its own route.
 * `[{ item, points }]` for every item, or null when no column takes them all.
 */
function freshLaneOf(drawing, node, items, { reach, sign, busy }, options) {
  const box = drawing.boxes[node];
  const border = sign > 0 ? box.y2 : box.y1;
  const middle = (box.x1 + box.x2) / 2;
  const far = reach + sign * (options.joinTries * options.joinStep + options.joinStep);
  const levels = Array.from({ length: options.joinTries }, (_, step) => reach + sign * (step + 1) * options.joinStep);
  for (let k = 0; middle + k * options.joinStep < box.x2 - options.joinStep; k += 1) {
    for (const x of k ? [middle - k * options.joinStep, middle + k * options.joinStep] : [middle]) {
      const column = { route: [{ x, y: border }, { x, y: far }] };
      const joined = items.map((item) => ({ item, points: joinOf(drawing, node, item, column, levels, busy, options) }));
      if (joined.every(({ points }) => points)) return joined;
    }
  }
  return null;
}

/**
 * The joins of `lanes`, a group's lanes of one top-level box: `{ lane, joined }`,
 * the lane the others join and each join `{ item, points }`, its new route. The
 * lane most of the edges leave in is tried first; where an edge cannot join it,
 * the others are tried in turn, the larger first, and the one most edges join is
 * taken; where even that leaves an edge out, every edge rides a lane of the
 * group's own (`freshLaneOf`), when one is free.
 */
function joinsOf(drawing, node, lanes, context, options) {
  const ranked = [...lanes].sort((a, b) => b.length - a.length);
  let best = null;
  for (const lane of ranked) {
    const others = lanes.filter((other) => other !== lane).flat();
    const joined = joinsTo(drawing, node, others, lane[0], context, options);
    if (!best || joined.length > best.joined.length) best = { lane, joined };
    if (joined.length === others.length) return best;
  }
  const fresh = freshLaneOf(drawing, node, lanes.flat(), context, options);
  return fresh ? { lane: [], joined: fresh } : best;
}

/** `items` grouped by the lane they cross the level in, lanes a unit apart or closer as one: `[[item, …], …]`. */
function lanesOf(items) {
  const lanes = [];
  let last = -Infinity;
  for (const item of [...items].sort((a, b) => a.lane - b.lane)) {
    if (item.lane - last > ONE_LANE) lanes.push([]);
    lanes[lanes.length - 1].push(item);
    last = item.lane;
  }
  return lanes;
}

/**
 * The edges of `node` that leave the side at `border` and cross the level
 * `reach` beyond it, per top-level box other than the node's own they lead to:
 * a map from the box to `[{ edge, route, lane }]`.
 */
function edgesByBox(drawing, node, border, reach) {
  const own = drawing.topBox(node);
  const groups = new Map();
  for (const edge of drawing.edgesAt(node)) {
    const box = drawing.topBox(otherEnd(edge, node));
    if (box === own || !drawing.boxes[box]) continue;
    const points = drawing.routes.get(edge.id);
    if (!near(headFrom(edge, node, points, 1)[0].y, border)) continue;
    const route = fromNode(edge, node, points);
    const lane = laneAt(route, reach);
    if (lane === null) continue;
    if (!groups.has(box)) groups.set(box, []);
    groups.get(box).push({ edge, route, lane });
  }
  return groups;
}

/** The direction edges take from `node`: "out", "in", or "both". */
function directionOf(edges, node) {
  const directions = new Set(edges.map((edge) => (edge.source === node ? "out" : "in")));
  return directions.size === 1 ? [...directions][0] : "both";
}

/**
 * The joins at `node`: on each side, per top-level box its edges there lead to,
 * the edges in lanes of their own joined to the lane most of them leave in. Each
 * is `{ node, box, direction, side, members }`, `members` the lane's edges and
 * the ones joined to it, `direction` "both" when they lead both ways.
 */
export function joinsAt(drawing, node, busy, options) {
  const joins = [];
  const box = drawing.boxes[node];
  for (const { side, sign } of SIDES) {
    const border = sign > 0 ? box.y2 : box.y1;
    const reach = border + sign * options.laneReach;
    for (const [target, items] of edgesByBox(drawing, node, border, reach)) {
      const lanes = lanesOf(items);
      if (lanes.length < 2) continue;
      const { lane, joined } = joinsOf(drawing, node, lanes, { reach, sign, busy }, options);
      if (!joined.length) continue;
      for (const { item, points } of joined) drawing.setRoute(item.edge, points);
      const edges = [...lane, ...joined.map(({ item }) => item)].map(({ edge }) => edge);
      const members = edges.map((edge) => edge.id);
      joins.push({ node, box: target, direction: directionOf(edges, node), side, members });
    }
  }
  return joins;
}
