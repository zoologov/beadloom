// beadloom:component=site-graph-viewer
// The lines drawn now that share a run: the edges along a hovered line, one arrowhead where lines share their last run, and the room it has.
//
// A trunk or a bus draws several edges along one line. Cytoscape draws each of
// them whole, so two things a reader needs are not in its drawing:
//
// - **The edges along a hovered line**: Cytoscape reports the one edge under the
//   pointer, which on a trunk is whichever member it drew last. Every drawn edge
//   that runs through the hovered point along the same line is the answer
//   instead (`lib/routeIndex.js`, `routesAlong`).
// - **One arrowhead per shared last run**: lines that reach one end along one run
//   would each draw a head there, on top of each other. Every line but one drops
//   its head, by a class the stylesheet reads (`lib/heads.js`), and ends at the
//   base of the head that stays; a line that reaches the end on its own keeps its own.
//   A line that leaves its node beside where another's head arrives, close
//   enough to run along the head's side, starts at that head's base too; and of
//   two heads side by side on one border, too near for both at the scale drawn
//   now, one gives way, its line ending at the other's base.
//   A line whose end lies on another line's way, which runs on through it — a
//   node's own line into an open box, on the border its lines into the box's
//   nodes cross — has no head there either: the head would sit across the line
//   running on, and the lines that run on carry the direction.
// - **The room a head has**: the straight run behind its tip that every line
//   ending there has before its last corner, or before another line crosses it
//   (`headRoomsOf`, `routeIndex.js`), which the head is sized to
//   (`lib/lineMarks.js`), kept in each line's data (`HEAD_ROOM`).
//
// All three are found for the routed lines drawn now, aggregated edges of the
// map included: a filter, a hidden neighbourhood or a level that removes a line
// gives its arrowhead, and its room, back to the line that remains. A loop keeps
// its own head: loops into one box run their last piece through the same
// control points, so their heads are drawn on one another and read as one,
// while a loop ended short of its tip would bend away from the head it left.

import {
  HEAD_ROOM,
  NO_SOURCE_HEAD,
  NO_TARGET_HEAD,
  SAME_END,
  crowdedHeadsOf,
  departuresBeside,
  droppedHeadsOf,
  headEndsOf,
  headRoomsOf,
} from "../lib/heads.js";
import { AGGREGATE } from "../lib/levels.js";
import { LINE_MARKS, routePointsOf } from "../lib/lineMarks.js";
import { routeIndexOf, routesAlong } from "../lib/routeIndex.js";

/**
 * Where a line beside a head's run is looked for, in layout units: up to
 * `HEAD_ZONE` back from its tip and `PAST_TIP` past it, and up to `BESIDE_REACH`
 * out from the run. A head is as long as `LINE_MARKS.head` times the map's scale,
 * which the lines are not read again at; these hold a head at the scales routed
 * lines are drawn at, and a line beside a head that small keeps clear of it anyway.
 */
const HEAD_ZONE = 60;
const PAST_TIP = 30;
const BESIDE_REACH = 40;

/** Two directions closer than this cross product apart are one: a point between them is no corner. */
const STRAIGHT_ON = 1e-6;

/** The point `length` from `from` towards `to`. */
function towards(from, to, length) {
  const whole = Math.hypot(to.x - from.x, to.y - from.y) || 1;
  return { x: from.x + ((to.x - from.x) * length) / whole, y: from.y + ((to.y - from.y) * length) / whole };
}

/**
 * How far from the start of `points` its first corner lies, in layout units, a
 * point on a straight run between two others not counted: Cytoscape needs a
 * corner on a line that has none, and is given one at its middle.
 */
function firstCornerAlong(points) {
  const [tip, next] = points;
  const length = Math.hypot(next.x - tip.x, next.y - tip.y) || 1;
  const way = { x: (next.x - tip.x) / length, y: (next.y - tip.y) / length };
  for (let i = 1; i < points.length - 1; i += 1) {
    const out = { x: points[i + 1].x - points[i].x, y: points[i + 1].y - points[i].y };
    const outLength = Math.hypot(out.x, out.y) || 1;
    if (Math.abs(way.x * out.y - way.y * out.x) / outLength > STRAIGHT_ON || way.x * out.x + way.y * out.y < 0) {
      return Math.hypot(points[i].x - tip.x, points[i].y - tip.y);
    }
  }
  const last = points[points.length - 1];
  return Math.hypot(last.x - tip.x, last.y - tip.y);
}

/**
 * Both ends of the routed `edge`, each with where it ends, where its last run
 * starts, how far its last corner lies, and whether it draws no head of its own
 * (`headless`): such an end matters only where another line's head is drawn.
 */
function endsOf(edge) {
  const points = routePointsOf(edge);
  const n = points.length;
  const heads = headEndsOf(edge);
  const styleKey = edge.data("styleKey");
  const mapLine = Boolean(edge.data(AGGREGATE));
  return [
    { id: edge.id(), end: "target", tip: points[n - 1], before: points[n - 2], corner: firstCornerAlong([...points].reverse()), styleKey, mapLine, headless: !heads.target },
    { id: edge.id(), end: "source", tip: points[0], before: points[1], corner: firstCornerAlong(points), styleKey, mapLine, headless: !heads.source },
  ];
}

