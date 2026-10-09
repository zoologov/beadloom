// beadloom:component=site-graph-viewer
// The Cytoscape stylesheet of the graph viewer, built from resolved theme tokens.
//
// Every colour here is a literal `rgb(...)` from `shared/theme-tokens`, never a
// `var(--vp-…)`: Cytoscape rejects a CSS variable and draws its fallback grey.
// The stylesheet is rebuilt whenever the tokens change, which is how the graph
// follows VitePress's dark mode.
//
// A node is drawn as the legend draws its layer, whether it holds other nodes or
// not: a thin border in its layer's tone over a tint of it, its title in the
// middle, its corners rounded at one radius on screen whatever its size and the
// zoom, a box's as a card's (`shared/geometry/corners.js`). Its status is a mark in its top right corner (`NODE_STATUSES`),
// filled for an error finding or stale docs and a ring for warn findings only,
// and never changes its border, which stays its layer's. A box that is open is a
// fainter tint of its layer's tone inside a thin solid border, its title inside
// at the top, so the nodes it holds stand out on it. The one box that holds
// everything is the project's frame: a border a pixel wide on screen in a
// neutral that keeps 3:1 against the canvas, over a faint tint of the text
// colour, fainter than any node it holds. On the landscape, which has no layers,
// a node is a card whose border is its health, a contract edge is drawn by its
// look, and a broken one carries its verdict as a badge.
//
// Every line has one thin weight, at every zoom, whatever its kind, its count or
// its state; kinds differ by colour and dash. A line is one colour from end to
// end (`entities/graph-edges/lib/edgePalette.js`), and its arrowhead carries the direction: one size
// on screen where its run has room for it, on a straight run of its own, and one
// head where lines share their last run, the others ending at its base
// (`entities/graph-edges/lib/lineMarks.js`, `entities/graph-edges/lib/heads.js`). A followed line is drawn again
// on top by the layer over the canvas, with its label when it is under the
// pointer (`features/follow-edge/model/followedOverlay.js`); Cytoscape draws no edge label but a
// landscape badge. While the pointer rests on a node, its lines are drawn on
// top in the same way and every other line falls back to a fainter look.
//
// A selection adds three looks. Outside the neighbourhood or the impact set a
// node or edge is dimmed, or hidden when the reader asks for it. In impact mode
// a node's fill is its distance ring's tone, and a risky node carries a dashed
// danger outline. A dimmed node is drawn see-through, a dimmed line opaque in
// its colour faded towards the background (`entities/graph-edges/lib/edgePalette.js`).
//
// The map (`shared/map-levels/levels.js`) adds its own looks. A closed box's title, and a
// top-level node's while the map titles it, is drawn at the size its data names,
// inside its box or above it on a plate with a border (`shared/map-levels/mapMarks.js`); a
// top-level node too small for its title is drawn at the size its data names,
// around its laid-out box (`shared/geometry/grownBoxes.js`); an aggregated edge is a solid
// line with an arrowhead at each end edges arrive at, its count on a pill drawn
// over the canvas (`features/edge-pills/model/pillOverlay.js`). Every size that keeps one size on screen
// whatever the zoom multiplies by the map's scale, which every mark of the map
// and every line keeps in its data.

import { RING_TONES, mixRgb } from "../../../shared/theme-tokens/index.js";
import {
  DIMMED_SHARE,
  EDGE_STYLES,
  NO_SOURCE_HEAD,
  NO_TARGET_HEAD,
  arrowScaleOf,
  dashOf,
  dashOffsetOf,
  dashOnScreen,
  edgeCornerRadiiOf,
  edgePaletteOf,
  endHeadLength,
  headEndsOf,
  lineWidthOf,
} from "../../../entities/graph-edges/index.js";
import { NODE_STATUSES } from "../../../entities/graph-nodes/index.js";
import { LAYER_FILL_SHARE, LAYER_TONES, UNLAYERED_TONE } from "../../../entities/layers/index.js";
import { CORNER } from "../../../shared/geometry/index.js";
import {
  AGGREGATE,
  COLLAPSED,
  GEOMETRY,
  HIDDEN_EDGES,
  LOOP_END,
  MAP_BOX,
  MAP_MARKS,
  MAP_TITLE,
  PROJECT_BOX,
  STUB_AT,
  boxMarkInsetOf,
  boxMarkOf,
  drawnSizeOf,
  plateLiftOf,
  scaleOf,
  titleOf,
} from "../../../shared/map-levels/index.js";

