// beadloom:component=site-graph-viewer
// The bridges drawn over the canvas: a hop on a highlighted edge wherever it crosses another drawn edge.
//
// The highlighted edges are the ones the canvas marks as followed: every edge
// along a hovered line, and every edge of a selection's walk (a neighbourhood or
// an impact). Where one of them crosses another edge drawn now — an edge of the
// data file or an aggregated edge of the map — a bridge is drawn on it
// (`lib/bridges.js`); with nothing highlighted, nothing is.
//
// What is drawn follows what Cytoscape draws. The crossings are found again when
// the highlighted edges or the edges drawn change: a hover, a selection, a
// filter, a hidden neighbourhood, a level of the map. An edge's crossings are
// found once for the edges drawn, so a hover that adds one edge to a selection
// looks for that edge's alone. The colours are read again after every refresh,
// so a theme switch or a selection that fades an edge repaints them
// (`lib/bridgePaint.js`). The bridges themselves are drawn on a canvas of their
// own above Cytoscape's (`overlayCanvas.js`) whenever Cytoscape renders, so they
// move with every pan and zoom.
//
// Drawing them must not cost a frame: the crossings are never looked for while
// the view moves; a bridge outside the view is skipped, and so is a hop too small
// to see at the zoom drawn now, so at the whole-graph fit of a full drawing none
// is drawn; and a bridge's colours are read only when it is first drawn. The
// time each frame's drawing took is kept for the test handle.

import { bridgesOf, crossingIndexOf, crossingsAlong } from "../lib/bridges.js";
import { colourAlong, colourUnder, hopRadius } from "../lib/bridgePaint.js";
import { pathOfSegments } from "../lib/routes.js";
import { gridIndex } from "../lib/spatialIndex.js";
import { HIGHLIGHTED_EDGES } from "./canvasMarks.js";
import { overlayCanvas } from "./overlayCanvas.js";

