// beadloom:component=site-graph-viewer
// The map's counts drawn over the canvas: each line's count on a pill, how many edges come into a closed box and go out of it, and a node's "+N".
//
// Cytoscape draws an edge's label with its edge, so the next edge drawn paints
// over it. A line's count is drawn instead on a canvas of its own laid over every
// line, the followed ones included (`overlayCanvas.js`), as a pill: an opaque
// rounded label with a thin border in the line's colour, at the place
// `lib/pillPlaces.js` finds on its line, worked out again only when what is
// drawn or the step of the map's scale changes. A pill keeps one size on screen.
// While the pointer rests on a node, the pills of its lines are drawn as they are
// and every other pill is faded, as their lines are; a pill of a line outside a
// selection is faded too.
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
// edges (`canvasMap.js`). A node drawn too small to read has no badge.
//
// What the last drawing showed is kept for the test handle: each pill's place on
// the canvas and whether it was faded, the lines whose pill found no place, each
// closed box's tally and each node's "+N", and where they were drawn.

import { headEndsOf } from "../lib/heads.js";
import { AGGREGATE, COLLAPSED } from "../lib/levels.js";
import { headLengthOf, routePointsOf } from "../lib/lineMarks.js";
import { MAP_MARKS, MAP_TITLE, OUTWARD, TALLY } from "../lib/mapMarks.js";
import { GEOMETRY } from "../lib/stylesheet.js";
import { PILL_MARKS, pillPlacesOf } from "../lib/pillPlaces.js";
import { BEHIND } from "./canvasMarks.js";
import { overlayCanvas } from "./overlayCanvas.js";

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

/** What a tally says. */
export const tallyTextOf = ({ incoming, outgoing }) => `in ${incoming}${TALLY_JOIN}out ${outgoing}`;

/**
 * The layer of the map's counts over `cy`, in `container`: `{ pills, tallies,
 * destroy }`. `tokens()` gives the resolved theme tokens now, `map()` the map
 * drawn now (`canvasMap.js`), or null.
 */
export function pillOverlay(cy, container, { tokens, map }) {
  const layer = overlayCanvas(container, "pills");
  const measurer = document.createElement("canvas").getContext("2d");
  let places = { key: null, placed: [], dropped: [] };
  let shown = { pills: [], dropped: [], tallies: {}, outward: {} };

  const pillFont = (look) => `600 ${PILL_MARKS.font}px ${look.font}`;
  const tallyFont = (look) => `${TALLY_MARKS.weight} ${TALLY_MARKS.size}px ${look.font}`;

  /** Where each drawn line's pill stands, worked out again when the drawing or the scale's step changes. */
  function placesNow(look) {
    const drawn = cy.edges().filter((edge) => edge.visible() && edge.data("route"));
    const lines = drawn.filter((edge) => edge.data(AGGREGATE));
    const key = `${map()?.version()}|${lines.map((edge) => edge.id()).join(",")}|${look.font}`;
    if (places.key === key) return places;
    const scale = map()?.scale() || 1;
    const routes = drawn.map((edge) => ({ id: edge.id(), points: routePointsOf(edge) }));
    const blocked = cy.nodes().filter((node) => node.visible() && !node.isParent()).map((node) => node.boundingBox(SHAPE));
    cy.nodes(`[${MAP_TITLE}]`).filter((node) => node.visible()).forEach((node) => blocked.push(node.boundingBox(TITLE)));
    for (const edge of drawn) {
      const points = routePointsOf(edge);
      const heads = headEndsOf(edge);
      const n = points.length;
      if (heads.target) blocked.push(headBoxOf(points[n - 1], points[n - 2], headLengthOf(edge)));
      if (heads.source) blocked.push(headBoxOf(points[0], points[1], headLengthOf(edge)));
    }
    measurer.font = pillFont(look);
    const { placed, dropped } = pillPlacesOf({
      lines: lines.map((edge) => {
        const heads = headEndsOf(edge);
        return { id: edge.id(), text: String(edge.data("countLabel")), weight: edge.data("weight") || 1, points: routePointsOf(edge), heads: [heads.source, heads.target] };
      }),
      drawn: routes,
      blocked,
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
      out.push({ id: pill.id, text: pill.text, ...rect, fontSize: PILL_MARKS.font, faded });
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

  function drawTallies(context, look) {
    const out = {};
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

  /** Draw each "+N" badge of a drawn node, across the middle of its right side; one on a node too small to read is not drawn. */
  function drawOutward(context, look) {
    const out = {};
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
      shown = { pills: [], dropped: [], tallies: {}, outward: {} };
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
    /** The pills drawn last, `{ pills: [{ id, text, x1, y1, x2, y2, fontSize, faded }], dropped }`, on the canvas in pixels. */
    pills: () => ({ pills: shown.pills.map((pill) => ({ ...pill })), dropped: [...shown.dropped] }),
    /** Each closed box's tally, `{ id: { incoming, outgoing, text, shown, x1, y1, x2, y2 } }`, on the canvas in pixels. */
    tallies: () => JSON.parse(JSON.stringify(shown.tallies)),
    /** Each drawn node's "+N", `{ id: { count, text, shown, x1, y1, x2, y2 } }`, on the canvas in pixels. */
    outward: () => JSON.parse(JSON.stringify(shown.outward)),
    destroy() {
      cy.removeListener("render", draw);
      layer.remove();
    },
  };
}
