// beadloom:component=site-graph-viewer
// The followed lines drawn over the canvas: every edge along a hovered line and on a selection's walk, on top of what they cross.
//
// A reader follows one line through a busy area by seeing it whole. The lines
// the canvas marks as followed (`canvasMarks.js`, `HIGHLIGHTED_EDGES`) are drawn
// again on a canvas of their own above Cytoscape's (`overlayCanvas.js`), in their
// full colour, over a casing in the canvas's background colour that clears what
// they cross. A hop drawn on the followed line where it crosses another, as a
// classic diagram draws one, erases a notch out of the line it hops and reads as
// a repair; a line drawn whole on top of the others does not.
//
// The drawing goes in passes: every casing, then every line, then the
// arrowheads, then the title of each open box a followed line runs through,
// then the label of the edge under the pointer, the one line that shows its
// kind. A box's title sits in the room ELK keeps at the box's top, clear of its
// children, and a line into a node of the first row can only arrive through it:
// such a title is drawn again over the lines, on a patch of the box's own fill,
// so the line runs under the title instead of striking it out. A line of the map's shows no label here: its count is on its
// pill, drawn above this layer (`pillOverlay.js`), and in the note the viewer
// shows while the pointer is on it. A bundle's lines run together and part, and a line drawn with
// its own casing would cut a slit into the one drawn before it where they part;
// drawn in passes, every casing lies under every line. A followed line is drawn
// as Cytoscape draws it — the same route, the same corners, the same sizes on
// screen, a dashed line's pattern ending a dash inside its head
// (`lib/lineMarks.js`) — and always with its arrowhead, also where it shares its
// last run with a line that carries the head at rest.
//
// What is followed is read again on `refresh`, whenever the hover, the
// selection, the level, the filters or the theme change, and drawn whenever
// Cytoscape renders, so it moves with every pan and zoom; a line out of view is
// skipped. The time each frame took is kept for the test handle (`frames`), and
// so is what the last refresh made of the lines followed (`followed`).

import { EDGE_STYLES, dashOf } from "../../../entities/graph-edge/index.js";
import { mixRgb } from "../../../shared/theme-tokens/index.js";
import { edgePaletteOf } from "../lib/edgePalette.js";
import { crossesAny } from "../lib/grownBoxes.js";
import { NO_SOURCE_HEAD, NO_TARGET_HEAD, headEndsOf } from "../lib/heads.js";
import { AGGREGATE, COLLAPSED } from "../lib/levels.js";
import { LINE_MARKS, cornerRadiiOf, dashOffsetOf, endHeadLength, headLengthOf, lineWidthOf, routePointsOf } from "../lib/lineMarks.js";
import { MAP_TITLE, scaleOf } from "../lib/mapMarks.js";
import { HIGHLIGHTED_EDGES, HOVERED } from "./canvasMarks.js";
import { overlayCanvas } from "./overlayCanvas.js";

/** How many of the last frames' drawing times are kept. */
const FRAMES_KEPT = 240;
/** The passes a frame is drawn in, in order. */
const PASSES = Object.freeze(["casings", "lines", "heads", "titles", "labels"]);
/** A node's main label alone, in the graph's coordinates. */
const TITLE_BOUNDS = Object.freeze({ includeNodes: false, includeEdges: false, includeLabels: true, includeMainLabels: true, includeOverlays: false });
/** What Cytoscape ends a title too wide for its room with. */
const ELLIPSIS = "\u2026";
/** A label's size and its plate's padding, in pixels on screen. */
const LABEL = Object.freeze({ size: 11, padding: 2, plateOpacity: 0.9 });
/** The arrowhead a line of the map's draws, whatever the edges it carries. */
const AGGREGATE_ARROW = "triangle";

const distance = (p, q) => Math.hypot(q.x - p.x, q.y - p.y);
const point = ({ x, y }) => ({ x, y });

/** The unit vector from `from` towards `to`. */
function unit(from, to) {
  const length = distance(from, to) || 1;
  return { x: (to.x - from.x) / length, y: (to.y - from.y) / length };
}

/**
 * How `edge` is drawn, in the graph's coordinates: a routed line is its ends and
 * corners with each corner's radius, a curve (a loop) its ends and Cytoscape's
 * control points.
 */
function shapeOf(edge) {
  if (edge.data("route")) {
    return { routed: true, points: routePointsOf(edge) };
  }
  const controls = edge.controlPoints() || [];
  return { routed: false, points: [edge.sourceEndpoint(), ...controls, edge.targetEndpoint()].map(point) };
}

/**
 * `text` as Cytoscape draws it in `maxWidth` by `measure(text)`: whole when it
 * fits, else as many of its first characters as fit with an ellipsis after them.
 */
