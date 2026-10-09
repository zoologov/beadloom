// beadloom:component=site-overview-map
// The map's own lines: the element that draws each aggregated edge and each node's own line, its route along the medoid, and the data it says.
//
// An aggregated edge is an element of the map's own, made once per pair of drawn
// ends and kept while the page lives. Its id is chosen against every id of the
// graph (`freshId`). Between two top-level nodes its route is the overview's own
// (`overviewPlan.js`), routed afresh between the boxes and kept at every level;
// any other runs along the medoid of its edges' routes between its two boxes
// (`shared/geometry/aggregateRoutes.js`). Either is drawn by the same segments as any routed
// edge; its counts, its arrowheads and its look are in its data, for the
// stylesheet and the pills (`features/edge-pills/model/pillOverlay.js`). A node's own line (`shared/map-levels/levels.js`,
// `ownLinesOf`) is an element of the same kind, along the medoid of its edges'
// drawn routes.
//
// What a line says is how many edges it carries, each way. While a node or a box
// is selected, a line that carries edges of its walk says how many of the walk's
// edges it carries instead (`SAID`), so a node folded into its box by zooming out
// still says its own count on the box's line; its arrowheads still show every
// edge it carries. A line of a node under the pointer or selected says its count
// even when it is one (`OWN_LINE`, `features/edge-pills/model/pillOverlay.js`). Every line drawn into a box
// the overview's plan draws larger than its layout is drawn up to where it enters
// the box (`shared/geometry/grownBoxes.js`, `pathOutside`).

import { freshId } from "../../../shared/ids/index.js";
import { aggregateRouteOf, pathOf, pathOutside, segmentsOf } from "../../../shared/geometry/index.js";
import { AGGREGATE, MAP_SCALE, OWN_LINE, STUB_AT, boxesHolding } from "../../../shared/map-levels/index.js";
import { giveData } from "../../../shared/canvas-marks/index.js";

/** The style key an aggregated edge takes when one of its edges is a violation: it must not be lost. */
const LOUDEST_STYLE = "violation";
/** The data a line carries while it says a selection's walk rather than all it carries: `{ forward, backward }`. */
export const SAID = "said";
/** How the name of a node's own line begins (`shared/map-levels/levels.js`, `ownLinesOf`). */
const OWN_NAME = "own\n";

/** Whether `pair` is a node's own line rather than a line of a level. */
export const isOwnLine = (pair) => pair.name.startsWith(OWN_NAME);

/** `pair` with only the edges `kept` shows, and its weight. */
export function weigh(pair, kept) {
  const forward = pair.forward.filter(kept);
  const backward = pair.backward.filter(kept);
  return { ...pair, forward, backward, weight: forward.length + backward.length };
}

/** How many edges come into each drawn end of `weighed` and go out of it, the ones left out included. */
export function talliesOf(weighed) {
  const tallies = new Map();
  const add = (id, incoming, outgoing) => {
    const now = tallies.get(id) || { incoming: 0, outgoing: 0 };
    tallies.set(id, { incoming: now.incoming + incoming, outgoing: now.outgoing + outgoing });
  };
  for (const pair of weighed) {
    add(pair.ends[0], pair.backward.length, pair.forward.length);
    add(pair.ends[1], pair.forward.length, pair.backward.length);
  }
  return tallies;
}

/** What an aggregated edge's label says: its count each way, the way that has any. */
function countLabelOf(forward, backward) {
  return [forward, backward].filter(Boolean).join(" + ");
}

