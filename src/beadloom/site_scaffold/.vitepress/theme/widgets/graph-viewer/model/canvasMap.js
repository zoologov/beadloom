// beadloom:component=site-graph-viewer
// The map drawn on the canvas: boxes opened and closed, aggregated edges, the budget and the map's marks.
//
// The levels are decided in `lib/levels.js`; this is what they do to Cytoscape.
// A closed box keeps its place and its size, ELK's, and its children are taken
// out of the graph with `cy.remove` and put back with `restore`: elements hidden
// with `display: none` stay in the graph, and Cytoscape keeps spending time on
// them every frame. The same element is put back, so it comes back with
// everything it had, where it was.
//
// An aggregated edge is an element of the map's own, made once per pair of drawn
// ends and kept while the page lives. Its id is chosen against every id of the
// graph (`freshId`). Between two top-level nodes its route is the overview's own
// (`overviewPlan.js`), routed afresh between the boxes and kept at every level;
// any other runs along the medoid of its edges' routes between its two boxes
// (`lib/aggregateRoutes.js`). Either is drawn by the same segments as any routed
// edge; its counts, its arrowheads and its look are in its data, for the
// stylesheet and the pills (`pillOverlay.js`). An aggregated edge the budget
// leaves out is taken out of the graph as well, and each end it would join
// carries the count (`hiddenEdges`); while the pointer is on an end, or the end
// is selected, all of its edges are drawn. A closed box carries how many edges
// come into it and go out of it (`tally`), the ones left out included.
//
// What a box or a line says on screen — every line's weight, arrowheads and
// corners, a closed box's title and a top-level node's — keeps one size on
// screen whatever the zoom: each carries the map's scale in its data, a power of
// 1.25 near 1 / zoom, and the stylesheet multiplies by it, so a zoom gesture
// restyles these elements only when the zoom crosses a step. An edge out of the
// graph is given the scale too, so it comes back at the size of the rest. A
// title is tried at a few sizes inside its box and otherwise stands above it on
// a plate (`lib/mapMarks.js`); which, is in the node's data (`mapTitle`), worked
// out again at each step of the scale. A top-level node that is not a box takes
// the map's title only while its own label would read smaller.
//
// Which boxes are open follows the view: on every change of the viewport, once
// per frame at most, the boxes in view are worked out again, and when they differ
// the canvas is told to draw the level again (`onLevel`).

import { freshId } from "../../../shared/ids/index.js";
import { aggregateRouteOf } from "../lib/aggregateRoutes.js";
import {
  AGGREGATE,
  COLLAPSED,
  HIDDEN_EDGES,
  LEVEL_OPTIONS,
  MAP_SCALE,
  boxTreeOf,
  boxesHolding,
  boxesRevealing,
  budgetOf,
  holdersOf,
  levelOf,
  openInView,
} from "../lib/levels.js";
import { MAP_TITLE, TALLY, mapTitleOf, statusMarkInsetOf, statusMarkOf } from "../lib/mapMarks.js";
import { routePointsOf } from "../lib/lineMarks.js";
import { pathOf, segmentsOf } from "../lib/routes.js";
import { GEOMETRY } from "../lib/stylesheet.js";
import { overviewPlanner } from "./overviewPlan.js";

/** The zoom step the map's marks are restyled at. */
export const SCALE_STEP = 1.25;
/** The style key an aggregated edge takes when one of its edges is a violation: it must not be lost. */
const LOUDEST_STYLE = "violation";

const sameSet = (a, b) => a.size === b.size && [...a].every((id) => b.has(id));

/** The map's scale at `zoom`: the power of `SCALE_STEP` nearest 1 / zoom. */
export function scaleAt(zoom) {
  return SCALE_STEP ** Math.round(Math.log(1 / zoom) / Math.log(SCALE_STEP));
}

