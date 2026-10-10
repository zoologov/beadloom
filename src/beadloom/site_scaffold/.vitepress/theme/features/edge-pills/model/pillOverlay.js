// beadloom:component=site-edge-pills
// The map's counts drawn over the canvas: each line's count on a pill, how many edges come into a closed box and go out of it, and a node's "+N".
//
// Cytoscape draws an edge's label with its edge, so the next edge drawn paints
// over it. A line's count is drawn instead on a canvas of its own laid over every
// line, the followed ones included (`shared/canvas-marks/overlayCanvas.js`), as a pill: an opaque
// rounded label with a thin border in the line's colour, at the place
// `shared/geometry/pillPlaces.js` finds on its line, worked out again only when what is
// drawn or the step of the map's scale changes. A pill keeps one size on screen.
// While the pointer rests on a node, the pills of its lines are drawn as they are
// and every other pill is faded, as their lines are; a pill of a line outside a
// selection is faded too. A line says its count on a pill once it carries more
// than one edge; a line of the node under the pointer, a node's own line and a
// line of a selection's walk say it even when it is one, so the numbers on the
// lines a reader is shown for a node add up to the node's count; such a pill is
// drawn even where its line has no free place for it (`shared/geometry/pillPlaces.js`,
// `crowded`). What a line says is its data's `countLabel` (`widgets/graph-viewer/model/canvasMap.js`):
// during a selection, how many of the walk's edges it carries. The pills of the
// lines between two top-level nodes are placed among what the top level draws
// alone, every box at the top taken as the room it takes closed, its title's
// plate included, whether it is open now or not: opening a box, whose nodes and
// their lines are drawn then and whose title then stands inside it, moves none
// of them. Every other pill is placed around them, except those of a node's own
// lines under the pointer or selected, which are placed first.
//
// A closed box large enough on screen says how many edges come into it and go
// out of it — the ones the budget leaves out included — in a line of small text
// in its lower right corner, where it covers neither its title nor its status
// mark; a box too small for it says nothing, and its lines' pills still do.
//
// A node inside an open box whose outward edges are not drawn at rest says how
// many there are, "+N", on a small badge across the middle of its right side,
// where no line of a layout drawn downwards arrives, and below its status mark
// when it has one; the pointer on the node, or a selection of it, draws those
// edges (`widgets/graph-viewer/model/canvasMap.js`). A node drawn too small to read has no badge.
//
// What the last drawing showed is kept for the test handle: each pill's place on
// the canvas and whether it was faded, the lines whose pill found no place, each
// closed box's tally and each node's "+N", and where they were drawn.

import { idRecord } from "../../../shared/ids/index.js";
import { headEndsOf, headLengthOf, routePointsOf } from "../../../entities/graph-edges/index.js";
import { AGGREGATE, COLLAPSED, GEOMETRY, MAP_MARKS, MAP_TITLE, OUTWARD, OWN_LINE, TALLY } from "../../../shared/map-levels/index.js";
import { PILL_MARKS, pillStagesOf } from "../../../shared/geometry/index.js";
import { BEHIND, IN_FRONT, overlayCanvas } from "../../../shared/canvas-marks/index.js";

/** How opaque a faded pill is drawn. */
const FADED_ALPHA = 0.35;
/** A tally's text size, its weight, the room it keeps from its box's edges and the height of its line, in pixels on screen. */
const TALLY_MARKS = Object.freeze({ size: 10, weight: 500, inset: 6, lineHeight: 1.25 });
/** A "+N" badge's text size and weight, its padding each side, its height, and the least height on screen a node carries one at, in pixels. */
const OUTWARD_MARKS = Object.freeze({ size: 10, weight: 600, padding: 4, height: 14, leastNode: 12 });
/** The text between a tally's two counts. */
const TALLY_JOIN = " · ";
/** A node's shape alone, for what no pill may cover. */
const SHAPE = Object.freeze({ includeLabels: false, includeOverlays: false });
/** A node's title alone. */
const TITLE = Object.freeze({ includeNodes: false, includeEdges: false, includeLabels: true, includeMainLabels: true, includeOverlays: false });

/** A copy of `marks`, a record of flat marks by node id, in a record any id is a key of (`shared/ids`). */
const copyOf = (marks) => idRecord(Object.entries(marks).map(([id, mark]) => [id, { ...mark }]));

const overlaps = (a, b) => a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1;