/** How much of a ring's tone a node's fill takes; the rest is the node's usual fill. */
const RING_FILL_SHARE = 0.55;
/** How much of its tone an open box's tint shows. */
const OPEN_BOX_TINT = 0.07;

/**
 * The project's frame, the one box that holds everything: its border's width on
 * screen, in pixels, and its tone, the faintest neutral that keeps WCAG's 3:1 for
 * a boundary against the canvas (3.10:1 light, 3.20:1 dark, measured); and the
 * tone of its tint and how much of it shows, 1.09:1 and 1.12:1 against the
 * canvas, where a node's tint stands at 1.2:1 or more. The theme's grey it was
 * drawn in read as the canvas: a border at 1.35:1 and 2.52:1 over a tint at
 * 1.02:1 and 1.05:1, one layout unit wide, 0.06 px at this portal's whole-graph fit.
 */
const PROJECT_FRAME = Object.freeze({ borderPx: 1, border: "text3", tint: "text1", tintShare: 0.05 });

/**
 * The curve style of an edge the layout did not route. Every line drawn has a
 * route — an edge into the node's own box too, by a line of its own to an end
 * on the box's border (`shared/map-levels/loopLines.js`) — so this is a fallback only.
 */
export const CURVE_STYLE = "bezier";

/** A loop's end's side, in layout units: a point, drawn as nothing. */
const LOOP_END_SIDE = 0.01;

/** How many decimals a route's numbers keep: far below a pixel, and never in exponent form. */
const ROUTE_DECIMALS = 6;

/** A landscape node's border tone by its health. */
const HEALTH_TONES = Object.freeze({ healthy: "green", broken: "danger", neutral: "gray" });

/** The contract looks drawn above the others, like a violation: the ones that hurt. */
const PROBLEM_STYLE_KEYS = Object.freeze(["contract-broken", "contract-drift"]);

/** The SVG of a status mark in `colour`: a filled dot, or a ring. */
function markSvg(shape, colour) {
  const half = GEOMETRY.statusMark / 2;
  const body =
    shape === "ring"
      ? `<circle cx="${half}" cy="${half}" r="${half - 1.25}" fill="none" stroke="${colour}" stroke-width="2.5"/>`
      : `<circle cx="${half}" cy="${half}" r="${half - 0.5}" fill="${colour}"/>`;
  const size = GEOMETRY.statusMark;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${body}</svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

/** The look of a status mark in the top right corner: a size in layout units, or a function of the node. */
function markStyle(image, size, inset) {
  return {
    "background-image": image,
    "background-fit": "none",
    "background-clip": "none",
    "background-image-containment": "over",
    "background-width": size,
    "background-height": size,
    "background-position-x": "100%",
    "background-position-y": "0%",
    "background-offset-x": typeof inset === "function" ? (node) => -inset(node) : -inset,
    "background-offset-y": inset,
  };
}

function nodeRules(tokens) {
  const tones = [...LAYER_TONES, UNLAYERED_TONE];
  return [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-valign": "center",
        "text-halign": "center",
        color: tokens.text1,
        "font-family": tokens.font,
        "font-size": `${GEOMETRY.nodeTitle}px`,
        "font-weight": 600,
        width: GEOMETRY.outerWidth - GEOMETRY.cardBorder,
        height: GEOMETRY.outerHeight - GEOMETRY.cardBorder,
        shape: "round-rectangle",
        "background-color": tokens.bgSoft,
        "border-width": GEOMETRY.cardBorder,
        "border-style": "solid",
        "border-color": tokens[UNLAYERED_TONE],
        "text-wrap": "ellipsis",
        "text-max-width": GEOMETRY.outerWidth - 20,
      },
    },
    // The radius the map gives a drawn node's corners, in layout units (`shared/geometry/corners.js`); a node it gives none keeps Cytoscape's own.
    { selector: `node[${CORNER}]`, style: { "corner-radius": (node) => node.data(CORNER) } },
    ...tones.map((tone) => ({
      selector: `node[tone = "${tone}"]`,
      style: { "border-color": tokens[tone] },
    })),
    // A node of the architecture is tinted in its layer's tone, as the legend draws it; a landscape node has a health instead.
    ...tones.map((tone) => ({
      selector: `node[tone = "${tone}"][^health]`,
      style: { "background-color": tokens[tone], "background-opacity": LAYER_FILL_SHARE },
    })),
    {
      selector: ":parent",
      style: {
        "background-opacity": OPEN_BOX_TINT,
        "border-width": GEOMETRY.boxBorder,
        "text-valign": "top",
        "text-halign": "center",
        "text-margin-y": GEOMETRY.boxTitleInset,
        "font-weight": 700,
        // ELK leaves the room around a box's children, and the box is drawn at
        // ELK's size (`geometryRules`); Cytoscape adds no padding of its own,
        // which would push a box past ELK's where ELK's room is narrower.
        padding: 0,
        // A box is sized from its children's shapes; a child's label never resizes it.
        "compound-sizing-wrt-labels": "exclude",
      },
    },
    ...tones.map((tone) => ({
      selector: `:parent[tone = "${tone}"]`,
      style: { "background-color": tokens[tone] },
    })),
    ...Object.entries(HEALTH_TONES).map(([health, tone]) => ({
      selector: `node[health = "${health}"]`,
      style: { "border-color": tokens[tone] },
    })),
    ...Object.entries(NODE_STATUSES).flatMap(([status, look]) => {
      const image = markSvg(look.mark, tokens[look.tone]);
      return [
        { selector: `node[status = "${status}"]`, style: markStyle(image, GEOMETRY.statusMark, GEOMETRY.statusMarkInset) },
        { selector: `node.${COLLAPSED}[status = "${status}"]`, style: markStyle(image, boxMarkOf, boxMarkInsetOf) },
      ];
    }),
    {
      selector: `node.${PROJECT_BOX}`,
      style: {
        "border-color": tokens[PROJECT_FRAME.border],
        // Inside the box, so the frame's width, which follows the zoom, never changes the box's size.
        "border-position": "inside",
        "border-width": (node) => PROJECT_FRAME.borderPx * scaleOf(node),
        "background-color": tokens[PROJECT_FRAME.tint],
        "background-opacity": PROJECT_FRAME.tintShare,
      },
    },
    {
      selector: "node.is-selected",
      style: {
        "border-width": GEOMETRY.selectedBorder,
        "overlay-color": tokens.brand,
        "overlay-opacity": 0.12,
        "overlay-padding": 4,
      },
    },
    // A selected node keeps its layer's tint; a landscape card, which has none, is drawn in the page's alternate background.
    { selector: "node[health].is-selected", style: { "background-color": tokens.bgAlt } },
  ];
}

