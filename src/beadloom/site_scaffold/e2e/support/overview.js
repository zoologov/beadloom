// The browser tests' own reading of the overview: arrowheads, gaps between lines, lines under titles, pills.
//
// Written apart from the viewer's code, so a case that asks whether two
// arrowheads overlap or how close two lines run does not ask the router it
// checks. Everything is measured on screen, in the canvas's pixels: the handle
// gives each line's route in the graph's coordinates (`lineLooks`), and the zoom
// and pan put it on screen. An arrowhead is a triangle as long as it is wide
// (Cytoscape's triangle and vee are 0.3 of its arrow size each way,
// `support/look.js`), its tip at the line's end and its base on the line.

import { headLength } from "./look.js";

/** Two ends closer than this, in pixels, are one end. */
const SAME_END_PX = 0.5;
/** How far two arrowheads' boxes must reach into each other, in pixels, to overlap rather than touch. */
const HEAD_SLACK_PX = 0.25;
/** How far apart a line's samples are, in pixels, when its distance to the lines beside it is read. */
const SAMPLE_PX = 2;
/** Two lines closer than this, in pixels, are drawn as one line: a shared run, not a gap. */
const MERGED_PX = 0.75;
/** The cosine above which two runs count as running beside each other. */
const PARALLEL = 0.966;
/** The side of the cells samples are filed in, in pixels. */
const CELL_PX = 12;

/** `point` of the graph on the canvas, in pixels, at `view` (`{ zoom, pan }`). */
export const onScreen = (point, { zoom, pan }) => ({ x: point.x * zoom + pan.x, y: point.y * zoom + pan.y });

