// beadloom:component=site-graph-viewer
// An aggregated edge's route, taken from the routes of the edges it carries.
//
// ELK routed every edge at full detail around every box. An aggregated edge joins
// two drawn ends, and each edge it carries already runs from one to the other:
// clipped to the stretch between where it last leaves the one end's box and
// where it first enters the other's, a member's route is a route between the two
// boxes that avoids every other box, as ELK computed it. Of those stretches the
// one drawn is the medoid: the one lying closest, on average, to all the others,
// so the line runs where most of its edges run. Nothing is routed again: an
// edge's own route is not moved, and no box is. A line between two top-level
// nodes is routed afresh instead, with the overview's others
// (`overviewRoutes.js`); the medoid draws every other aggregated line, and one
// the overview's router found no route for.
//
// Every function here is pure: polylines and boxes in, a polyline out.

/** How many points each stretch is compared at when the medoid is chosen. */
const SAMPLES = 16;
/** The shortest stretch kept between two boxes, in layout units: below it there is no line to draw. */
const SHORTEST = 1;
/** Two points closer than this are one, in layout units. */
const SAME_POINT = 0.01;
/**
 * How far outside a box a route's end may stop and still reach it, in layout
 * units: ELK ends a route on the border, and its arithmetic can leave the end a
 * hair outside it (1e-13 units, measured).
 */
const BORDER_SLACK = 0.01;

/** `box` grown by the border slack on every side. */
const reaching = (box) => ({
  x1: box.x1 - BORDER_SLACK,
  y1: box.y1 - BORDER_SLACK,
  x2: box.x2 + BORDER_SLACK,
  y2: box.y2 + BORDER_SLACK,
});

/** The parameters `[t0, t1]` of the part of segment `a`-`b` inside `box`, or null (Liang-Barsky). */
function clipSegment(a, b, box) {
  let t0 = 0;
  let t1 = 1;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const p = [-dx, dx, -dy, dy];
  const q = [a.x - box.x1, box.x2 - a.x, a.y - box.y1, box.y2 - a.y];
  for (let i = 0; i < 4; i += 1) {
    if (p[i] === 0) {
      if (q[i] < 0) return null;
      continue;
    }
    const r = q[i] / p[i];
    if (p[i] < 0) {
      if (r > t1) return null;
      t0 = Math.max(t0, r);
    } else {
      if (r < t0) return null;
      t1 = Math.min(t1, r);
    }
  }
  return t0 <= t1 ? [t0, t1] : null;
}

const distance = (a, b) => Math.hypot(b.x - a.x, b.y - a.y);

/** How far along `path` it last lies in `box`, as a length from its start; -1 when it never does. */
function lastInside(path, box) {
  let along = 0;
  let last = -1;
  for (let i = 1; i < path.length; i += 1) {
    const length = distance(path[i - 1], path[i]);
    const inside = clipSegment(path[i - 1], path[i], box);
    if (inside) last = Math.max(last, along + inside[1] * length);
    along += length;
  }
  return last;
}

/** How far along `path` it first lies in `box` after `from`; Infinity when it does not. */
function firstInsideAfter(path, box, from) {
  let along = 0;
  let first = Infinity;
  for (let i = 1; i < path.length; i += 1) {
    const length = distance(path[i - 1], path[i]);
    const inside = clipSegment(path[i - 1], path[i], box);
    if (inside && along + inside[1] * length > from) first = Math.min(first, Math.max(along + inside[0] * length, from));
    along += length;
  }
  return first;
}

/** The part of `path` between the lengths `from` and `to` along it. */
function stretchOf(path, from, to) {
  const out = [];
  let along = 0;
  const at = (a, b, length, where) => {
    const t = length ? (where - along) / length : 0;
    return { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) };
  };
  for (let i = 1; i < path.length; i += 1) {
    const [a, b] = [path[i - 1], path[i]];
    const length = distance(a, b);
    if (along + length >= from && along <= to) {
      if (!out.length) out.push(at(a, b, length, Math.max(from, along)));
      if (along + length <= to) out.push({ x: b.x, y: b.y });
      else {
        out.push(at(a, b, length, to));
        break;
      }
    }
    along += length;
  }
  return out.filter((point, i) => i === 0 || distance(point, out[i - 1]) > SAME_POINT);
}

/**
 * The stretch of `path` from where it last leaves `fromBox` to where it next
 * enters `toBox`, or null when it does not run from one to the other.
 */
export function stretchBetween(path, fromBox, toBox) {
  const leaves = lastInside(path, reaching(fromBox));
  if (leaves < 0) return null;
  const enters = firstInsideAfter(path, reaching(toBox), leaves);
  if (!Number.isFinite(enters) || enters - leaves < SHORTEST) return null;
  const stretch = stretchOf(path, leaves, enters);
  return stretch.length >= 2 ? stretch : null;
}

/** `path` at `count` points evenly spaced along it. */
function resample(path, count) {
  const lengths = path.slice(1).map((point, i) => distance(path[i], point));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  const out = [];
  for (let k = 0; k < count; k += 1) {
    let left = (total * k) / (count - 1);
    let i = 0;
    while (i < lengths.length - 1 && left > lengths[i]) {
      left -= lengths[i];
      i += 1;
    }
    const t = lengths[i] ? Math.min(1, left / lengths[i]) : 0;
    out.push({ x: path[i].x + t * (path[i + 1].x - path[i].x), y: path[i].y + t * (path[i + 1].y - path[i].y) });
  }
  return out;
}

/** The polyline among `paths` with the least summed distance to all the others, sampled alike. */
export function medoidOf(paths) {
  if (paths.length <= 1) return paths[0] || null;
  const sampled = paths.map((path) => resample(path, SAMPLES));
  let best = 0;
  let bestSum = Infinity;
  sampled.forEach((one, i) => {
    let sum = 0;
    sampled.forEach((other, j) => {
      if (i !== j) for (let k = 0; k < SAMPLES; k += 1) sum += distance(one[k], other[k]);
    });
    if (sum < bestSum) {
      bestSum = sum;
      best = i;
    }
  });
  return paths[best];
}

/**
 * The route of an aggregated edge from `fromBox` to `toBox`: the medoid of its
 * members' stretches between the two, each member `{ path, reversed }`, `reversed`
 * when the member runs from `toBox` to `fromBox`; null when no member runs between
 * them.
 */
export function aggregateRouteOf(members, fromBox, toBox) {
  const stretches = [];
  for (const { path, reversed } of members) {
    if (!path || path.length < 2) continue;
    const stretch = reversed ? stretchBetween(path, toBox, fromBox) : stretchBetween(path, fromBox, toBox);
    if (stretch) stretches.push(reversed ? [...stretch].reverse() : stretch);
  }
  return medoidOf(stretches);
}
