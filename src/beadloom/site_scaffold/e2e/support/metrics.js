// The metrics cases' own geometry: arrowheads as triangles, gaps between runs, lines through rectangles.
//
// Written apart from the viewer's code and apart from the other cases' oracles
// (`overview.js`, `heads.js`), so a reading taken here is a second measurement of
// what those cases hold, by another method, and not the same arithmetic run twice:
//
// - Two arrowheads overlap when their triangles do, by the separating-axis test,
//   rather than when the rectangles around them do.
// - The gap between two lines is read between the straight runs of each that lie
//   along one axis and overlap along it, rather than between samples.
// - A line runs through a rectangle when a point of it, read every half pixel,
//   lies inside the rectangle, rather than by clipping the segment.
//
// Everything is measured on screen, in the canvas's pixels, from what the test
// handle reports: a line's route in the graph's coordinates (`lineLooks`), and
// the zoom and the pan that put it on screen. Cytoscape's arrowhead is restated
// from its source (3.34.1): a line `w` units wide at an `arrow-scale` of `s` has
// an arrow `max((13.37 w)^0.9, 29) * s` units across, and a triangle or a vee
// takes 0.3 of that along the line and 0.3 across it.

/** How much of Cytoscape's arrow size an arrowhead takes along its line, and across it. */
const ARROW_SHARE = 0.3;
/** Two runs closer than this, in pixels, are drawn as one line: a shared run, not a gap. */
export const MERGED_PX = 0.75;
/** Two runs beside each other overlap along their axis by more than this, in pixels. */
const ALONG_PX = 2;
/** A run lies along an axis when it leaves it by less than this, in pixels. */
const AXIS_PX = 0.5;
/** How far apart the points of a line are read when it is tested against a rectangle, in pixels. */
const STEP_PX = 0.5;

/** `point` of the graph on the canvas, in pixels, at `view` (`{ zoom, pan }`). */
export const toScreen = (point, view) => ({ x: point.x * view.zoom + view.pan.x, y: point.y * view.zoom + view.pan.y });

/** `box` of the graph (`{ x1, y1, x2, y2 }`) on the canvas, in pixels. */
export function rectToScreen(box, view) {
  const [a, b] = [toScreen({ x: box.x1, y: box.y1 }, view), toScreen({ x: box.x2, y: box.y2 }, view)];
  return { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
}

/** `rect` with `by` pixels taken off every side. */
export const shrink = (rect, by) => ({ x1: rect.x1 + by, y1: rect.y1 + by, x2: rect.x2 - by, y2: rect.y2 - by });

/** Whether `point` lies strictly inside `rect`. */
export const inside = (point, rect) => point.x > rect.x1 && point.x < rect.x2 && point.y > rect.y1 && point.y < rect.y2;

/** Whether rectangles `a` and `b` share an area wider and taller than `slack`. */
export const rectsShare = (a, b, slack = 0) =>
  Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1) > slack && Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1) > slack;

/** The length of an arrowhead of `look` (`lineLooks`) along its line, in layout units. */
export const arrowLength = (look) => Math.max((13.37 * look.width) ** 0.9, 29) * look.arrowScale * ARROW_SHARE;

/** `points` with every point that repeats the one before it left out. */
function distinct(points) {
  return points.filter((p, k) => k === 0 || Math.hypot(p.x - points[k - 1].x, p.y - points[k - 1].y) > 1e-6);
}

/**
 * Every arrowhead `looks` draw, on screen: `[{ id, end, tip, way, length,
 * triangle, run }]`, `way` the unit direction the line arrives at its tip in,
 * `length` the head's length in pixels, `triangle` its three corners and `run`
 * the straight run of the line into the tip: its last segment less what its
 * rounded corner takes of it, in pixels.
 */