/** How many of the last frames' drawing times are kept. */
const FRAMES_KEPT = 240;
/** The side of a cell of the index over the drawn nodes, in layout units. */
const NODE_CELL = 512;
/** How much wider than the highlighted line the gap erased around a crossing is, on each side, in pixels. */
const ERASE_MARGIN = 1;
/** The stops of a gradient line, as Cytoscape gives them in one string. */
const STOP_SEPARATOR = /\s+(?=rgb|#|hsl)/;

const idsOf = (collection) => collection.map((element) => element.id());

/** Whether `edge` is drawn now along a route: shown, and routed rather than a curve. */
const isDrawnRoute = (edge) => Boolean(edge.data("route")) && edge.visible();

/** The polyline `edge` is drawn along, in the graph's coordinates, from its source end to its target end. */
function polylineOf(edge) {
  return pathOfSegments(edge.data("route"), edge.source().position(), edge.target().position());
}

/** How Cytoscape strokes `edge` along `points`: `{ width, colourAt(point) }`. */
function strokeOf(edge, points) {
  const width = parseFloat(edge.style("width"));
  if (edge.style("line-fill") !== "linear-gradient") {
    const colour = edge.style("line-color");
    return { width, colourAt: () => colour };
  }
  const stops = String(edge.style("line-gradient-stop-colors")).split(STOP_SEPARATOR);
  const positions = String(edge.style("line-gradient-stop-positions"))
    .split(/\s+/)
    .map((value) => parseFloat(value) / 100);
  const [start, end] = [points[0], points[points.length - 1]];
  return { width, colourAt: (point) => colourAlong(stops, positions, start, end, point) };
}

/** The drawn nodes of `cy` by place, each with its depth: what tints the canvas under a point. */
function nodesByPlace(cy) {
  const index = gridIndex(NODE_CELL);
  cy.nodes().forEach((node) => {
    if (!node.visible()) return;
    index.insert({ node, depth: node.ancestors().length }, node.boundingBox({ includeLabels: false, includeOverlays: false }));
  });
  return index;
}

/** The tints over the canvas at `point`, the outermost first: each drawn node's fill there. */
function tintsAt(nodes, point) {
  const found = [];
  nodes.query({ x1: point.x, y1: point.y, x2: point.x, y2: point.y }, (item) => found.push(item));
  return found
    .sort((a, b) => a.depth - b.depth)
    .map(({ node }) => ({
      colour: node.style("background-color"),
      alpha: parseFloat(node.style("background-opacity")) * node.effectiveOpacity(),
    }));
}

/**
 * What the bridges `found` over `crossings` are painted with in `cy` now, read
 * once per edge and per bridge, and only when asked: `{ widthOf(id), widest(),
 * of(bridge), ms }`. `widthOf` gives an edge's drawn width, and `widest` the
 * widest of the edges the bridges join; `of` gives `bridge` with both lines'
 * widths and colours at its place and the colour under it; `ms()` how long
 * reading the colours took so far. A hop out of view or too small to see is
 * never painted, so a selection with thousands of crossings costs only what is
 * drawn.
 */
function painterOf(cy, crossings, found, background) {
  const strokes = new Map();
  const painted = new Map();
  let nodes = null;
  let widest = null;
  let ms = 0;
  const strokeFor = (id) => {
    if (!strokes.has(id)) strokes.set(id, strokeOf(cy.getElementById(id), crossings.runs.get(id)));
    return strokes.get(id);
  };
  return {
    widthOf: (id) => strokeFor(id).width,
    widest() {
      if (widest === null) {
        const ids = new Set(found.flatMap(({ edge, crossed }) => [edge, crossed]));
        widest = Math.max(0, ...[...ids].map((id) => strokeFor(id).width));
      }
      return widest;
    },
    of(bridge) {
      if (painted.has(bridge)) return painted.get(bridge);
      const started = performance.now();
      nodes ||= nodesByPlace(cy);
      const own = strokeFor(bridge.edge);
      const crossed = strokeFor(bridge.crossed);
      const paint = {
        ...bridge,
        width: own.width,
        colour: own.colourAt(bridge),
        crossedWidth: crossed.width,
        crossedColour: crossed.colourAt(bridge),
        under: colourUnder(background(), tintsAt(nodes, bridge)),
      };
      painted.set(bridge, paint);
      ms += performance.now() - started;
      return paint;
    },
    ms: () => ms,
  };
}

/**
 * The bridges of `cy` drawn over `container`: `{ refresh, bridges, frames, destroy }`.
 *
 * `siblings` maps an edge's id to the ids it shares a bundle with
 * (`lib/bridges.js`, `siblingsOf`); `background()` gives the canvas's background
 * colour now. Call `refresh()` whenever the highlighted edges, the edges drawn or
 * their looks change. `bridges()` gives `[{ edge, crossings }]`, one entry per
 * highlighted edge drawn, each crossing `{ x, y, crossed, colour, crossedColour,
 * under }`; `frames()` gives `{ findMs, paintMs, frames }`, how long the
 * crossings took to find the last time they changed, how long their colours
 * have taken to read since the last refresh, and for each recent frame `{ at, ms, drawn }`: when it was drawn
 * (`performance.now()`), how long the bridges took, and how many were drawn.
 */
export function bridgeOverlay(cy, container, { siblings, background }) {
  const layer = overlayCanvas(container, "bridges");
  let drawnKey = "";
  let routesSeen = new Map();
  let crossings = crossingIndexOf([]);
  let along = new Map();
  let litKey = "";
  let lit = [];
  let found = [];
  let paints = painterOf(cy, crossings, found, background);
  let findMs = 0;
  const frames = [];

  /** Index the routes drawn now, when they differ from the ones indexed. */
  function indexDrawn() {
    const drawn = cy.edges().filter(isDrawnRoute);
    const key = idsOf(drawn).join("\n");
    if (key === drawnKey && drawn.every((edge) => routesSeen.get(edge.id()) === edge.data("route"))) return false;
    drawnKey = key;
    routesSeen = new Map(drawn.map((edge) => [edge.id(), edge.data("route")]));
    crossings = crossingIndexOf(drawn.map((edge) => ({ id: edge.id(), points: polylineOf(edge) })));
    along = new Map();
    return true;
  }

  /** The crossings of the drawn edge `id`, found once for the routes indexed. */
  function crossingsOf(id) {
    if (!along.has(id)) along.set(id, crossingsAlong(crossings, id, siblings));
    return along.get(id);
  }

  function refresh() {
    const highlighted = cy.edges(HIGHLIGHTED_EDGES).filter(isDrawnRoute);
    if (highlighted.empty()) {
      litKey = "";
      lit = [];
      found = [];
    } else {
      const started = performance.now();
      const changed = indexDrawn();
      const ids = idsOf(highlighted).sort();
      const key = ids.join("\n");
      if (changed || key !== litKey) {
        litKey = key;
        lit = ids;
        found = bridgesOf(new Set(ids), crossingsOf);
        findMs = performance.now() - started;
      }
    }
    // The looks may have changed with the classes or the theme: they are read again when drawn.
    paints = painterOf(cy, crossings, found, background);
    draw();
  }

  function drawBridge(context, bridge, radius, margin) {
    const { x, y } = bridge;
    const [ux, uy] = bridge.horizontal ? [1, 0] : [0, 1];
    // The highlighted line erased around the crossing, in what lies under it.
    context.strokeStyle = bridge.under;
    context.lineWidth = bridge.width + 2 * margin;
    context.beginPath();
    context.moveTo(x - ux * radius, y - uy * radius);
    context.lineTo(x + ux * radius, y + uy * radius);
    context.stroke();
    // The crossed line drawn again through the gap.
    const reach = bridge.width / 2 + 2 * margin;
    context.strokeStyle = bridge.crossedColour;
    context.lineWidth = bridge.crossedWidth;
    context.beginPath();
    context.moveTo(x - uy * reach, y - ux * reach);
    context.lineTo(x + uy * reach, y + ux * reach);
    context.stroke();
    // The hop: over a vertical line it rises, past a horizontal one it bows to the right.
    context.strokeStyle = bridge.colour;
    context.lineWidth = bridge.width;
    context.beginPath();
    if (bridge.horizontal) context.arc(x, y, radius, Math.PI, 2 * Math.PI);
    else context.arc(x, y, radius, -Math.PI / 2, Math.PI / 2);
    context.stroke();
  }

  function draw() {
    const started = performance.now();
    const context = layer.begin();
    let drawn = 0;
    const zoom = cy.zoom();
    // The widest hop, over the widest line by the widest: when even it is too
    // small to see, no hop is drawn; else no hop farther outside the view than it reaches in.
    const widest = found.length ? hopRadius(zoom, paints.widest(), paints.widest()) : 0;
    if (widest) {
      const extent = cy.extent();
      const reach = widest / zoom;
      layer.inGraph(cy);
      context.lineCap = "butt";
      for (const bridge of found) {
        const { x, y } = bridge;
        if (x < extent.x1 - reach || x > extent.x2 + reach || y < extent.y1 - reach || y > extent.y2 + reach) continue;
        const onScreen = hopRadius(zoom, paints.widthOf(bridge.edge), paints.widthOf(bridge.crossed));
        if (!onScreen) continue;
        const radius = onScreen / zoom;
        if (x + radius < extent.x1 || x - radius > extent.x2 || y + radius < extent.y1 || y - radius > extent.y2) continue;
        drawBridge(context, paints.of(bridge), radius, ERASE_MARGIN / zoom);
        drawn += 1;
      }
      if (drawn) layer.drew();
    }
    frames.push({ at: started, ms: performance.now() - started, drawn });
    if (frames.length > FRAMES_KEPT) frames.shift();
  }

  function bridges() {
    const byEdge = new Map(lit.map((id) => [id, []]));
    for (const bridge of found) {
      const { edge, crossed, x, y, colour, crossedColour, under } = paints.of(bridge);
      byEdge.get(edge)?.push({ x, y, crossed, colour, crossedColour, under });
    }
    return [...byEdge].map(([edge, list]) => ({ edge, crossings: list }));
  }

  cy.on("render", draw);
  return {
    refresh,
    bridges,
    frames: () => ({ findMs, paintMs: paints.ms(), frames: frames.map((frame) => ({ ...frame })) }),
    destroy() {
      cy.removeListener("render", draw);
      layer.remove();
    },
  };
}