/** The look an aggregated edge takes: a violation's when one of its edges is one, else its edges' most common. */
function styleKeyOf(edges) {
  const counts = new Map();
  for (const edge of edges) {
    const key = edge.data("styleKey");
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  if (counts.has(LOUDEST_STYLE)) return LOUDEST_STYLE;
  return [...counts].sort((a, b) => b[1] - a[1])[0]?.[0];
}

/**
 * The elements of the map's own lines on `cy`, in the box tree `tree` laid out
 * as `geometry`; `nodes` and `edges` the file's by id, `taken` every id in use,
 * `drawnRouteOf(id)` the route an edge of the file is drawn along, or null:
 * `{ routeOf, elementOf, dress, entryOf, elementOfPair, undrawn }`.
 */
export function aggregateElements(cy, { tree, geometry, nodes, edges, taken, drawnRouteOf }) {
  const aggregates = new Map();
  // The pair each aggregated edge draws, by the edge's id: Cytoscape hands out a new wrapper per lookup.
  const pairOfElement = new Map();
  const routes = new Map();

  /** Whether `id` is a box drawn closed when the boxes `openNow` are open. */
  const isClosed = (id, openNow) => tree.boxes.has(id) && !openNow.has(id);

  /**
   * The medoid of the routes of a pair's edges between its two ends' boxes: the
   * routes ELK gave them for a pair of a level, and the bundled ones they are
   * drawn along for a node's own line, which leaves the node by its bus port. An
   * end at a box drawn `closed` (`{ from, to }`) is entered straight where its
   * edges' routes step across just before its border to a node not drawn
   * (`shared/geometry/aggregateRoutes.js`, `straightenedInto`).
   */
  function computeRoute(pair, closed) {
    const { ends: [a, b], forward, backward } = pair;
    const [from, to] = [geometry.boxes[a], geometry.boxes[b]];
    if (!from || !to) return null;
    const holds = (outer, inner) => boxesHolding(tree, [inner]).has(outer);
    if (holds(a, b) || holds(b, a)) return null;
    const own = isOwnLine(pair);
    const pathFor = (id) => (own ? drawnRouteOf(id) : null) || (geometry.routes[id] ? pathOf(geometry.routes[id]) : null);
    const member = (id, reversed) => ({ path: pathFor(id), reversed });
    return aggregateRouteOf([...forward.map((id) => member(id, false)), ...backward.map((id) => member(id, true))], from, to, closed);
  }

  /**
   * The path of the pair `pair` between its two drawn ends' laid-out boxes, or
   * null, with the boxes `openNow` open; cached by its members and by which of
   * its ends are closed boxes.
   */
  function routeOf(pair, openNow) {
    const closed = { from: isClosed(pair.ends[0], openNow), to: isClosed(pair.ends[1], openNow) };
    const signature = `${pair.name}\n${pair.forward.join(",")}\n${pair.backward.join(",")}\n${closed.from}\n${closed.to}`;
    if (!routes.has(signature)) routes.set(signature, computeRoute(pair, closed));
    return routes.get(signature);
  }

  /** The element that draws `pair`, made the first time the pair is drawn. */
  function elementOf(pair) {
    if (!aggregates.has(pair.name)) {
      const id = freshId(`aggregate:${pair.ends[0]}<->${pair.ends[1]}`, taken);
      taken.add(id);
      const element = cy.add({ group: "edges", data: { id, source: pair.ends[0], target: pair.ends[1], [AGGREGATE]: true } });
      aggregates.set(pair.name, { element, pair });
      pairOfElement.set(id, pair.name);
    }
    const entry = aggregates.get(pair.name);
    entry.pair = pair;
    return entry.element;
  }

  /**
   * Give `element` what `pair` says and its route along `path`, cut where it
   * enters a box of `grownNow` (`id => the box it is drawn as`), at the map's
   * `scale`; `stub` the open box it ends at as a stub, or undefined (`STUB_AT`).
   */
  function dress(element, pair, { path, scale, grownNow, stub }) {
    const members = [...pair.forward, ...pair.backward].map((id) => edges.get(id));
    const said = pair.said || { forward: pair.forward.length, backward: pair.backward.length };
    const data = {
      forward: pair.forward.length,
      backward: pair.backward.length,
      weight: pair.weight,
      countLabel: countLabelOf(said.forward, said.backward),
      saidWeight: said.forward + said.backward,
      [OWN_LINE]: isOwnLine(pair),
      styleKey: styleKeyOf(members),
      [MAP_SCALE]: scale,
    };
    const [a, b] = pair.ends;
    // Drawn up to where it enters an end drawn larger than its layout: on its last run, for a planned line.
    const shown = path && (pathOutside(path, grownNow.get(a) || null, grownNow.get(b) || null) || path);
    const route = shown ? segmentsOf(shown, nodes.get(a).position(), nodes.get(b).position()) : null;
    giveData(element, { ...data, [SAID]: pair.said || undefined, route: route || undefined, [STUB_AT]: stub });
  }

  return {
    routeOf,
    elementOf,
    dress,
    /** The element and the pair it drew last, `{ element, pair }`, of the element whose id is `id`; undefined for any other. */
    entryOf: (id) => aggregates.get(pairOfElement.get(id)),
    /** The element that draws the pair named `name`, once it has been drawn. */
    elementOfPair: (name) => aggregates.get(name)?.element,
    /** The elements of the pairs whose names are not in `drawnNames`. */
    undrawn: (drawnNames) => [...aggregates.values()].filter(({ pair }) => !drawnNames.has(pair.name)).map(({ element }) => element),
  };
}