/** A title's width in pixels at a size, measured in the font `cy`'s nodes are drawn in, bold. */
function titleMeasurer(cy) {
  const context = typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  return (text, px) => {
    if (!context) return String(text).length * px * 0.62;
    context.font = `700 ${px}px ${cy.nodes().first().style("font-family")}`;
    return context.measureText(String(text)).width;
  };
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
 * The map over `cy`, drawn as `geometry` lays it out: `{ apply, evaluate,
 * reveal, setShown, setExempt, aggregates, openBoxes, collapsedBoxes, allNodes,
 * isAggregate, keysOf, scale, fitZoom, destroy }`.
 *
 * `fitZoom()` gives the zoom of the whole-graph fit now; `onLevel()` is called
 * when the view opens or closes a box, and is expected to call `apply`. Nothing
 * is drawn differently until the first `apply`.
 */
export function canvasMap(cy, geometry, { fitZoom, onLevel, options = LEVEL_OPTIONS }) {
  const tree = boxTreeOf(cy.nodes().map((node) => ({ id: node.id(), parent: node.isChild() ? node.parent().id() : null })));
  const nodes = new Map(cy.nodes().map((node) => [node.id(), node]));
  const edges = new Map(cy.edges().map((edge) => [edge.id(), edge]));
  const taken = new Set([...nodes.keys(), ...edges.keys()]);
  const plainEdges = [...edges.values()].map((edge) => ({ id: edge.id(), source: edge.data("source"), target: edge.data("target") }));
  const aggregates = new Map();
  // The pair each aggregated edge draws, by the edge's id: Cytoscape hands out a new wrapper per lookup.
  const pairOfElement = new Map();
  const routes = new Map();
  const reveals = new Map();
  const exempt = new Map();
  let shown = () => true;
  let inView = new Set();
  let open = new Set();
  let pairs = [];
  let scale = scaleAt(cy.zoom());
  let queued = false;
  let destroyed = false;
  let version = 0;
  let hiddenAt = new Map();
  const measure = titleMeasurer(cy);
  const planner = overviewPlanner(cy, {
    tree,
    geometry,
    plainEdges,
    routePointsOf: (id) => (edges.get(id)?.data("route") ? routePointsOf(edges.get(id)) : null),
    titleOf: (id, at, hidden) => titleLookOf(id, at, hidden),
    measure,
    scaleAt,
    budget: options.budget,
  });

  /** The title node `id` is drawn with at `at` when `hidden` of its lines are left out, or null for its own label. */
  function titleLookOf(id, at, hidden) {
    const node = nodes.get(id);
    const box = geometry.boxes[id];
    if (!node || !box) return null;
    const isBox = tree.boxes.has(id);
    const size = { width: box.x2 - box.x1, height: box.y2 - box.y1 };
    const marked = Boolean(node.data("status"));
    const reserved = !marked ? 0 : isBox ? statusMarkOf(at, size.height) + statusMarkInsetOf(at, size.height) : GEOMETRY.statusMark + GEOMETRY.statusMarkInset;
    const lines = [String(node.data("label")), ...(hidden ? [`+${hidden}`] : [])];
    return mapTitleOf(lines, size, at, measure, { reserved, natural: isBox ? null : GEOMETRY.nodeTitle });
  }

  /** Give the drawn node `node` the title it is drawn with now: a closed box's, or a top-level node's while it reads larger. */
  function dressTitle(node) {
    const id = node.id();
    const mapped = node.hasClass(COLLAPSED) || (planner.isTop(id) && !tree.boxes.has(id));
    const title = mapped ? titleLookOf(id, scale, hiddenAt.get(id) || 0) : null;
    if (title) node.data({ [MAP_TITLE]: { ...title, side: planner.plateSideOf(id) }, [MAP_SCALE]: scale });
    else node.removeData(MAP_TITLE);
  }

  /** Whether `id` is one of `ids` or inside one: a box's edges are those of everything in it. */
  function isWithin(id, ids) {
    return ids.has(id) || holdersOf(tree, id).some((box) => ids.has(box));
  }

  function wanted() {
    const next = new Set(inView);
    for (const boxes of reveals.values()) for (const box of boxes) next.add(box);
    if (tree.wrapper) next.add(tree.wrapper);
    return next;
  }

  /** The route of the pair `pair` between its two drawn ends, or null; cached by its members. */
  function routeOf(pair) {
    const signature = `${pair.name}\n${pair.forward.join(",")}\n${pair.backward.join(",")}`;
    if (!routes.has(signature)) routes.set(signature, computeRoute(pair));
    return routes.get(signature);
  }

  function computeRoute({ ends: [a, b], forward, backward }) {
    const [from, to] = [geometry.boxes[a], geometry.boxes[b]];
    if (!from || !to) return null;
    const holds = (outer, inner) => boxesHolding(tree, [inner]).has(outer);
    if (holds(a, b) || holds(b, a)) return null;
    const member = (id, reversed) => ({ path: geometry.routes[id] ? pathOf(geometry.routes[id]) : null, reversed });
    const path = aggregateRouteOf([...forward.map((id) => member(id, false)), ...backward.map((id) => member(id, true))], from, to);
    return path ? segmentsOf(path, nodes.get(a).position(), nodes.get(b).position()) : null;
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

  function dress(element, pair) {
    const members = [...pair.forward, ...pair.backward].map((id) => edges.get(id));
    const data = {
      forward: pair.forward.length,
      backward: pair.backward.length,
      weight: pair.weight,
      countLabel: countLabelOf(pair.forward.length, pair.backward.length),
      styleKey: styleKeyOf(members),
      [MAP_SCALE]: scale,
    };
    const planned = planner.routeOf(pair);
    const at = (id) => nodes.get(id).position();
    const route = planned ? segmentsOf(planned, at(pair.ends[0]), at(pair.ends[1])) : routeOf(pair);
    element.data(data);
    if (route) element.data("route", route);
    else element.removeData("route");
  }

  /** Take `elements` out of the graph, those still in it. */
  const takeOut = (elements) => cy.remove(cy.collection(elements.filter((element) => element.inside())));
  /** Put `elements` back, those out of it, holders before what they hold. */
  function putBack(elements) {
    const out = elements.filter((element) => element.removed());
    out.sort((x, y) => (tree.depth.get(x.id()) ?? 0) - (tree.depth.get(y.id()) ?? 0));
    if (out.length) cy.collection(out).restore();
  }

  /** Draw the level wanted now: the boxes open by the view and by every reveal. */
  function apply() {
    const nextOpen = wanted();
    const level = levelOf(tree, nextOpen, plainEdges);
    // An edge the filters hide is drawn as itself and marked hidden, as ever; an
    // aggregated edge carries only the edges they show.
    const kept = (id) => shown(edges.get(id));
    const weighed = [...level.pairs.values()]
      .map((pair) => ({ ...pair, forward: pair.forward.filter(kept), backward: pair.backward.filter(kept) }))
      .map((pair) => ({ ...pair, weight: pair.forward.length + pair.backward.length }))
      .filter((pair) => pair.weight > 0);
    const leftOut = budgetOf(weighed, options.budget);
    const free = new Set([...exempt.values()].filter(Boolean));
    for (const pair of weighed) {
      pair.overBudget = leftOut.has(pair.name);
      pair.hidden = pair.overBudget && !pair.ends.some((end) => isWithin(end, free));
    }
    hiddenAt = new Map();
    for (const pair of weighed.filter((p) => p.hidden)) for (const end of pair.ends) hiddenAt.set(end, (hiddenAt.get(end) || 0) + 1);
    const tallies = talliesOf(weighed);
    planner.current(kept);
    const drawnPairs = new Set(weighed.filter((pair) => !pair.hidden).map((pair) => pair.name));
    const originals = new Set(level.originals);

    cy.batch(() => {
      takeOut([...aggregates.values()].filter(({ pair }) => !drawnPairs.has(pair.name)).map(({ element }) => element));
      takeOut([...edges.values()].filter((edge) => !originals.has(edge.id())));
      takeOut([...nodes.values()].filter((node) => !level.nodes.has(node.id())));
      putBack([...level.nodes].map((id) => nodes.get(id)));
      putBack([...originals].map((id) => edges.get(id)));
      const drawn = weighed.filter((pair) => !pair.hidden).map((pair) => {
        const element = elementOf(pair);
        dress(element, pair);
        return element;
      });
      putBack(drawn);
      for (const edge of edges.values()) if (edge.data(MAP_SCALE) !== scale) edge.data(MAP_SCALE, scale);
      for (const id of level.nodes) {
        const node = nodes.get(id);
        node.toggleClass(COLLAPSED, tree.boxes.has(id) && !nextOpen.has(id));
        if (hiddenAt.has(id)) node.data({ [HIDDEN_EDGES]: hiddenAt.get(id), [MAP_SCALE]: scale });
        else node.removeData(HIDDEN_EDGES);
        if (node.hasClass(COLLAPSED)) node.data(MAP_SCALE, scale);
        // A box no line comes into or goes out of has nothing to say.
        if (node.hasClass(COLLAPSED) && tallies.has(id)) node.data(TALLY, tallies.get(id));
        else node.removeData(TALLY);
        dressTitle(node);
      }
    });
    open = nextOpen;
    pairs = weighed;
    version += 1;
  }

  /** How many edges come into each drawn end of `weighed` and go out of it, the ones left out included. */
  function talliesOf(weighed) {
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

  /** Restyle the map's marks when the zoom has crossed a step. */
  function rescale() {
    const next = scaleAt(cy.zoom());
    if (next === scale) return;
    scale = next;
    cy.batch(() => {
      cy.elements(`.${COLLAPSED}, edge[${AGGREGATE}], node[${HIDDEN_EDGES}]`).data(MAP_SCALE, scale);
      for (const edge of edges.values()) edge.data(MAP_SCALE, scale);
      cy.nodes().forEach(dressTitle);
    });
    version += 1;
  }

  /** Work out the boxes in view again, and have the level drawn again when they differ. */
  function evaluate() {
    if (destroyed) return;
    rescale();
    const view = { zoom: cy.zoom(), fitZoom: fitZoom(), extent: cy.extent() };
    const next = openInView(tree, geometry.boxes, open, view, options);
    if (sameSet(next, inView)) return;
    inView = next;
    onLevel();
  }

  function onViewport() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      evaluate();
    });
  }
  cy.on("viewport", onViewport);

  return {
    tree,
    apply,
    evaluate: onViewport,
    /**
     * Draw each node of `ids` as itself with its own edges, for `source`: every
     * box that holds one open, and each one that is a box; an empty list lets them close.
     */
    reveal(source, ids) {
      reveals.set(source, boxesRevealing(tree, ids || []));
    },
    /** Have an aggregated edge carry only the edges `predicate` keeps: the ones the filters show. */
    setShown(predicate) {
      shown = predicate;
    },
    /**
     * Draw every edge of the node `id`, and of everything inside it, for `source`
     * (the pointer, the selection), whatever the budget; null releases it. True
     * when the drawing changes. The root that holds everything exempts nothing:
     * its edges are every edge, and the pointer rests on it wherever it is on no
     * other node, so it would lift the budget at the overview.
     */
    setExempt(source, id) {
      const before = exempt.get(source) || null;
      const after = id && id !== tree.wrapper ? id : null;
      exempt.set(source, after);
      if (before === after) return false;
      const weakAt = (id) => id !== null && pairs.some((pair) => pair.overBudget && pair.ends.some((end) => isWithin(end, new Set([id]))));
      return weakAt(before) || weakAt(after);
    },
    /** Every pair of the level drawn now: `[{ element, pair }]`, `pair.hidden` when the budget leaves it out. */
    aggregates: () => pairs.map((pair) => ({ element: aggregates.get(pair.name)?.element, pair })),
    openBoxes: () => [...open].filter((id) => tree.boxes.has(id) && nodes.get(id).inside()).sort(),
    collapsedBoxes: () => cy.nodes(`.${COLLAPSED}`),
    allNodes: () => [...nodes.values()],
    isAggregate: (edge) => Boolean(edge.data(AGGREGATE)),
    /** The keys of the edges an aggregated edge carries. */
    keysOf(element) {
      const entry = aggregates.get(pairOfElement.get(element.id()));
      if (!entry) return [];
      return [...entry.pair.forward, ...entry.pair.backward].map((id) => edges.get(id).data("key"));
    },
    keysEachWay(pair) {
      const keyOf = (id) => edges.get(id).data("key");
      return { forward: pair.forward.map(keyOf), backward: pair.backward.map(keyOf) };
    },
    scale: () => scale,
    /** A number that changes whenever what the map draws or the scale it draws at changes. */
    version: () => version,
    /** What the overview's last plan was (`overviewPlan.js`): `{ ms, unit, routed, failed }`. */
    plan: () => planner.report(),
    fitZoom,
    destroy() {
      destroyed = true;
      cy.removeListener("viewport", onViewport);
    },
  };
}
