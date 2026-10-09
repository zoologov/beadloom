// beadloom:component=site-graph-viewer
// The corners of the drawn nodes: the radius each is drawn at for the map's scale, held where a line ends near one.
//
// The rule is `shared/geometry/corners.js`'s; this reads what it needs off the canvas, its
// sizes from the data (`drawnSizeOf`), so it can run in the batch a level is
// drawn in. Each time a level is drawn, every line's two ends are found where
// its route meets a node's border, and each node keeps the room the end nearest
// one of its corners leaves. A node's radius is given to it in its data (`CORNER`), worked
// out again at each step of the map's scale, and written only where it changed,
// so a zoom step restyles no card whose corners stay as they were.

import { CORNER, cornerRadiusOf, cornerRoomOf } from "../../../shared/geometry/index.js";
import { LOOP_END, LOOP_OF, drawnSizeOf, rimOf } from "../../../shared/map-levels/index.js";

/** How far a line's end may lie off a node's border and still be on it, in pixels on screen. */
const ON_BORDER_PX = 0.5;

/**
 * Drawn node `node` as `cornerRoomOf` reads it: its centre, and its size with and
 * without its border, from its data (`drawnSizeOf`): inside a batch, Cytoscape's
 * own sizes still trail the data just given.
 */
function shapeOf(node) {
  const { x, y } = node.position();
  const { width, height } = drawnSizeOf(node);
  const rim = rimOf(node);
  return { x, y, width, height, outerWidth: width + 2 * rim, outerHeight: height + 2 * rim };
}

/**
 * The nodes an end of `edge`, at its node `end`, may meet the border of: the box
 * a loop's end stands on, or the node and every box that holds it, which a line
 * into an open box ends on as its stub.
 */
function ownersOf(edge, end) {
  if (end.hasClass(LOOP_END)) return [edge.cy().getElementById(edge.data(LOOP_OF))].filter((box) => box.nonempty());
  const owners = [];
  for (let node = end; node.nonempty(); node = node.parent()) owners.push(node);
  return owners;
}

/** The corners of the nodes drawn on `cy`: `measure` once a level is drawn, then `dress` each drawn node. */
export function nodeCorners(cy) {
  let rooms = new Map();
  return {
    /** Find again, at the map's `scale`, the room every line's ends leave the corners of the nodes they meet. */
    measure(scale) {
      rooms = new Map();
      const tolerance = ON_BORDER_PX * scale;
      cy.edges().forEach((edge) => {
        const route = edge.data("route");
        if (!route) return;
        const ends = [
          [edge.source(), route.sourceEndpoint],
          [edge.target(), route.targetEndpoint],
        ];
        for (const [end, [dx, dy]] of ends) {
          const at = end.position();
          const point = { x: at.x + dx, y: at.y + dy };
          for (const owner of ownersOf(edge, end)) {
            const room = cornerRoomOf(point, shapeOf(owner), tolerance);
            if (room < (rooms.get(owner.id()) ?? Infinity)) rooms.set(owner.id(), room);
          }
        }
      });
    },
    /** Give drawn node `node` the radius its corners are drawn at, at `scale`, where it changed. */
    dress(node, scale) {
      const { width, height } = drawnSizeOf(node);
      const radius = cornerRadiusOf(width, height, scale, rooms.get(node.id()));
      if (node.data(CORNER) !== radius) node.data(CORNER, radius);
    },
  };
}
