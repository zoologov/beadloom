// beadloom:component=site-graph-viewer
// The overview's plan on the canvas: its lines routed by the overview's own router, kept until what they are routed from changes.
//
// The overview is the level with every top-level box closed. Its lines are
// routed together (`lib/overviewRoutes.js`) at the scale of the whole-graph fit,
// where the reader sees them, between the top-level nodes' boxes from ELK's
// layout and around the plate of every title too wide for its box. A top-level
// node whose title fits its laid-out box at no size is drawn at the least box
// that holds the title, where that box keeps clear of every other
// (`lib/grownBoxes.js`); the lines are routed around the drawn box and on into
// the laid-out one. Only a title no such box fits around stands on a plate,
// and only where the fit is not held at the smallest zoom: an overview whose
// top level does not fit the canvas is left as it was (the owner's deferral).
// A plate stands above its box unless there it would come within a lane of another
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
import { drawnBoxOf, grownBoxesOf } from "../lib/grownBoxes.js";
import { budgetOf, levelOf } from "../lib/levels.js";
import { MAP_MARKS, PLATE_SIDES, plateOf } from "../lib/mapMarks.js";
import { OVERVIEW_MARKS, planOverview } from "../lib/overviewRoutes.js";

/** The room a box drawn larger keeps from every other box, in pixels on screen, tried in turn: a lane, else a plate's gap. */
const GROWN_GAPS = Object.freeze([OVERVIEW_MARKS.pitch, MAP_MARKS.plateGap]);

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
 * null; `titleOf(id, scale, hidden)` the title a node is drawn with in its
 * laid-out box at a scale when `hidden` of its lines are left out
 * (`lib/mapMarks.js`, `mapTitleOf`), and `leastBoxOf(id, px, scale, hidden)` the
 * least box, in layout units, that holds that title inside at `px`
 * (`titleBoxOf`); `measure(text, px)` a title's width in pixels; `scaleAt(zoom)`
 * the map's scale at a zoom; `budget` how many lines a level draws.
 */
