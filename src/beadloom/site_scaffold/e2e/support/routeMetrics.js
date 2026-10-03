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
// And five things about how a node's edges fan out, for the trunks and buses:
//
// - the channels a node's edges leave it in, per side and direction: the heights
//   of their first horizontal runs, one per step of a staircase;
// - the excess steps over a drawing, every node's steps beyond two;
// - the lanes a node's edges take across a line some distance out;
// - the points where routes that ran together part, found the slow way;
// - the pairs of edges with no common end drawn along one line.
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

/** Two coordinates closer than this are one, in layout units. */
const SAME = 0.5;
const same = (a, b) => Math.abs(a - b) < SAME;

/** `route`'s points read from `node`'s end: as drawn from a source, reversed into a target. */
function fromEnd(route, node) {
  return route.source === node ? route.points : [...route.points].reverse();
}

/** The side of `box` a route read from its end leaves by: "top", "bottom", or null for another side. */
function sideLeft(points, box) {
  if (same(points[0].y, box.y1)) return "top";
  if (same(points[0].y, box.y2)) return "bottom";
  return null;
}

/** The height of a route's first horizontal run, read from its end, or null when it has none. */
function firstChannel(points) {
  for (let i = 1; i < points.length; i += 1) {
    if (same(points[i - 1].y, points[i].y) && !same(points[i - 1].x, points[i].x)) return points[i - 1].y;
  }
  return null;
}

/**
 * The channels `node`'s edges leave it in: a map from "side/direction" to the
 * set of heights, to the unit, of their first horizontal runs. A fan drawn as a
 * staircase has one height per step; a bus has one.
 */
export function channelsOf(routes, node, box) {
  const channels = new Map();
  for (const route of routes) {
    if (route.source !== node && route.target !== node) continue;
    const points = fromEnd(route, node);
    const side = sideLeft(points, box);
    const channel = firstChannel(points);
    if (!side || channel === null) continue;
    const key = `${side}/${route.source === node ? "out" : "in"}`;
    if (!channels.has(key)) channels.set(key, new Set());
    channels.get(key).add(Math.round(channel));
  }
  return channels;
}

/**
 * How many steps a drawing's fans have beyond the two a node may take on its
 * own: over every node in `leaves` with two edges or more, its first-run heights
 * less two, and none below zero.
 */
export function excessSteps(routes, leaves) {
  const byNode = new Map();
  for (const route of routes) {
    for (const node of [route.source, route.target]) {
      if (!leaves.has(node)) continue;
      if (!byNode.has(node)) byNode.set(node, []);
      byNode.get(node).push(route);
    }
  }
  let excess = 0;
  for (const [node, own] of byNode) {
    if (own.length < 2) continue;
    const heights = new Set();
    for (const route of own) {
      const channel = firstChannel(fromEnd(route, node));
      if (channel !== null) heights.add(Math.round(channel));
    }
    excess += Math.max(0, heights.size - 2);
  }
  return excess;
}

/**
 * Where `node`'s edges cross a line `distance` units out from each side they
 * leave by: `{ top, bottom }`, each `{ lanes, others }` — the lanes, distinct to
 * the unit, and the other ends of the edges that leave by that side.
 */
export function lanesAt(routes, node, box, distance) {
  const sides = {};
  for (const route of routes) {
    if (route.source !== node && route.target !== node) continue;
    const points = fromEnd(route, node);
    const side = sideLeft(points, box);
    if (!side) continue;
    const y = side === "bottom" ? box.y2 + distance : box.y1 - distance;
    sides[side] ||= { xs: [], others: [] };
    sides[side].others.push(route.source === node ? route.target : route.source);
    for (let i = 1; i < points.length; i += 1) {
      const a = points[i - 1];
      const b = points[i];
      if (same(a.y, b.y)) {
        if (same(a.y, y)) sides[side].xs.push(a.x, b.x);
        continue;
      }
      if ((a.y - y) * (b.y - y) <= 0) {
        sides[side].xs.push(a.x + ((y - a.y) / (b.y - a.y)) * (b.x - a.x));
        break;
      }
    }
  }
  return Object.fromEntries(
    Object.entries(sides).map(([side, { xs, others }]) => [side, { lanes: new Set(xs.map(Math.round)).size, others }])
  );
}

