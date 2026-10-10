// beadloom:component=site-overview-map
// The overview's plan on the canvas: its lines routed by the overview's own router, kept until what they are routed from changes.
//
// The overview is the level with every top-level box closed. Its lines are
// routed together (`shared/grid-routing/overviewRoutes.js`) at the scale of the whole-graph fit,
// where the reader sees them, between the top-level nodes' boxes from ELK's
// layout and around the plate of every title too wide for its box. A top-level
// node whose title fits its laid-out box at no size is drawn at the least box
// that holds the title, where that box keeps clear of every other
// (`shared/geometry/grownBoxes.js`); the lines are routed around the drawn box and on into
// the laid-out one. Where no such box fits the title on one line, the title is
// broken onto two (`shared/map-levels/mapMarks.js`, `brokenLabelOf`), in the laid-out box or
// in the least box that holds it so. Only a title neither fits stands on a
// plate, and only where the fit is not held at the smallest zoom: an overview
// whose top level does not fit the canvas is left as it was (the owner's
// deferral). A title on a plate is broken onto two lines where its name breaks,
// as a title in a box is: a plate stands in the room between boxes the lines
// need, and a node added in another box can make that room a track too narrow
// for a plate one line wide (one node added to a wide box widened the frame of
// one portal, its fit stepped one scale coarser, and three lines between other
// boxes ran under a third box's plate). A plate's title is always broken where its
// name breaks, and the plan is made once (the owner's ruling, 2026-10-10). An
// overview held at the smallest zoom keeps its plates one line wide, as it was.
// A node an edge drawn as itself ends at is drawn larger only by a box that keeps
// that edge's line outside it, its end on the border, as a box widened in its
// row does for the lines from the rows above and below; otherwise its title
// broken onto two lines is drawn in its laid-out box where it fits there, and
// stands on a plate only where it does not.
// A plate stands above its box unless there it would come within a lane of another
// top-level box, where it would close that box's ways in, or cover a plate
// placed before it, or stand over a line drawn as itself, which the plan's routes
// cannot move; then below, then beside it; and when no side is clear, on a side
// clear of boxes and plates alone, or else where it covers the least; the side is decided here, once per
// plan, so the drawn title and the routes around it agree. The plan is made
// from the overview whatever level is drawn, so a zoom or a box opened
// moves no line between two top-level nodes: such a line keeps the plan's route
// at every level. It is made again only when what it reads changes: the edges
// the filters show, or the scale of the fit when the canvas is resized. That
// scale is the one the viewer's fit lands on once the plan is drawn: a box drawn
// larger keeps within the room past which the fit would step coarser
// (`scaleKeepingBoxOf`), so a title sized at the plan's scale reads within half
// a step of its size on screen, in any font.
//
// The box that holds everything is titled at the top, inside, at the size of
// a node's title in the graph's units: at the fit of a large graph that is a
// speck. While it reads smaller than the smallest size a title is tried at, the
// title stands on a plate above the box, as a closed box's title that fits its
// box at no size does, and the plan keeps the plate's room from every line,
// over every height the box is drawn at: it grows around the nodes drawn larger
// than their layout (`shared/geometry/routes.js`, `compoundSizeOf`).
//
// The lines keep inside the frame of the box that holds everything as it is
// laid out, below the band its title is drawn in inside it: the box is drawn no
// smaller at any height, so they keep inside it as drawn too.
//
// A line between two top-level nodes that the plan left out — the budget hid it,
// and the pointer or the selection draws it now — is routed around the plan's
// lines and kept the same way. A line the router finds no route for is drawn
// along its medoid (`shared/geometry/aggregateRoutes.js`), its last run into each end it
// carries a head to lengthened for the head as a routed line's is, clear of the
// plan's lines (`shared/bundling/headRuns.js`, `lengthenLineEnds`), and kept the same way.
// Any line with an end inside an open box is drawn along its medoid as before.

import { centreOf, compoundSizeOf, crossesAny, drawnBoxOf, grownBoxesOf } from "../../../shared/geometry/index.js";
import { FIT_MAX_ZOOM, FIT_PADDING, GEOMETRY, MAP_MARKS, PLATE_SIDES, budgetOf, levelOf, plateOf } from "../../../shared/map-levels/index.js";
import { lengthenLineEnds } from "../../../shared/bundling/index.js";
import { OVERVIEW_MARKS, planOverview } from "../../../shared/grid-routing/index.js";
import { BOX_SIDE } from "../../../shared/elk/index.js";