/** `box` of the graph on the canvas, in pixels. */
export function boxOnScreen(box, view) {
  const [a, b] = [onScreen({ x: box.x1, y: box.y1 }, view), onScreen({ x: box.x2, y: box.y2 }, view)];
  return { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
}

const unit = (from, to) => {
  const length = Math.hypot(to.x - from.x, to.y - from.y) || 1;
  return { x: (to.x - from.x) / length, y: (to.y - from.y) / length };
};

/**
 * Every end of the drawn lines `looks` (`lineLooks`), on screen: `{ id, end,
 * tip, way, arrives, drawn, triangle }`. Edges arrive at an end of a line of the
 * map's that has a count that way, and at the target of an edge of the file;
 * `drawn` says whether an arrowhead is drawn there, and `way` is the direction
 * the line's last run reaches the end in.
 */
export function arrivalsOf(looks, view) {
  const out = [];
  for (const look of looks) {
    const points = look.points.map((p) => onScreen(p, view));
    const n = points.length;
    if (n < 2) continue;
    const length = headLength(look) * view.zoom;
    const at = (end) => {
      const [tip, before] = end === "target" ? [points[n - 1], points[n - 2]] : [points[0], points[1]];
      const way = unit(before, tip);
      const base = { x: tip.x - way.x * length, y: tip.y - way.y * length };
      const normal = { x: -way.y, y: way.x };
      const triangle = [tip, { x: base.x + (normal.x * length) / 2, y: base.y + (normal.y * length) / 2 }, { x: base.x - (normal.x * length) / 2, y: base.y - (normal.y * length) / 2 }];
      const arrow = end === "target" ? look.targetArrow : look.sourceArrow;
      const arrives = end === "target" ? !look.aggregated || look.forward > 0 : look.aggregated && look.backward > 0;
      out.push({ id: look.id, end, tip, way, arrives, drawn: arrow !== "none", triangle });
    };
    at("target");
    at("source");
  }
  return out;
}

/** The arrivals that end at one point from one direction, each group a list. */
export function sharedArrivals(arrivals) {
  const groups = new Map();
  for (const arrival of arrivals) {
    const key = `${Math.round(arrival.tip.x / SAME_END_PX)},${Math.round(arrival.tip.y / SAME_END_PX)}|${Math.round(arrival.way.x)},${Math.round(arrival.way.y)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(arrival);
  }
  return [...groups.values()];
}

const boundsOf = (points) => ({
  x1: Math.min(...points.map((p) => p.x)),
  y1: Math.min(...points.map((p) => p.y)),
  x2: Math.max(...points.map((p) => p.x)),
  y2: Math.max(...points.map((p) => p.y)),
});

/** Whether rectangles `a` and `b` overlap by more than `slack` each way. */
export const rectsOverlap = (a, b, slack = 0) => a.x1 < b.x2 - slack && a.x2 > b.x1 + slack && a.y1 < b.y2 - slack && a.y2 > b.y1 + slack;

/** The pairs of drawn arrowheads, not one shared head, whose boxes overlap, a line's own two heads included: each named "a + b". */
export function overlappingHeads(arrivals) {
  const heads = arrivals.filter((arrival) => arrival.drawn).map((arrival) => ({ ...arrival, box: boundsOf(arrival.triangle) }));
  const same = (p, q) => Math.hypot(p.tip.x - q.tip.x, p.tip.y - q.tip.y) < SAME_END_PX && Math.round(p.way.x) === Math.round(q.way.x) && Math.round(p.way.y) === Math.round(q.way.y);
  const out = [];
  for (let p = 0; p < heads.length; p += 1) {
    for (let q = p + 1; q < heads.length; q += 1) {
      if (same(heads[p], heads[q])) continue;
      if (rectsOverlap(heads[p].box, heads[q].box, HEAD_SLACK_PX)) out.push(`${heads[p].id}:${heads[p].end} + ${heads[q].id}:${heads[q].end}`);
    }
  }
  return out;
}

const orient = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

/** Whether segments `a`-`b` and `c`-`d` cross at a point inside both. */
function segmentsCross(a, b, c, d) {
  const [o1, o2, o3, o4] = [orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)];
  return o1 * o2 < -1e-9 && o3 * o4 < -1e-9;
}

/** Whether the segment `a`-`b` passes through rectangle `r` shrunk by `shrink` on every side (Liang-Barsky). */
export function segmentInRect(a, b, r, shrink = 0) {
  const box = { x1: r.x1 + shrink, y1: r.y1 + shrink, x2: r.x2 - shrink, y2: r.y2 - shrink };
  if (box.x2 <= box.x1 || box.y2 <= box.y1) return false;
  let [t0, t1] = [0, 1];
  const [dx, dy] = [b.x - a.x, b.y - a.y];
  for (const [p, q] of [[-dx, a.x - box.x1], [dx, box.x2 - a.x], [-dy, a.y - box.y1], [dy, box.y2 - a.y]]) {
    if (Math.abs(p) < 1e-12) {
      if (q < 0) return false;
      continue;
    }
    const t = q / p;
    if (p < 0) t0 = Math.max(t0, t);
    else t1 = Math.min(t1, t);
    if (t0 > t1) return false;
  }
  return t1 - t0 > 1e-9;
}

/** The segments of every line in `looks`, on screen: `[{ id, a, b }]`. */
export function segmentsOf(looks, view) {
  return looks.flatMap((look) => {
    const points = look.points.map((p) => onScreen(p, view));
    return points.slice(1).map((b, k) => ({ id: look.id, a: points[k], b }));
  });
}

/** The drawn arrowheads another line crosses: a line that is not the head's own and does not share its last run. */
export function headsUnderLines(arrivals, segments) {
  const groups = sharedArrivals(arrivals);
  const out = [];
  for (const group of groups) {
    const own = new Set(group.map((arrival) => arrival.id));
    for (const head of group.filter((arrival) => arrival.drawn)) {
      const [t0, t1, t2] = head.triangle;
      const crossed = segments.filter((s) => !own.has(s.id) && [[t0, t1], [t1, t2], [t2, t0]].some(([p, q]) => segmentsCross(s.a, s.b, p, q)));
      if (crossed.length) out.push(`${head.id}:${head.end} under ${[...new Set(crossed.map((s) => s.id))].join(", ")}`);
    }
  }
  return out;
}

/**
 * The smallest distance, in pixels, between two lines that run beside each
 * other, over every sample of `looks`; lines closer than `MERGED_PX` are drawn as
 * one and are a shared run, not a gap. `{ minimum, closest }`, `closest` naming
 * the two lines and where.
 */
export function narrowestGap(looks, view) {
  const samples = [];
  looks.forEach((look, line) => {
    const points = look.points.map((p) => onScreen(p, view));
    for (let k = 1; k < points.length; k += 1) {
      const [a, b] = [points[k - 1], points[k]];
      const length = Math.hypot(b.x - a.x, b.y - a.y);
      if (length < 1e-6) continue;
      const t = { x: (b.x - a.x) / length, y: (b.y - a.y) / length };
      for (let s = SAMPLE_PX / 2; s < length; s += SAMPLE_PX) samples.push({ line, x: a.x + t.x * s, y: a.y + t.y * s, t });
    }
  });
  const grid = new Map();
  const keyOf = (x, y) => `${Math.floor(x / CELL_PX)},${Math.floor(y / CELL_PX)}`;
  for (const sample of samples) {
    const key = keyOf(sample.x, sample.y);
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push(sample);
  }
  let minimum = Infinity;
  let closest = null;
  for (const s of samples) {
    const [cx, cy] = [Math.floor(s.x / CELL_PX), Math.floor(s.y / CELL_PX)];
    for (let gx = cx - 1; gx <= cx + 1; gx += 1) {
      for (let gy = cy - 1; gy <= cy + 1; gy += 1) {
        for (const o of grid.get(`${gx},${gy}`) || []) {
          if (o.line === s.line || Math.abs(o.t.x * s.t.x + o.t.y * s.t.y) < PARALLEL) continue;
          const [dx, dy] = [o.x - s.x, o.y - s.y];
          if (Math.abs(dx * s.t.x + dy * s.t.y) > SAMPLE_PX) continue;
          const across = Math.abs(-dx * s.t.y + dy * s.t.x);
          if (across < MERGED_PX || across >= minimum) continue;
          minimum = across;
          closest = `${looks[s.line].id} and ${looks[o.line].id} at ${s.x.toFixed(0)},${s.y.toFixed(0)}`;
        }
      }
    }
  }
  return { minimum, closest };
}
