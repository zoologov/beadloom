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
// data (no view-time randomness). The canonical view is LAYER LANES: each node
// is assigned a `partition` = its layer rank (service=0 … infra=3), and ELK
// `partitioning.activate` pins every node into its rank's band, top→bottom
// (`elk.direction: DOWN`). The lanes are therefore STABLE regardless of graph
// topology (NOT topology-derived layering). hierarchyHandling INCLUDE_CHILDREN
// lays out the COMPOUND parents (domains as boxes holding their features/
// components) with orthogonal edge routing.
export const ELK_OPTIONS = {
  name: "elk",
  elk: {
    algorithm: "layered",
    "elk.direction": "DOWN",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.hierarchyHandling": "INCLUDE_CHILDREN",
    "elk.partitioning.activate": "true",
    "elk.layered.spacing.nodeNodeBetweenLayers": "70",
    "elk.spacing.nodeNode": "45",
    "elk.padding": "[top=36,left=24,bottom=24,right=24]",
    "elk.layered.crossingMinimization.semiInteractive": "true",
  },
  fit: true,
  padding: 40,
  animate: false,
};

// The canonical layer lanes (rank → human name), top→bottom by dependency
// direction. Drives the legend + the per-node `partition` the view assigns.
export const LAYER_LANES = [
  { rank: 0, layer: "service", label: "service / interface" },
  { rank: 1, layer: "application", label: "application" },
  { rank: 2, layer: "domain", label: "domain" },
  { rank: 3, layer: "infra", label: "infrastructure" },
];

// Edge meaning (for the legend): a healthy/neutral dependency goes DOWN the
// layers; one that points UP or cross-cuts the layer order is a layering
// concern (distinct color + dash). Containment is subtle, not a flow arrow.
export const EDGE_LEGEND = [
  { cls: "healthy", label: "depends on (down a layer — healthy)" },
  { cls: "violation", label: "depends on (up / cross-cut — layering concern)" },
  { cls: "containment", label: "part of (containment)" },
  { cls: "runtime", label: "uses at runtime (declared — subprocess / file contract)" },
];

// The layering-violation accent (an up/cross-cut depends_on edge).
export const VIOLATION_EDGE_COLOR = "#e45649"; // red — dogfood our own rule

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
      // A layering-concern edge: a depends_on that points UP or cross-cuts the
      // canonical layer order (red + dashed). We dogfood our own layering rule.
      selector: "edge.violation",
      style: {
        "line-color": VIOLATION_EDGE_COLOR,
        "target-arrow-color": VIOLATION_EDGE_COLOR,
        "line-style": "dashed",
        width: GEOMETRY.edgeWidth + 1,
        "z-index": 8,
      },
    },
    {
      // A DECLARED runtime coupling (`uses`): a subprocess call or a
      // file-format contract. Dotted and muted so it reads as a weaker,
      // non-import binding, and deliberately NOT styled as a violation —
      // crossing a process boundary to call a published interface is not a
      // layering break.
      selector: "edge.runtime",
      style: {
        "line-style": "dotted",
        "line-color": "var(--vp-c-text-3)",
        "target-arrow-color": "var(--vp-c-text-3)",
        "target-arrow-shape": "vee",
        opacity: 0.75,
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
