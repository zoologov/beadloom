// beadloom:component=site-graph-viewer
// Where drawn routes branch, and which routes run through a point: read from the routes alone.
//
// A trunk or a bus draws several edges along one line, and a reader can only
// tell where one of them leaves the others if the place is marked. A junction is
// a point where two routes that run together part: they share a direction out of
// the point and differ in another. Two routes that merely cross share no
// direction there, and two that run on together share all of theirs, so neither
// is a junction. Only the routes given are read, so a junction is found for the
// edges drawn now: one whose second branch a filter hid is no junction.
//
// Every function here is pure: routes in, points out.

import { lineIndex } from "./spatialIndex.js";

/** How close a point must lie to a route to be on it, in layout units. */
const ON_ROUTE = 0.5;
/** Steps of `ON_ROUTE` a point key reserves for its second coordinate, so a point's key is one number. */
const KEY_SPAN = 1 << 24;
/** The width of a band of the index over the routes' segments. */
const BAND_WIDTH = 2;

/** The four directions a route can leave a point in, one bit each, so a set of them is a number. */
const EAST = 1;
const WEST = 2;
const SOUTH = 4;
const NORTH = 8;

/** The direction from `from` towards `to` along an axis-aligned segment, or 0 when they meet. */
function directionTowards(from, to) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) < ON_ROUTE && Math.abs(dy) < ON_ROUTE) return 0;
  if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? EAST : WEST;
  return dy > 0 ? SOUTH : NORTH;
}

/** The point of the segment from `a` to `b` nearest to `point`. */
function nearestOnSegment(point, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length2 = dx * dx + dy * dy;
  const t = length2 ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length2)) : 0;
  return { x: a.x + t * dx, y: a.y + t * dy };
}

const distance = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

/**
 * An index over `routes` (`[{ id, points }]`): `{ throughPoint(point) }`, the
 * routes that pass through `point`, each with the directions it leaves it in.
 * A routed edge is orthogonal; a segment that is neither horizontal nor vertical
 * is not indexed.
 */
export function routeIndexOf(routes) {
  const index = lineIndex(BAND_WIDTH);
  for (const route of routes) {
    const { points } = route;
    for (let i = 1; i < points.length; i += 1) index.insert(route, points[i - 1], points[i]);
  }
  return {
    /**
     * `[{ id, directions }]`: each route through `point`, with the directions it
     * leaves it in as bits (east 1, west 2, south 4, north 8).
     */
    throughPoint(point) {
      const found = [];
      const visit = (route, a, b) => {
        if (distance(point, nearestOnSegment(point, a, b)) > ON_ROUTE) return;
        const directions = directionTowards(point, a) | directionTowards(point, b);
        const known = found.find((entry) => entry.id === route.id);
        if (known) known.directions |= directions;
        else found.push({ id: route.id, directions });
      };
      index.along("horizontal", point.y, ON_ROUTE, point.x - ON_ROUTE, point.x + ON_ROUTE, visit);
      index.along("vertical", point.x, ON_ROUTE, point.y - ON_ROUTE, point.y + ON_ROUTE, visit);
      return found;
    },
  };
}


/**
 * The edges that branch at `point` among `through` (`routeIndexOf`'s answer):
 * every route that shares a direction with another route there and differs from
 * it in another. Empty when nothing branches.
 */
function branchingAt(through) {
  if (through.length < 2) return [];
  const branching = new Set();
  for (let i = 0; i < through.length; i += 1) {
    for (let j = i + 1; j < through.length; j += 1) {
      const a = through[i].directions;
      const b = through[j].directions;
      if ((a & b) !== 0 && a !== b) {
        branching.add(through[i].id);
        branching.add(through[j].id);
      }
    }
  }
  return [...branching].sort();
}

/**
 * The junctions of `routes` (`[{ id, points }]`): `[{ x, y, edges }]`, every
 * point where routes that run together part, with the ids of the routes that
 * branch there. A route branches only at a corner of one of them, so only
 * corners are read.
 */
export function junctionsOf(routes) {
  const index = routeIndexOf(routes);
  const seen = new Set();
  const junctions = [];
  for (const { points } of routes) {
    for (let i = 1; i < points.length - 1; i += 1) {
      const point = points[i];
      const key = Math.round(point.x / ON_ROUTE) * KEY_SPAN + Math.round(point.y / ON_ROUTE);
      if (seen.has(key)) continue;
      seen.add(key);
      const edges = branchingAt(index.throughPoint(point));
      if (edges.length) junctions.push({ x: point.x, y: point.y, edges });
    }
  }
  return junctions;
}

/**
 * The routes of `routes` drawn along `route` at `point`: every route that passes
 * through the point of `route` nearest to `point` and leaves it in a direction
 * `route` leaves it in. `route` itself is among them.
 */
export function routesAlong(index, route, point) {
  let nearest = null;
  for (let i = 1; i < route.points.length; i += 1) {
    const on = nearestOnSegment(point, route.points[i - 1], route.points[i]);
    if (!nearest || distance(point, on) < distance(point, nearest)) nearest = on;
  }
  if (!nearest) return [route.id];
  const through = index.throughPoint(nearest);
  const own = through.find((entry) => entry.id === route.id);
  if (!own) return [route.id];
  return through
    .filter((entry) => entry.id === route.id || (entry.directions & own.directions) !== 0)
    .map((entry) => entry.id)
    .sort();
}
