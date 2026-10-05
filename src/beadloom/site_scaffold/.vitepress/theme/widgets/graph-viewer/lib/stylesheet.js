// beadloom:component=site-graph-viewer
// The Cytoscape stylesheet of the graph viewer, built from resolved theme tokens.
//
// Every colour here is a literal `rgb(...)` from `shared/theme-tokens`, never a
// `var(--vp-…)`: Cytoscape rejects a CSS variable and draws its fallback grey.
// The stylesheet is rebuilt whenever the tokens change, which is how the graph
// follows VitePress's dark mode.
//
// A node is a card: its fill, a thin border in its layer's tone, its title in
// the middle. Its status is a mark in its top right corner (`NODE_STATUSES`),
// filled for an error finding or stale docs and a ring for warn findings only,
// and never changes its border, which stays its layer's. A box that is open is a
// light tint of its layer's tone inside a thin solid border, its title inside at
// the top. On the landscape, which has no layers, a node's border is its health,
// a contract edge is drawn by its look, and a broken one carries its verdict as
// a badge.
//
// Every line has one thin weight, at every zoom, whatever its kind, its count or
// its state; kinds differ by colour and dash. A line is one colour from end to
// end (`lib/edgePalette.js`), and its arrowhead carries the direction: one size
// on screen, on a straight run of its own, and one head where lines share their
// last run (`lib/lineMarks.js`, `lib/heads.js`). A followed line is drawn again
// on top by the layer over the canvas, with its label when it is under the
// pointer (`model/followedOverlay.js`); Cytoscape draws no edge label but an
// aggregated edge's count and a landscape badge.
//
// A selection adds three looks. Outside the neighbourhood or the impact set a
// node or edge is dimmed, or hidden when the reader asks for it. In impact mode
// a node's fill is its distance ring's tone, and a risky node carries a dashed
// danger outline. A dimmed node is drawn see-through, a dimmed line opaque in
// its colour faded towards the background (`lib/edgePalette.js`).
//
// The map (`lib/levels.js`) adds its own looks. A closed box is drawn tinted, its
// title in the middle, or above it when the box is too narrow for it; an
// aggregated edge is a solid line with an arrowhead at each end edges arrive at
// and the counts as its label. Every size that keeps one size on screen whatever
// the zoom multiplies by the map's scale, which every mark of the map and every
// line keeps in its data.

import { mixRgb } from "../../../shared/theme-tokens/index.js";
import { EDGE_STYLES, dashOf } from "../../../entities/graph-edge/index.js";
import { NODE_STATUSES } from "../../../entities/graph-node/index.js";
import { LAYER_TONES, UNLAYERED_TONE } from "../../../entities/layer/index.js";
import { RING_TONES } from "../../../features/impact-view/index.js";
import { DIMMED_SHARE, edgePaletteOf } from "./edgePalette.js";
import { NO_SOURCE_HEAD, NO_TARGET_HEAD } from "./heads.js";
import { AGGREGATE, COLLAPSED, HIDDEN_EDGES } from "./levels.js";
import { arrowScaleOf, dashOnScreen, edgeCornerRadiiOf, lineWidthOf } from "./lineMarks.js";
import { MAP_MARKS, boxMarkInsetOf, boxMarkOf, scaleOf, titleFits, titleOf, titleSizeOf } from "./mapMarks.js";

/**
 * A node's sizes, in layout units. `outerWidth` and `outerHeight` are a leaf's
 * size with its border, the size the layout places it by, and the same whatever
 * its status: a status is a mark inside the card, so a finding moves no node.
 */
export const GEOMETRY = Object.freeze({
  outerWidth: 163,
  outerHeight: 47,
  cardBorder: 1.5,
  boxBorder: 1,
  selectedBorder: 3,
  riskOutlineWidth: 4,
  /** A status mark's side, and how far it sits in from the card's top right corner. */
  statusMark: 10,
  statusMarkInset: 6,
  /** How far an open box's title sits below its top border. */
  boxTitleInset: 20,
});

