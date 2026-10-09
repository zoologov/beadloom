// beadloom:component=site-shared-geometry
// The radius a node's corners are drawn at: one size on screen, a card's at zoom 1, and never over a line's end.
//
// Every node of the architecture, a card or a box, open or closed, is a rounded
// rectangle whose corners keep one radius on screen at every zoom: the radius
// Cytoscape gives a card at zoom 1, the look the overview's boxes share with the
// nodes (owner, 2026-10-07). Before, every shape took Cytoscape's own radius, 8
// layout units, so a box at the overview, a hundred times a card's size and
// drawn at a twentieth of its zoom, had corners half a pixel round and read
// square. A shape smaller than four times the radius takes a quarter of its
// shorter side, Cytoscape's own clamp for its `auto` radius.
//
// A corner never rounds off under a line's end. A line ends on its node's
// border; inside a rounded corner the border it was routed to is not drawn, so
// the line would stop in the air beside the arc. Where a line's end lies nearer
// a corner than the radius, measured along the border, the node's corners take
// the room that end leaves. The overview's router keeps its ports clear of the
// radius at the scale it plans at (`shared/grid-routing/overviewGrid.js`, `sideRange`), so at the
// overview a box is held at most a pixel smaller, where a small box's radius
// reaches that little past the ports it always had; zoomed out past the plan, a
// port may lie inside the larger arc and hold its box. At full detail ELK starts
// a few lines near a corner: on this portal, lines from a node to a box that
// holds it.
//
// Everything here is pure, in layout units unless a name says pixels.

/** The radius every node's corners are drawn at, in pixels on screen: Cytoscape's `auto` radius for a rounded rectangle, a card's at zoom 1. */
export const NODE_CORNER_PX = 8;

/** The data a drawn node carries: the radius its corners are drawn at, in layout units. */
export const CORNER = "corner";

/** The radius of the corners of a shape `width` by `height` at the map's `scale`, held to `room`. */
export function cornerRadiusOf(width, height, scale, room = Infinity) {
  return Math.max(0, Math.min(NODE_CORNER_PX * scale, width / 4, height / 4, room));
}

/**
 * The room a line's end at `point` leaves the corners of the shape `shape`:
 * `{ x, y }` its centre, `outerWidth` and `outerHeight` its size with what of its
 * border is drawn outside it, `width` and `height` its size. A corner's arc on the
 * border's outer edge reaches as far along it as the radius and that border
 * more, so the room is the end's distance along the border from the nearer
 * corner, less that border. Infinity where the end does not lie on the border,
 * within `tolerance`.
 */
export function cornerRoomOf(point, shape, tolerance) {
  const halfWidth = shape.outerWidth / 2;
  const halfHeight = shape.outerHeight / 2;
  const fromSide = halfWidth - Math.abs(point.x - shape.x);
  const fromTopOrBottom = halfHeight - Math.abs(point.y - shape.y);
  if (fromSide < -tolerance || fromTopOrBottom < -tolerance || Math.min(fromSide, fromTopOrBottom) > tolerance) return Infinity;
  const rim = Math.min((shape.outerWidth - shape.width) / 2, (shape.outerHeight - shape.height) / 2);
  return Math.max(fromSide, fromTopOrBottom) - Math.max(0, rim);
}
