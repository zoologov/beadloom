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
//   now, one gives way, its line ending beside the other's head, behind its base.
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
import { segmentRect } from "../lib/spatialIndex.js";
import { setClass } from "./canvasMarks.js";

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
/**
 * How far around an end's last run its search for room reads, in layout units:
 * the reach beside it, the run past its tip, and the half unit a point on a
 * route may lie off it (`lib/routeIndex.js`), with a unit to spare.
 */
const SEARCH_REACH = Math.max(BESIDE_REACH, PAST_TIP) + 1;

const samePoint = (p, q) => p.x === q.x && p.y === q.y;

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
  // The routed lines drawn, by what names each (`keyOf`), and each end's search among them (`searchOf`).
  let routesNow = new Map();
  let searches = new Map();

  /** What names a drawn line's route: its id, and for a line of the map, which can be routed again, the route. */
  const keyOf = (edge) => (edge.data(AGGREGATE) ? `${edge.id()} ${JSON.stringify(edge.data("route"))}` : edge.id());

  /**
   * Keep the searches of the ends no line that came or went since can change:
   * an end's search reads only what lies within its run and a reach around it.
   */
  function keepSearches(before, after) {
    const changed = [...before].filter(([key]) => !after.has(key)).concat([...after].filter(([key]) => !before.has(key)));
    const segments = changed.flatMap(([, points]) => points.slice(1).map((b, i) => segmentRect(points[i], b)));
    const untouched = (region) => !segments.some((r) => r.x1 <= region.x2 && region.x1 <= r.x2 && r.y1 <= region.y2 && region.y1 <= r.y2);
    searches = new Map([...searches].filter(([, search]) => untouched(search.region)));
  }

  /**
   * How much room `end` has and what lies beside its head, among the lines drawn
   * now: `{ corner, beside, arrival, besideId }`, searched again only when its
   * last run, or a line within its reach, changed since it was last searched.
   */
  function searchOf(end) {
    const key = `${end.id}\n${end.end}`;
    const from = towards(end.tip, end.before, end.corner);
    const kept = searches.get(key);
    if (kept && samePoint(kept.tip, end.tip) && samePoint(kept.from, from)) return kept.found;
    const corner = Math.min(end.corner, lines.nearestCrossing(end.tip, from, SAME_END));
    const zone = towards(end.tip, end.before, Math.min(corner, HEAD_ZONE));
    const found = { corner, ...lines.nearestBeside(end.tip, zone, BESIDE_REACH, SAME_END, PAST_TIP, end.id) };
    searches.set(key, { tip: end.tip, from, found, region: segmentRect(end.tip, from, SEARCH_REACH) });
    return found;
  }

  function refresh() {
    const drawn = cy.edges().filter((edge) => edge.visible());
    const routed = drawn.filter((edge) => paths[edge.id()]);
    // The map's own lines can be routed again, or drawn to another end, with the same ids drawn.
    const withRoutes = drawn.filter((edge) => edge.data("route"));
    const keys = withRoutes.map(keyOf);
    const ids = keys.join("\n");
    if (ids !== drawnIds) {
      drawnIds = ids;
      index = routeIndexOf(routed.map((edge) => ({ id: edge.id(), points: paths[edge.id()] })));
      // Every routed line drawn, the map's own among them, for the room around a head.
      const now = new Map(withRoutes.map((edge, i) => [keys[i], routePointsOf(edge)]));
      lines = routeIndexOf(withRoutes.map((edge, i) => ({ id: edge.id(), points: now.get(keys[i]) })));
      keepSearches(routesNow, now);
      routesNow = now;
    }
    const ends = withRoutes.flatMap(endsOf).map((end) => ({ ...end, ...searchOf(end) }));
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
    const crowded = crowdedHeadsOf(ends, dropped, LINE_MARKS.smallestHead * s, LINE_MARKS.headClearance * s);
    for (const key of crowded.keys()) dropped.add(key);
    // A head on another line's way, where that line runs on through the tip, would sit across it: the line ends there without one.
    for (const end of ends) {
      if (end.headless || dropped.has(`${end.id}\n${end.end}`)) continue;
      if (lines.runningOn(end.tip, end.before).some((id) => id !== end.id)) dropped.add(`${end.id}\n${end.end}`);
    }
    // A headless end has a room only where a head is drawn at its tip.
    const rooms = headRoomsOf(ends.filter((end) => !end.headless || dropped.has(`${end.id}\n${end.end}`)));
    // It starts behind that head's base: it takes the head's room, which sizes the head, and keeps clear of it.
    // So does a line whose head gave way to one beside it: it ends beside that head, behind its base.
    for (const [key, head] of [...aside, ...crowded]) if (rooms.has(head)) rooms.set(key, { ...rooms.get(head), aside: true });
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        const id = edge.id();
        const room = { source: rooms.get(`${id}\nsource`) ?? null, target: rooms.get(`${id}\ntarget`) ?? null };
        if (!sameRoom(edge.data(HEAD_ROOM), room)) edge.data(HEAD_ROOM, room);
        setClass(edge, NO_TARGET_HEAD, dropped.has(`${id}\ntarget`));
        setClass(edge, NO_SOURCE_HEAD, dropped.has(`${id}\nsource`));
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
