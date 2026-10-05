// The browser tests' own reading of how a line enters its arrowhead, on screen.
//
// Written apart from the viewer's code, so a case that asks whether a head is
// entered correctly does not ask the functions it checks. Cytoscape's rules are
// restated here from its source (3.34.1), as `look.js` restates its arrowhead size:
//
// - A routed line is drawn from its source endpoint to its target endpoint, each
//   pulled back along its run by the end's gap and the end's distance from its
//   node. A triangle's gap is `2 * width * arrow-scale`, a vee's 0.525 of that,
//   and an end that draws no head has none.
// - A corner of radius `r` between two runs at an angle takes `r / tan(angle/2)` of
//   each run (`r` at a right angle), and never more than half of either; the runs
//   are measured on the line as drawn, its ends pulled back.
// - A dashed line's pattern starts at its source end, `line-dash-offset` into it.
// - A loop is drawn as quadratic pieces through its control points, and its head
//   points along the chord from the point a tenth of the way back on its last
//   piece to its end.
// - A head is a triangle (a vee) with its tip on the line's end, as long as it is
//   wide (`look.js`, `headLength`).
//
// What "entered correctly" means, for every head drawn: every line that ends at
// its tip from its direction, the one that draws it and those that leave their
// head to it, stays straight for the head's length and half a head more behind
// the tip; none is drawn into the head nearer its tip than its own width, and
// the head's own line, its dash pattern read, reaches into the head; the
// head is between the smallest size the viewer draws one at and its full size;
// no other head overlaps it, and no other line touches it. The diagnosis that
// fixed this definition confirmed it against rendered pixels (each head drawn
// alone, its ink read back): a head the geometry passes shows no ink off its
// triangle and the straight line behind it.

import { headLength } from "./look.js";

/** How much straight line a head keeps behind it, as a share of its length: a bend nearer than that reads as bent into the head. */
export const STEM_SHARE = 0.5;
/** The one weight every line is drawn at, in pixels on screen: a line's width tells the scale its marks are drawn at. */
const LINE_PX = 1.35;
/** How far a line may stray from a head's axis, in pixels, and still run into it straight. */
const ON_AXIS_PX = 0.35;
/** Two last runs whose directions' cosine is at least this arrive the same way: a few degrees apart at most. */
const SAME_WAY = 0.998;
/**
 * Two tips a layout unit apart or closer are one tip, the precision a route is
 * drawn to. Two further apart are two ends, each with its own head, however
 * near on screen: lines that reach a node separately stay separate (ruling 10),
 * and two heads that then overlap are heads the drawing leaves no room for.
 */
const SAME_TIP_UNITS = 1;
/** How little a measured length may fall short of the one it is held to, in pixels: a route's numbers are rounded at six decimals. */
const SLACK_PX = 0.05;
/** How far apart, in pixels, a foreign line must keep from a head beyond half its own width. */
const CLEAR_PX = 0.25;
/** How many pieces a quadratic is sampled in. */
const CURVE_STEPS = 24;

const distance = (p, q) => Math.hypot(q.x - p.x, q.y - p.y);
const unit = (from, to) => {
  const length = distance(from, to) || 1;
  return { x: (to.x - from.x) / length, y: (to.y - from.y) / length };
};
const along = (from, to, length) => {
  const d = unit(from, to);
  return { x: from.x + d.x * length, y: from.y + d.y * length };
};

/** How far a line `look` ends short of its route's end at `end`, in layout units: its head's gap and its distance from the node. */
export function endPullback(look, end) {
  const shape = end === "target" ? look.targetArrow : look.sourceArrow;
  const standard = 2 * look.width * look.arrowScale;
  const gap = shape === "triangle" ? standard : shape === "vee" ? 0.525 * standard : 0;
  return gap + ((end === "target" ? look.targetDistance : look.sourceDistance) || 0);
}

