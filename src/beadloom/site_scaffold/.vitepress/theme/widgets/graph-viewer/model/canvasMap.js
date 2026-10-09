// beadloom:component=site-graph-viewer
// The map drawn on the canvas: which boxes are open and closed, and the level they make drawn on Cytoscape.
//
// The levels are decided in `lib/levels.js`; this is what they do to Cytoscape.
// A closed box keeps its place and its size, ELK's, and its children are taken
// out of the graph with `cy.remove` and put back with `restore`: elements hidden
// with `display: none` stay in the graph, and Cytoscape keeps spending time on
// them every frame. The same element is put back, so it comes back with
// everything it had, where it was.
//
// The pairs of drawn ends a level holds are drawn as aggregated edges, elements
// of the map's own (`aggregateElements.js`). An aggregated edge the budget
// leaves out is taken out of the graph as well, and each end it would join
// carries the count (`hiddenEdges`); while the pointer is on an end, or the end
// is selected, all of its edges are drawn. A closed box carries how many edges
// come into it and go out of it (`tally`), the ones left out included. What the
// pointer, a selection and the test handle draw besides — a node's own lines,
// edges as themselves, stubs, a walk's counts — is `mapExtras.js`'s; an edge
// from a node to a box that holds it is drawn by a line of its own along its
// route (`loopLines.js`).
//
// The map's marks keep one size on screen at a scale stepped with the zoom, and
// the titles and boxes drawn larger than their layout are dressed at it
// (`mapTitles.js`), every node's corners too (`nodeCorners.js`). An edge out of
// the graph is given the scale when it is put back, so it comes back at the size
// of the rest: Cytoscape restyles an element out of the graph as it does one in
// it, and giving every edge of the file the scale at each step restyled them
// all.
//
// Which boxes are open follows the view: on every change of the viewport, once
// per frame at most and not while the view is animated, the readable boxes in
// view and those a selection or a search needs are worked out again, and when
// they differ the canvas is told to draw the level again (`onLevel`). A box the
// test handle reveals is open at any zoom: the one way to force it. A selected box
// is open at any zoom too, the box being what the reader asked to see — but not a
// box holding the boxes a layer rule draws (`LAYER_BOX`): a closed box's title
// keeps one size on screen, so layer boxes drawn smaller than their parts are
// readable at would stand their titles on plates over each other. Such a box
// opens where they are readable, selected or not, as a reader's zoom opens any box.

import {
  AGGREGATE,
  COLLAPSED,
  HIDDEN_EDGES,
  LAYER_BOX,
  LEVEL_OPTIONS,
  MAP_SCALE,
  PROJECT_BOX,
  boxTreeOf,
  boxesRevealing,
  budgetOf,
  isWithinAny,
  levelOf,
  openInView,
  outwardOf,
  smallestChildOf,
  zoomDrawingOf,
} from "../lib/levels.js";
import { STUB_AT } from "../lib/heads.js";
import { OUTWARD, TALLY } from "../lib/mapMarks.js";
import { routePointsOf } from "../lib/lineMarks.js";
import { aggregateElements, isOwnLine, talliesOf, weigh } from "./aggregateElements.js";
import { isLoop } from "./canvasLayout.js";
import { giveData, setClass } from "./canvasMarks.js";
import { loopLines } from "./loopLines.js";
import { FORCED, mapExtras } from "./mapExtras.js";
import { scaleAt, titleDresser, titleLooks } from "./mapTitles.js";
import { nodeCorners } from "./nodeCorners.js";
import { overviewPlanner } from "./overviewPlan.js";

const sameSet = (a, b) => a.size === b.size && [...a].every((id) => b.has(id));

/**
 * The map over `cy`, drawn as `geometry` lays it out: `{ apply, evaluate,
 * reveal, expose, setWalk, setShown, setExempt, aggregates, ownLines,
 * openBoxes, collapsedBoxes, allNodes, isAggregate, keysOf, scale, fitZoom,
 * zoomDrawing, pending, destroy }`.
 *
 * `fitZoom({ drawing })` gives the zoom of the whole-graph fit now, which may be
 * measured once per `drawing`, a token the map changes whenever it draws a level
 * or the filters change, and never for a zoom or a pan alone; `onLevel()` is called
 * when the view opens or closes a box, and is expected to call `apply`;
 * `onRescale()` when the scale stepped and nothing else changed. Nothing is
 * drawn differently until the first `apply`.
 */
