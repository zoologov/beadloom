// beadloom:component=site-graph-edge
// A line's marks and the size each keeps on screen: its weight, its dash, its arrowhead and its corners.
//
// Every line is drawn at one thin weight, at every zoom, whatever its kind, its
// count or its state: a line as wide as its count fuses with its neighbours into
// a slab, and its arrowhead, which Cytoscape grows with the width, breaks over the
// bend before its end. A count is said in words instead. Its arrowheads are
// drawn at one length and its corners at one radius. Each carries the map's
// scale in its data (`shared/map-levels/mapMarks.js`, `scaleOf`), so a size in pixels multiplied by
// it is about that many pixels on screen.
//
// Cytoscape sizes an arrowhead from the line's width: `max((13.37 w)^0.9, 29)`
// units across, times `arrow-scale`, of which a triangle or a vee takes 0.3 along
// the line. `arrowScaleOf` inverts that, so a head is the length asked for on
// screen whatever the width.
//
// A head stands on a straight line of its own: its length and half a head more
// behind its tip (`LINE_MARKS.stem`), over every line that ends there, or the
// line reads as bent into the head. That run is the room an end has along its
// line (`HEAD_ROOM`, `lib/heads.js`): from its tip to the nearest corner of the
// lines that end there, or to a line that crosses them. Its room across is the
// nearest line beside its run: a head keeps clear of a line beside it, and of the
// head of a line that arrives beside it, which is sized the same way. A head is
// `LINE_MARKS.head` long where its room holds it, and shorter where it does not,
// down to `LINE_MARKS.smallestHead` (`headLengthAt`); the routes give it the room
// where nothing is in the way (`shared/bundling/headRuns.js`).
//
// The corner before an end with a head is rounded only by what its run has to
// spare beyond the head and its stem, and is square when it has none
// (`cornerRadiiOf`); Cytoscape keeps every rounding within half of each run it
// joins. Every other corner is rounded at `LINE_MARKS.corner`, so a branch
// leaves its trunk in a rounded merge.
//
// A dashed or dotted line starts its pattern at its source, so it would reach
// its head wherever the pattern happens to be: in a gap short of the head, or in
// a dash on into a vee's tip. Its pattern is shifted (`dashOffsetOf`) so that a
// dash ends inside the head, where the head is wider than the line, and the gap
// after it covers the rest of the line under the head.
//
// Every function here is pure: an element's data or a route in, a size out.

import { HEAD_ROOM, NO_SOURCE_HEAD, NO_TARGET_HEAD, headEndsOf } from "./heads.js";
import { scaleOf } from "../../../shared/map-levels/index.js";
import { pathOfSegments } from "../../../shared/geometry/index.js";

/**
 * What a line's marks measure on screen, in pixels: its width; its arrowhead's
 * length, and the smallest length it is drawn at where its run has no room for
 * more; the straight line a head keeps behind it, as a share of the head; the
 * radius of its corners; and the casing a followed line is drawn over on each side.
 */
export const LINE_MARKS = Object.freeze({
  width: 1.35,
  head: 6,
  smallestHead: 3,
  stem: 0.5,
  corner: 6,
  casing: 2,
  /** How far a head keeps from a line beside it, beyond half that line's width, and from a head beside it. */
  headClearance: 0.5,
});

const distance = (p, q) => Math.hypot(q.x - p.x, q.y - p.y);

/** How much of Cytoscape's arrow size a triangle or a vee takes along its line. */
const ARROW_LENGTH_SHARE = 0.3;
/** Cytoscape's arrow size: `max((width * FACTOR)^EXPONENT, FLOOR)` at an `arrow-scale` of 1. */
const ARROW_SIZE = Object.freeze({ factor: 13.37, exponent: 0.9, floor: 29 });

/** A line's width, in layout units. */
export const lineWidthOf = (edge) => LINE_MARKS.width * scaleOf(edge);

