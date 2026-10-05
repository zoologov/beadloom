// beadloom:component=site-graph-viewer
// The overview's plan on the canvas: its lines routed by the overview's own router, kept until what they are routed from changes.
//
// The overview is the level with every top-level box closed. Its lines are
// routed together (`lib/overviewRoutes.js`) at the scale of the whole-graph fit,
// where the reader sees them, between the top-level nodes' boxes from ELK's
// layout and around the plate of every title too wide for its box. A plate
// stands above its box unless there it would come within a lane of another
// top-level box, where it would close that box's ways in, or cover a plate
// placed before it; then below; and when neither side is clear, on the side
// where it covers no box, or else the least of one; the side is decided here, once per
// plan, so the drawn title and the routes around it agree. The plan is made
// from the overview whatever level is drawn, so a zoom or a box opened
// moves no line between two top-level nodes: such a line keeps the plan's route
// at every level. It is made again only when what it reads changes: the edges
// the filters show, or the scale of the fit when the canvas is resized.
//
// A line between two top-level nodes that the plan left out — the budget hid it,
// and the pointer or the selection draws it now — is routed around the plan's
// lines and kept the same way. A line the router finds no route for, and any
// line with an end inside an open box, is drawn along its medoid as before
// (`lib/aggregateRoutes.js`).

import { FIT_MAX_ZOOM, FIT_PADDING } from "../../../features/navigate-graph/index.js";
import { budgetOf, levelOf } from "../lib/levels.js";
import { PLATE_SIDES, plateOf } from "../lib/mapMarks.js";
import { OVERVIEW_MARKS, planOverview } from "../lib/overviewRoutes.js";

/** Whether rectangles `a` and `b` come closer than `gap`. */
const overlaps = (a, b, gap) => a.x1 - gap < b.x2 && a.x2 + gap > b.x1 && a.y1 - gap < b.y2 && a.y2 + gap > b.y1;

/** How much of rectangles `a` and `b` overlaps, as an area. */
const areaOfOverlap = (a, b) => Math.max(0, Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1)) * Math.max(0, Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1));

/** A pair's lines each way, in a form two plans can be compared by. */
const signatureOf = (pairs) => pairs.map((pair) => `${pair.name}:${pair.forward.length}:${pair.backward.length}`).join("\n");

/** `pair` of a level as the router takes it. */
const inputPairOf = (pair) => ({ name: pair.name, a: pair.ends[0], b: pair.ends[1], forward: pair.forward.length, backward: pair.backward.length });

/**
 * The planner of the overview over `cy`: `{ current, routeOf, isTop }`.
 *
 * `tree`, `geometry` and `plainEdges` are the map's (`canvasMap.js`);
 * `routePointsOf(id)` gives the route an edge of the file is drawn along, or
 * null; `titleOf(id, scale, hidden)` the title a node is drawn with at a scale
 * when `hidden` of its lines are left out (`lib/mapMarks.js`, `mapTitleOf`);
 * `measure(text, px)` a title's width in pixels; `scaleAt(zoom)` the map's scale
 * at a zoom; `budget` how many lines a level draws.
 */