function ellipsizedOf(text, maxWidth, measure) {
  if (measure(text) < maxWidth) return text;
  let kept = "";
  for (const character of text) {
    if (measure(kept + character + ELLIPSIS) > maxWidth) return kept + ELLIPSIS;
    kept += character;
  }
  return kept;
}

/**
 * The colour open box `node` is drawn in over the canvas's background `bg`:
 * the tint of every box that holds it laid over the background in turn, then its own.
 */
function drawnFillOf(node, bg) {
  let under = bg;
  for (const box of [...node.ancestors().toArray().reverse(), node]) {
    const tinted = mixRgb(box.style("background-color"), under, parseFloat(box.style("background-opacity")));
    under = mixRgb(tinted, under, parseFloat(box.style("opacity")));
  }
  return under;
}

/** The rectangle around `points`, grown by `margin`. */
function boundsOf(points, margin) {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  return { x1: Math.min(...xs) - margin, y1: Math.min(...ys) - margin, x2: Math.max(...xs) + margin, y2: Math.max(...ys) + margin };
}

/** The radius a corner of `radius` is drawn at between its runs: Cytoscape keeps a rounding within half of either run. */
function clampedRadius(before, corner, after, radius) {
  const [u, v] = [unit(corner, before), unit(corner, after)];
  const half = Math.acos(Math.max(-1, Math.min(1, u.x * v.x + u.y * v.y))) / 2;
  if (half < 1e-3 || Math.PI / 2 - half < 1e-3) return 0;
  const tangent = Math.tan(half);
  const limit = Math.min(distance(corner, before), distance(corner, after)) / 2;
  return Math.min(radius, limit * tangent);
}

/** Trace a routed line through `points`, its corners rounded by `radii`, ending `cut` short of each end named. */
function traceRoute(context, points, radii, cut) {
  const n = points.length;
  const start = cut.source ? along(points[0], points[1], cut.source) : points[0];
  const end = cut.target ? along(points[n - 1], points[n - 2], cut.target) : points[n - 1];
  context.moveTo(start.x, start.y);
  for (let i = 1; i < n - 1; i += 1) {
    const r = clampedRadius(points[i - 1], points[i], points[i + 1], radii[i - 1] || 0);
    if (r > 0) context.arcTo(points[i].x, points[i].y, points[i + 1].x, points[i + 1].y, r);
    else context.lineTo(points[i].x, points[i].y);
  }
  context.lineTo(end.x, end.y);
}

/** Trace a curve as Cytoscape draws one through control points: quadratic pieces through their middles. */
function traceCurve(context, points) {
  const [start, ...rest] = points;
  const end = rest.pop();
  context.moveTo(start.x, start.y);
  if (!rest.length) {
    context.lineTo(end.x, end.y);
    return;
  }
  for (let i = 0; i < rest.length - 1; i += 1) {
    const middle = { x: (rest[i].x + rest[i + 1].x) / 2, y: (rest[i].y + rest[i + 1].y) / 2 };
    context.quadraticCurveTo(rest[i].x, rest[i].y, middle.x, middle.y);
  }
  const last = rest[rest.length - 1];
  context.quadraticCurveTo(last.x, last.y, end.x, end.y);
}

/** The point `length` from `from` towards `to`. */
function along(from, to, length) {
  const d = unit(from, to);
  return { x: from.x + d.x * length, y: from.y + d.y * length };
}

/**
 * How far short of its end at `end` a followed line is drawn: halfway into its
 * own head, at the base of another line's head where it starts at one, and
 * otherwise all the way.
 */
function cutAt(line, end, head) {
  if (line.heads[end]) return head / 2;
  return line.shape.routed && line.edge.hasClass(end === "source" ? NO_SOURCE_HEAD : NO_TARGET_HEAD) ? endHeadLength(line.edge, end) : 0;
}

/** The outline of an arrowhead `length` long with its tip at `tip`, arriving from `from`: a triangle, or a vee. */
function headOutline(tip, from, length, shape) {
  const d = unit(from, tip);
  const n = { x: -d.y, y: d.x };
  const base = { x: tip.x - d.x * length, y: tip.y - d.y * length };
  const left = { x: base.x + (n.x * length) / 2, y: base.y + (n.y * length) / 2 };
  const right = { x: base.x - (n.x * length) / 2, y: base.y - (n.y * length) / 2 };
  if (shape !== "vee") return [tip, left, right];
  return [tip, left, { x: tip.x - (d.x * length) / 2, y: tip.y - (d.y * length) / 2 }, right];
}

