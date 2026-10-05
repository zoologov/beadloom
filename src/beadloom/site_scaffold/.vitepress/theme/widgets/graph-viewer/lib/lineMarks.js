// beadloom:component=site-graph-viewer
// A line's marks and the size each keeps on screen: its weight, its dash, its arrowhead and its corners.
//
// Every line is drawn at one thin weight, at every zoom, whatever its kind, its
// count or its state: a line as wide as its count fuses with its neighbours into
// a slab, and its arrowhead, which Cytoscape grows with the width, breaks over the
// bend before its end. A count is said in words instead. Its arrowheads are
// drawn at one length and its corners at one radius. Each carries the map's
// scale in its data (`mapMarks.js`, `scaleOf`), so a size in pixels multiplied by
// it is about that many pixels on screen.
//
// Cytoscape sizes an arrowhead from the line's width: `max((13.37 w)^0.9, 29)`
// units across, times `arrow-scale`, of which a triangle or a vee takes 0.3 along
// the line. `arrowScaleOf` inverts that, so a head is `LINE_MARKS.head` long on
// screen whatever the width.
//
// A head needs a straight run to sit on: where the corner before an end is
// rounded into the run the head stands on, the head bends with it. So the corner
// before an end with a head is rounded only by what its run has to spare beyond
// the head, and is square when it has none (`cornerRadiiOf`); Cytoscape keeps
// every rounding within half of each run it joins. Every other corner is rounded
// at `LINE_MARKS.corner`, so a branch leaves its trunk in a rounded merge.
//
// Every function here is pure: an element's data or a route in, a size out.

import { headEndsOf } from "./heads.js";
import { scaleOf } from "./mapMarks.js";
import { pathOfSegments } from "./routes.js";

/**
 * What a line's marks measure on screen, in pixels: its width, its arrowhead's
 * length, the radius of its corners, and the casing a followed line is drawn
 * over on each side.
 */
export const LINE_MARKS = Object.freeze({
  width: 1.35,
  head: 6,
  corner: 6,
  casing: 2,
});

/** How much of Cytoscape's arrow size a triangle or a vee takes along its line. */
const ARROW_LENGTH_SHARE = 0.3;
/** Cytoscape's arrow size: `max((width * FACTOR)^EXPONENT, FLOOR)` at an `arrow-scale` of 1. */
const ARROW_SIZE = Object.freeze({ factor: 13.37, exponent: 0.9, floor: 29 });

/** A line's width, in layout units. */
export const lineWidthOf = (edge) => LINE_MARKS.width * scaleOf(edge);

/** An arrowhead's length, in layout units. */
export const headLengthOf = (edge) => LINE_MARKS.head * scaleOf(edge);

/** The `arrow-scale` that draws `edge`'s arrowheads `LINE_MARKS.head` long on screen. */
export function arrowScaleOf(edge) {
  const size = Math.max((lineWidthOf(edge) * ARROW_SIZE.factor) ** ARROW_SIZE.exponent, ARROW_SIZE.floor);
  return headLengthOf(edge) / (ARROW_LENGTH_SHARE * size);
}

/** A dash pattern given in pixels on screen, in layout units for `edge`. */
export const dashOnScreen = (pattern, edge) => pattern.map((length) => length * scaleOf(edge));

const distance = (p, q) => Math.hypot(q.x - p.x, q.y - p.y);

/**
 * The radius of each corner of `points` (a route's ends and corners), in layout
 * units, at `scale`: `LINE_MARKS.corner`, except that the corner before an end
 * `heads` names (`{ source, target }`) keeps the head's length of its run straight.
 */
export function cornerRadiiOf(points, scale, heads) {
  const corners = points.length - 2;
  if (corners < 1) return [];
  const radii = new Array(corners).fill(LINE_MARKS.corner * scale);
  const head = LINE_MARKS.head * scale;
  const spare = (a, b) => Math.max(0, distance(a, b) - head);
  const n = points.length;
  if (heads.target) radii[corners - 1] = Math.min(radii[corners - 1], spare(points[n - 2], points[n - 1]));
  if (heads.source) radii[0] = Math.min(radii[0], spare(points[0], points[1]));
  return radii;
}

/** The route `edge` is drawn along, in the graph's coordinates: its ends and every corner. */
export function routePointsOf(edge) {
  return pathOfSegments(edge.data("route"), edge.source().position(), edge.target().position());
}

/** The radius of each corner of the routed `edge`, in layout units. */
export const edgeCornerRadiiOf = (edge) => cornerRadiiOf(routePointsOf(edge), scaleOf(edge), headEndsOf(edge));