/** The rectangle around an arrowhead `length` long at `tip`, arriving from `before`. */
function headBoxOf(tip, before, length) {
  const run = Math.hypot(tip.x - before.x, tip.y - before.y) || 1;
  const way = { x: (tip.x - before.x) / run, y: (tip.y - before.y) / run };
  const base = { x: tip.x - way.x * length, y: tip.y - way.y * length };
  const corners = [tip, { x: base.x - (way.y * length) / 2, y: base.y + (way.x * length) / 2 }, { x: base.x + (way.y * length) / 2, y: base.y - (way.x * length) / 2 }];
  const xs = corners.map((p) => p.x);
  const ys = corners.map((p) => p.y);
  return { x1: Math.min(...xs), y1: Math.min(...ys), x2: Math.max(...xs), y2: Math.max(...ys) };
}

/** The ends of `edge` that carry an arrowhead with every box at the top closed: its stub at an open box is a head there. */
function headEndsClosed(edge) {
  if (!edge.data(AGGREGATE)) return { source: false, target: true };
  return { source: edge.data("backward") > 0, target: edge.data("forward") > 0 };
}

/** What a tally says. */
export const tallyTextOf = ({ incoming, outgoing }) => `in ${incoming}${TALLY_JOIN}out ${outgoing}`;

/**
 * The layer of the map's counts over `cy`, in `container`: `{ pills, tallies,
 * destroy }`. `tokens()` gives the resolved theme tokens now, `map()` the map
 * drawn now (`widgets/graph-viewer/model/canvasMap.js`), or null.
 */
