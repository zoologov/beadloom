// beadloom:component=site-graph-viewer
// Where a highlighted edge crosses another drawn edge: the places a bridge is drawn.
//
// A reader following one line through a busy area loses it where it crosses
// others. A classic diagram draws a small hop there, a bridge, on the line being
// followed. Here the lines being followed are the highlighted ones (a hover, a
// neighbourhood, an impact walk), and only they carry bridges: on every crossing
// the graph would be texture.
//
// A crossing is a point where a horizontal run of one route and a vertical run
// of another pass through each other, each at least `INSIDE` from its ends. So
// none of these is a crossing:
//
// - two routes that run along one line, as the edges of a trunk or a bus do, or
//   that part at a junction: they meet along a run or at its end;
// - two routes that touch where one turns;
// - a route and itself.
//
// Edges that share a trunk or a bus (`lib/bundles.js`) are drawn as one bundle,
// and where they cross each other no bridge is drawn either: a bundle is one
// line to the reader. When both edges at a crossing are highlighted, the bridge
// is on the horizontal one, so one crossing carries one bridge.
//
// A routed edge is orthogonal, so its routes are read as runs that are
// horizontal or vertical; a run that is neither crosses nothing here. A corner
// with no turn, such as the one Cytoscape needs on a straight route, is not a
// place a run ends.
//
// Every function here is pure: routes in, points out.

import { lineIndex, orientationOf } from "./spatialIndex.js";

/** How far inside both runs a crossing lies at least, in layout units: closer to an end it is a touch. */
export const INSIDE = 0.5;
/** The width of a band of the index over the drawn runs. */
const BAND_WIDTH = 16;

/** Whether the route runs on from `before` through `last` to `point` without turning or turning back. */
function runsOn(before, last, point) {
  const orientation = orientationOf(before, last);
  if (!orientation || orientation !== orientationOf(last, point)) return false;
  return (last.x - before.x) * (point.x - last.x) + (last.y - before.y) * (point.y - last.y) > 0;
}

/** `points` as straight runs: a corner where the route does not turn, and a point repeated, dropped. */
export function straightRunsOf(points) {
  const runs = [];
  for (const point of points) {
    const last = runs[runs.length - 1];
    if (last && last.x === point.x && last.y === point.y) continue;
    const before = runs[runs.length - 2];
    if (before && runsOn(before, last, point)) runs[runs.length - 1] = point;
    else runs.push(point);
  }
  return runs;
}

/** Each edge's bundle siblings, the edges it shares a trunk or a bus with: id to a set of ids. */
export function siblingsOf({ trunks = [], buses = [] } = {}) {
  const siblings = new Map();
  for (const { members } of [...trunks, ...buses]) {
    for (const id of members) {
      if (!siblings.has(id)) siblings.set(id, new Set());
      for (const other of members) if (other !== id) siblings.get(id).add(other);
    }
  }
  return siblings;
}

/** The low and high ends of a run along `axis`. */
function spanOf(a, b, axis) {
  return a[axis] <= b[axis] ? [a[axis], b[axis]] : [b[axis], a[axis]];
}

/**
 * An index over `routes` (`[{ id, points }]`, the routes drawn now, in layout
 * units) for finding where they cross: `{ runs, lines }`, each route's straight
 * runs by id and an index of every run. Built once for the routes drawn, it
 * answers for any set of highlighted edges among them.
 */
export function crossingIndexOf(routes) {
  const lines = lineIndex(BAND_WIDTH);
  const runs = new Map();
  for (const { id, points } of routes) {
    const route = { id, points: straightRunsOf(points) };
    runs.set(id, route.points);
    for (let i = 1; i < route.points.length; i += 1) lines.insert(route, route.points[i - 1], route.points[i]);
  }
  return { runs, lines };
}

/**
 * Every crossing of the drawn edge `id` with another drawn edge, over the routes
 * of `crossings` (`crossingIndexOf`): `[{ edge, crossed, x, y, horizontal }]`,
 * `horizontal` when the run of `id` that crosses is. None with itself, and none
 * with an edge `siblings` (`siblingsOf`) names as sharing its bundle.
 */
export function crossingsAlong({ runs, lines }, id, siblings = new Map()) {
  const points = runs.get(id);
  if (!points) return [];
  const related = siblings.get(id);
  const found = [];
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const orientation = orientationOf(a, b);
    if (!orientation) continue;
    const horizontal = orientation === "horizontal";
    const [along, across] = horizontal ? ["x", "y"] : ["y", "x"];
    const [lo, hi] = spanOf(a, b, along);
    if (hi - lo < 2 * INSIDE) continue;
    const at = a[across];
    const visit = (other, c, d) => {
      if (other.id === id || related?.has(other.id)) return;
      const [otherLo, otherHi] = spanOf(c, d, across);
      if (at < otherLo + INSIDE || at > otherHi - INSIDE) return;
      const place = c[along];
      found.push({ edge: id, crossed: other.id, x: horizontal ? place : at, y: horizontal ? at : place, horizontal });
    };
    lines.along(horizontal ? "vertical" : "horizontal", (lo + hi) / 2, (hi - lo) / 2 - INSIDE, at, at, visit);
  }
  return found;
}

/**
 * The bridges of the edges in `highlighted` (a set of ids), given each one's
 * crossings by `crossingsOf(id)` (`crossingsAlong`): every crossing, except that
 * one of two highlighted edges is bridged once, on the horizontal one.
 */
export function bridgesOf(highlighted, crossingsOf) {
  const found = [];
  for (const id of highlighted) {
    for (const crossing of crossingsOf(id)) {
      if (!crossing.horizontal && highlighted.has(crossing.crossed)) continue;
      found.push(crossing);
    }
  }
  return found;
}