export function overviewPlanner(cy, { tree, geometry, plainEdges, routePointsOf, titleOf, leastBoxOf, measure, scaleAt, budget }) {
  const top = new Set([...tree.parent.keys()].filter((id) => id !== tree.wrapper && tree.parent.get(id) === tree.wrapper && geometry.boxes[id]));
  const overview = levelOf(tree, new Set(tree.wrapper ? [tree.wrapper] : []), plainEdges);
  const edgeById = new Map(plainEdges.map((edge) => [edge.id, edge]));
  let plan = { signature: null, paths: new Map(), failed: [], ms: 0, unit: null, input: null, sides: new Map(), grown: new Map(), plated: [] };
  const extras = new Map();

  /**
   * The map's scale at the zoom that fits every box in the canvas, as the
   * viewer's fit does: `{ unit, clamped }`, `clamped` when that zoom is held at
   * the smallest and the top level does not fit the canvas.
   */
  function fitScale() {
    let [x1, y1, x2, y2] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const box of Object.values(geometry.boxes)) {
      [x1, y1, x2, y2] = [Math.min(x1, box.x1), Math.min(y1, box.y1), Math.max(x2, box.x2), Math.max(y2, box.y2)];
    }
    const [width, height] = [cy.width() - 2 * FIT_PADDING, cy.height() - 2 * FIT_PADDING];
    if (!(width > 0 && height > 0 && x2 > x1 && y2 > y1)) return { unit: scaleAt(cy.zoom()), clamped: false };
    const zoom = Math.min(width / (x2 - x1), height / (y2 - y1), FIT_MAX_ZOOM, cy.maxZoom());
    return { unit: scaleAt(Math.max(zoom, cy.minZoom())), clamped: zoom < cy.minZoom() };
  }

  /**
   * The top-level nodes drawn larger than their layout at `unit`, chosen among
   * `unfit`, whose titles fit their laid-out box at no size: none at a fit held
   * at the smallest zoom, and none that an edge drawn as itself ends at, whose
   * end its drawn box would cover (`lib/grownBoxes.js`).
   */
  function grownAt(unit, unfit, hiddenAt, clamped) {
    if (clamped) return new Map();
    const lines = overview.originals.map(routePointsOf).filter(Boolean);
    const ownEnds = new Set(overview.originals.flatMap((id) => [edgeById.get(id).source, edgeById.get(id).target]));
    const boxes = Object.fromEntries([...top].map((id) => [id, geometry.boxes[id]]));
    return grownBoxesOf(
      unfit.filter((id) => !ownEnds.has(id)),
      boxes,
      {
        leastBoxOf: (id, px) => leastBoxOf(id, px, unit, hiddenAt.get(id) || 0),
        sizes: MAP_MARKS.titleSizes,
        gaps: GROWN_GAPS.map((gap) => gap * unit),
        lines,
        within: tree.wrapper ? geometry.boxes[tree.wrapper] : null,
      }
    );
  }

  /**
   * The plates of the titles of `ids` at `unit`, too wide for their boxes and
   * drawn no larger, when `hiddenAt` counts each node's lines left out and
   * `boxOf(id)` gives each top-level node's drawn box: `{ plates, sides }`, in
   * the order of `ids`, each plate on the first side of its box where it keeps a
   * lane from every other box and covers no plate placed before it; else the
   * first where it covers neither; else the one where it covers the least.
   */
  function platesAt(unit, hiddenAt, ids, boxOf) {
    const plates = [];
    const sides = new Map();
    const others = [...top].map((id) => ({ id, ...boxOf(id) }));
    const lane = OVERVIEW_MARKS.pitch * unit;
    const obstacles = (id) => [...others.filter((box) => box.id !== id), ...plates];
    const clearBy = (gap) => (rect, id) => others.every((box) => box.id === id || !overlaps(rect, box, gap)) && plates.every((plate) => !overlaps(rect, plate, unit));
    const covers = (rect, id) => obstacles(id).reduce((sum, other) => sum + areaOfOverlap(rect, other), 0);
    for (const id of ids) {
      const title = titleOf(id, unit, hiddenAt.get(id) || 0);
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
    const { unit, clamped } = fitScale();
    const signature = `${unit}\n${signatureOf(drawn)}`;
    if (plan.signature === signature) return plan;
    const started = performance.now();
    const unfit = [...top].sort().filter((id) => {
      const title = titleOf(id, unit, hiddenAt.get(id) || 0);
      return title && !title.inside;
    });
    const grown = grownAt(unit, unfit, hiddenAt, clamped);
    const boxOf = (id) => grown.get(id)?.box || geometry.boxes[id];
    const plated = unfit.filter((id) => !grown.has(id));
    const { plates, sides } = platesAt(unit, hiddenAt, plated, boxOf);
    const input = {
      unit,
      boxes: [...top].map((id) => (grown.has(id) ? { id, ...grown.get(id).box, core: geometry.boxes[id] } : { id, ...geometry.boxes[id] })),
      plates,
      pairs: drawn.map(inputPairOf),
      fixed: overview.originals.map(routePointsOf).filter(Boolean),
    };
    const { paths, failed } = planOverview(input);
    plan = { signature, paths, failed, ms: performance.now() - started, unit, input, sides, grown, plated };
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
    /** The scale the plan decided its titles and plates at, or null before the first plan. */
    titleScale: () => plan.unit,
    /** Whether the plan draws node `id` larger than its layout. */
    isGrown: (id) => plan.grown.has(id),
    /** The box the plan draws node `id` as at most, in layout units, the box its lines were routed around; null for a node drawn as laid out. */
    plannedBoxOf: (id) => plan.grown.get(id)?.box ?? null,
    /**
     * The box node `id` is drawn as at scale `at`, with `hidden` of its lines
     * left out, when the plan draws it larger than its layout, in layout units:
     * the least box that holds its title at the plan's size, between its
     * laid-out box and the box the lines were routed around; null for a node
     * drawn as laid out.
     */
    drawnBoxAt(id, at, hidden) {
      const entry = plan.grown.get(id);
      if (!entry) return null;
      const least = leastBoxOf(id, entry.px, Math.min(at, plan.unit), hidden);
      return drawnBoxOf(geometry.boxes[id], entry.box, least);
    },
    /**
     * What the last plan was: `{ ms, unit, routed, failed, grown, plates }`,
     * `grown` the nodes it draws larger than their layout and `plates` those
     * whose title it stands on a plate, every list sorted.
     */
    report: () => ({
      ms: plan.ms,
      unit: plan.unit,
      routed: [...plan.paths.keys()].sort(),
      failed: [...plan.failed],
      grown: [...plan.grown.keys()].sort(),
      plates: [...plan.plated],
    }),
  };
}
