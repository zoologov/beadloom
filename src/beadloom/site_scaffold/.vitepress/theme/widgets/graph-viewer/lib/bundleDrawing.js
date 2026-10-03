// beadloom:component=site-graph-viewer
// The drawing the bundling rewrites: its containment, its boxes and its live routes, indexed.
//
// The buses and the trunks (`buses.js`, `trunks.js`) read one drawing and
// rewrite its routes one edge at a time, and each rewrite is checked against
// the routes as they stand: a new segment may not cross a box or run along an
// edge that has nothing to do with it. So the drawing keeps every route's
// current version in an index (`spatialIndex.js`), and a replaced route's
// segments are skipped wherever the index still holds them.
//
// The helpers here read a route from either end, since a node's edges into it
// are bundled from its side too, and every route's points are shared, never
// changed: a rewrite replaces a route.

import { gridIndex, lineIndex, orientationOf, segmentRect } from "./spatialIndex.js";

/** Two coordinates closer than this are one. */
export const NEAR = 0.5;
/** How far inside a box a segment must reach to cross it. */
export const BOX_INSET = 1;
/** How far two collinear segments must overlap to run along each other. */
const OVERLAP = 1;

export const near = (a, b) => Math.abs(a - b) < NEAR;
export const centreX = (box) => (box.x1 + box.x2) / 2;

/**
 * A polyline without repeated points and without a corner on a straight run. Its
 * points are the ones given, not copies: a route's points are never changed, only
 * replaced.
 */
export function simplify(points) {
  const out = [];
  for (const point of points) {
    const last = out[out.length - 1];
    if (last && near(last.x, point.x) && near(last.y, point.y)) continue;
    if (out.length >= 2) {
      const before = out[out.length - 2];
      const straight =
        (near(before.x, last.x) && near(last.x, point.x)) || (near(before.y, last.y) && near(last.y, point.y));
      if (straight) {
        out[out.length - 1] = point;
        continue;
      }
    }
    out.push(point);
  }
  return out;
}

/**
 * The drawing of `{ nodes, edges, loops, boxes, paths }` (`bundleRoutes`),
 * indexed by `options.cellSize` and `options.bandWidth`: its containment, the
 * routed edges at each node, how many edges each node draws, and its routes,
 * which `setRoute` replaces one at a time.
 */
export function drawingOf({ nodes, edges, loops = [], boxes, paths }, options) {
  const parent = new Map(nodes.map((node) => [node.id, node.parent || null]));
  const holders = new Set([...parent.values()].filter(Boolean));
  const roots = nodes.map((node) => node.id).filter((id) => !parent.get(id));
  // One root that holds everything is a wrapper; its children are the top-level boxes.
  const wrapper = roots.length === 1 && holders.has(roots[0]) ? roots[0] : null;
  const ancestorsCache = new Map();
  const ancestors = (id) => {
    if (!ancestorsCache.has(id)) {
      const chain = [];
      for (let cursor = parent.get(id); cursor; cursor = parent.get(cursor)) chain.push(cursor);
      ancestorsCache.set(id, chain);
    }
    return ancestorsCache.get(id);
  };
  const holdersCache = new Map();
  const withHolders = (id) => {
    if (!holdersCache.has(id)) holdersCache.set(id, new Set([id, ...ancestors(id)]));
    return holdersCache.get(id);
  };
  const topBox = (id) => {
    let cursor = id;
    while (parent.get(cursor) && parent.get(cursor) !== wrapper) cursor = parent.get(cursor);
    return cursor;
  };

  const routed = edges.filter((e) => paths[e.id]?.length >= 2 && boxes[e.source] && boxes[e.target]);
  const atNode = new Map();
  const order = [];
  for (const edge of routed) {
    for (const id of [edge.source, edge.target]) {
      if (!atNode.has(id)) {
        atNode.set(id, []);
        order.push(id);
      }
      atNode.get(id).push(edge);
    }
  }
  // A node draws its routed edges and its loops: a box's edges into its own
  // children, a node's into a box that holds it. A loop is never rerouted, but it
  // is one of the node's drawn edges, and a node is busy by the edges it draws.
  const drawn = new Map([...atNode].map(([id, at]) => [id, at.length]));
  for (const loop of loops) {
    for (const id of new Set([loop.source, loop.target])) drawn.set(id, (drawn.get(id) || 0) + 1);
  }
  const withDegree = (degree) => order.filter((id) => drawn.get(id) >= degree);

  const boxIndex = gridIndex(options.cellSize);
  for (const [id, box] of Object.entries(boxes)) boxIndex.insert({ id, box }, box);

  const routes = new Map();
  const versions = new Map();
  const segmentIndex = lineIndex(options.bandWidth);
  const setRoute = (edge, points) => {
    const version = (versions.get(edge.id) || 0) + 1;
    versions.set(edge.id, version);
    routes.set(edge.id, points);
    const tag = { edge, version };
    for (let i = 1; i < points.length; i += 1) segmentIndex.insert(tag, points[i - 1], points[i]);
  };
  for (const edge of routed) setRoute(edge, paths[edge.id]);

  return {
    boxes,
    ancestors,
    /** The node `id` and every box that holds it, as a set. */
    withHolders,
    topBox,
    routes,
    setRoute,
    edgesAt: (id) => atNode.get(id) || [],
    /**
     * The nodes, leaves and boxes alike, that route an edge and draw at least
     * `degree` edges, in the order the routed edges first name them.
     */
    nodesWithDegree: withDegree,
    /** The same, the nodes that draw the most edges first. */
    nodesByDegree: (degree) => withDegree(degree).sort((a, b) => drawn.get(b) - drawn.get(a)),
    /** The bus channel each edge was given, by the node whose bus gave it: edge id to `{ node, y }`. */
    channels: new Map(),
    /** Visit every box whose rectangle meets `rect`. */
    boxesIn: (rect, visit) => boxIndex.query(rect, ({ id, box }) => visit(id, box)),
    /**
     * Visit every segment of a live route of `orientation` within `clearance` of
     * the line at `at` whose span meets `[lo, hi]`: `visit(edge, a, b)`.
     */
    segmentsAlong: (orientation, at, clearance, lo, hi, visit) =>
      segmentIndex.along(orientation, at, clearance, lo, hi, ({ edge, version }, a, b) => {
        if (versions.get(edge.id) === version) visit(edge, a, b);
      }),
  };
}

