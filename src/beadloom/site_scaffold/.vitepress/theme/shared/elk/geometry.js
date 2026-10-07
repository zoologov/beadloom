// beadloom:component=site-shared
// ELK's answer read as geometry: a box for every node and a route for every edge, in root coordinates.
//
// The graph was laid out with `elk.json.shapeCoords` and `elk.json.edgeCoords`
// set to `ROOT` (`graph.js`), so a box's corner and a section's points are
// already absolute and no parent's offset is added here. The geometry is frozen:
// one layout serves every viewer of the same graph, and none of them may move it.
// The root is ELK's graph, not a node, so it is told apart by where it stands,
// never by its id, which a node of the drawing may share. Both maps are keyed by
// the drawing's ids and have no prototype (`idRecord`), so any id is a key of its own.

import { idRecord } from "../ids/index.js";

const pointOf = ({ x, y }) => Object.freeze({ x, y });

/** A section as the polyline it draws: its start, its bend points, its end. */
function polylineOf(section) {
  const points = [section.startPoint, ...(section.bendPoints || []), section.endPoint];
  return Object.freeze(points.map(pointOf));
}

/** A node's box, its corners. */
function boxOf(shape) {
  return Object.freeze({
    x1: shape.x,
    y1: shape.y,
    x2: shape.x + shape.width,
    y2: shape.y + shape.height,
  });
}

function routeOf(edge) {
  return Object.freeze({
    source: edge.sources[0],
    target: edge.targets[0],
    sections: Object.freeze((edge.sections || []).map(polylineOf)),
  });
}

/**
 * `{ boxes, routes }` of a laid-out ELK graph.
 *
 * `boxes` maps each node's id to `{ x1, y1, x2, y2 }`, its box's corners;
 * `routes` maps each edge's id to `{ source, target, sections }`, where each
 * section is a polyline of `{ x, y }` points from the source's end to the target's.
 */
export function geometryOf(laidOut) {
  const boxes = idRecord();
  const routes = idRecord();
  const visit = (shape) => {
    for (const edge of shape.edges || []) routes[edge.id] = routeOf(edge);
    for (const child of shape.children || []) {
      boxes[child.id] = boxOf(child);
      visit(child);
    }
  };
  visit(laidOut);
  return Object.freeze({ boxes: Object.freeze(boxes), routes: Object.freeze(routes) });
}
