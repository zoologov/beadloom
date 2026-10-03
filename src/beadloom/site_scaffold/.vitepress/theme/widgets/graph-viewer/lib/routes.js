// beadloom:component=site-graph-viewer
// ELK's geometry in the terms Cytoscape draws by: an edge's route as segments, a box's size as a compound's.
//
// Cytoscape draws a `segments` edge from two endpoints, each given relative to
// the centre of its node, through corners each given as a weight along the line
// between the endpoints and a distance off it. ELK gives a route as polylines in
// the graph's coordinates; `segmentsOf` turns one into the other, so the edge is
// drawn exactly where ELK routed it, around every box.
//
// Cytoscape sizes a compound node around its children, plus its padding and
// border, and when a filter hides every child it falls back on its stylesheet
// size where it stands. ELK sized the box with room for its title and its
// edges. `compoundSizeOf` gives the compound ELK's box either way: a minimum
// size, spread around the children as ELK spread them, and the same size as
// its stylesheet size.
//
// Every function here is pure: geometry in, numbers out.

/** A box's centre. */
export function centreOf(box) {
  return { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };
}

/** A route's sections laid end to end as one polyline, without a point repeated where two meet. */
export function pathOf(route) {
  const points = [];
  for (const section of route.sections) {
    for (const point of section) {
      const last = points[points.length - 1];
      if (!last || last.x !== point.x || last.y !== point.y) points.push(point);
    }
  }
  return points;
}

/**
 * The segments Cytoscape draws `path` by, between nodes centred at `sourceCentre`
 * and `targetCentre`: `{ sourceEndpoint, targetEndpoint, weights, distances }`.
 *
 * The endpoints are offsets from their node's centre, `[dx, dy]`; each corner
 * between them is a weight along the line from the first endpoint to the last
 * and a signed distance off it along the line's normal, `(-dy, dx)` for a line
 * of direction `(dx, dy)` (Cytoscape's `edge-distances: endpoints`). A path with no corner gets one at its middle,
 * since a segments edge needs at least one. Null when the path's ends coincide,
 * since no line between them gives a direction.
 */
export function segmentsOf(path, sourceCentre, targetCentre) {
  const start = path[0];
  const end = path[path.length - 1];
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length2 = dx * dx + dy * dy;
  if (path.length < 2 || length2 === 0) return null;
  const length = Math.sqrt(length2);
  const corners = path.length > 2 ? path.slice(1, -1) : [{ x: start.x + dx / 2, y: start.y + dy / 2 }];
  return {
    sourceEndpoint: [start.x - sourceCentre.x, start.y - sourceCentre.y],
    targetEndpoint: [end.x - targetCentre.x, end.y - targetCentre.y],
    weights: corners.map((c) => ((c.x - start.x) * dx + (c.y - start.y) * dy) / length2),
    distances: corners.map((c) => ((c.x - start.x) * -dy + (c.y - start.y) * dx) / length),
  };
}

/**
 * The size that draws a compound node as `box`, ELK's box for it, around its
 * children drawn in `childrenBox`, or around none when it is null: `{ width,
 * height, biasLeft, biasRight, biasTop, biasBottom }`.
 *
 * `inset` is how far inside its drawn edge a compound's children area begins:
 * its padding and half its border, which Cytoscape adds around the size. Width
 * and height are the box less that inset on each side, both a minimum size and
 * the size of a compound with no child drawn; each bias is the room left on
 * that side of the children, which is how Cytoscape spreads a minimum size
 * larger than the children around them.
 */
export function compoundSizeOf(box, childrenBox, inset) {
  const inner = { x1: box.x1 + inset, y1: box.y1 + inset, x2: box.x2 - inset, y2: box.y2 - inset };
  const children = childrenBox || inner;
  return {
    width: Math.max(0, inner.x2 - inner.x1),
    height: Math.max(0, inner.y2 - inner.y1),
    biasLeft: Math.max(0, children.x1 - inner.x1),
    biasRight: Math.max(0, inner.x2 - children.x2),
    biasTop: Math.max(0, children.y1 - inner.y1),
    biasBottom: Math.max(0, inner.y2 - children.y2),
  };
}