/** How much of a ring's tone a node's fill takes; the rest is the node's usual fill. */
const RING_FILL_SHARE = 0.55;
/** How much of its tone an open box's tint shows. */
const OPEN_BOX_TINT = 0.07;

/**
 * The curve style of an edge the layout did not route: Cytoscape draws an edge
 * into the node's own box as a loop, whatever its style, and `bezier` is that
 * loop's style.
 */
export const CURVE_STYLE = "bezier";

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
        "font-size": "12px",
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
    ...tones.map((tone) => ({
      selector: `node[tone = "${tone}"]`,
      style: { "border-color": tokens[tone] },
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
      selector: "node.is-selected",
      style: {
        "background-color": tokens.bgAlt,
        "border-width": GEOMETRY.selectedBorder,
        "overlay-color": tokens.brand,
        "overlay-opacity": 0.12,
        "overlay-padding": 4,
      },
    },
  ];
}

const decimal = (value) => value.toFixed(ROUTE_DECIMALS);
const pixels = (value) => `${decimal(value)}px`;

/**
 * The rules that draw ELK's geometry: a box at the size ELK gave it, and an edge
 * along ELK's route (`lib/routes.js`) with its corners rounded (`lib/lineMarks.js`).
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

/** A line's style as Cytoscape draws its dash: a dotted line is a pattern of dots in pixels on screen. */
function dashStyle(look) {
  const pattern = dashOf(look);
  if (!pattern.length) return { "line-style": "solid" };
  return { "line-style": "dashed", "line-dash-pattern": (edge) => dashOnScreen(pattern, edge) };
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
      style: { "background-color": mixRgb(tokens[tone], tokens.bgSoft, RING_FILL_SHARE) },
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
    ...dimmedEdgeRules(palette),
  ];
}

/** The map's looks: a closed box and its title, an aggregated edge, a count of hidden edges. */
function mapRules(tokens) {
  const tones = [...LAYER_TONES, UNLAYERED_TONE];
  return [
    { selector: `node[${HIDDEN_EDGES}]`, style: { label: titleOf, "text-wrap": "wrap" } },
    {
      selector: `node.${COLLAPSED}`,
      style: {
        label: titleOf,
        "text-wrap": "wrap",
        "font-weight": 700,
        "font-size": (node) => MAP_MARKS.boxTitle * scaleOf(node),
        "text-valign": (node) => (titleFits(node) ? "center" : "top"),
        "text-margin-y": 0,
        "text-max-width": (node) => (titleFits(node) ? node.data("box").width : titleSizeOf(node).width + 1),
        "background-opacity": MAP_MARKS.collapsedOpacity,
        // A closed box's border is an open box's, so a box is drawn at ELK's size either way.
        "border-width": GEOMETRY.boxBorder,
      },
    },
    ...tones.map((tone) => ({
      selector: `node.${COLLAPSED}[tone = "${tone}"]`,
      style: { "background-color": tokens[tone] },
    })),
    {
      selector: `edge[${AGGREGATE}]`,
      style: {
        "line-style": "solid",
        label: "data(countLabel)",
        "font-size": (edge) => MAP_MARKS.countLabel * scaleOf(edge),
        "font-weight": 700,
        "text-rotation": "none",
        "text-background-padding": (edge) => `${2 * scaleOf(edge)}px`,
        "source-arrow-shape": (edge) => (edge.data("backward") ? "triangle" : "none"),
        "target-arrow-shape": (edge) => (edge.data("forward") ? "triangle" : "none"),
        "z-index": 5,
      },
    },
  ];
}

/** The ends that draw no arrowhead because another line on their last run draws it (`lib/heads.js`). */
const SHARED_HEAD_RULES = [
  { selector: `edge.${NO_TARGET_HEAD}`, style: { "target-arrow-shape": "none" } },
  { selector: `edge.${NO_SOURCE_HEAD}`, style: { "source-arrow-shape": "none" } },
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
    { selector: ".is-hidden, .is-outside", style: { display: "none" } },
  ];
}