export function drawnHeads(looks, view) {
  const out = [];
  for (const look of looks) {
    const points = look.points.map((p) => toScreen(p, view));
    if (distinct(points).length < 2) continue;
    // Cytoscape's corner k (a point of the route other than its ends) is rounded at radius k - 1.
    const radii = look.cornerRadii || [];
    const radiusAt = (k) => (radii.length === 1 ? radii[0] : radii[k - 1] ?? 0) * view.zoom;
    for (const end of ["target", "source"]) {
      if ((end === "target" ? look.targetArrow : look.sourceArrow) === "none") continue;
      const indices = points.map((_, k) => k);
      const order = end === "target" ? indices : indices.reverse();
      const at = (k) => points[order[k]];
      const n = order.length;
      let k = n - 2;
      while (k > 0 && Math.hypot(at(k).x - at(n - 1).x, at(k).y - at(n - 1).y) < 1e-6) k -= 1;
      const tip = at(n - 1);
      const last = Math.hypot(tip.x - at(k).x, tip.y - at(k).y);
      const way = { x: (tip.x - at(k).x) / last, y: (tip.y - at(k).y) / last };
      const length = arrowLength(look) * view.zoom;
      const base = { x: tip.x - way.x * length, y: tip.y - way.y * length };
      const half = length / 2;
      const triangle = [tip, { x: base.x - way.y * half, y: base.y + way.x * half }, { x: base.x + way.y * half, y: base.y - way.x * half }];
      // The straight run into the tip goes back through every point on one line with it, and
      // loses to the corner that ends it what its rounding takes: r, never more than half of
      // either segment the corner joins.
      let run = 0;
      let corner = n - 1;
      for (let j = n - 2; j >= 0; j -= 1) {
        const [p, q] = [at(j), at(j + 1)];
        const segment = Math.hypot(q.x - p.x, q.y - p.y);
        if (segment < 1e-6) continue;
        if (Math.abs((q.x - p.x) * way.y - (q.y - p.y) * way.x) > 1e-3 * segment || (q.x - p.x) * way.x + (q.y - p.y) * way.y <= 0) break;
        run += segment;
        corner = j;
      }
      if (corner > 0) {
        const joined = Math.hypot(at(corner + 1).x - at(corner).x, at(corner + 1).y - at(corner).y);
        const before = Math.hypot(at(corner).x - at(corner - 1).x, at(corner).y - at(corner - 1).y);
        run -= Math.min(radiusAt(order[corner]), joined / 2, before / 2);
      }
      out.push({ id: look.id, end, tip, way, length, triangle, run });
    }
  }
  return out;
}

/** How far triangles `a` and `b` reach into each other, in pixels: 0 or less when they are apart (separating axes). */
export function triangleOverlap(a, b) {
  let depth = Infinity;
  for (const polygon of [a, b]) {
    for (let k = 0; k < 3; k += 1) {
      const [p, q] = [polygon[k], polygon[(k + 1) % 3]];
      const length = Math.hypot(q.x - p.x, q.y - p.y);
      if (length < 1e-9) continue;
      const axis = { x: -(q.y - p.y) / length, y: (q.x - p.x) / length };
      const project = (t) => t.map((r) => r.x * axis.x + r.y * axis.y);
      const [pa, pb] = [project(a), project(b)];
      const reach = Math.min(Math.max(...pa), Math.max(...pb)) - Math.max(Math.min(...pa), Math.min(...pb));
      depth = Math.min(depth, reach);
      if (depth <= 0) return depth;
    }
  }
  return depth;
}

/** Whether heads `a` and `b` end at one point from one direction: one shared head, drawn once. */
export const sameEnd = (a, b) => Math.hypot(a.tip.x - b.tip.x, a.tip.y - b.tip.y) <= 0.5 && a.way.x * b.way.x + a.way.y * b.way.y > 0.99;

/** The pairs of `heads` that are not one shared end and whose triangles reach into each other by more than `slack` px: "a + b (depth)". */
export function overlappingTriangles(heads, slack) {
  const out = [];
  for (let p = 0; p < heads.length; p += 1) {
    for (let q = p + 1; q < heads.length; q += 1) {
      if (sameEnd(heads[p], heads[q])) continue;
      const depth = triangleOverlap(heads[p].triangle, heads[q].triangle);
      if (depth > slack) out.push(`${heads[p].id}:${heads[p].end} + ${heads[q].id}:${heads[q].end} (${depth.toFixed(2)} px)`);
    }
  }
  return out;
}

/**
 * The ends where lines arrive together: `[{ tip, ids, heads }]`, each group the
 * lines whose last run ends at one point from one direction (`sameEnd`), with
 * how many arrowheads are drawn there. `arrivals` are every line end that
 * edges arrive at, `drawn` saying whether a head is drawn there.
 */