/** Whether two rooms (`HEAD_ROOM`) are the same. */
const sameRoom = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

/**
 * The shared lines of `cy` for the routes in `paths` (edge id to its drawn
 * polyline): `{ refresh, along, droppedHeads }`.
 *
 * `refresh()` reads the lines drawn now again and gives each shared last run
 * one arrowhead; call it whenever a filter, a selection or a level changes what
 * is drawn, and whenever `scale()`, the map's scale, does: two heads side by side
 * on one border fit at one scale and not at another. `along(id, point)` gives the ids of the drawn edges that run along
 * edge `id` at `point`, in graph coordinates. `droppedHeads()` gives the ends that
 * draw no head, `[{ id, end }]`.
 */
export function sharedLines(cy, paths, { scale = () => 1 } = {}) {
  let drawnIds = "";
  let index = routeIndexOf([]);
  let lines = routeIndexOf([]);
  let dropped = new Set();

  function refresh() {
    const drawn = cy.edges().filter((edge) => edge.visible());
    const routed = drawn.filter((edge) => paths[edge.id()]);
    // The map's own lines can be routed again, or drawn to another end, with the same ids drawn.
    const ids = drawn
      .filter((edge) => edge.data("route"))
      .map((edge) => (edge.data(AGGREGATE) ? `${edge.id()} ${JSON.stringify(edge.data("route"))}` : edge.id()))
      .join("\n");
    if (ids !== drawnIds) {
      drawnIds = ids;
      index = routeIndexOf(routed.map((edge) => ({ id: edge.id(), points: paths[edge.id()] })));
      // Every routed line drawn, the map's own among them, for the room around a head.
      lines = routeIndexOf(drawn.filter((edge) => edge.data("route")).map((edge) => ({ id: edge.id(), points: routePointsOf(edge) })));
    }
    const ends = drawn
      .filter((edge) => edge.data("route"))
      .flatMap(endsOf)
      .map((end) => {
        const corner = Math.min(end.corner, lines.nearestCrossing(end.tip, towards(end.tip, end.before, end.corner), SAME_END));
        const zone = towards(end.tip, end.before, Math.min(corner, HEAD_ZONE));
        return { ...end, corner, ...lines.nearestBeside(end.tip, zone, BESIDE_REACH, SAME_END, PAST_TIP, end.id) };
      });
    dropped = droppedHeadsOf(ends);
    // A line that leaves its node beside where a head arrives starts at that head's base, clear of its side.
    const aside = departuresBeside(ends, dropped);
    for (const key of aside.keys()) dropped.add(key);
    // Such a line, started behind the head's base, is no longer beside the head: the head has the room across
    // it, and as much of its own run as that line's first run is straight, so it can start behind it.
    const leftAside = new Set([...aside.keys()].map((key) => key.slice(0, key.lastIndexOf("\n"))));
    const byKey = new Map(ends.map((end) => [`${end.id}\n${end.end}`, end]));
    for (const end of ends) if (end.besideId && leftAside.has(end.besideId)) Object.assign(end, { beside: Infinity, arrival: false });
    for (const [key, head] of aside) {
      const [departure, arrival] = [byKey.get(key), byKey.get(head)];
      if (departure && arrival) arrival.corner = Math.min(arrival.corner, departure.corner);
    }
    // Heads side by side on one border, too near for two at the scale drawn now: one gives way.
    const s = scale();
    for (const key of crowdedHeadsOf(ends, dropped, LINE_MARKS.smallestHead * s, LINE_MARKS.headClearance * s)) dropped.add(key);
    // A head on another line's way, where that line runs on through the tip, would sit across it: the line ends there without one.
    for (const end of ends) {
      if (end.headless || dropped.has(`${end.id}\n${end.end}`)) continue;
      if (lines.runningOn(end.tip, end.before).some((id) => id !== end.id)) dropped.add(`${end.id}\n${end.end}`);
    }
    // A headless end has a room only where a head is drawn at its tip.
    const rooms = headRoomsOf(ends.filter((end) => !end.headless || dropped.has(`${end.id}\n${end.end}`)));
    // It starts behind that head's base: it takes the head's room, which sizes the head, and keeps clear of it.
    for (const [key, head] of aside) if (rooms.has(head)) rooms.set(key, { ...rooms.get(head), aside: true });
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        const id = edge.id();
        const room = { source: rooms.get(`${id}\nsource`) ?? null, target: rooms.get(`${id}\ntarget`) ?? null };
        if (!sameRoom(edge.data(HEAD_ROOM), room)) edge.data(HEAD_ROOM, room);
        edge.toggleClass(NO_TARGET_HEAD, dropped.has(`${id}\ntarget`));
        edge.toggleClass(NO_SOURCE_HEAD, dropped.has(`${id}\nsource`));
      });
    });
  }

  function along(id, point) {
    const points = paths[id];
    return points ? routesAlong(index, { id, points }, point) : [id];
  }

  return {
    refresh,
    along,
    droppedHeads: () =>
      [...dropped].map((key) => {
        const cut = key.lastIndexOf("\n");
        return { id: key.slice(0, cut), end: key.slice(cut + 1) };
      }),
  };
}
