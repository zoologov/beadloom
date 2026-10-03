// How well a drawing's edges read, measured on the polylines it draws, in layout units.
//
// The browser tests read each drawn edge as a polyline (`edgeRoutes()` on the test
// handle) and each node's box, and measure three things here, independently of
// the viewer's code:
//
// - how far a drawn polyline lies from the route the layout computed;
// - which edges pass through a box they do not connect;
// - which edges are hard to tell apart: an edge is sampled at evenly spaced points
//   over the middle of its length, a sample is shared when a sample of another
//   edge lies in the same or a neighbouring small cell, and an edge is
//   indistinct when more than half of its samples are shared. Only edges with no
//   common endpoint count against each other: edges that leave or reach one node
//   meet there by design.
//
// Nothing here knows a project's names; a box, an edge and a point are plain data.

/** How many samples an edge is read at. */
const SAMPLES = 60;
/** The part of an edge's length its samples cover, centred, so its ends at shared nodes are left out. */
const SAMPLED_SHARE = 0.8;
/** The side of a sharing cell: two samples in one cell, or in neighbouring cells, are shared. */
const SHARING_CELL = 4;
/** How far inside a box a segment must reach to count as passing through it. */
const BOX_INSET = 1;

/** A route's sections, ELK's polylines laid end to end, as one polyline. */
export function polylineOf(sections) {
  const points = [];
  for (const section of sections) {
    for (const point of section) {
      const last = points[points.length - 1];
      if (!last || last.x !== point.x || last.y !== point.y) points.push(point);
    }
  }
  return points;
}

/** The distance from `point` to the segment from `a` to `b`. */
function distanceToSegment(point, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length2 = dx * dx + dy * dy;
  const t = length2 ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length2)) : 0;
  return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
}

/** The distance from `point` to the nearest point of `polyline`. */
export function distanceToPolyline(point, polyline) {
  if (polyline.length === 1) return Math.hypot(point.x - polyline[0].x, point.y - polyline[0].y);
  let nearest = Infinity;
  for (let i = 1; i < polyline.length; i += 1) {
    nearest = Math.min(nearest, distanceToSegment(point, polyline[i - 1], polyline[i]));
  }
  return nearest;
}

/**
 * How far two polylines lie apart: the largest distance from a corner of either
 * to the other. Two drawings of one orthogonal route, one with an extra corner
 * on a straight stretch, are 0 apart.
 */
export function deviation(drawn, reference) {
  const farthest = (from, to) => Math.max(...from.map((point) => distanceToPolyline(point, to)));
  return Math.max(farthest(drawn, reference), farthest(reference, drawn));
}

/** Whether the segment from `a` to `b` enters the open box `box` (Liang-Barsky clipping). */
function entersBox(a, b, box) {
  let t0 = 0;
  let t1 = 1;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const p = [-dx, dx, -dy, dy];
  const q = [a.x - box.x1, box.x2 - a.x, a.y - box.y1, box.y2 - a.y];
  for (let i = 0; i < 4; i += 1) {
    if (p[i] === 0) {
      if (q[i] <= 0) return false;
      continue;
    }
    const t = q[i] / p[i];
    if (p[i] < 0) {
      if (t > t1) return false;
      t0 = Math.max(t0, t);
    } else {
      if (t < t0) return false;
      t1 = Math.min(t1, t);
    }
  }
  return t1 - t0 > 1e-6;
}

/** Each id in `ids` with every container of it, by `parents` (id to parent id or null). */
function withContainers(ids, parents) {
  const out = new Set();
  for (const id of ids) {
    for (let cursor = id; cursor && !out.has(cursor); cursor = parents[cursor]) out.add(cursor);
  }
  return out;
}

/**
 * The edges that pass through a box they do not connect: `[{ edge, box }]`, one
 * entry per edge and box.
 *
 * `edges` are `{ id, source, target, points }`; `boxes` maps a node's id to its
 * box `{ x1, y1, x2, y2 }`; `parents` maps a node's id to its container's. An edge
 * may cross the boxes of its ends and of their containers, since it has to leave
 * them; any other box it enters, by more than a unit, it passes through.
 */
export function edgesThroughBoxes(edges, boxes, parents) {
  const found = [];
  const inset = Object.entries(boxes).map(([id, b]) => [
    id,
    { x1: b.x1 + BOX_INSET, y1: b.y1 + BOX_INSET, x2: b.x2 - BOX_INSET, y2: b.y2 - BOX_INSET },
  ]);
  for (const edge of edges) {
    const own = withContainers([edge.source, edge.target], parents);
    for (const [id, box] of inset) {
      if (own.has(id)) continue;
      const { points } = edge;
      for (let i = 1; i < points.length; i += 1) {
        if (entersBox(points[i - 1], points[i], box)) {
          found.push({ edge: edge.id, box: id });
          break;
        }
      }
    }
  }
  return found;
}

/** `SAMPLES` points evenly spaced over the middle `SAMPLED_SHARE` of a polyline's length. */
function samplesOf(points) {
  const lengths = points.slice(1).map((point, i) => Math.hypot(point.x - points[i].x, point.y - points[i].y));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  const margin = (1 - SAMPLED_SHARE) / 2;
  const samples = [];
  for (let k = 0; k < SAMPLES; k += 1) {
    let along = total * (margin + (SAMPLED_SHARE * k) / (SAMPLES - 1));
    let i = 0;
    while (i < lengths.length - 1 && along > lengths[i]) {
      along -= lengths[i];
      i += 1;
    }
    const f = lengths[i] ? along / lengths[i] : 0;
    samples.push({
      x: points[i].x + (points[i + 1].x - points[i].x) * f,
      y: points[i].y + (points[i + 1].y - points[i].y) * f,
    });
  }
  return samples;
}

const sharesAnEnd = (a, b) =>
  a.source === b.source || a.source === b.target || a.target === b.source || a.target === b.target;

/**
 * How distinct the edges are: `{ meanShared, indistinct }`.
 *
 * `meanShared` is the mean share of an edge's samples that lie by a sample of
 * another edge with no common endpoint; `indistinct` lists the ids of the edges
 * more than half of whose samples do. `edges` are `{ id, source, target, points }`.
 */
export function sharing(edges) {
  const cellOf = (value) => Math.floor(value / SHARING_CELL);
  const sampled = edges.map((edge) => samplesOf(edge.points));
  const cells = new Map();
  sampled.forEach((samples, index) => {
    for (const { x, y } of samples) {
      const key = `${cellOf(x)},${cellOf(y)}`;
      if (!cells.has(key)) cells.set(key, new Set());
      cells.get(key).add(index);
    }
  });
  const sharedAt = (index, { x, y }) => {
    for (let dx = -1; dx <= 1; dx += 1) {
      for (let dy = -1; dy <= 1; dy += 1) {
        for (const other of cells.get(`${cellOf(x) + dx},${cellOf(y) + dy}`) || []) {
          if (other !== index && !sharesAnEnd(edges[index], edges[other])) return true;
        }
      }
    }
    return false;
  };
  const shares = sampled.map(
    (samples, index) => samples.filter((sample) => sharedAt(index, sample)).length / samples.length
  );
  return {
    meanShared: shares.reduce((sum, share) => sum + share, 0) / (shares.length || 1),
    indistinct: edges.filter((_, index) => shares[index] > 0.5).map((edge) => edge.id),
  };
}