const decimal = (value) => value.toFixed(ROUTE_DECIMALS);
const pixels = (value) => `${decimal(value)}px`;

/**
 * The rules that draw ELK's geometry: a box at the size ELK gave it, and an edge
 * along ELK's route (`shared/geometry/routes.js`) with its corners rounded (`entities/graph-edges/lib/lineMarks.js`).
 * Their values are read from each element's data, so a stylesheet rebuilt for
 * another theme draws the same geometry.
 */
function geometryRules() {
  const box = (node) => node.data("box");
  const route = (edge) => edge.data("route");
  return [
    {
      selector: "node[box]",
      style: {
        width: (node) => box(node).width,
        height: (node) => box(node).height,
        "min-width": (node) => box(node).width,
        "min-height": (node) => box(node).height,
        "min-width-bias-left": (node) => pixels(box(node).biasLeft),
        "min-width-bias-right": (node) => pixels(box(node).biasRight),
        "min-height-bias-top": (node) => pixels(box(node).biasTop),
        "min-height-bias-bottom": (node) => pixels(box(node).biasBottom),
      },
    },
    {
      selector: "edge[route]",
      style: {
        "curve-style": "round-segments",
        "segment-radii": (edge) => edgeCornerRadiiOf(edge).map(decimal).join(" ") || "0",
        "edge-distances": "endpoints",
        "source-endpoint": (edge) => route(edge).sourceEndpoint.map(pixels).join(" "),
        "target-endpoint": (edge) => route(edge).targetEndpoint.map(pixels).join(" "),
        "segment-weights": (edge) => route(edge).weights.map(decimal).join(" "),
        "segment-distances": (edge) => route(edge).distances.map(decimal).join(" "),
      },
    },
  ];
}

/**
 * A line's style as Cytoscape draws its dash: a dotted line is a pattern of dots
 * in pixels on screen, shifted to end a dash inside its head (`dashOffsetOf`).
 */
function dashStyle(look) {
  const pattern = dashOf(look);
  if (!pattern.length) return { "line-style": "solid" };
  return {
    "line-style": "dashed",
    "line-dash-pattern": (edge) => dashOnScreen(pattern, edge),
    "line-dash-offset": (edge) => dashOffsetOf(edge, dashOnScreen(pattern, edge), look.arrow),
  };
}