export function canvasMap(cy, geometry, { fitZoom, onLevel, onRescale = () => {}, options = LEVEL_OPTIONS }) {
  const tree = boxTreeOf(cy.nodes().map((node) => ({ id: node.id(), parent: node.isChild() ? node.parent().id() : null })));
  const nodes = new Map(cy.nodes().map((node) => [node.id(), node]));
  const edges = new Map(cy.edges().map((edge) => [edge.id(), edge]));
  const taken = new Set([...nodes.keys(), ...edges.keys()]);
  const plainEdges = [...edges.values()].map((edge) => ({ id: edge.id(), source: edge.data("source"), target: edge.data("target") }));
  const edgeById = new Map(plainEdges.map((edge) => [edge.id, edge]));
  const byKey = new Map([...edges.values()].map((edge) => [edge.data("key"), edge.id()]));
  // An edge from a node to a box that holds it is drawn by a line of its own, to an end on the box's border.
  const loops = loopLines(cy, geometry, { isLoop, taken });
  /** The elements that draw the edge `id` of the file: its loop's end and line, or the edge. */
  const drawingOf = (id) => (loops.has(id) ? [loops.get(id).end, loops.get(id).line] : [edges.get(id)]);
  /** The line that draws the edge `id` of the file. */
  const lineOf = (id) => loops.get(id)?.line ?? edges.get(id);
  // The edge of the file each loop's end stands for, by the end's id.
  const loopEdgeOfEnd = new Map([...loops].map(([id, { end }]) => [end.id(), id]));
  const smallest = smallestChildOf(tree, geometry.boxes);
  // The boxes that hold the boxes a layer rule draws: they open only where those are readable.
  const layered = new Set(cy.nodes().filter((node) => node.data(LAYER_BOX) && node.isChild()).map((node) => node.parent().id()));
  const reveals = new Map();
  const exempt = new Map();
  let shown = () => true;
  // How many times the filters have changed, and the level last worked out (`levelNow`).
  let shownVersion = 0;
  let levelCache = { key: null };
  let open = new Set();
  let pairs = [];
  let ownPairs = [];
  // The edges of the file a line other than their box's draws now: as themselves, or on a node's own line.
  let drawnElsewhere = new Set();
  // The lines that end as a stub at an open box, and the box (`mapExtras.js`).
  let stubs = new Map();
  // The scale the map is drawn at: the overview plan's, read from ELK's boxes, from the first drawing on
  // (`apply`), so the first fit measures the map as the overview draws it. Without a plan, the scale of the
  // whole-graph fit, measured when it is first read (`scaleNow`).
  let scale = null;
  let planned = false;
  let queued = false;
  let destroyed = false;
  // Whether the view has been placed since the canvas was made: its first change is the first fit.
  let placed = false;
  let version = 0;
  // A token of what is drawn, which the fit is measured once per: it changes with every drawing of a level.
  let drawing = 0;
  let hiddenAt = new Map();
  // The nodes an edge of the file is drawn as itself into at rest, and the box each node drawn larger than its layout is drawn as now.
  let ownEnds = new Set();
  let grownNow = new Map();
  /**
   * The scale the map is drawn at now. The whole-graph fit is measured only when
   * no plan has given the scale: measuring it reads the shape and the route of
   * every element still in the graph, all of them before the first drawing,
   * which took 220 ms over an adopter-sized graph that the plan's scale replaces
   * at once.
   */
  function scaleNow() {
    if (scale === null) scale = scaleAt(fitZoom());
    return scale;
  }
  /** The map's drawing now, as the titles read it (`mapTitles.js`). */
  const drawnNow = () => ({ scale: scaleNow(), hiddenAt, grownNow, ownEnds });
  const corners = nodeCorners(cy);
  /** The route an edge of the file is drawn along, bundled, or null. */
  const drawnRouteOf = (id) => (edges.get(id)?.data("route") ? routePointsOf(edges.get(id)) : null);
  const lines = aggregateElements(cy, { tree, geometry, nodes, edges, taken, drawnRouteOf });
  const extras = mapExtras(cy, { tree, edges, plainEdges, edgeById, byKey });
  const looks = titleLooks(cy, { nodes, tree, geometry });
  const planner = overviewPlanner(cy, {
    tree,
    geometry,
    plainEdges,
    routePointsOf: drawnRouteOf,
    // The plan asks whether a title fits its box on one line: whether to break it is the plan's to decide.
    titleOf: (id, at, hidden) => looks.lookOf(id, at, hidden, null, false),
    projectTitleOf: (at) => looks.projectTitleAt(at),
    // A box is drawn at least as tall as it was laid out, and its status mark takes room by the height it is drawn at.
    leastBoxOf: looks.leastBoxOf,
    breakable: looks.breakable,
    // A line the plan finds no route for is drawn along its medoid as the overview draws it, every top-level box closed.
    medoidOf: (pair) => lines.routeOf(pair, new Set(tree.wrapper ? [tree.wrapper] : [])),
    measure: looks.measure,
    scaleAt,
    budget: options.budget,
  });
  const titles = titleDresser(looks, planner, tree);

  /** The view now, as the levels read it: the fit measured once per drawing (`drawing`). */
  const viewNow = () => ({ zoom: cy.zoom(), fitZoom: fitZoom({ drawing }), extent: cy.extent() });

  /**
   * The boxes to draw open now: the readable ones in view and those a reveal
   * needs, once the view has been placed — before, the canvas stands at a zoom
   * nobody chose, and the first drawing is the overview — every one the test
   * handle forces, and the root. A reveal at any zoom other than the handle's
   * (a selected box) opens a box holding a layer rule's boxes only where they are
   * readable.
   */
  function wanted() {
    const needed = new Set();
    const forced = new Set();
    for (const [source, { boxes, anyZoom }] of reveals) {
      for (const box of boxes) (anyZoom && (source === FORCED || !layered.has(box)) ? forced : needed).add(box);
    }
    const next = placed ? openInView(tree, geometry.boxes, smallest, open, viewNow(), needed, options, forced) : new Set();
    for (const box of forced) next.add(box);
    if (tree.wrapper) next.add(tree.wrapper);
    return next;
  }

  /** Take `elements` out of the graph, those still in it. */
  const takeOut = (elements) => cy.remove(cy.collection(elements.filter((element) => element.inside())));
  /** Put `elements` back, those out of it, holders before what they hold. */
  function putBack(elements) {
    const out = elements.filter((element) => element.removed());
    out.sort((x, y) => (tree.depth.get(x.id()) ?? 0) - (tree.depth.get(y.id()) ?? 0));
    if (out.length) cy.collection(out).restore();
  }

  /**
   * The level drawn with the boxes `openNow` open and its outward edges, those
   * the filters keep (`kept`): worked out again only when the boxes or the
   * filters change, not when the pointer or the selection exposes another node.
   */
  function levelNow(openNow, kept) {
    const key = `${shownVersion}\n${[...openNow].sort().join("\n")}`;
    if (levelCache.key !== key) {
      const level = levelOf(tree, openNow, plainEdges);
      const outward = outwardOf(tree, openNow, plainEdges.filter((edge) => kept(edge.id)), level);
      levelCache = { key, level, outward };
    }
    return levelCache;
  }

  /**
   * Draw the level wanted now: the boxes open by the view and by every reveal;
   * with `sameLevel`, the boxes open now, as for the pointer, which opens none.
   */
  function apply({ sameLevel = false } = {}) {
    const nextOpen = sameLevel ? open : wanted();
    // An edge the filters hide is drawn as itself and marked hidden, as ever; an
    // aggregated edge carries only the edges they show.
    const kept = (id) => shown(edges.get(id));
    const { level, outward } = levelNow(nextOpen, kept);
    const weighed = [...level.pairs.values()].map((pair) => weigh(pair, kept)).filter((pair) => pair.weight > 0);
    const leftOut = budgetOf(weighed, options.budget);
    const free = new Set([...exempt.values()].filter(Boolean));
    for (const pair of weighed) {
      pair.overBudget = leftOut.has(pair.name);
      pair.hidden = pair.overBudget && !pair.ends.some((end) => isWithinAny(tree, end, free));
    }
    hiddenAt = new Map();
    for (const pair of weighed.filter((p) => p.hidden)) for (const end of pair.ends) hiddenAt.set(end, (hiddenAt.get(end) || 0) + 1);
    const tallies = talliesOf(weighed);
    planner.current(kept);
    // The first drawing is at the fit's scale as the plan measured it, not at the scale of the graph before any level.
    if (!planned && planner.titleScale()) [scale, planned] = [planner.titleScale(), true];
    scaleNow();
    const full = extras.fullDetailOf(level, nextOpen);
    ownEnds = new Set([...level.originals, ...full].flatMap((id) => [edgeById.get(id).source, edgeById.get(id).target]));
    grownNow = titles.grownBoxesNow(level.nodes, nextOpen, drawnNow());
    const besides = extras.extrasOf(level, nextOpen, outward, kept, grownNow);
    for (const id of full) besides.originals.add(id);
    stubs = besides.stubs;
    drawnElsewhere = new Set([...besides.originals, ...besides.own.flatMap((pair) => [...pair.forward, ...pair.backward])]);
    // A line of a box whose every edge shown is drawn by another line now is not drawn twice.
    for (const pair of weighed) pair.twice = [...pair.forward, ...pair.backward].every((id) => drawnElsewhere.has(id));
    for (const pair of [...weighed, ...besides.own]) pair.said = extras.saidOf(pair, drawnElsewhere);
    const drawnPairs = [...weighed.filter((pair) => !pair.hidden && !pair.twice), ...besides.own];
    const originals = new Set([...level.originals, ...besides.originals]);

    cy.batch(() => {
      takeOut(lines.undrawn(new Set(drawnPairs.map((pair) => pair.name))));
      takeOut([...edges.keys()].filter((id) => !originals.has(id)).flatMap(drawingOf));
      takeOut([...nodes.values()].filter((node) => !level.nodes.has(node.id())));
      putBack([...level.nodes].map((id) => nodes.get(id)));
      putBack([...originals].flatMap(drawingOf));
      const drawn = drawnPairs.map((pair) => {
        const element = lines.elementOf(pair);
        const path = planner.routeOf(pair) || lines.routeOf(pair, nextOpen);
        lines.dress(element, pair, { path, scale, grownNow, stub: stubs.get(pair.name) });
        return element;
      });
      putBack(drawn);
      for (const id of originals) {
        const line = lineOf(id);
        if (line.data(MAP_SCALE) !== scale) line.data(MAP_SCALE, scale);
        if (stubs.has(id)) line.data(STUB_AT, stubs.get(id));
        else if (line.data(STUB_AT) !== undefined) line.removeData(STUB_AT);
      }
      const now = drawnNow();
      for (const id of level.nodes) {
        const node = nodes.get(id);
        setClass(node, COLLAPSED, tree.boxes.has(id) && !nextOpen.has(id));
        const collapsed = node.hasClass(COLLAPSED);
        // The project's frame keeps its width on screen, as a mark of the map does.
        if (id === tree.wrapper) setClass(node, PROJECT_BOX, true);
        giveData(node, {
          ...(id === tree.wrapper || hiddenAt.has(id) || collapsed ? { [MAP_SCALE]: scale } : {}),
          [HIDDEN_EDGES]: hiddenAt.get(id),
          // A box no line comes into or goes out of has nothing to say.
          [TALLY]: collapsed ? tallies.get(id) : undefined,
          // A node inside an open box counts its outward edges; the root's children have none.
          [OUTWARD]: outward.has(id) && tree.parent.get(id) && tree.parent.get(id) !== tree.wrapper ? outward.get(id).length : undefined,
        });
        titles.dressBox(node, grownNow);
        titles.dressTitle(node, now);
      }
      // Once every node has the size it is drawn at and every line its route: where the lines end decides the room.
      corners.measure(scale);
      for (const id of level.nodes) corners.dress(nodes.get(id), scale);
    });
    open = nextOpen;
    pairs = weighed;
    ownPairs = besides.own;
    version += 1;
    drawing += 1;
  }

  // Whether each element asked about is of the top level, by its id: an element's ends never change.
  const topLevel = new Map();
  /** Whether `id` is at the top: the box that holds everything, or a node right under it. */
  const atTop = (id) => id === tree.wrapper || tree.parent.get(id) === tree.wrapper;

  /** Whether `element`, whose id is `id`, is of the top level (`ofTopLevel`). */
  function isOfTopLevel(element, id) {
    const fileEdge = edgeById.get(element.isEdge() ? id : loopEdgeOfEnd.get(id));
    if (fileEdge) return atTop(fileEdge.source) && atTop(fileEdge.target);
    if (element.isEdge()) return Boolean(lines.entryOf(id)?.pair.ends.every(atTop));
    return nodes.has(id) && atTop(id);
  }

  /** Whether two maps of drawn boxes (`grownBoxesNow`) draw the same boxes. */
  const sameBoxes = (a, b) => a.size === b.size && [...a].every(([id, box]) => JSON.stringify(b.get(id)) === JSON.stringify(box));

  /**
   * Restyle the map's marks when the zoom has crossed a step; true when a node
   * drawn larger than its layout is drawn at another size now, so the lines into
   * it, and every mark found from them, are to be drawn again.
   */
  function rescale() {
    const next = scaleAt(cy.zoom());
    if (next === scaleNow()) return false;
    scale = next;
    cy.batch(() => {
      cy.elements(`.${COLLAPSED}, .${PROJECT_BOX}, edge[${AGGREGATE}], node[${HIDDEN_EDGES}]`).data(MAP_SCALE, scale);
      for (const id of edges.keys()) if (lineOf(id).inside()) lineOf(id).data(MAP_SCALE, scale);
      const now = drawnNow();
      for (const node of nodes.values()) {
        if (!node.inside()) continue;
        titles.dressTitle(node, now);
        corners.dress(node, scale);
      }
    });
    version += 1;
    const drawn = [...nodes.values()].filter((node) => node.inside()).map((node) => node.id());
    return !sameBoxes(grownNow, titles.grownBoxesNow(drawn, open, drawnNow()));
  }

  /**
   * Work out the boxes wanted again, and have the level drawn again when they
   * differ or a drawn box changed size; otherwise, when only the scale stepped,
   * tell the canvas (`onRescale`), whose marks of shared lines depend on it.
   */
  function evaluate() {
    if (destroyed) return;
    placed = true;
    const before = scaleNow();
    const resized = rescale();
    if (sameSet(wanted(), open) && !resized) {
      if (scale !== before) onRescale();
      return;
    }
    onLevel();
  }

  // Once per frame at most, and only once the view holds still: a frame of an animated move is not a level.
  function onViewport() {
    if (queued) return;
    queued = true;
    const next = () =>
      requestAnimationFrame(() => {
        if (cy.animated()) return next();
        queued = false;
        evaluate();
      });
    next();
  }
  cy.on("viewport", onViewport);

  /** The edges of the file `entry`'s pair carries, forward then backward. */
  const membersOf = (entry) => [...entry.pair.forward, ...entry.pair.backward];

  return {
    tree,
    apply,
    evaluate: onViewport,
    /**
     * Draw each node of `ids` as itself with its own edges, for `source`: every
     * box that holds one open, and each one that is a box, once its nodes are
     * readable — at any zoom for the test handle (`FORCED`) and with `anyZoom`
     * (a selected box), but for a box holding a layer rule's boxes, which only
     * the handle opens at any zoom (`wanted`); an empty list lets them close.
     */
    reveal(source, ids, { anyZoom = source === FORCED } = {}) {
      reveals.set(source, { boxes: boxesRevealing(tree, ids || []), anyZoom });
    },
    expose: extras.expose,
    setWalk: extras.setWalk,
    /** Have an aggregated edge carry only the edges `predicate` keeps: the ones the filters show. */
    setShown(predicate) {
      shown = predicate;
      shownVersion += 1;
      drawing += 1;
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
      const weakAt = (id) => id !== null && pairs.some((pair) => pair.overBudget && pair.ends.some((end) => isWithinAny(tree, end, new Set([id]))));
      return weakAt(before) || weakAt(after);
    },
    /** Every pair of the level drawn now: `[{ element, pair }]`, `pair.hidden` when the budget leaves it out, `pair.twice` when other lines draw all it carries. */
    aggregates: () => pairs.map((pair) => ({ element: lines.elementOfPair(pair.name), pair })),
    /** The own lines drawn now: `[{ element, pair }]`. */
    ownLines: () => ownPairs.map((pair) => ({ element: lines.elementOfPair(pair.name), pair })),
    openBoxes: () => [...open].filter((id) => tree.boxes.has(id) && nodes.get(id).inside()).sort(),
    collapsedBoxes: () => cy.nodes(`.${COLLAPSED}`),
    allNodes: () => [...nodes.values()],
    isAggregate: (edge) => Boolean(edge.data(AGGREGATE)),
    /**
     * Whether `element` is of the top level, drawn alike at every level: a node
     * at the top or the box that holds everything, a line whose ends both are —
     * the overview's own lines among them — and a loop of such a line, its end too.
     */
    ofTopLevel(element) {
      const id = element.id();
      if (!topLevel.has(id)) topLevel.set(id, isOfTopLevel(element, id));
      return topLevel.get(id);
    },
    /** The keys of the edges an aggregated edge carries and no other line draws now. */
    keysOf(element) {
      const entry = lines.entryOf(element.id());
      if (!entry) return [];
      return membersOf(entry).filter((id) => !drawnElsewhere.has(id) || isOwnLine(entry.pair)).map((id) => edges.get(id).data("key"));
    },
    /** The keys of the walk's edges a node's own line `element` draws: the ones it carries that the walk took. */
    walkedKeysOf(element) {
      const entry = lines.entryOf(element.id());
      const walkKeys = extras.walkKeys();
      if (!entry || !walkKeys) return [];
      return membersOf(entry).map((id) => edges.get(id).data("key")).filter((key) => walkKeys.has(key));
    },
    keysEachWay(pair) {
      const keyOf = (id) => edges.get(id).data("key");
      return { forward: pair.forward.map(keyOf), backward: pair.backward.map(keyOf) };
    },
    scale: scaleNow,
    /** A number that changes whenever what the map draws or the scale it draws at changes. */
    version: () => version,
    /** What the overview's last plan was (`overviewPlan.js`): `{ ms, unit, routed, failed, grown, plates }`. */
    plan: () => planner.report(),
    /**
     * The room box `id` holds besides its children as drawn, or null: for the box
     * that holds everything, the most the nodes drawn larger than their layout at
     * this level ever take, so it is one size at every zoom of a level
     * (`canvasLayout.js`, `fitCompounds`).
     */
    reachOf(id) {
      const boxes = id === tree.wrapper ? [...grownNow.keys()].map((grown) => planner.plannedBoxOf(grown)) : [];
      if (!boxes.length) return null;
      return boxes.reduce((a, b) => ({ x1: Math.min(a.x1, b.x1), y1: Math.min(a.y1, b.y1), x2: Math.max(a.x2, b.x2), y2: Math.max(a.y2, b.y2) }));
    },
    fitZoom,
    /** The least zoom at which node `id` is drawn as itself and readable (`lib/levels.js`, `zoomDrawingOf`). */
    zoomDrawing: (id) => zoomDrawingOf(tree, id, smallest, fitZoom(), options),
    /** Whether a change of the view is still to be read: the boxes open may be about to change. */
    pending: () => queued,
    destroy() {
      destroyed = true;
      cy.removeListener("viewport", onViewport);
    },
  };
}