/**
 * The length of an arrowhead at `scale` in `room`, in layout units:
 * `LINE_MARKS.head` on screen where the room holds it, less where it does not,
 * never less than `LINE_MARKS.smallestHead`. `room` is `{ run, beside, arrival }`
 * (`HEAD_ROOM`): the straight run behind the tip; how far the nearest line beside
 * that run lies from it, Infinity for none; and whether that line arrives there
 * with a head of its own. A room not known (null) holds the full head.
 */
export function headLengthAt(scale, room) {
  const full = LINE_MARKS.head * scale;
  if (!room) return full;
  const clearance = LINE_MARKS.headClearance * scale;
  const run = room.run ?? Infinity;
  const beside = room.beside ?? Infinity;
  const across = room.arrival ? beside - clearance : 2 * (beside - (LINE_MARKS.width / 2) * scale - clearance);
  const fits = Math.min(full, run / (1 + LINE_MARKS.stem), across);
  return Math.max(LINE_MARKS.smallestHead * scale, fits);
}

/**
 * The length of `edge`'s arrowheads, in layout units: one length for both of its
 * ends, since Cytoscape draws both at one `arrow-scale`, the shorter where the
 * two ends' rooms differ. An end that leaves its head to another line is sized
 * all the same: its line ends at that head's base (`widgets/graph-viewer/lib/stylesheet.js`).
 */
export function headLengthOf(edge) {
  const scale = scaleOf(edge);
  const room = edge.data(HEAD_ROOM) || {};
  const heads = headEndsOf(edge);
  const lengths = ["source", "target"].filter((end) => heads[end]).map((end) => headLengthAt(scale, room[end] ?? null));
  return lengths.length ? Math.min(...lengths) : headLengthAt(scale, null);
}

/** The class of a line whose `end` leaves the head drawn there to another line. */
const DROPPED = Object.freeze({ source: NO_SOURCE_HEAD, target: NO_TARGET_HEAD });

/**
 * How long the head at `edge`'s `end` is, in layout units: its own where it draws
 * one, and where it leaves the head to another line, that head, sized by the room
 * they share; the line ends at its base there (`widgets/graph-viewer/lib/stylesheet.js`), and a line's
 * width and a clearance further back where it leaves beside the head (`aside`).
 */
export function endHeadLength(edge, end) {
  if (headEndsOf(edge)[end] && !edge.hasClass(DROPPED[end])) return headLengthOf(edge);
  const room = (edge.data(HEAD_ROOM) || {})[end] ?? null;
  const head = headLengthAt(scaleOf(edge), room);
  if (!room?.aside) return head;
  // A line that leaves beside the head rather than behind it keeps a line's width and a clearance past its base,
  // within its own first run, which the head's room is no longer than.
  return Math.min(head + (LINE_MARKS.width + LINE_MARKS.headClearance) * scaleOf(edge), Math.max(head, room.run ?? Infinity));
}

/** The `arrow-scale` that draws `edge`'s arrowheads `headLengthOf` long. */
export function arrowScaleOf(edge) {
  const size = Math.max((lineWidthOf(edge) * ARROW_SIZE.factor) ** ARROW_SIZE.exponent, ARROW_SIZE.floor);
  return headLengthOf(edge) / (ARROW_LENGTH_SHARE * size);
}

/** A dash pattern given in pixels on screen, in layout units for `edge`. */
export const dashOnScreen = (pattern, edge) => pattern.map((length) => length * scaleOf(edge));

/** How far behind its tip a dash ends inside a head, as a share of the head: a vee is solid only in front of its notch, halfway back. */
const DASH_INSIDE = Object.freeze({ triangle: 0.6, vee: 0.4 });
/** How much of the gap Cytoscape leaves between a line and its head a vee leaves, against a triangle's. */
const VEE_GAP_SHARE = 0.525;

/** How far short of its tip Cytoscape ends the line of the routed `edge` at its target, in layout units. */
function targetPullback(edge, shape) {
  if (edge.hasClass(NO_TARGET_HEAD)) return endHeadLength(edge, "target");
  const gap = 2 * lineWidthOf(edge) * arrowScaleOf(edge);
  return shape === "vee" ? VEE_GAP_SHARE * gap : gap;
}