export const otherEnd = (edge, node) => (edge.source === node ? edge.target : edge.source);
export const directionAt = (edge, node) => (edge.source === node ? "out" : "in");
/** A route oriented away from `node`, and back: an edge into the node is read from its target end. */
export const fromNode = (edge, node, points) => (edge.source === node ? points : [...points].reverse());
/** The first `count` points of a route read from `node`'s end, without copying the rest. */
export function headFrom(edge, node, points, count) {
  if (edge.source === node) return points.slice(0, count);
  const head = [];
  for (let i = points.length - 1; i >= 0 && head.length < count; i -= 1) head.push(points[i]);
  return head;
}

/** Whether the segment from `a` to `b` crosses a box `allowed` does not accept. */
export function crossesABox(drawing, a, b, allowed) {
  const x1 = Math.min(a.x, b.x);
  const x2 = Math.max(a.x, b.x);
  const y1 = Math.min(a.y, b.y);
  const y2 = Math.max(a.y, b.y);
  let crosses = false;
  drawing.boxesIn(segmentRect(a, b), (id, r) => {
    if (crosses || allowed(id)) return;
    crosses = x2 > r.x1 + BOX_INSET && x1 < r.x2 - BOX_INSET && y2 > r.y1 + BOX_INSET && y1 < r.y2 - BOX_INSET;
  });
  return crosses;
}

/**
 * Whether the axis-aligned segment from `a` to `b` runs along a segment of an
 * edge `related` does not accept, closer than `clearance` and over more than a unit.
 */
export function runsAlongAnother(drawing, a, b, clearance, related) {
  const orientation = orientationOf(a, b);
  if (!orientation) return false;
  const fixed = orientation === "vertical" ? "x" : "y";
  const moving = orientation === "vertical" ? "y" : "x";
  const lo = Math.min(a[moving], b[moving]);
  const hi = Math.max(a[moving], b[moving]);
  if (hi - lo < OVERLAP) return false;
  let runs = false;
  drawing.segmentsAlong(orientation, a[fixed], clearance, lo, hi, (edge, c, d) => {
    if (runs || related(edge) || Math.abs(c[fixed] - a[fixed]) >= clearance) return;
    runs = Math.min(hi, Math.max(c[moving], d[moving])) - Math.max(lo, Math.min(c[moving], d[moving])) > OVERLAP;
  });
  return runs;
}