/** The points of a routed line's route with every point on a straight run between two others dropped. */
function cornersOnly(points) {
  const out = [];
  for (const point of points) {
    if (out.length && distance(out[out.length - 1], point) < 1e-6) continue;
    if (out.length >= 2) {
      const [a, b] = [out[out.length - 2], out[out.length - 1]];
      const cross = (b.x - a.x) * (point.y - b.y) - (b.y - a.y) * (point.x - b.x);
      if (Math.abs(cross) < 1e-6 * distance(a, b) * distance(b, point) + 1e-9) {
        out[out.length - 1] = point;
        continue;
      }
    }
    out.push(point);
  }
  return out;
}

/** How much of each run a corner of radius `radius` at `corner` takes, as Cytoscape draws it. */
function cornerTake(before, corner, after, radius) {
  const [u, v] = [unit(corner, before), unit(corner, after)];
  const angle = Math.acos(Math.max(-1, Math.min(1, u.x * v.x + u.y * v.y)));
  if (radius <= 0 || angle < 1e-6) return 0;
  const take = Math.abs(radius / Math.tan(angle / 2));
  return Math.min(take, distance(before, corner) / 2, distance(corner, after) / 2);
}

/** The quadratic pieces Cytoscape draws a curve through `points` with: `[start, control, end]` each, through the middles of its control points. */
function curvePieces(points) {
  const [start, ...rest] = points;
  const end = rest.pop();
  if (!rest.length) return [[start, { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 }, end]];
  const pieces = [];
  let from = start;
  for (let i = 0; i < rest.length - 1; i += 1) {
    const middle = { x: (rest[i].x + rest[i + 1].x) / 2, y: (rest[i].y + rest[i + 1].y) / 2 };
    pieces.push([from, rest[i], middle]);
    from = middle;
  }
  pieces.push([from, rest[rest.length - 1], end]);
  return pieces;
}