export function arrivalGroups(looks, view) {
  const ends = [];
  for (const look of looks) {
    const points = distinct(look.points.map((p) => toScreen(p, view)));
    if (points.length < 2) continue;
    const arrivesAt = [];
    if (!look.aggregated || look.forward > 0) arrivesAt.push("target");
    if (look.aggregated && look.backward > 0) arrivesAt.push("source");
    for (const end of arrivesAt) {
      const ordered = end === "target" ? points : [...points].reverse();
      const [before, tip] = ordered.slice(-2);
      const last = Math.hypot(tip.x - before.x, tip.y - before.y);
      const drawn = (end === "target" ? look.targetArrow : look.sourceArrow) !== "none";
      ends.push({ id: look.id, tip, way: { x: (tip.x - before.x) / last, y: (tip.y - before.y) / last }, drawn });
    }
  }
  const groups = [];
  for (const end of ends) {
    const group = groups.find((g) => sameEnd(g.first, end));
    if (group) {
      group.ids.push(end.id);
      group.heads += end.drawn ? 1 : 0;
    } else groups.push({ first: end, tip: end.tip, ids: [end.id], heads: end.drawn ? 1 : 0 });
  }
  return groups.map(({ tip, ids, heads }) => ({ tip, ids, heads }));
}

/** The straight runs of `looks` on screen that lie along an axis: `[{ id, axis, at, from, to }]`. */
function axisRuns(looks, view) {
  const runs = [];
  for (const look of looks) {
    const points = distinct(look.points.map((p) => toScreen(p, view)));
    for (let k = 1; k < points.length; k += 1) {
      const [a, b] = [points[k - 1], points[k]];
      if (Math.abs(a.y - b.y) < AXIS_PX) runs.push({ id: look.id, axis: "h", at: (a.y + b.y) / 2, from: Math.min(a.x, b.x), to: Math.max(a.x, b.x) });
      else if (Math.abs(a.x - b.x) < AXIS_PX) runs.push({ id: look.id, axis: "v", at: (a.x + b.x) / 2, from: Math.min(a.y, b.y), to: Math.max(a.y, b.y) });
    }
  }
  return runs;
}

/**
 * The narrowest gap between two lines that run beside each other, in pixels:
 * two runs of different lines along one axis that overlap along it by more than
 * `ALONG_PX`, apart by `MERGED_PX` or more (closer, they are one drawn line).
 * `{ gap, between, pairs }`, `between` naming the two lines and where, and
 * `pairs` how many pairs of runs beside each other were read.
 */
export function narrowestRunGap(looks, view) {
  const runs = axisRuns(looks, view);
  let gap = Infinity;
  let between = null;
  let pairs = 0;
  for (let p = 0; p < runs.length; p += 1) {
    for (let q = p + 1; q < runs.length; q += 1) {
      const [a, b] = [runs[p], runs[q]];
      if (a.id === b.id || a.axis !== b.axis) continue;
      if (Math.min(a.to, b.to) - Math.max(a.from, b.from) <= ALONG_PX) continue;
      const apart = Math.abs(a.at - b.at);
      if (apart < MERGED_PX) continue;
      pairs += 1;
      if (apart < gap) {
        gap = apart;
        between = `${a.id} and ${b.id} (${a.axis === "h" ? "y" : "x"} ${a.at.toFixed(1)} / ${b.at.toFixed(1)})`;
      }
    }
  }
  return { gap, between, pairs };
}

/** Whether `look`'s line, read every half pixel on screen, has a point inside `rect`. */
export function lineEnters(look, rect, view) {
  const points = look.points.map((p) => toScreen(p, view));
  for (let k = 1; k < points.length; k += 1) {
    const [a, b] = [points[k - 1], points[k]];
    const steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / STEP_PX));
    for (let s = 0; s <= steps; s += 1) {
      if (inside({ x: a.x + ((b.x - a.x) * s) / steps, y: a.y + ((b.y - a.y) * s) / steps }, rect)) return true;
    }
  }
  return false;
}

/** The median of `values`, a list of numbers. */
export const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];

/** `values` summed up as "min / median / max", to two decimals. */
export function spread(values) {
  if (!values.length) return "none";
  const sorted = [...values].sort((a, b) => a - b);
  return `${sorted[0].toFixed(2)} / ${median(sorted).toFixed(2)} / ${sorted[sorted.length - 1].toFixed(2)}`;
}