/** The room a box drawn larger keeps from every other box, in pixels on screen, tried in turn: a lane, else a plate's gap. */
const GROWN_GAPS = Object.freeze([OVERVIEW_MARKS.pitch, MAP_MARKS.plateGap]);

/** The size of the cells a medoid line's neighbours are filed in, in pitches. */
const FILED_PITCHES = 4;

/** Whether rectangles `a` and `b` come closer than `gap`. */
const overlaps = (a, b, gap) => a.x1 - gap < b.x2 && a.x2 + gap > b.x1 && a.y1 - gap < b.y2 && a.y2 + gap > b.y1;

/** How much of rectangles `a` and `b` overlaps, as an area. */
const areaOfOverlap = (a, b) => Math.max(0, Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1)) * Math.max(0, Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1));

/** The side of its box the title of the box that holds everything stands on, when it stands on a plate. */
export const PROJECT_PLATE_SIDE = "above";

/** The least rectangle that holds rectangles `a` and `b`. */
const unionOf = (a, b) => ({ x1: Math.min(a.x1, b.x1), y1: Math.min(a.y1, b.y1), x2: Math.max(a.x2, b.x2), y2: Math.max(a.y2, b.y2) });

/** The least rectangle that holds every rectangle of `boxes` and every point of `points`. */
function extentOf(boxes, points) {
  let [x1, y1, x2, y2] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const box of boxes) [x1, y1, x2, y2] = [Math.min(x1, box.x1), Math.min(y1, box.y1), Math.max(x2, box.x2), Math.max(y2, box.y2)];
  for (const point of points) [x1, y1, x2, y2] = [Math.min(x1, point.x), Math.min(y1, point.y), Math.max(x2, point.x), Math.max(y2, point.y)];
  return { x1, y1, x2, y2 };
}

/** How much larger than the plan's scale the fit's must be to count as a step coarser: more than rounding. */
const COARSER = 1e-9;

/** How many times the least zoom of a scale is halved towards (`leastZoomAt`): past a double's precision. */
const HALVINGS = 60;

/**
 * The least zoom at which `scaleAt` gives `unit`, between `lowest` and 1 / `unit`,
 * found by halving: below it the map's scale is a step coarser. A hair above
 * the boundary, so a fit at it lands on `unit` whatever the rounding.
 */
function leastZoomAt(unit, scaleAt, lowest) {
  let [below, at] = [lowest, 1 / unit];
  if (scaleAt(below) <= unit * (1 + COARSER)) return below;
  for (let halving = 0; halving < HALVINGS; halving += 1) {
    const middle = (below + at) / 2;
    if (scaleAt(middle) > unit * (1 + COARSER)) below = middle;
    else at = middle;
  }
  return at * (1 + COARSER);
}

/** How many times the plan is made again at a coarser scale, when what it draws widens the fit past a step (`settledLayOut`). */
const REFITS = 3;

/** Whether rectangles `a` and `b` are one, within a hair of rounding. */
const sameBox = (a, b) => ["x1", "y1", "x2", "y2"].every((side) => Math.abs(a[side] - b[side]) < 1e-9);

/** `box` drawn as a compound around `reach`, larger on both sides of an axis by as much as `reach` passes it there. */
function heldBoxOf(box, reach) {
  const { width, height } = compoundSizeOf(box, null, 0, reach);
  const { x, y } = centreOf(box);
  return { x1: x - width / 2, y1: y - height / 2, x2: x + width / 2, y2: y + height / 2 };
}

/** How far inside a box's border a line counts as entering it, in layout units: a line ending on the border does not. */
const BORDER_HAIR = 0.01;

/** Whether every polyline of `paths` keeps outside `box`, an end on its border included. */
export function keepsOutside(box, paths) {
  const inner = { x1: box.x1 + BORDER_HAIR, y1: box.y1 + BORDER_HAIR, x2: box.x2 - BORDER_HAIR, y2: box.y2 - BORDER_HAIR };
  return !crossesAny(inner, paths);
}