/**
 * The length of a route of `points` drawn with corners of `radii`, its end
 * pulled back by `pullback` and its start by `lead`: a right-angled corner takes
 * its rounding off both runs, as drawn, and adds its arc; a point on a straight
 * run is no corner.
 */
function strokeLength(points, radii, pullback, lead = 0) {
  const n = points.length;
  const runs = points.slice(1).map((point, i) => distance(points[i], point));
  runs[n - 2] = Math.max(0, runs[n - 2] - pullback);
  runs[0] = Math.max(0, runs[0] - lead);
  let length = runs.reduce((sum, run) => sum + run, 0);
  for (let i = 1; i < n - 1; i += 1) {
    const [a, b, c] = [points[i - 1], points[i], points[i + 1]];
    const turns = Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-6 * (runs[i - 1] * runs[i] || 1);
    if (!turns) continue;
    const take = Math.min(radii[i - 1] || 0, runs[i - 1] / 2, runs[i] / 2);
    length -= (2 - Math.PI / 2) * take;
  }
  return length;
}

/**
 * The `line-dash-offset` that ends a dash of `pattern` (layout units) inside the
 * head at the target of the routed `edge`, drawn with `shape`; for a line that
 * leaves its head to another, at its own end, the head's base. 0 for a solid line.
 * `ownHead` draws the line with its own head whatever it leaves to another, and
 * ends it `ownHead.pullback` short of its tip, as the followed lines are drawn.
 */
export function dashOffsetOf(edge, pattern, shape, ownHead = null) {
  if (!pattern.length || !edge.data("route")) return 0;
  const points = routePointsOf(edge);
  const pullback = ownHead ? ownHead.pullback : targetPullback(edge, shape);
  const dropped = !ownHead && edge.hasClass(NO_TARGET_HEAD);
  const inside = dropped ? pullback : (DASH_INSIDE[shape] ?? DASH_INSIDE.triangle) * headLengthOf(edge);
  // The pattern starts where the line is drawn from: past the base of a head it leaves its source to.
  const lead = edge.hasClass(NO_SOURCE_HEAD) ? endHeadLength(edge, "source") : 0;
  const anchor = strokeLength(points, edgeCornerRadiiOf(edge), pullback, lead) - Math.max(0, inside - pullback);
  const period = pattern.reduce((sum, length) => sum + length, 0);
  return (((pattern[0] - anchor) % period) + period) % period;
}

/**
 * The radius of each corner of `points` (a route's ends and corners), in layout
 * units, at `scale`: `LINE_MARKS.corner`, except that the corner before an end
 * `heads` names (`{ source, target }`) keeps a head `head` long (one length, or
 * one per end) and its stem straight on its run.
 */
export function cornerRadiiOf(points, scale, heads, head = LINE_MARKS.head * scale) {
  const corners = points.length - 2;
  if (corners < 1) return [];
  const radii = new Array(corners).fill(LINE_MARKS.corner * scale);
  const kept = (end) => (typeof head === "number" ? head : head[end]) * (1 + LINE_MARKS.stem);
  const spare = (a, b, end) => Math.max(0, distance(a, b) - kept(end));
  const n = points.length;
  if (heads.target) radii[corners - 1] = Math.min(radii[corners - 1], spare(points[n - 2], points[n - 1], "target"));
  if (heads.source) radii[0] = Math.min(radii[0], spare(points[0], points[1], "source"));
  return radii;
}

/** The route `edge` is drawn along, in the graph's coordinates: its ends and every corner. */
export function routePointsOf(edge) {
  return pathOfSegments(edge.data("route"), edge.source().position(), edge.target().position());
}

/**
 * The radius of each corner of the routed `edge`, in layout units: an end that
 * leaves a head to another line keeps that head's run straight as well.
 */
export function edgeCornerRadiiOf(edge) {
  const own = headEndsOf(edge);
  const heads = { source: own.source || edge.hasClass(NO_SOURCE_HEAD), target: own.target || edge.hasClass(NO_TARGET_HEAD) };
  const lengths = { source: endHeadLength(edge, "source"), target: endHeadLength(edge, "target") };
  return cornerRadiiOf(routePointsOf(edge), scaleOf(edge), heads, lengths);
}