/** The compass directions a polyline leaves `point` in, when the point lies on it; empty when not. */
function directionsAt(points, point) {
  const directions = new Set();
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    if (distanceToSegment(point, a, b) > SAME) continue;
    for (const end of [a, b]) {
      const dx = end.x - point.x;
      const dy = end.y - point.y;
      if (Math.abs(dx) < SAME && Math.abs(dy) < SAME) continue;
      directions.add(Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? "E" : "W") : dy > 0 ? "S" : "N");
    }
  }
  return directions;
}

/**
 * Where drawn routes branch: `[{ x, y, edges }]`. A point branches when two
 * routes through it share a direction out of it and differ in another — they ran
 * together and part there. Two routes that cross share no direction, and two
 * that run on together differ in none. Read by comparing every route with every
 * other at every corner, the slow way, so it checks a faster finder.
 */
export function branchPoints(routes) {
  const found = [];
  const boxes = routes.map(({ points }) => ({
    x1: Math.min(...points.map((p) => p.x)) - SAME,
    x2: Math.max(...points.map((p) => p.x)) + SAME,
    y1: Math.min(...points.map((p) => p.y)) - SAME,
    y2: Math.max(...points.map((p) => p.y)) + SAME,
  }));
  for (const route of routes) {
    for (const point of route.points.slice(1, -1)) {
      if (found.some((f) => Math.abs(f.x - point.x) < SAME && Math.abs(f.y - point.y) < SAME)) continue;
      const through = [];
      routes.forEach((other, i) => {
        const b = boxes[i];
        if (point.x < b.x1 || point.x > b.x2 || point.y < b.y1 || point.y > b.y2) return;
        const directions = directionsAt(other.points, point);
        if (directions.size) through.push({ id: other.id, directions });
      });
      const edges = new Set();
      for (const a of through) {
        for (const b of through) {
          if (a === b) continue;
          const shared = [...a.directions].some((d) => b.directions.has(d));
          const differ = a.directions.size !== b.directions.size || [...a.directions].some((d) => !b.directions.has(d));
          if (shared && differ) edges.add(a.id);
        }
      }
      if (edges.size) found.push({ x: point.x, y: point.y, edges: [...edges].sort() });
    }
  }
  return found;
}

/**
 * The pairs of edges with no common endpoint whose routes run along one line for
 * more than a unit: `["a|b", …]`, sorted. Edges that share an end may share a
 * line by design, in a bundle; two that do not are drawn as one there.
 */
export function collinearPairs(routes) {
  const lines = { x: new Map(), y: new Map() };
  for (const route of routes) {
    for (let i = 1; i < route.points.length; i += 1) {
      const [a, b] = [route.points[i - 1], route.points[i]];
      const axis = same(a.y, b.y) ? "y" : same(a.x, b.x) ? "x" : null;
      if (!axis) continue;
      const along = axis === "y" ? "x" : "y";
      const key = Math.round(a[axis]);
      if (!lines[axis].has(key)) lines[axis].set(key, []);
      lines[axis].get(key).push({ route, lo: Math.min(a[along], b[along]), hi: Math.max(a[along], b[along]) });
    }
  }
  const pairs = new Set();
  for (const byLine of Object.values(lines)) {
    for (const segments of byLine.values()) {
      for (let i = 0; i < segments.length; i += 1) {
        for (let j = i + 1; j < segments.length; j += 1) {
          const [s, t] = [segments[i], segments[j]];
          if (s.route === t.route || sharesAnEnd(s.route, t.route)) continue;
          if (Math.min(s.hi, t.hi) - Math.max(s.lo, t.lo) > 1) pairs.add([s.route.id, t.route.id].sort().join("|"));
        }
      }
    }
  }
  return [...pairs].sort();
}
