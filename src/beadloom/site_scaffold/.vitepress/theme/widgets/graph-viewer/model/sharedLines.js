// beadloom:component=site-graph-viewer
// The lines drawn now that share a run: the edges along a hovered line, and one arrowhead where lines share their last run.
//
// A trunk or a bus draws several edges along one line. Cytoscape draws each of
// them whole, so two things a reader needs are not in its drawing:
//
// - **The edges along a hovered line**: Cytoscape reports the one edge under the
//   pointer, which on a trunk is whichever member it drew last. Every drawn edge
//   that runs through the hovered point along the same line is the answer
//   instead (`lib/routeIndex.js`, `routesAlong`).
// - **One arrowhead per shared last run**: lines that reach one end along one run
//   would each draw a head there, on top of each other. Every line but one drops
//   its head, by a class the stylesheet reads (`lib/heads.js`); a line that
//   reaches the end on its own keeps its own.
//
// Both are found for the lines drawn now, aggregated edges of the map included:
// a filter, a hidden neighbourhood or a level that removes a line gives its
// arrowhead back to the line that remains.

import { droppedHeadsOf, headEndsOf, NO_SOURCE_HEAD, NO_TARGET_HEAD } from "../lib/heads.js";
import { routePointsOf } from "../lib/lineMarks.js";
import { routeIndexOf, routesAlong } from "../lib/routeIndex.js";

/** The ends of the routed `edge` that carry an arrowhead, each with where it ends and where its last run starts. */
function headedEndsOf(edge) {
  const points = routePointsOf(edge);
  const n = points.length;
  const heads = headEndsOf(edge);
  const ends = [];
  const styleKey = edge.data("styleKey");
  if (heads.target) ends.push({ id: edge.id(), end: "target", tip: points[n - 1], before: points[n - 2], styleKey });
  if (heads.source) ends.push({ id: edge.id(), end: "source", tip: points[0], before: points[1], styleKey });
  return ends;
}

/**
 * The shared lines of `cy` for the routes in `paths` (edge id to its drawn
 * polyline): `{ refresh, along, droppedHeads }`.
 *
 * `refresh()` reads the lines drawn now again and gives each shared last run
 * one arrowhead; call it whenever a filter, a selection or a level changes what
 * is drawn. `along(id, point)` gives the ids of the drawn edges that run along
 * edge `id` at `point`, in graph coordinates. `droppedHeads()` gives the ends that
 * draw no head, `[{ id, end }]`.
 */
export function sharedLines(cy, paths) {
  let drawnIds = "";
  let index = routeIndexOf([]);
  let dropped = new Set();

  function refresh() {
    const drawn = cy.edges().filter((edge) => edge.visible());
    const routed = drawn.filter((edge) => paths[edge.id()]);
    const ids = routed.map((edge) => edge.id()).join("\n");
    if (ids !== drawnIds) {
      drawnIds = ids;
      index = routeIndexOf(routed.map((edge) => ({ id: edge.id(), points: paths[edge.id()] })));
    }
    dropped = droppedHeadsOf(drawn.filter((edge) => edge.data("route")).flatMap(headedEndsOf));
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        edge.toggleClass(NO_TARGET_HEAD, dropped.has(`${edge.id()}\ntarget`));
        edge.toggleClass(NO_SOURCE_HEAD, dropped.has(`${edge.id()}\nsource`));
      });
    });
  }

  function along(id, point) {
    const points = paths[id];
    return points ? routesAlong(index, { id, points }, point) : [id];
  }

  return {
    refresh,
    along,
    droppedHeads: () =>
      [...dropped].map((key) => {
        const cut = key.lastIndexOf("\n");
        return { id: key.slice(0, cut), end: key.slice(cut + 1) };
      }),
  };
}