/** A loop's drawn path, in layout units: its quadratic pieces, sampled. */
function loopPath(points) {
  const out = [points[0]];
  for (const [p0, c, p1] of curvePieces(points)) {
    for (let k = 1; k <= CURVE_STEPS; k += 1) {
      const t = k / CURVE_STEPS;
      out.push({ x: (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * c.x + t * t * p1.x, y: (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * c.y + t * t * p1.y });
    }
  }
  return out;
}

/**
 * A drawn line `look` (`lineLooks`) as Cytoscape draws it, in layout units:
 * `{ path, ends }`, `path` a polyline sampling the stroke from its source end to
 * its target end, `ends` the route's two ends `{ source, target }`, each `{ tip,
 * way }`: where a head there has its tip and the direction it points.
 */
export function drawnLine(look) {
  const routed = look.cornerRadii.length > 0;
  if (!routed) {
    const ends = { source: look.points[0], target: look.points[look.points.length - 1] };
    const inner = look.points.slice(1, -1);
    const drawn = [
      along(ends.source, inner[0] || ends.target, endPullback(look, "source")),
      ...inner,
      along(ends.target, inner[inner.length - 1] || ends.source, endPullback(look, "target")),
    ];
    const path = loopPath(drawn);
    // Cytoscape aims a loop's head along its last piece, from a tenth of the way back on it.
    const aim = (end) => {
      const pieces = curvePieces(drawn);
      const [p0, c, p1] = end === "target" ? pieces[pieces.length - 1] : [...pieces[0]].reverse();
      const t = 0.9;
      return { x: (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * c.x + t * t * p1.x, y: (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * c.y + t * t * p1.y };
    };
    return {
      path,
      routed,
      ends: Object.fromEntries(["source", "target"].map((end) => [end, { tip: ends[end], way: unit(aim(end), ends[end]) }])),
    };
  }
  const points = cornersOnly(look.points);
  const n = points.length;
  const drawn = points.slice();
  drawn[0] = along(points[0], points[1], endPullback(look, "source"));
  drawn[n - 1] = along(points[n - 1], points[n - 2], endPullback(look, "target"));
  const radii = look.cornerRadii;
  const path = [drawn[0]];
  for (let i = 1; i < n - 1; i += 1) {
    const radius = radii.length === 1 ? radii[0] : radii[i - 1] ?? 0;
    const take = cornerTake(drawn[i - 1], drawn[i], drawn[i + 1], radius);
    if (take <= 0) {
      path.push(drawn[i]);
      continue;
    }
    const enter = along(drawn[i], drawn[i - 1], take);
    const leave = along(drawn[i], drawn[i + 1], take);
    path.push(enter);
    // The arc: tangent to both runs where it meets them, its centre where the normals there cross.
    const [u, v] = [unit(drawn[i], drawn[i - 1]), unit(drawn[i], drawn[i + 1])];
    const half = Math.acos(Math.max(-1, Math.min(1, u.x * v.x + u.y * v.y))) / 2;
    const toCentre = take / Math.cos(half);
    const bisector = unit({ x: 0, y: 0 }, { x: u.x + v.x, y: u.y + v.y });
    const centre = { x: drawn[i].x + bisector.x * toCentre, y: drawn[i].y + bisector.y * toCentre };
    const [from, to] = [Math.atan2(enter.y - centre.y, enter.x - centre.x), Math.atan2(leave.y - centre.y, leave.x - centre.x)];
    let sweep = to - from;
    if (sweep > Math.PI) sweep -= 2 * Math.PI;
    if (sweep < -Math.PI) sweep += 2 * Math.PI;
    const arc = Math.hypot(enter.x - centre.x, enter.y - centre.y);
    for (let k = 1; k < CURVE_STEPS; k += 1) {
      const angle = from + (sweep * k) / CURVE_STEPS;
      path.push({ x: centre.x + arc * Math.cos(angle), y: centre.y + arc * Math.sin(angle) });
    }
    path.push(leave);
  }
  path.push(drawn[n - 1]);
  return {
    path,
    routed,
    ends: {
      source: { tip: points[0], way: unit(points[1], points[0]) },
      target: { tip: points[n - 1], way: unit(points[n - 2], points[n - 1]) },
    },
  };
}

/** `point` of the graph on the canvas, in pixels, at `view` (`{ zoom, pan }`). */
const onScreen = (point, { zoom, pan }) => ({ x: point.x * zoom + pan.x, y: point.y * zoom + pan.y });

/** The length of a polyline. */
const lengthOf = (path) => path.slice(1).reduce((sum, point, i) => sum + distance(path[i], point), 0);

/**
 * How far before the end of the stroke `path` (on screen, from its source end
 * to its target end) its last ink is, drawn with the dash pattern `dash` started
 * `offset` into it, both on screen: 0 for a solid line, or one that ends in a dash.
 */
function inkShortOfEnd(path, dash, offset) {
  if (!dash.length) return 0;
  const period = dash.reduce((sum, length) => sum + length, 0);
  const phase = (((lengthOf(path) + offset) % period) + period) % period;
  return phase < dash[0] ? 0 : phase - dash[0];
}

/**
 * How far the stroke `path` (on screen, ordered so that its first point is at
 * the end in question) runs straight into `tip` along `way`: how far behind the
 * tip it first strays more than `ON_AXIS_PX` from the axis, and how far behind
 * the tip it ends. Null when its end is not on the axis at all.
 */
function runInto(path, tip, way) {
  const off = (p) => Math.abs((p.x - tip.x) * way.y - (p.y - tip.y) * way.x);
  const behind = (p) => (tip.x - p.x) * way.x + (tip.y - p.y) * way.y;
  if (off(path[0]) > ON_AXIS_PX) return null;
  let straight = behind(path[0]);
  for (let i = 1; i < path.length; i += 1) {
    const [a, b] = [path[i - 1], path[i]];
    if (off(b) <= ON_AXIS_PX && behind(b) >= behind(a) - 1e-9) {
      straight = behind(b);
      continue;
    }
    const t = off(b) > off(a) ? Math.max(0, Math.min(1, (ON_AXIS_PX - off(a)) / (off(b) - off(a)))) : 0;
    straight = behind({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
    break;
  }
  return { straight, endsBehind: behind(path[0]) };
}

const orient = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
function insideTriangle(p, [a, b, c]) {
  const [d1, d2, d3] = [orient(a, b, p), orient(b, c, p), orient(c, a, p)];
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
}
function segmentDistance(p, a, b) {
  const [dx, dy] = [b.x - a.x, b.y - a.y];
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1e-12)));
  return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy);
}
function segmentsDistance(a, b, c, d) {
  if (orient(a, b, c) * orient(a, b, d) < 0 && orient(c, d, a) * orient(c, d, b) < 0) return 0;
  return Math.min(segmentDistance(a, c, d), segmentDistance(b, c, d), segmentDistance(c, a, b), segmentDistance(d, a, b));
}
/** How near the polyline `path` comes to `triangle`: 0 when it enters it. */
/** How near the segments `pieces` (`[a, b]` pairs) come to `triangle`: 0 when one enters it. */
function nearestTo(pieces, triangle) {
  let nearest = Infinity;
  const edges = [[triangle[0], triangle[1]], [triangle[1], triangle[2]], [triangle[2], triangle[0]]];
  for (const [a, b] of pieces) {
    if (insideTriangle(a, triangle) || insideTriangle(b, triangle)) return 0;
    for (const [p, q] of edges) nearest = Math.min(nearest, segmentsDistance(a, b, p, q));
  }
  return nearest;
}

/** The side of a cell of the index over the drawn strokes' segments, in pixels. */
const CELL_PX = 16;

/** An index over the segments of `lines`' strokes: `near(box)` gives each line with a segment in a cell `box` meets, and those segments. */
function segmentIndexOf(lines) {
  const cells = new Map();
  const cell = (value) => Math.floor(value / CELL_PX);
  lines.forEach((line, which) => {
    for (let i = 1; i < line.path.length; i += 1) {
      const [a, b] = [line.path[i - 1], line.path[i]];
      for (let cx = cell(Math.min(a.x, b.x)); cx <= cell(Math.max(a.x, b.x)); cx += 1) {
        for (let cy = cell(Math.min(a.y, b.y)); cy <= cell(Math.max(a.y, b.y)); cy += 1) {
          const key = `${cx},${cy}`;
          if (!cells.has(key)) cells.set(key, []);
          cells.get(key).push([which, i]);
        }
      }
    }
  });
  return {
    near(box) {
      const found = new Map();
      for (let cx = cell(box.x1); cx <= cell(box.x2); cx += 1) {
        for (let cy = cell(box.y1); cy <= cell(box.y2); cy += 1) {
          for (const [which, i] of cells.get(`${cx},${cy}`) || []) {
            if (!found.has(which)) found.set(which, new Set());
            found.get(which).add(i);
          }
        }
      }
      return [...found].map(([which, indices]) => ({
        line: lines[which],
        pieces: [...indices].map((i) => [lines[which].path[i - 1], lines[which].path[i]]),
      }));
    },
  };
}
const boundsOf = (points, margin = 0) => ({
  x1: Math.min(...points.map((p) => p.x)) - margin,
  y1: Math.min(...points.map((p) => p.y)) - margin,
  x2: Math.max(...points.map((p) => p.x)) + margin,
  y2: Math.max(...points.map((p) => p.y)) + margin,
});
const meets = (a, b) => a.x1 <= b.x2 && a.x2 >= b.x1 && a.y1 <= b.y2 && a.y2 >= b.y1;

/** A head `length` long with its tip at `tip`, pointing along `way`: its triangle and the box around it. */
function triangleOf(tip, way, length) {
  const base = { x: tip.x - way.x * length, y: tip.y - way.y * length };
  const normal = { x: -way.y, y: way.x };
  const triangle = [tip, { x: base.x + (normal.x * length) / 2, y: base.y + (normal.y * length) / 2 }, { x: base.x - (normal.x * length) / 2, y: base.y - (normal.y * length) / 2 }];
  return { triangle, box: boundsOf(triangle) };
}

/**
 * Every arrowhead the drawn lines `looks` draw, on screen at `view`, with what
 * is wrong with how its lines enter it: `[{ id, end, length, straight, wrong,
 * roomless, loops }]`. `loops` lists what is wrong because of a loop, a line
 * Cytoscape draws from a node across its box (its own head, or its line in the
 * way); of the rest, `wrong` lists what is wrong at the size the head is drawn that
 * the viewer answers for, empty for a head entered correctly; `roomless` lists
 * what stays wrong with the head at the smallest size the viewer draws one at,
 * where the drawing leaves no room for any head: a line that bends, crosses or
 * runs beside it too near. A bend, an overlap or a line too near that the
 * smallest head would clear is the viewer's, in `wrong`. `sizes`
 * are `{ head, smallest }`, the head's full length on screen and that smallest,
 * in pixels; a size held to them is held within half of `step`, the zoom step
 * the viewer restyles its marks at.
 */
export function headsOf(looks, view, { head, smallest, step }) {
  const half = Math.sqrt(step);
  const lines = looks.map((look) => {
    const line = drawnLine(look);
    const path = line.path.map((p) => onScreen(p, view));
    const dash = (look.dash || []).map((length) => length * view.zoom);
    // A pattern starts at the source end: how far short of the target end its last dash stops.
    const inkShort = { source: 0, target: inkShortOfEnd(path, dash, (look.dashOffset || 0) * view.zoom) };
    return { look, path, ends: line.ends, inkShort };
  });
  const ends = lines.flatMap((line) =>
    ["source", "target"].map((end) => ({
      line,
      end,
      tip: onScreen(line.ends[end].tip, view),
      way: line.ends[end].way,
      drawn: (end === "target" ? line.look.targetArrow : line.look.sourceArrow) !== "none",
      path: end === "target" ? [...line.path].reverse() : line.path,
    }))
  );
  const segments = segmentIndexOf(lines);
  const sameTip = SAME_TIP_UNITS * view.zoom;
  const tipCell = (point) => `${Math.floor(point.x / sameTip)},${Math.floor(point.y / sameTip)}`;
  const byTip = new Map();
  for (const end of ends) {
    const key = tipCell(end.tip);
    if (!byTip.has(key)) byTip.set(key, []);
    byTip.get(key).push(end);
  }
  const endsNear = (tip) => {
    const [cx, cy] = [Math.floor(tip.x / sameTip), Math.floor(tip.y / sameTip)];
    const found = [];
    for (let dx = -1; dx <= 1; dx += 1) for (let dy = -1; dy <= 1; dy += 1) found.push(...(byTip.get(`${cx + dx},${cy + dy}`) || []));
    return found;
  };
  const heads = ends
    .filter((end) => end.drawn)
    .map((end) => {
      const length = headLength(end.line.look) * view.zoom;
      const group = endsNear(end.tip).filter((e) => distance(e.tip, end.tip) <= sameTip && e.way.x * end.way.x + e.way.y * end.way.y >= SAME_WAY);
      // The smallest the viewer draws this head at now: its size multiplies by the scale its line's width shows.
      const floor = smallest * ((end.line.look.width * view.zoom) / LINE_PX);
      return { ...end, group, length, floor, drawnAs: triangleOf(end.tip, end.way, length), smallest: triangleOf(end.tip, end.way, floor) };
    });

  /**
   * What is wrong with head `h` were it drawn as `size` ("drawnAs" or "smallest"),
   * every other head drawn the same way: each finding `{ text, room, by }`,
   * `room` whether room decides it (a bend, an overlap, a line too near) and `by`
   * the other line it names, if any.
   */
  function findings(h, size) {
    const found = [];
    const { triangle, box } = h[size];
    const length = size === "drawnAs" ? h.length : h.floor;
    const width = h.line.look.width * view.zoom;
    let straight = Infinity;
    for (const member of h.group) {
      const run = runInto(member.path, h.tip, h.way);
      if (!run) continue;
      straight = Math.min(straight, run.straight);
      const own = member.line === h.line && member.end === h.end;
      const name = own ? "its own line" : `${member.line.look.id}`;
      const by = own ? null : member.line;
      const inkBehind = run.endsBehind + member.line.inkShort[member.end];
      // Its own line ends inside the head where the head is at least half its width wide; another line, where the head is as wide as the line.
      if (inkBehind < (own ? width / 2 : width) - SLACK_PX) {
        found.push({ text: `${name} is drawn into the head ${inkBehind.toFixed(2)} px from its tip`, room: false, by });
      }
      // Its ink reaches the head: a triangle's base, or a vee's notch, halfway back.
      const reach = h.end === "target" && h.line.look.targetArrow === "vee" ? length / 2 : length;
      if (own && size === "drawnAs" && inkBehind > reach + SLACK_PX) {
        found.push({ text: `its line stops ${(inkBehind - reach).toFixed(2)} px short of the head`, room: false, by: null });
      }
    }
    if (straight < length * (1 + STEM_SHARE) - SLACK_PX) {
      found.push({ text: `a bend ${straight.toFixed(2)} px behind the tip of a head ${length.toFixed(2)} px long`, room: true, by: null });
    }
    for (const other of heads) {
      if (other === h || !meets(other[size].box, box)) continue;
      const stacked = other.group.some((e) => e.line === h.line && e.end === h.end);
      const cross = other[size].triangle.some((p) => insideTriangle(p, triangle)) || triangle.some((p) => insideTriangle(p, other[size].triangle));
      if (stacked) found.push({ text: `another head is drawn on it, of ${other.line.look.id}`, room: false, by: other.line });
      else if (cross) found.push({ text: `overlaps the head of ${other.line.look.id}`, room: true, by: other.line });
    }
    const members = new Set(h.group.map((e) => e.line));
    for (const { line, pieces } of segments.near(boundsOf(triangle, width + CLEAR_PX + 1))) {
      if (members.has(line)) continue;
      const near = nearestTo(pieces, triangle);
      if (near < (line.look.width * view.zoom) / 2 + CLEAR_PX) found.push({ text: `${line.look.id} runs ${near.toFixed(2)} px from the head`, room: true, by: line });
    }
    return { found, straight };
  }

  // A loop is drawn by Cytoscape, from a node across its box to the box's border:
  // a finding on a loop's head, or one a loop's line causes, is the loop's.
  const isLoop = (line) => Boolean(line) && !line.look.aggregated && !line.look.cornerRadii.length;
  return heads.map((h) => {
    const { found, straight } = findings(h, "drawnAs");
    if (h.length > head * half + SLACK_PX || h.length < smallest / half - SLACK_PX) {
      found.push({ text: `a head ${h.length.toFixed(2)} px long`, room: false, by: null });
    }
    const ofLoop = (finding) => isLoop(h.line) || isLoop(finding.by);
    const loops = found.filter(ofLoop).map((finding) => finding.text);
    const rest = found.filter((finding) => !ofLoop(finding));
    // Room decides a bend, an overlap and a line too near; nothing excuses a line drawn on into a
    // head, one that stops short of it, a head drawn on another, or a head out of its sizes.
    const roomless = rest.some((finding) => finding.room)
      ? findings(h, "smallest").found.filter((finding) => finding.room && !ofLoop(finding)).map((finding) => finding.text)
      : [];
    const wrong = rest.filter((finding) => !finding.room || !roomless.length).map((finding) => finding.text);
    return { id: h.line.look.id, end: h.end, length: h.length, straight, wrong, roomless, loops };
  });
}

/** The heads of `headsOf`'s answer the viewer drew wrong, each named with what is wrong: a fault no room explains. */
export const wrongHeads = (heads) => heads.filter((h) => h.wrong.length).map((h) => `${h.id}:${h.end}: ${h.wrong.join("; ")}`);

/** The heads of `headsOf`'s answer the drawing leaves no room for: wrong even at the smallest size, each named with what is in the way. */
export const roomlessHeads = (heads) => heads.filter((h) => h.roomless.length).map((h) => `${h.id}:${h.end}: ${h.roomless.join("; ")}`);

/** The heads of `headsOf`'s answer that are wrong because of a loop: a loop's own head, or a loop's line in the way. */
export const loopHeads = (heads) => heads.filter((h) => h.loops.length).map((h) => `${h.id}:${h.end}: ${h.loops.join("; ")}`);
