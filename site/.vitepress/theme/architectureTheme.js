// architectureTheme — the dedicated theme config for the interactive
// architecture graph (BDL-060 S4 ext). All palette/typography/geometry/layout
// lives HERE so the visual is changeable without touching ArchitectureMap.vue.
//
// Two principles (mirrors landscapeTheme):
//  1. Auto light/dark — neutral chrome (node bg / text / lines) resolves at
//     runtime against the VitePress portal (`--vp-*`), so the map follows the
//     appearance toggle. Layer colors are explicit hex (they carry the SAME
//     meaning in both modes — a domain is always the domain hue).
//  2. Color MEANS the layer. The architecture graph's readability win is the
//     layered stratification: service / application / domain / infra each get a
//     stable border color; status (stale docs / lint violations) is a distinct
//     warning accent so "show only violations" reads at a glance.

// Layer → its stable border color (the stratification the owner asked for).
export const LAYER_COLORS = {
  service: "#8957e5", // purple — the outer service shell
  application: "#1f6feb", // blue — orchestration
  domain: "#2da44e", // green — the bounded contexts
  infra: "#bf8700", // amber — the lowest layer
  "": "#8b949e", // grey — unlayered (feature/component) honest fallback
};

export function layerColor(layer) {
  return LAYER_COLORS[String(layer || "")] || LAYER_COLORS[""];
}

// Status accents (independent of layer): a node with stale docs or a lint
// violation gets a warning ring so the "show only violations" filter reads.
export const STATUS_COLORS = {
  stale: "#d29922", // amber — doc went stale
  violation: "#e45649", // red — lint violation
};

// Geometry (sizes) — compound parents are roomy, leaves compact.
export const GEOMETRY = {
  nodeWidth: 160,
  nodeHeight: 44,
  edgeWidth: 1.8,
  fontFamily:
    "var(--vp-font-family-base, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
};

// ELK layout — FIXED + seedless so the layout is deterministic given the same
// data (no view-time randomness). `nodePlacement.strategy` + hierarchyHandling
// INCLUDE_CHILDREN make ELK lay out the COMPOUND parents (domains as boxes
// containing their features/components) with orthogonal edge routing.
export const ELK_OPTIONS = {
  name: "elk",
  elk: {
    algorithm: "layered",
    "elk.direction": "DOWN",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.hierarchyHandling": "INCLUDE_CHILDREN",
    "elk.layered.spacing.nodeNodeBetweenLayers": "70",
    "elk.spacing.nodeNode": "45",
    "elk.padding": "[top=36,left=24,bottom=24,right=24]",
    "elk.layered.crossingMinimization.semiInteractive": "true",
  },
  fit: true,
  padding: 40,
  animate: false,
};

// The Cytoscape stylesheet. Neutral chrome follows the portal (CSS vars);
// layer/status colors are explicit. `data(...)` mappers read the per-element
// fields the Python artifact + the component compute (layerColor / statusColor).
export function buildStylesheet() {
  return [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-valign": "center",
        "text-halign": "center",
        color: "var(--vp-c-text-1)",
        "font-family": GEOMETRY.fontFamily,
        "font-size": "12px",
        "font-weight": 600,
        width: GEOMETRY.nodeWidth,
        height: GEOMETRY.nodeHeight,
        shape: "round-rectangle",
        "background-color": "var(--vp-c-bg-soft)",
        "border-width": 3,
        "border-color": "data(layerColor)",
        "text-wrap": "ellipsis",
        "text-max-width": GEOMETRY.nodeWidth - 16,
      },
    },
    {
      // Compound parents (a domain/service that contains children): a roomy box
      // with the label at the top, layout-driven size, layer-colored border.
      selector: ":parent",
      style: {
        "background-opacity": 0.06,
        "background-color": "data(layerColor)",
        "text-valign": "top",
        "text-halign": "center",
        "font-weight": 700,
        "border-style": "dashed",
        padding: "12px",
      },
    },
    {
      // A node flagged with stale docs or a lint violation: a warning ring.
      selector: "node.flagged",
      style: { "border-color": "data(statusColor)", "border-width": 5 },
    },
    {
      selector: "node:selected",
      style: { "background-color": "var(--vp-c-bg-alt)", "border-width": 6 },
    },
    {
      selector: "node.dimmed",
      style: { opacity: 0.16 },
    },
    {
      selector: "edge",
      style: {
        width: GEOMETRY.edgeWidth,
        "line-color": "var(--vp-c-text-3)",
        "target-arrow-color": "var(--vp-c-text-3)",
        "target-arrow-shape": "triangle",
        "curve-style": "taxi",
        "taxi-direction": "vertical",
      },
    },
    {
      // Impact/blast-radius highlight: edges into/out of the focused node.
      selector: "edge.impact",
      style: {
        "line-color": "var(--vp-c-brand-1, #3451b2)",
        "target-arrow-color": "var(--vp-c-brand-1, #3451b2)",
        width: GEOMETRY.edgeWidth + 1.6,
        "z-index": 10,
      },
    },
    {
      selector: "edge.dimmed",
      style: { opacity: 0.1 },
    },
    {
      selector: ".hidden",
      style: { display: "none" },
    },
  ];
}