function edgeRules(tokens, palette) {
  const byKey = Object.entries(EDGE_STYLES).map(([key, look]) => ({
    selector: `edge[styleKey = "${key}"]`,
    style: {
      ...dashStyle(look),
      "line-color": palette[key].rest,
      "target-arrow-color": palette[key].rest,
      "source-arrow-color": palette[key].rest,
      "target-arrow-shape": look.arrow,
    },
  }));
  return [
    {
      selector: "edge",
      style: {
        width: lineWidthOf,
        "line-fill": "solid",
        "curve-style": CURVE_STYLE,
        "arrow-scale": arrowScaleOf,
        "font-family": tokens.font,
        "font-size": "11px",
        color: tokens.text1,
        "text-background-color": tokens.bg,
        "text-background-opacity": 0.9,
        "text-background-padding": "2px",
        "text-rotation": "autorotate",
      },
    },
    ...byKey,
    { selector: 'edge[styleKey = "violation"]', style: { "z-index": 8 } },
    ...PROBLEM_STYLE_KEYS.map((key) => ({ selector: `edge[styleKey = "${key}"]`, style: { "z-index": 8 } })),
    {
      selector: "edge[badge]",
      style: { label: "data(badge)", color: tokens.danger, "font-weight": 700, "font-size": "10px" },
    },
  ];
}

/** An edge behind the lines of the node under the pointer (`shared/canvas-marks/canvasMarks.js`, `BEHIND`): its own look faded towards the background. */
function behindEdgeRules(palette) {
  return Object.keys(EDGE_STYLES).map((key) => ({
    selector: `edge.is-behind[styleKey = "${key}"]`,
    style: { "line-color": palette[key].behind, "target-arrow-color": palette[key].behind, "source-arrow-color": palette[key].behind },
  }));
}

/** An edge outside the selection: its own look faded towards the background, at full opacity. */
function dimmedEdgeRules(palette) {
  return Object.keys(EDGE_STYLES).map((key) => ({
    selector: `edge.is-dimmed[styleKey = "${key}"]`,
    style: {
      "line-color": palette[key].dimmed,
      "target-arrow-color": palette[key].dimmed,
      "source-arrow-color": palette[key].dimmed,
      "text-opacity": DIMMED_SHARE,
    },
  }));
}

function selectionRules(tokens, palette) {
  const rings = RING_TONES.flatMap((tone, ring) => [
    {
      selector: `node.ring-${ring}`,
      style: { "background-color": mixRgb(tokens[tone], tokens.bgSoft, RING_FILL_SHARE), "background-opacity": 1 },
    },
    {
      selector: `:parent.ring-${ring}`,
      style: { "background-color": tokens[tone], "background-opacity": 0.16 },
    },
  ]);
  return [
    { selector: "edge.is-walk-edge", style: { "z-index": 9 } },
    ...rings,
    {
      selector: "node.is-risk",
      style: {
        "outline-width": GEOMETRY.riskOutlineWidth,
        "outline-color": tokens.danger,
        "outline-style": "dashed",
        "outline-offset": 3,
        "outline-opacity": 1,
      },
    },
    { selector: "node.is-dimmed", style: { opacity: DIMMED_SHARE } },
    ...behindEdgeRules(palette),
    ...dimmedEdgeRules(palette),
  ];
}

/** Where a map title is drawn, inside its box or on a plate on one side of it: its alignment, and which way it is lifted off the box. */
const PLATE_PLACES = Object.freeze({
  inside: { valign: "center", halign: "center", x: 0, y: 0 },
  above: { valign: "top", halign: "center", x: 0, y: -1 },
  below: { valign: "bottom", halign: "center", x: 0, y: 1 },
  right: { valign: "center", halign: "right", x: 1, y: 0 },
  left: { valign: "center", halign: "left", x: -1, y: 0 },
});

/** How much of the text colour a title plate's border takes over the background. */
const PLATE_BORDER_SHARE = 0.3;