export function overviewPlanner(cy, { tree, geometry, plainEdges, routePointsOf, titleOf, measure, scaleAt, budget }) {
  const top = new Set([...tree.parent.keys()].filter((id) => id !== tree.wrapper && tree.parent.get(id) === tree.wrapper && geometry.boxes[id]));
  const overview = levelOf(tree, new Set(tree.wrapper ? [tree.wrapper] : []), plainEdges);
  let plan = { signature: null, paths: new Map(), failed: [], ms: 0, unit: null, input: null, sides: new Map() };
  const extras = new Map();

  /** The map's scale at the zoom that fits every box in the canvas, as the viewer's fit does. */
  function fitUnit() {
    let [x1, y1, x2, y2] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const box of Object.values(geometry.boxes)) {
      [x1, y1, x2, y2] = [Math.min(x1, box.x1), Math.min(y1, box.y1), Math.max(x2, box.x2), Math.max(y2, box.y2)];
    }
    const [width, height] = [cy.width() - 2 * FIT_PADDING, cy.height() - 2 * FIT_PADDING];
    if (!(width > 0 && height > 0 && x2 > x1 && y2 > y1)) return scaleAt(cy.zoom());
    const zoom = Math.min(width / (x2 - x1), height / (y2 - y1), FIT_MAX_ZOOM, cy.maxZoom());
    return scaleAt(Math.max(zoom, cy.minZoom()));
  }

  /**
   * The plates of the titles too wide for their boxes at `unit`, when `hiddenAt`
   * counts each node's lines left out: `{ plates, sides }`, in the order of the
   * boxes' ids, each plate on the first side of its box where it keeps a lane
   * from every other box and covers no plate placed before it; else the first
   * where it covers neither; else the one where it covers the least.
   */
  function platesAt(unit, hiddenAt) {
    const plates = [];
    const sides = new Map();
    const others = [...top].map((id) => ({ id, ...geometry.boxes[id] }));
    const lane = OVERVIEW_MARKS.pitch * unit;
    const obstacles = (id) => [...others.filter((box) => box.id !== id), ...plates];
    const clearBy = (gap) => (rect, id) => others.every((box) => box.id === id || !overlaps(rect, box, gap)) && plates.every((plate) => !overlaps(rect, plate, unit));
    const covers = (rect, id) => obstacles(id).reduce((sum, other) => sum + areaOfOverlap(rect, other), 0);
    for (const id of [...top].sort()) {
      const title = titleOf(id, unit, hiddenAt.get(id) || 0);
      if (!title || title.inside) continue;
      const label = String(cy.getElementById(id).data("label"));
      const lines = hiddenAt.get(id) ? [label, `+${hiddenAt.get(id)}`] : [label];
      const placeAt = (side) => plateOf(geometry.boxes[id], side, lines, title.px, unit, measure);
      const side =
        PLATE_SIDES.find((candidate) => clearBy(lane)(placeAt(candidate), id)) ||
        PLATE_SIDES.find((candidate) => clearBy(unit)(placeAt(candidate), id)) ||
        [...PLATE_SIDES].sort((p, q) => covers(placeAt(p), id) - covers(placeAt(q), id))[0];
      sides.set(id, side);
      plates.push(placeAt(side));
    }
    return { plates, sides };
  }

  /** The plan for the edges `kept` shows: made again only when they or the fit's scale change. */
  function current(kept) {
    const pairs = [...overview.pairs.values()]
      .map((pair) => ({ ...pair, forward: pair.forward.filter(kept), backward: pair.backward.filter(kept) }))
      .filter((pair) => pair.forward.length + pair.backward.length > 0)
      .map((pair) => ({ ...pair, weight: pair.forward.length + pair.backward.length }));
    const leftOut = budgetOf(pairs, budget);
    const drawn = pairs.filter((pair) => !leftOut.has(pair.name));
    const hiddenAt = new Map();
    for (const pair of pairs.filter((p) => leftOut.has(p.name))) for (const end of pair.ends) hiddenAt.set(end, (hiddenAt.get(end) || 0) + 1);
    const unit = fitUnit();
    const signature = `${unit}\n${signatureOf(drawn)}`;
    if (plan.signature === signature) return plan;
    const started = performance.now();
    const { plates, sides } = platesAt(unit, hiddenAt);
    const input = {
      unit,
      boxes: [...top].map((id) => ({ id, ...geometry.boxes[id] })),
      plates,
      pairs: drawn.map(inputPairOf),
      fixed: overview.originals.map(routePointsOf).filter(Boolean),
    };
    const { paths, failed } = planOverview(input);
    plan = { signature, paths, failed, ms: performance.now() - started, unit, input, sides };
    extras.clear();
    return plan;
  }

  /** The route of a pair between two top-level nodes the plan left out, around the plan's lines. */
  function extraRouteOf(pair) {
    const signature = signatureOf([pair]);
    if (!extras.has(signature) && plan.input) {
      const input = { ...plan.input, pairs: [inputPairOf(pair)], fixed: [...plan.input.fixed, ...plan.paths.values()] };
      extras.set(signature, planOverview(input).paths.get(pair.name) || null);
    }
    return extras.get(signature) ?? null;
  }

  return {
    current,
    /** The side of its box the plan stands node `id`'s plate on: "above" or "below". */
    plateSideOf: (id) => plan.sides.get(id) || PLATE_SIDES[0],
    /** Whether `id` is a node at the top: under the box that holds everything, or a root when none does. */
    isTop: (id) => top.has(id),
    /** The planned route of `pair`, a polyline from a border of its first end to one of its second; null when it has none. */
    routeOf(pair) {
      if (!pair.ends.every((id) => top.has(id))) return null;
      return plan.paths.get(pair.name) || (plan.failed.includes(pair.name) ? null : extraRouteOf(pair));
    },
    /** What the last plan was: `{ ms, unit, routed, failed }`. */
    report: () => ({ ms: plan.ms, unit: plan.unit, routed: [...plan.paths.keys()].sort(), failed: [...plan.failed] }),
  };
}
