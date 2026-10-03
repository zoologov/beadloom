// beadloom:component=site-graph-viewer
// What the bundles draw over the canvas: a dot where routes part, and every edge along a hovered line.
//
// A trunk or a bus draws several edges along one line. Cytoscape draws each of
// them whole, so two things a reader needs are not in its drawing: where one
// edge leaves the others, and which edges a shared line carries.
//
// - A **junction dot** marks each point where drawn routes part
//   (`lib/junctions.js`). The dots are found for the edges drawn now: a filter or
//   a hidden neighbourhood that removes one branch removes its dot. They are
//   drawn on a canvas of their own above Cytoscape's (`overlayCanvas.js`),
//   redrawn whenever Cytoscape renders, in the colour of the strongest edge through them, so a dot outside a
//   selection fades with its edges.
// - **The edges along a hovered line**: Cytoscape reports the one edge under the
//   pointer, which on a trunk is whichever member it drew last. Every drawn edge
//   that runs through the hovered point along the same line is the answer
//   instead (`routesAlong`).

import { junctionsOf, routeIndexOf, routesAlong } from "../lib/junctions.js";
import { overlayCanvas } from "./overlayCanvas.js";

/** A junction dot's radius, in layout units: wider than the widest edge it sits on. */
export const JUNCTION_RADIUS = 3.6;
/** The smallest radius on screen a dot is still drawn at, in pixels: below it the dots are noise. */
const SMALLEST_DOT = 1;

/** The colour of the strongest edge among `ids`: an edge outside a selection is drawn faded. */
function colourOf(cy, ids) {
  const edges = ids.map((id) => cy.getElementById(id)).filter((edge) => edge.nonempty());
  const strongest = edges.find((edge) => !edge.hasClass("is-dimmed")) || edges[0];
  return strongest ? strongest.style("line-color") : null;
}

/**
 * The overlay of `cy` in `container` for the routes in `paths` (edge id to its
 * drawn polyline): `{ refresh, along, junctions, destroy }`.
 *
 * `refresh()` finds the junctions of the edges drawn now and recolours them;
 * call it whenever a filter, a selection or the theme changes. `along(id, point)`
 * gives the ids of the drawn edges that run along edge `id` at `point`, in graph
 * coordinates. `junctions()` gives `[{ x, y, edges }]`.
 */
export function bundleOverlay(cy, container, paths) {
  const layer = overlayCanvas(container, "junctions");
  let drawnIds = "";
  let index = routeIndexOf([]);
  let found = [];
  let dots = [];

  function draw() {
    const context = layer.begin();
    const zoom = cy.zoom();
    if (!dots.length || JUNCTION_RADIUS * zoom < SMALLEST_DOT) return;
    layer.inGraph(cy);
    const extent = cy.extent();
    for (const dot of dots) {
      if (dot.x < extent.x1 || dot.x > extent.x2 || dot.y < extent.y1 || dot.y > extent.y2) continue;
      context.fillStyle = dot.colour;
      context.beginPath();
      context.arc(dot.x, dot.y, JUNCTION_RADIUS, 0, 2 * Math.PI);
      context.fill();
      layer.drew();
    }
  }

  function refresh() {
    const drawn = cy.edges().filter((edge) => paths[edge.id()] && edge.visible());
    const ids = drawn.map((edge) => edge.id()).join("\n");
    if (ids !== drawnIds) {
      drawnIds = ids;
      const routes = drawn.map((edge) => ({ id: edge.id(), points: paths[edge.id()] }));
      index = routeIndexOf(routes);
      found = junctionsOf(routes);
    }
    dots = found.map((junction) => ({ ...junction, colour: colourOf(cy, junction.edges) })).filter((dot) => dot.colour);
    draw();
  }

  function along(id, point) {
    const points = paths[id];
    return points ? routesAlong(index, { id, points }, point) : [id];
  }

  cy.on("render", draw);
  return {
    refresh,
    along,
    junctions: () => found.map(({ x, y, edges }) => ({ x, y, edges: [...edges] })),
    destroy() {
      cy.removeListener("render", draw);
      layer.remove();
    },
  };
}