/** A map title's look: its size, its place inside its box or on one side of it, and the plate it stands on outside. */
function mapTitleRule(tokens) {
  const title = (node) => node.data(MAP_TITLE);
  // The scale the title was laid out at: the map's, or the overview plan's when the view is zoomed out past it.
  const at = (node) => title(node).scale || scaleOf(node);
  const outside = (node) => !title(node).inside;
  const placeOf = (node) => (outside(node) ? title(node).side : "inside");
  return {
    selector: `node[${MAP_TITLE}]`,
    style: {
      label: titleOf,
      "text-wrap": "wrap",
      "font-weight": 700,
      "font-size": (node) => title(node).px * at(node),
      "text-valign": (node) => PLATE_PLACES[placeOf(node)].valign,
      "text-halign": (node) => PLATE_PLACES[placeOf(node)].halign,
      "text-margin-x": (node) => PLATE_PLACES[placeOf(node)].x * plateLiftOf(at(node)),
      "text-margin-y": (node) => PLATE_PLACES[placeOf(node)].y * plateLiftOf(at(node)),
      // Wide enough for the widest line, so a title is never wrapped where it was measured whole.
      "text-max-width": (node) => title(node).width + at(node),
      "text-background-color": tokens.bg,
      "text-background-opacity": (node) => (outside(node) ? 1 : 0),
      "text-background-shape": "round-rectangle",
      "text-background-padding": (node) => `${MAP_MARKS.platePadding * at(node)}px`,
      "text-border-width": (node) => (outside(node) ? MAP_MARKS.plateBorder * at(node) : 0),
      "text-border-color": mixRgb(tokens.text1, tokens.bg, PLATE_BORDER_SHARE),
      "text-border-opacity": (node) => (outside(node) ? 1 : 0),
    },
  };
}

/** The map's looks: a closed box and its title, a top-level node's title and size, an aggregated edge, a count of hidden edges. */
function mapRules(tokens) {
  const tones = [...LAYER_TONES, UNLAYERED_TONE];
  return [
    { selector: `node[${HIDDEN_EDGES}]`, style: { label: titleOf, "text-wrap": "wrap" } },
    {
      selector: `node.${COLLAPSED}`,
      style: {
        "background-opacity": LAYER_FILL_SHARE,
        // A closed box's border is an open box's, so a box is drawn at ELK's size either way.
        "border-width": GEOMETRY.boxBorder,
      },
    },
    {
      // A node drawn larger than its layout: the size its data names, its border included, around its centre.
      selector: `node[${MAP_BOX}]`,
      style: {
        width: (node) => drawnSizeOf(node).width,
        height: (node) => drawnSizeOf(node).height,
      },
    },
    mapTitleRule(tokens),
    ...tones.map((tone) => ({
      selector: `node.${COLLAPSED}[tone = "${tone}"]`,
      style: { "background-color": tokens[tone] },
    })),
    {
      selector: `edge[${AGGREGATE}]`,
      style: {
        "line-style": "solid",
        "source-arrow-shape": (edge) => (headEndsOf(edge).source ? "triangle" : "none"),
        "target-arrow-shape": (edge) => (headEndsOf(edge).target ? "triangle" : "none"),
        "z-index": 5,
      },
    },
  ];
}

/**
 * The ends that draw no arrowhead because another line on their last run draws
 * it (`entities/graph-edges/lib/heads.js`), or that start where another line arrives along its last
 * run: such a line ends at that head's base rather than on into the head, past
 * its sides near the tip and in its own colour across it.
 */
const SHARED_HEAD_RULES = [
  // An edge drawn as itself into an open box its node's other lines run on into ends there as their stub, with no head.
  { selector: `edge[${STUB_AT}][!${AGGREGATE}]`, style: { "target-arrow-shape": (edge) => (headEndsOf(edge).target ? EDGE_STYLES[edge.data("styleKey")]?.arrow || "triangle" : "none") } },
  { selector: `edge.${NO_TARGET_HEAD}`, style: { "target-arrow-shape": "none", "target-distance-from-node": (edge) => endHeadLength(edge, "target") } },
  { selector: `edge.${NO_SOURCE_HEAD}`, style: { "source-arrow-shape": "none", "source-distance-from-node": (edge) => endHeadLength(edge, "source") } },
];

/** The whole stylesheet for resolved `tokens` (see `shared/theme-tokens`). */
export function buildStylesheet(tokens) {
  const palette = edgePaletteOf(tokens);
  return [
    ...nodeRules(tokens),
    ...edgeRules(tokens, palette),
    ...geometryRules(),
    ...selectionRules(tokens, palette),
    ...mapRules(tokens),
    ...SHARED_HEAD_RULES,
    {
      // Where a loop meets its box's border: a point with no look, no title and no events.
      selector: `node.${LOOP_END}`,
      style: { width: LOOP_END_SIDE, height: LOOP_END_SIDE, "background-opacity": 0, "border-width": 0, label: "", events: "no", "overlay-opacity": 0, "background-image": "none" },
    },
    { selector: ".is-hidden, .is-outside", style: { display: "none" } },
  ];
}