export function pillOverlay(cy, container, { tokens, map }) {
  const layer = overlayCanvas(container, "pills");
  const measurer = document.createElement("canvas").getContext("2d");
  let places = { key: null, placed: [], dropped: [] };
  let shown = { pills: [], dropped: [], tallies: idRecord(), outward: idRecord() };

  const pillFont = (look) => `600 ${PILL_MARKS.font}px ${look.font}`;
  const tallyFont = (look) => `${TALLY_MARKS.weight} ${TALLY_MARKS.size}px ${look.font}`;

  /** Whether a line says its count even when it is one: a line of the node under the pointer, a node's own line, a line of a walk. */
  const saysOne = (edge) => edge.hasClass(IN_FRONT) || edge.hasClass("is-walk-edge") || Boolean(edge.data(OWN_LINE));

  /**
   * The rectangles of the arrowheads of `edge`, drawn along `points`, in the
   * graph's coordinates; with `closed`, the ones it carries with every box at the
   * top closed, its end at a box opened now as a stub too (`STUB_AT`).
   */
  function headBoxesOf(edge, points, closed = false) {
    const boxes = [];
    const heads = closed ? headEndsClosed(edge) : headEndsOf(edge);
    const n = points.length;
    if (heads.target) boxes.push(headBoxOf(points[n - 1], points[n - 2], headLengthOf(edge)));
    if (heads.source) boxes.push(headBoxOf(points[0], points[1], headLengthOf(edge)));
    return boxes;
  }

  /**
   * Where each drawn line's pill stands, worked out again when the drawing, the
   * scale's step or the lines that say a count of one change.
   *
   * The lines asked to say their count that are not at the top — a node's own
   * lines, under the pointer or selected — are placed first, among everything
   * drawn. Then the lines at the top, between two top-level nodes as the overview
   * draws them at every level, among what is at the top alone: its leaves and
   * their titles, every box at the top as the room it takes closed, open or not
   * (`closedRoomsOf`), its lines and their arrowheads. Nothing a box opened draws
   * inside it or out of it, such as its nodes' lines to the box that holds
   * everything, moves them. Every other line's pill is placed last, around them all.
   */
  function placesNow(look) {
    const drawn = cy.edges().filter((edge) => edge.visible() && edge.data("route"));
    const lines = drawn.filter((edge) => edge.data(AGGREGATE));
    const ones = lines.filter(saysOne).map((edge) => edge.id());
    const key = `${map()?.version()}|${lines.map((edge) => edge.id()).join(",")}|${ones.join(",")}|${look.font}`;
    if (places.key === key) return places;
    const scale = map()?.scale() || 1;
    const atTop = (element) => map()?.ofTopLevel(element) ?? true;
    const wrapper = map()?.tree.wrapper ?? null;
    const isTopBox = (node) => Boolean(map()?.isTopBox(node.id()));
    // What the top level draws (routes and what no pill covers) and what is drawn below the top; of the top,
    // what stays as it is whichever boxes are open, and every box at the top as the room it takes closed.
    // The box that holds everything takes no room.
    const [topRoutes, belowRoutes, topRooms, belowRooms, topFixed, closedTops] = [[], [], [], [], [], []];
    const pointsOf = new Map();
    drawn.forEach((edge) => {
      const points = routePointsOf(edge);
      pointsOf.set(edge.id(), points);
      const ofTop = atTop(edge);
      (ofTop ? topRoutes : belowRoutes).push({ id: edge.id(), points });
      (ofTop ? topRooms : belowRooms).push(...headBoxesOf(edge, points));
      if (ofTop) topFixed.push(...headBoxesOf(edge, points, true));
    });
    cy.nodes().forEach((node) => {
      if (!node.visible() || node.id() === wrapper) return;
      const ofTop = atTop(node);
      if (ofTop && isTopBox(node)) closedTops.push(...map().closedRoomsOf(node.id()));
      if (node.isParent()) return;
      const shape = node.boundingBox(SHAPE);
      (ofTop ? topRooms : belowRooms).push(shape);
      if (ofTop && !isTopBox(node)) topFixed.push(shape);
    });
    cy.nodes(`[${MAP_TITLE}]`).forEach((node) => {
      if (!node.visible()) return;
      const title = node.boundingBox(TITLE);
      (atTop(node) ? topRooms : belowRooms).push(title);
      if (atTop(node) && !isTopBox(node)) topFixed.push(title);
    });
    const top = { drawn: [topRoutes], blocked: [topFixed, closedTops] };
    const everything = { drawn: [topRoutes, belowRoutes], blocked: [topRooms, belowRooms] };
    const always = new Set(ones);
    const asked = (edges) =>
      edges.map((edge) => {
        const heads = headEndsOf(edge);
        const weight = edge.data("saidWeight") ?? edge.data("weight") ?? 1;
        return { id: edge.id(), text: String(edge.data("countLabel")), weight, always: always.has(edge.id()), points: pointsOf.get(edge.id()), heads: [heads.source, heads.target] };
      });
    const below = lines.filter((edge) => !atTop(edge));
    measurer.font = pillFont(look);
    const { placed, dropped } = pillStagesOf({
      stages: [
        { lines: asked(below.filter((edge) => always.has(edge.id()))), ...everything },
        { lines: asked(lines.filter(atTop)), ...top },
        { lines: asked(below.filter((edge) => !always.has(edge.id()))), ...everything },
      ],
      scale,
      measure: (text) => measurer.measureText(text).width,
    });
    places = { key, placed, dropped };
    return places;
  }

  /** Whether a line is faded now: behind the lines of the node under the pointer, or outside a selection. */
  const fadedLine = (edge) => edge.hasClass(BEHIND) || edge.hasClass("is-dimmed");

  function drawPills(context, look) {
    const zoom = cy.zoom();
    const pan = cy.pan();
    const out = [];
    context.font = pillFont(look);
    context.textAlign = "center";
    context.textBaseline = "middle";
    for (const pill of placesNow(look).placed) {
      const edge = cy.getElementById(pill.id);
      if (edge.empty() || !edge.visible()) continue;
      const [x, y] = [pill.x * zoom + pan.x, pill.y * zoom + pan.y];
      const rect = { x1: x - pill.width / 2, y1: y - pill.height / 2, x2: x + pill.width / 2, y2: y + pill.height / 2 };
      const faded = fadedLine(edge);
      context.globalAlpha = faded ? FADED_ALPHA : 1;
      context.beginPath();
      context.roundRect(rect.x1, rect.y1, pill.width, pill.height, pill.height / 2);
      context.fillStyle = look.bg;
      context.fill();
      context.lineWidth = 1;
      context.strokeStyle = edge.style("line-color");
      context.stroke();
      context.fillStyle = look.text1;
      context.fillText(pill.text, x, y + 0.5);
      out.push({ id: pill.id, text: pill.text, ...rect, fontSize: PILL_MARKS.font, faded, crowded: pill.crowded });
    }
    context.globalAlpha = 1;
    return out;
  }

  /** The place of `node`'s tally on screen, or null when its box has no room for it clear of its title and its mark. */
  function tallyPlaceOf(node, width) {
    const box = node.renderedBoundingBox(SHAPE);
    const height = TALLY_MARKS.size * TALLY_MARKS.lineHeight;
    const rect = { x1: box.x2 - TALLY_MARKS.inset - width, y1: box.y2 - TALLY_MARKS.inset - height, x2: box.x2 - TALLY_MARKS.inset, y2: box.y2 - TALLY_MARKS.inset };
    if (rect.x1 < box.x1 + TALLY_MARKS.inset || rect.y1 < box.y1 + TALLY_MARKS.inset) return null;
    const title = node.renderedBoundingBox(TITLE);
    if (node.data(MAP_TITLE) && overlaps(rect, title)) return null;
    const corner = MAP_MARKS.statusMarkInset + MAP_MARKS.statusMark + TALLY_MARKS.inset;
    const mark = node.data("status") ? { x1: box.x2 - corner, y1: box.y1, x2: box.x2, y2: box.y1 + corner } : null;
    return mark && overlaps(rect, mark) ? null : rect;
  }

  /** Draw each closed box's tally; what each says, by the box's id, in a record any id is a key of (`shared/ids`). */
  function drawTallies(context, look) {
    const out = idRecord();
    context.font = tallyFont(look);
    context.textAlign = "right";
    context.textBaseline = "bottom";
    cy.nodes(`.${COLLAPSED}[${TALLY}]`).forEach((node) => {
      if (!node.visible()) return;
      const tally = node.data(TALLY);
      const text = tallyTextOf(tally);
      const rect = tallyPlaceOf(node, context.measureText(text).width);
      out[node.id()] = { ...tally, text, shown: Boolean(rect), ...(rect || {}) };
      if (!rect) return;
      context.globalAlpha = node.hasClass("is-dimmed") ? FADED_ALPHA : 1;
      context.fillStyle = look.text2;
      context.fillText(text, rect.x2, rect.y2);
    });
    context.globalAlpha = 1;
    return out;
  }

  /**
   * Draw each "+N" badge of a drawn node, across the middle of its right side;
   * one on a node too small to read is not drawn. What each says, by the node's
   * id, in a record any id is a key of (`shared/ids`).
   */
  function drawOutward(context, look) {
    const out = idRecord();
    context.font = `${OUTWARD_MARKS.weight} ${OUTWARD_MARKS.size}px ${look.font}`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    cy.nodes(`[${OUTWARD}]`).forEach((node) => {
      if (!node.visible()) return;
      const count = node.data(OUTWARD);
      const text = `+${count}`;
      const box = node.renderedBoundingBox(SHAPE);
      const width = context.measureText(text).width + 2 * OUTWARD_MARKS.padding;
      // Below the status mark in the corner above it, when the node has one.
      const markEnd = node.data("status") ? box.y1 + (GEOMETRY.statusMarkInset + GEOMETRY.statusMark) * cy.zoom() + 1 : -Infinity;
      const y = Math.max((box.y1 + box.y2) / 2, markEnd + OUTWARD_MARKS.height / 2);
      const rect = { x1: box.x2 - width / 2, y1: y - OUTWARD_MARKS.height / 2, x2: box.x2 + width / 2, y2: y + OUTWARD_MARKS.height / 2 };
      const readable = box.y2 - box.y1 >= OUTWARD_MARKS.leastNode;
      out[node.id()] = { count, text, shown: readable, ...rect };
      if (!readable) return;
      context.globalAlpha = node.hasClass("is-dimmed") ? FADED_ALPHA : 1;
      context.beginPath();
      context.roundRect(rect.x1, rect.y1, width, OUTWARD_MARKS.height, OUTWARD_MARKS.height / 2);
      context.fillStyle = look.bg;
      context.fill();
      context.lineWidth = 1;
      context.strokeStyle = look.text2;
      context.stroke();
      context.fillStyle = look.text1;
      context.fillText(text, (rect.x1 + rect.x2) / 2, y + 0.5);
    });
    context.globalAlpha = 1;
    return out;
  }

  function draw() {
    const context = layer.begin();
    const look = tokens();
    if (!look || !map()) {
      shown = { pills: [], dropped: [], tallies: idRecord(), outward: idRecord() };
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const pills = drawPills(context, look);
    const tallies = drawTallies(context, look);
    const outward = drawOutward(context, look);
    shown = { pills, dropped: [...places.dropped], tallies, outward };
    if (pills.length || [...Object.values(tallies), ...Object.values(outward)].some((mark) => mark.shown)) layer.drew();
  }

  cy.on("render", draw);
  return {
    /** The pills drawn last, `{ pills: [{ id, text, x1, y1, x2, y2, fontSize, faded, crowded }], dropped }`, on the canvas in pixels. */
    pills: () => ({ pills: shown.pills.map((pill) => ({ ...pill })), dropped: [...shown.dropped] }),
    /** Each closed box's tally, `{ id: { incoming, outgoing, text, shown, x1, y1, x2, y2 } }`, on the canvas in pixels. */
    tallies: () => copyOf(shown.tallies),
    /** Each drawn node's "+N", `{ id: { count, text, shown, x1, y1, x2, y2 } }`, on the canvas in pixels. */
    outward: () => copyOf(shown.outward),
    destroy() {
      cy.removeListener("render", draw);
      layer.remove();
    },
  };
}