/**
 * The frame the plan's lines keep inside, in layout units: the box that holds
 * everything without the band its title is drawn in once the view is zoomed in
 * far enough for the title to read inside it, at the top. A line routed through
 * that band ran under the title at every zoom past that one. The band is the
 * title room less the room ELK keeps inside a box's border on its other sides
 * (`BOX_SIDE`), so the lines keep as much room above the children as beside
 * them; it is read from the layout, so a change to ELK's padding moves it too.
 */
export const routedFrameOf = (frame) => ({ ...frame, y1: frame.y1 + GEOMETRY.boxTitleRoom - BOX_SIDE });

/** A pair's lines each way, in a form two plans can be compared by. */
const signatureOf = (pairs) => pairs.map((pair) => `${pair.name}:${pair.forward.length}:${pair.backward.length}`).join("\n");

/** `pair` of a level as the router takes it. */
const inputPairOf = (pair) => ({ name: pair.name, a: pair.ends[0], b: pair.ends[1], forward: pair.forward.length, backward: pair.backward.length });

/**
 * The planner of the overview over `cy`: `{ current, routeOf, isTop }`.
 *
 * `tree`, `geometry` and `plainEdges` are the map's (`widgets/graph-viewer/model/canvasMap.js`);
 * `routePointsOf(id)` gives the route an edge of the file is drawn along, or
 * null; `titleOf(id, scale, hidden, broken)` the title a node is drawn with in its
 * laid-out box at a scale when `hidden` of its lines are left out, on one line or,
 * `broken`, on two where one fits at no size (`shared/map-levels/mapMarks.js`, `mapTitleOf`), `linesOf(id, hidden, broken)` its lines,
 * its name `broken` onto two where it breaks, and `leastBoxOf(id, px, scale, hidden)` the
 * least box, in layout units, that holds that title inside at `px`
 * (`titleBoxOf`); `medoidOf(pair)` the medoid of a pair's edges' routes as the
 * overview draws it, or null; `measure(text, px)` a title's width in pixels;
 * `scaleAt(zoom)` the map's scale at a zoom; `budget` how many lines a level draws.
 */
