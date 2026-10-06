// beadloom:component=site-graph-viewer
// The lines that draw an edge from a node to a box that holds it: square along its route, never Cytoscape's loop.
//
// Cytoscape draws every edge between a node and one of the boxes that hold it
// as a compound loop: a curve from the node straight across the box to one point
// of its border, whatever the edge's curve style or route. ELK routes such an
// edge like any other, square, from the node to the box's border inside it. So
// each one is drawn by a line of its own, between the node and an **end**: a
// node with no look of its own, outside every box, standing where the route
// meets the border, which Cytoscape joins to the node by segments as it joins
// any two nodes. The edge itself is taken out of the graph for good, and the line
// takes its place: its id, its data — its key, kind and look — and the box it
// ends at (`LOOP_OF`); the end names the box it stands on (`LOOP_BOX`), so a
// filter that hides the box hides the end with it.

import { freshId } from "../../../shared/ids/index.js";
import { LOOP_BOX, LOOP_END, LOOP_OF } from "../lib/levels.js";
import { pathOf, segmentsOf } from "../lib/routes.js";

/**
 * Draw each edge of `cy` that `isLoop` names along its route in `geometry`, by
 * a line to an end on its box's border; `taken` holds every id given, and takes
 * the new ones. Returns `Map(edge id => { line, end })`; an edge with no route
 * is left as it is.
 */
export function loopLines(cy, geometry, { isLoop, taken }) {
  const out = new Map();
  const fresh = (base) => {
    const id = freshId(base, taken);
    taken.add(id);
    return id;
  };
  cy.batch(() => {
    cy.edges()
      .filter(isLoop)
      .forEach((edge) => {
        const route = geometry.routes[edge.id()];
        const path = route ? pathOf(route) : [];
        if (path.length < 2) return;
        // The box is the end that holds the other; the route meets its border at that end.
        const boxIsTarget = edge.source().ancestors().contains(edge.target());
        const box = boxIsTarget ? edge.target() : edge.source();
        const at = boxIsTarget ? path[path.length - 1] : path[0];
        const end = cy.add({ group: "nodes", data: { id: fresh(`loop-end:${edge.id()}`), [LOOP_BOX]: box.id() }, classes: LOOP_END, position: { x: at.x, y: at.y } });
        const [source, target] = boxIsTarget ? [edge.source(), end] : [end, edge.target()];
        const data = { ...edge.data(), source: source.id(), target: target.id(), [LOOP_OF]: box.id() };
        const segments = segmentsOf(path, source.position(), target.position());
        if (segments) data.route = segments;
        else delete data.route;
        const classes = edge.classes();
        // The edge leaves the graph first, so its line takes its id.
        cy.remove(edge);
        const line = cy.add({ group: "edges", data, classes });
        out.set(edge.id(), { line, end });
      });
  });
  return out;
}
