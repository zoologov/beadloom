// beadloom:component=site-graph-viewer
// The Cytoscape stylesheet of the graph viewer, built from resolved theme tokens.
//
// Every colour here is a literal `rgb(...)` from `shared/theme-tokens`, never a
// `var(--vp-…)`: Cytoscape rejects a CSS variable and draws its fallback grey.
// The stylesheet is rebuilt whenever the tokens change, which is how the graph
// follows VitePress's dark mode.
//
// Colour means the layer: a node's border, and a box's tint, are its layer's
// tone. Status is a separate accent, drawn by `NODE_STATUSES`: an error finding
// gets a danger ring, stale docs a warning ring, and warn findings only a
// double warning ring. Each edge kind has its own line style. On the
// landscape, which has no layers, a node's border is its health, a contract
// edge is drawn by its look, and a broken one carries its verdict as a badge.
//
// A selection adds three looks. Outside the neighbourhood or the impact set a
// node or edge is dimmed, or hidden when the reader asks for it. In impact mode
// a node's fill is its distance ring's tone, and a risky node carries a dashed
// danger outline.

import { mixRgb } from "../../../shared/theme-tokens/index.js";
import { EDGE_STYLES } from "../../../entities/graph-edge/index.js";
import { NODE_STATUSES } from "../../../entities/graph-node/index.js";
import { LAYER_TONES, UNLAYERED_TONE } from "../../../entities/layer/index.js";
import { RING_TONES } from "../../../features/impact-view/index.js";

export const GEOMETRY = Object.freeze({
  nodeWidth: 160,
  nodeHeight: 44,
  edgeWidth: 1.8,
  violationWidth: 3.2,
  selectedEdgeWidth: 3.6,
  walkEdgeWidth: 2.8,
  riskOutlineWidth: 4,
  statusBorderWidth: 5,
  // A double border needs the width to show both of its lines.
  doubleBorderWidth: 7,
});

/** How much of a ring's tone a node's fill takes; the rest is the node's usual fill. */
const RING_FILL_SHARE = 0.55;
/** How visible a node or edge outside the selection stays when it is dimmed. */
const DIMMED_OPACITY = 0.14;

/**
 * The edge curve style, chosen by measurement: `bezier` lets fewer edges share a
 * stretch than `taxi`, which runs every edge out of a node down one trunk.
 */
export const CURVE_STYLE = "bezier";

/** How much of the full colour the source end of an edge keeps: direction reads as light to dark. */
const SOURCE_END_SHARE = 0.35;

/** A landscape node's border tone by its health. */
const HEALTH_TONES = Object.freeze({ healthy: "green", broken: "danger", neutral: "gray" });

/** The contract looks drawn as heavy as a violation: the ones that hurt. */
const PROBLEM_STYLE_KEYS = Object.freeze(["contract-broken", "contract-drift"]);

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
        width: GEOMETRY.nodeWidth,
        height: GEOMETRY.nodeHeight,
        shape: "round-rectangle",
        "background-color": tokens.bgSoft,
        "border-width": 3,
        "border-color": tokens[UNLAYERED_TONE],
        "text-wrap": "ellipsis",
        "text-max-width": GEOMETRY.nodeWidth - 16,
      },
    },
    ...tones.map((tone) => ({
      selector: `node[tone = "${tone}"]`,
      style: { "border-color": tokens[tone] },
    })),
    {
      selector: ":parent",
      style: {
        "background-opacity": 0.07,
        "text-valign": "top",
        "text-halign": "center",
        "font-weight": 700,
        "border-style": "dashed",
        padding: "12px",
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
    ...Object.entries(NODE_STATUSES).map(([status, look]) => ({
      selector: `node[status = "${status}"]`,
      style: {
        "border-color": tokens[look.tone],
        ...(look.border === "double"
          ? { "border-style": "double", "border-width": GEOMETRY.doubleBorderWidth }
          : { "border-width": GEOMETRY.statusBorderWidth }),
      },
    })),
    {
      selector: "node.is-selected",
      style: {
        "background-color": tokens.bgAlt,
        "border-width": 6,
        "overlay-color": tokens.brand,
        "overlay-opacity": 0.12,
        "overlay-padding": 4,
      },
    },
  ];
}

function edgeRules(tokens) {
  const byKey = Object.entries(EDGE_STYLES).map(([key, look]) => {
    const colour = tokens[look.tone];
    const style = {
      "line-style": look.line,
      "line-color": colour,
      "line-fill": "linear-gradient",
      "line-gradient-stop-colors": [mixRgb(colour, tokens.bg, SOURCE_END_SHARE), colour],
      "line-gradient-stop-positions": [0, 70],
      "target-arrow-color": colour,
      "target-arrow-shape": look.arrow,
    };
    if (look.dash) style["line-dash-pattern"] = look.dash;
    return { selector: `edge[styleKey = "${key}"]`, style };
  });
  return [
    {
      selector: "edge",
      style: {
        width: GEOMETRY.edgeWidth,
        "curve-style": CURVE_STYLE,
        "arrow-scale": 1.1,
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
    { selector: 'edge[styleKey = "violation"]', style: { width: GEOMETRY.violationWidth, "z-index": 8 } },
    ...PROBLEM_STYLE_KEYS.map((key) => ({
      selector: `edge[styleKey = "${key}"]`,
      style: { width: GEOMETRY.violationWidth, "z-index": 8 },
    })),
    {
      selector: "edge[badge]",
      style: { label: "data(badge)", color: tokens.danger, "font-weight": 700, "font-size": "10px" },
    },
    { selector: "edge.is-selected-edge", style: { width: GEOMETRY.selectedEdgeWidth, "z-index": 10 } },
    { selector: "edge.is-selected-edge, edge.is-hovered", style: { label: "data(label)" } },
  ];
}

function selectionRules(tokens) {
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
    { selector: "edge.is-walk-edge", style: { width: GEOMETRY.walkEdgeWidth, "z-index": 9 } },
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
    { selector: ".is-dimmed", style: { opacity: DIMMED_OPACITY } },
  ];
}

/** The whole stylesheet for resolved `tokens` (see `shared/theme-tokens`). */
export function buildStylesheet(tokens) {
  return [
    ...nodeRules(tokens),
    ...edgeRules(tokens),
    ...selectionRules(tokens),
    { selector: ".is-hidden, .is-outside", style: { display: "none" } },
  ];
}