export function overviewPlanner(cy, { tree, geometry, plainEdges, routePointsOf, titleOf, linesOf, projectTitleOf, leastBoxOf, breakable, medoidOf, measure, scaleAt, budget }) {
  const top = new Set([...tree.parent.keys()].filter((id) => id !== tree.wrapper && tree.parent.get(id) === tree.wrapper && geometry.boxes[id]));
  const overview = levelOf(tree, new Set(tree.wrapper ? [tree.wrapper] : []), plainEdges);
  const edgeById = new Map(plainEdges.map((edge) => [edge.id, edge]));
  let plan = {
    signature: null,
    paths: new Map(),
    fallbacks: new Map(),
    failed: [],
    ms: 0,
    unit: null,
    input: null,
    sides: new Map(),
    grown: new Map(),
    broken: new Set(),
    plated: [],
    project: null,
    hiddenAt: new Map(),
  };
  const extras = new Map();

  /**
   * The map's scale at the zoom that fits `extent` (`{ x1, y1, x2, y2 }`, layout
   * units) in the canvas, as the viewer's fit does: `{ unit, clamped }`,
   * `clamped` when that zoom is held at the smallest and the top level does not
   * fit the canvas. By default the extent is every box as it is laid out.
   */
  function fitScale(extent = extentOf(Object.values(geometry.boxes), [])) {
    const { x1, y1, x2, y2 } = extent;
    const [width, height] = [cy.width() - 2 * FIT_PADDING, cy.height() - 2 * FIT_PADDING];
    if (!(width > 0 && height > 0 && x2 > x1 && y2 > y1)) return { unit: scaleAt(cy.zoom()), clamped: false };
    const zoom = Math.min(width / (x2 - x1), height / (y2 - y1), FIT_MAX_ZOOM, cy.maxZoom());
    return { unit: scaleAt(Math.max(zoom, cy.minZoom())), clamped: zoom < cy.minZoom() };
  }

  /**
   * The box every box the plan draws larger keeps within at `unit`, in layout
   * units, so the whole-graph fit still lands on `unit`: the laid-out extent
   * grown on both sides of each axis by half of what the fit can take before its
   * zoom drops past the least one `scaleAt` gives `unit` at. A box that reaches
   * out of the box that holds everything draws that box as much larger on both
   * sides (`heldBoxOf`), so a reach of that half keeps the fit on `unit`.
   * Null where the canvas has no size.
   */
  function scaleKeepingBoxOf(unit) {
    const laid = extentOf(Object.values(geometry.boxes), []);
    const [width, height] = [cy.width() - 2 * FIT_PADDING, cy.height() - 2 * FIT_PADDING];
    if (!(width > 0 && height > 0)) return null;
    const zoom = leastZoomAt(unit, scaleAt, cy.minZoom());
    const dx = Math.max(0, (width / zoom - (laid.x2 - laid.x1)) / 2);
    const dy = Math.max(0, (height / zoom - (laid.y2 - laid.y1)) / 2);
    return { x1: laid.x1 - dx, y1: laid.y1 - dy, x2: laid.x2 + dx, y2: laid.y2 + dy };
  }

  /**
   * What the viewer's fit measures over the overview `made` draws, in layout
   * units: every box, the boxes it draws larger than their layout and the box
   * that holds everything grown around them, and every point of every line
   * drawn between top-level nodes, its own routes and the lines drawn as
   * themselves (`features/navigate-graph`, `shapesBoxOf`). A title's plate is a
   * label, which the fit leaves out.
   */
  function drawnExtentOf(made) {
    const grown = [...made.grown.values()].map((entry) => entry.box);
    const reach = grown.reduce((a, b) => (a ? unionOf(a, b) : b), null);
    const held = tree.wrapper && reach ? [heldBoxOf(geometry.boxes[tree.wrapper], reach)] : [];
    const lines = [...made.paths.values(), ...made.fallbacks.values(), ...overview.originals.map(routePointsOf).filter(Boolean)];
    return extentOf([...Object.values(geometry.boxes), ...grown, ...held], lines.flat());
  }

  /**
   * The top-level nodes drawn in a box of their own at `unit`, chosen among
   * `ids`, whose titles fit their laid-out box at no size: each in the least box
   * that holds its title on one line, or, `broken`, broken onto two lines
   * (`shared/geometry/grownBoxes.js`). None at a fit held at the smallest zoom. A
   * node an edge drawn as itself ends at is drawn larger only by a box that keeps
   * those lines outside it, their ends on its border (`keepsOutside`): a node laid
   * out in a row is widened, and lines from the rows above and below still end
   * on its top and bottom; it takes the largest size at which it is so, and is
   * decided after the nodes no such line ends at.
   */
  function grownAt(unit, ids, hiddenAt, clamped, broken = false) {
    if (clamped) return new Map();
    const routed = overview.originals.map((id) => ({ edge: edgeById.get(id), path: routePointsOf(id) })).filter((line) => line.path);
    const lines = routed.map((line) => line.path);
    const ownOf = (id) => routed.filter(({ edge }) => edge.source === id || edge.target === id).map((line) => line.path);
    const boxes = Object.fromEntries([...top].map((id) => [id, geometry.boxes[id]]));
    const options = {
      leastBoxOf: (id, px) => leastBoxOf(id, px, unit, hiddenAt.get(id) || 0, broken),
      sizes: MAP_MARKS.titleSizes,
      gaps: GROWN_GAPS.map((gap) => gap * unit),
      lines,
      within: tree.wrapper ? geometry.boxes[tree.wrapper] : null,
      limit: scaleKeepingBoxOf(unit),
    };
    const grown = grownBoxesOf(ids.filter((id) => !ownOf(id).length), boxes, options);
    const placed = { ...boxes, ...Object.fromEntries([...grown].map(([id, entry]) => [id, entry.box])) };
    for (const id of ids.filter((node) => ownOf(node).length)) {
      const own = ownOf(id);
      const others = lines.filter((path) => !own.includes(path));
      const entry = MAP_MARKS.titleSizes
        .map((px) => grownBoxesOf([id], placed, { ...options, sizes: [px], lines: others }).get(id))
        .find((found) => found && keepsOutside(found.box, own));
      if (!entry) continue;
      grown.set(id, entry);
      placed[id] = entry.box;
    }
    return grown;
  }

  /**
   * The plates of the titles of `ids` at `unit`, too wide for their boxes and
   * drawn no larger, when `hiddenAt` counts each node's lines left out and
   * `boxOf(id)` gives each top-level node's drawn box, the titles of `broken`
   * broken onto two lines: `{ plates, sides }`, in
   * the order of `ids`, each plate on the first side of its box where it keeps a
   * lane from every other box, covers no plate placed before it and no line drawn
   * as itself runs under it, which no route can move; else the first where it
   * covers neither and no such line runs under it; else, those lines left aside,
   * the first where it keeps a lane, then the first where it covers neither; else
   * the one where it covers the least.
   */
  function platesAt(unit, hiddenAt, ids, boxOf, broken) {
    const plates = [];
    const sides = new Map();
    const others = [...top].map((id) => ({ id, ...boxOf(id) }));
    const lane = OVERVIEW_MARKS.pitch * unit;
    const fixed = overview.originals.map(routePointsOf).filter(Boolean);
    const obstacles = (id) => [...others.filter((box) => box.id !== id), ...plates];
    const clearBy = (gap) => (rect, id) => others.every((box) => box.id === id || !overlaps(rect, box, gap)) && plates.every((plate) => !overlaps(rect, plate, unit));
    const clearOfLines = (gap) => (rect, id) => clearBy(gap)(rect, id) && !crossesAny(rect, fixed);
    const covers = (rect, id) => obstacles(id).reduce((sum, other) => sum + areaOfOverlap(rect, other), 0);
    for (const id of ids) {
      const title = titleOf(id, unit, hiddenAt.get(id) || 0);
      const lines = linesOf(id, hiddenAt.get(id) || 0, broken.has(id));
      const placeAt = (side) => plateOf(geometry.boxes[id], side, lines, title.px, unit, measure);
      const firstClear = (test) => PLATE_SIDES.find((candidate) => test(placeAt(candidate), id));
      const side =
        firstClear(clearOfLines(lane)) ||
        firstClear(clearOfLines(unit)) ||
        firstClear(clearBy(lane)) ||
        firstClear(clearBy(unit)) ||
        [...PLATE_SIDES].sort((p, q) => covers(placeAt(p), id) - covers(placeAt(q), id))[0];
      sides.set(id, side);
      plates.push(placeAt(side));
    }
    return { plates, sides };
  }

  /**
   * The plate the title of the box that holds everything stands on above it at
   * `unit`, when the nodes `grown` are drawn larger than their layout: the room
   * it takes over every height the box is drawn at, from its laid-out box to the
   * box around every grown node, in layout units; null where there is no such box
   * or its own title reads at a size a title is drawn at.
   */
  function projectPlateAt(unit, grown) {
    const title = tree.wrapper ? projectTitleOf(unit) : null;
    if (!title) return null;
    const laid = geometry.boxes[tree.wrapper];
    const reach = [...grown.values()].map((entry) => entry.box).reduce((a, b) => (a ? unionOf(a, b) : b), null);
    const lines = [String(cy.getElementById(tree.wrapper).data("label"))];
    const plateOver = (box) => plateOf(box, PROJECT_PLATE_SIDE, lines, title.px, unit, measure);
    return unionOf(plateOver(laid), plateOver(reach ? heldBoxOf(laid, reach) : laid));
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
    const { made, at } = settledLayOut(unit, drawn, hiddenAt, clamped);
    plan = { signature, ...made, ms: performance.now() - started, unit: at, hiddenAt };
    extras.clear();
    return plan;
  }

  /**
   * The plan laid out at the scale the viewer's fit lands on once it is drawn:
   * `{ made, at }`. The fit measures what the plan draws, and a box the plan
   * draws larger, or the box that holds everything grown around it, can widen
   * the fit past a step of the map's scale: the titles, laid out at the plan's
   * scale, then read a step smaller than every other mark, under the smallest
   * size a title is drawn at in a wider font (vue-fsd on Linux: 8.57 px for 10).
   * The boxes drawn larger keep within `scaleKeepingBoxOf`, so the fit stays on
   * `unit`; should what the plan drew still move it, the plan is made again at
   * the fit's scale of what it drew, a step coarser each time, at most `REFITS`
   * times. A fit held at the smallest zoom is left as it was.
   */
  function settledLayOut(unit, drawn, hiddenAt, clamped) {
    let at = unit;
    let made = layOut(at, drawn, hiddenAt, clamped);
    for (let refit = 0; refit < REFITS && !clamped; refit += 1) {
      const fit = fitScale(drawnExtentOf(made));
      if (fit.clamped || !(fit.unit > at * (1 + COARSER))) break;
      at = fit.unit;
      made = layOut(at, drawn, hiddenAt, clamped);
    }
    return { made, at };
  }

  /**
   * The plan's boxes, plates and routes at `unit` for the lines `drawn`. A
   * top-level node whose title fits its laid-out box at no size is drawn larger
   * to hold it on one line; where no such box fits, its title is broken onto two
   * lines, in its box or a larger one that holds it so; where neither fits, it
   * stands on a plate (`plated`), broken onto two lines where its name breaks.
   */
  function layOut(unit, drawn, hiddenAt, clamped) {
    const unfit = [...top].sort().filter((id) => {
      const title = titleOf(id, unit, hiddenAt.get(id) || 0);
      return title && !title.inside;
    });
    const whole = grownAt(unit, unfit, hiddenAt, clamped);
    const brokenAt = clamped ? new Map() : grownAt(unit, unfit.filter((id) => !whole.has(id) && breakable(id)), hiddenAt, clamped, true);
    const grows = ([id, entry]) => !sameBox(entry.box, geometry.boxes[id]);
    const grown = new Map([...whole, ...[...brokenAt].filter(grows)]);
    // A node an edge drawn as itself ends at is drawn no larger (`grownAt`), and its title broken onto two lines
    // may still fit its laid-out box: it is titled there, not on a plate.
    const inBox = clamped ? [] : unfit.filter((id) => !whole.has(id) && !brokenAt.has(id) && breakable(id) && titleOf(id, unit, hiddenAt.get(id) || 0, true)?.inside);
    const broken = new Set([...brokenAt.keys(), ...inBox]);
    const boxOf = (id) => grown.get(id)?.box || geometry.boxes[id];
    const plated = unfit.filter((id) => !whole.has(id) && !broken.has(id));
    const project = projectPlateAt(unit, grown);
    const boxes = [...top].map((id) => (grown.has(id) ? { id, ...grown.get(id).box, core: geometry.boxes[id] } : { id, ...geometry.boxes[id] }));
    const routed = (brokenPlates) => {
      const made = plated.length ? platesAt(unit, hiddenAt, plated, boxOf, brokenPlates) : { plates: [], sides: new Map() };
      const input = {
        unit,
        boxes,
        plates: project ? [...made.plates, project] : made.plates,
        pairs: drawn.map(inputPairOf),
        fixed: overview.originals.map(routePointsOf).filter(Boolean),
        frame: tree.wrapper ? routedFrameOf(geometry.boxes[tree.wrapper]) : null,
      };
      const { paths, failed } = planOverview(input);
      const fallbacks = failed.length ? fallbacksOf(drawn.filter((pair) => failed.includes(pair.name)), drawn, paths, input) : new Map();
      return { paths, fallbacks, failed, input, sides: made.sides, brokenPlates };
    };
    const made = routed(new Set(clamped ? [] : plated.filter((id) => breakable(id))));
    const { paths, fallbacks, failed, input, sides } = made;
    return { paths, fallbacks, failed, input, sides, grown, broken: new Set([...broken, ...made.brokenPlates]), plated, project };
  }

  /**
   * The lines of `unrouted`, pairs of `drawn` the router found no route for,
   * each along its medoid with its last run into each end it carries a head to
   * lengthened for the head, among the plan's `paths` and the lines drawn as
   * themselves, clear of `input`'s boxes and plates: `Map(name => points)`, in
   * layout units, a line with no medoid left out.
   */
  function fallbacksOf(unrouted, drawn, paths, input) {
    const lines = unrouted
      .map((pair) => ({ id: pair.name, source: pair.ends[0], target: pair.ends[1], points: medoidOf(pair), heads: { source: pair.backward.length > 0, target: pair.forward.length > 0 } }))
      .filter((line) => line.points?.length >= 2);
    if (!lines.length) return new Map();
    const endsOf = new Map(drawn.map((pair) => [pair.name, pair.ends]));
    const planned = [...paths].map(([name, points]) => ({ id: name, source: endsOf.get(name)[0], target: endsOf.get(name)[1], points }));
    const asThemselves = overview.originals
      .map((id) => ({ id, source: edgeById.get(id).source, target: edgeById.get(id).target, points: routePointsOf(id) }))
      .filter((line) => line.points);
    const boxes = Object.fromEntries([
      ...input.boxes.map(({ id, x1, y1, x2, y2 }) => [id, { x1, y1, x2, y2 }]),
      ...input.plates.map((plate, k) => [`plate\n${k}`, plate]),
    ]);
    const { unit } = input;
    const options = {
      headRun: OVERVIEW_MARKS.run * unit,
      headRunStep: unit,
      headRunClearance: (OVERVIEW_MARKS.pitch / 2) * unit,
      cellSize: FILED_PITCHES * OVERVIEW_MARKS.pitch * unit,
      bandWidth: OVERVIEW_MARKS.pitch * unit,
    };
    return lengthenLineEnds({ lines, others: [...planned, ...asThemselves], boxes }, options);
  }

  /** The route of a pair between two top-level nodes the plan left out, around the plan's lines. */
  function extraRouteOf(pair) {
    const signature = signatureOf([pair]);
    if (!extras.has(signature) && plan.input) {
      const input = { ...plan.input, pairs: [inputPairOf(pair)], fixed: [...plan.input.fixed, ...plan.paths.values(), ...plan.fallbacks.values()] };
      extras.set(signature, planOverview(input).paths.get(pair.name) || null);
    }
    return extras.get(signature) ?? null;
  }

  return {
    current,
    /** The side of its box the plan stands node `id`'s plate on: "above" or "below". */
    plateSideOf: (id) => plan.sides.get(id) || PLATE_SIDES[0],
    /** Whether the plan keeps room above the box that holds everything for its title on a plate. */
    hasProjectPlate: () => Boolean(plan.project),
    /** Whether `id` is a node at the top: under the box that holds everything, or a root when none does. */
    isTop: (id) => top.has(id),
    /**
     * The planned route of `pair`, a polyline from a border of its first end to
     * one of its second: routed, or its medoid with room for its heads where the
     * router found it none; null when it has neither.
     */
    routeOf(pair) {
      if (!pair.ends.every((id) => top.has(id))) return null;
      return plan.paths.get(pair.name) || plan.fallbacks.get(pair.name) || (plan.failed.includes(pair.name) ? null : extraRouteOf(pair));
    },
    /** The scale the plan decided its titles and plates at, or null before the first plan. */
    titleScale: () => plan.unit,
    /** Whether the plan draws node `id` larger than its layout. */
    isGrown: (id) => plan.grown.has(id),
    /** Whether the plan breaks node `id`'s title onto two lines (`shared/map-levels/mapMarks.js`, `brokenLabelOf`), in its box or on its plate. */
    isBroken: (id) => plan.broken.has(id),
    /** How many of node `id`'s lines the overview leaves out, as the plan counted them. */
    hiddenOf: (id) => plan.hiddenAt.get(id) || 0,
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
      const least = leastBoxOf(id, entry.px, Math.min(at, plan.unit), hidden, plan.broken.has(id));
      return drawnBoxOf(geometry.boxes[id], entry.box, least);
    },
    /**
     * What the last plan was: `{ ms, unit, routed, failed, grown, broken,
     * plates, projectPlate }`, `grown` the top-level nodes it draws
     * larger than their layout, `broken` those whose title it breaks onto two
     * lines, `plates` those whose title it stands on a plate, every list sorted,
     * and `projectPlate` the room it keeps for the title of the box that holds
     * everything, `{ x1, y1, x2, y2 }` in layout units, or null.
     */
    report: () => ({
      ms: plan.ms,
      unit: plan.unit,
      routed: [...plan.paths.keys()].sort(),
      failed: [...plan.failed],
      grown: [...plan.grown.keys()].sort(),
      broken: [...plan.broken].sort(),
      plates: [...plan.plated],
      projectPlate: plan.project ? { ...plan.project } : null,
    }),
  };
}