/**
 * The layer of followed lines over `cy`, in `container`: `{ refresh, followed,
 * labelled, frames, destroy }`.
 *
 * `tokens()` gives the resolved theme tokens now (`shared/theme-tokens`). Call
 * `refresh()` whenever the followed lines, the lines drawn or their looks change.
 * `followed()` gives `{ edges, passes }`: each followed line `{ id, colour,
 * casing, width }` and each pass with the ids it draws, the titles' pass with
 * the lines it is drawn over and the boxes whose titles it draws (`boxes`); `labelled()` the ids of
 * the lines whose label is drawn; `frames()` `{ frames }`, each recent frame
 * `{ at, ms, drawn }`: when it was drawn (`performance.now()`), how long it took,
 * and how many lines it drew.
 */
export function followedOverlay(cy, container, { tokens }) {
  const layer = overlayCanvas(container, "followed");
  const frames = [];
  let lines = [];
  let titles = [];
  let look = null;

  /** What `edge` is drawn as when it is followed, read once per refresh. */
  function lineOf(edge, palette) {
    const shape = shapeOf(edge);
    const styleKey = edge.data("styleKey");
    const aggregated = Boolean(edge.data(AGGREGATE));
    const heads = shape.routed ? headEndsOf(edge) : { source: false, target: true };
    const label = !aggregated && edge.hasClass(HOVERED) ? edge.data("label") : "";
    return {
      edge,
      id: edge.id(),
      shape,
      heads,
      label,
      arrow: aggregated ? AGGREGATE_ARROW : EDGE_STYLES[styleKey]?.arrow || AGGREGATE_ARROW,
      dash: aggregated ? [] : dashOf(EDGE_STYLES[styleKey] || {}),
      colour: palette[styleKey]?.full || look.text1,
    };
  }

  function refresh() {
    look = tokens();
    if (!look) {
      lines = [];
    } else {
      const palette = edgePaletteOf(look);
      lines = cy
        .edges(HIGHLIGHTED_EDGES)
        .filter((edge) => edge.visible())
        .map((edge) => lineOf(edge, palette))
        .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    }
    titles = lines.length ? titlesUnder(lines) : [];
    draw();
  }

  /**
   * The titles of the open boxes a line of `lines` runs through, each with what
   * draws it again: `{ id, rect, text, x, y, font, colour, fill, under }`, its
   * place and size in the graph's coordinates and the lines that run through it.
   * A title on a plate outside its box is the map's, and no line runs under it.
   */
  function titlesUnder(followedLines) {
    const measurer = document.createElement("canvas").getContext("2d");
    return cy
      .nodes(":parent")
      .filter((node) => node.visible() && !node.hasClass(COLLAPSED) && !node.data(MAP_TITLE) && Boolean(node.style("label")))
      .map((node) => {
        const rect = node.boundingBox(TITLE_BOUNDS);
        const under = followedLines.filter((line) => crossesAny(rect, [line.shape.points])).map((line) => line.id);
        if (!under.length) return null;
        const font = `${node.style("font-weight")} ${node.pstyle("font-size").pfValue}px ${node.style("font-family")}`;
        measurer.font = font;
        const fill = drawnFillOf(node, look.bg);
        const opacity = parseFloat(node.style("opacity")) * parseFloat(node.style("text-opacity"));
        const box = node.boundingBox({ includeLabels: false, includeOverlays: false });
        return {
          id: node.id(),
          rect,
          text: ellipsizedOf(String(node.style("label")), node.pstyle("text-max-width").pfValue, (text) => measurer.measureText(text).width),
          // Where Cytoscape draws a title above its box's top, moved in by its margin, its bottom on that line.
          x: node.position().x + node.pstyle("text-margin-x").pfValue,
          y: box.y1 + node.pstyle("text-margin-y").pfValue,
          font,
          colour: mixRgb(node.style("color"), fill, opacity),
          fill,
          under,
        };
      })
      .filter(Boolean)
      .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  /** Draw each title a followed line runs through again, over the lines, on a patch of its box's fill. */
  function drawTitles(context) {
    context.textAlign = "center";
    context.textBaseline = "bottom";
    for (const title of titles) {
      context.fillStyle = title.fill;
      context.fillRect(title.rect.x1, title.rect.y1, title.rect.x2 - title.rect.x1, title.rect.y2 - title.rect.y1);
      context.font = title.font;
      context.fillStyle = title.colour;
      context.fillText(title.text, title.x, title.y);
    }
  }

  /** The sizes `line` is drawn at now, in layout units, at the map's scale its edge carries. */
  function sizesOf(line) {
    const scale = scaleOf(line.edge);
    const head = headLengthOf(line.edge);
    return {
      scale,
      width: lineWidthOf(line.edge),
      casing: LINE_MARKS.casing * scale,
      head,
      radii: line.shape.routed ? cornerRadiiOf(line.shape.points, scale, line.heads, head) : [],
      cut: { source: cutAt(line, "source", head), target: cutAt(line, "target", head) },
      dashOffset: line.dash.length ? dashOffsetOf(line.edge, line.dash.map((length) => length * scale), line.arrow, { pullback: head / 2 }) : 0,
    };
  }

  function trace(context, line, sizes) {
    context.beginPath();
    if (line.shape.routed) traceRoute(context, line.shape.points, sizes.radii, sizes.cut);
    else traceCurve(context, line.shape.points);
  }

  /** The arrowheads of `line`, each an outline. */
  function headsOf(line, sizes) {
    const points = line.shape.points;
    const n = points.length;
    const outlines = [];
    if (line.heads.target) outlines.push(headOutline(points[n - 1], points[n - 2], sizes.head, line.arrow));
    if (line.heads.source) outlines.push(headOutline(points[0], points[1], sizes.head, line.arrow));
    return outlines;
  }

  function fillOutline(context, outline) {
    context.beginPath();
    context.moveTo(outline[0].x, outline[0].y);
    for (const corner of outline.slice(1)) context.lineTo(corner.x, corner.y);
    context.closePath();
  }

  function drawLabel(context, line, sizes) {
    const middle = line.edge.midpoint();
    const size = LABEL.size * sizes.scale;
    const padding = LABEL.padding * sizes.scale;
    context.font = `600 ${size}px ${look.font}`;
    const width = context.measureText(line.label).width;
    context.globalAlpha = LABEL.plateOpacity;
    context.fillStyle = look.bg;
    context.fillRect(middle.x - width / 2 - padding, middle.y - size / 2 - padding, width + 2 * padding, size + 2 * padding);
    context.globalAlpha = 1;
    context.fillStyle = look.text1;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(line.label, middle.x, middle.y);
  }

  function draw() {
    const started = performance.now();
    const context = layer.begin();
    let drawn = 0;
    if (lines.length && look) {
      const extent = cy.extent();
      const shown = lines
        .map((line) => ({ line, sizes: sizesOf(line) }))
        .filter(({ line, sizes }) => {
          const box = boundsOf(line.shape.points, sizes.head + sizes.casing);
          return box.x2 >= extent.x1 && box.x1 <= extent.x2 && box.y2 >= extent.y1 && box.y1 <= extent.y2;
        });
      if (shown.length) {
        layer.inGraph(cy);
        context.lineJoin = "round";
        context.lineCap = "butt";
        context.strokeStyle = look.bg;
        context.fillStyle = look.bg;
        for (const { line, sizes } of shown) {
          context.setLineDash([]);
          context.lineWidth = sizes.width + 2 * sizes.casing;
          trace(context, line, sizes);
          context.stroke();
          context.lineWidth = 2 * sizes.casing;
          for (const outline of headsOf(line, sizes)) {
            fillOutline(context, outline);
            context.fill();
            context.stroke();
          }
        }
        for (const { line, sizes } of shown) {
          context.strokeStyle = line.colour;
          context.lineWidth = sizes.width;
          context.setLineDash(line.dash.map((length) => length * sizes.scale));
          context.lineDashOffset = sizes.dashOffset;
          trace(context, line, sizes);
          context.stroke();
        }
        context.setLineDash([]);
        context.lineDashOffset = 0;
        for (const { line, sizes } of shown) {
          context.fillStyle = line.colour;
          for (const outline of headsOf(line, sizes)) {
            fillOutline(context, outline);
            context.fill();
          }
        }
        drawTitles(context);
        for (const { line, sizes } of shown) if (line.label) drawLabel(context, line, sizes);
        drawn = shown.length;
        layer.drew();
      }
    }
    frames.push({ at: started, ms: performance.now() - started, drawn });
    if (frames.length > FRAMES_KEPT) frames.shift();
  }

  cy.on("render", draw);
  return {
    refresh,
    followed: () => {
      const ids = (pick) => lines.filter(pick).map((line) => line.id);
      const casing = look?.bg || null;
      return {
        edges: lines.map((line) => ({ id: line.id, colour: line.colour, casing, width: lineWidthOf(line.edge) })),
        passes: PASSES.map((name) => {
          if (name === "titles") return { name, edges: [...new Set(titles.flatMap((title) => title.under))].sort(), boxes: titles.map((title) => title.id) };
          return {
            name,
            edges: name === "labels" ? ids((line) => Boolean(line.label)) : name === "heads" ? ids((line) => line.heads.source || line.heads.target) : ids(() => true),
          };
        }),
      };
    },
    labelled: () => lines.filter((line) => line.label).map((line) => line.id),
    frames: () => ({ frames: frames.map((frame) => ({ ...frame })) }),
    destroy() {
      cy.removeListener("render", draw);
      layer.remove();
    },
  };
}
