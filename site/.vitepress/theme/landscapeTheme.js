// landscapeTheme — the dedicated theme config for the interactive landscape
// (BDL-060 S4, G2). All palette/typography/geometry lives HERE so the visual
// is changeable without touching the rendering logic in LandscapeMap.vue.
//
// Two principles the owner asked for:
//  1. Auto light/dark — the colors are CSS custom properties resolved at runtime
//     against the VitePress portal theme (`--vp-*`), so the map follows the
//     portal's appearance toggle. Semantic colors (health/verdict) are explicit
//     hex (they must carry the SAME meaning in both modes — DRIFT is always red).
//  2. Neutral base, semantic color only where it MEANS something. Healthy edges
//     are quiet; problem edges (DRIFT/BREAKING/orphaned/undeclared) dominate
//     (saturated color + thick width + a badge) — an honest "where it hurts" map.

// Health buckets (mirror the Python `_health_class`: healthy / broken / neutral).
// Each verdict string maps to a bucket; the bucket drives node border + edge color.
export const VERDICT_BUCKET = {
  confirmed: "healthy",
  ok: "healthy",
  expected: "neutral",
  external: "neutral",
  dead: "neutral",
  unmapped: "neutral",
  drift: "broken",
  breaking: "broken",
  orphaned_consumer: "broken",
  undeclared_producer: "broken",
  undeclared: "broken",
};

export function bucketOf(verdict) {
  return VERDICT_BUCKET[String(verdict || "").toLowerCase()] || "healthy";
}

// Semantic colors (stable across light/dark — meaning, not chrome).
export const COLORS = {
  healthy: "#2da44e", // green
  broken: "#e45649", // red
  neutral: "#8b949e", // grey
  drift: "#d29922", // amber (a distinct "drift" within the broken bucket)
};

// Verdict → its dominant edge/badge color. BREAKING/orphaned/undeclared = red;
// DRIFT = amber; healthy = green; neutral = grey. Problem verdicts dominate.
export function verdictColor(verdict) {
  const v = String(verdict || "").toLowerCase();
  if (v === "drift") return COLORS.drift;
  const bucket = bucketOf(v);
  return COLORS[bucket] || COLORS.healthy;
}

// Geometry (widths/sizes) — problem edges are visibly heavier than healthy ones.
export const GEOMETRY = {
  nodeWidth: 150,
  nodeHeight: 44,
  healthyEdgeWidth: 1.6,
  problemEdgeWidth: 3.6,
  fontFamily:
    "var(--vp-font-family-base, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
};

// ELK layout options — FIXED + seedless so the layout is deterministic given the
// same data (the invariant: no view-time randomness). Orthogonal edge routing +
// non-overlapping nodes + grouping spacing, the readability the owner requires.
export const ELK_OPTIONS = {
  name: "elk",
  elk: {
    algorithm: "layered",
    "elk.direction": "RIGHT",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.spacing.nodeNodeBetweenLayers": "80",
    "elk.spacing.nodeNode": "50",
    "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
    "elk.layered.crossingMinimization.semiInteractive": "true",
  },
  // Deterministic: no randomized seed, fit after layout, no animation jitter.
  fit: true,
  padding: 40,
  animate: false,
};

// The Cytoscape stylesheet, built from the theme above. Colors that follow the
// portal (text/background/lines) are CSS vars resolved at runtime; semantic
// health/verdict colors are explicit. `data(...)` mappers read the per-element
// fields the Python artifact carries (health / verdict / bucket).
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
        "border-color": "data(healthColor)",
        "text-wrap": "ellipsis",
        "text-max-width": GEOMETRY.nodeWidth - 16,
      },
    },
    {
      selector: "node:selected",
      style: { "border-width": 5, "background-color": "var(--vp-c-bg-alt)" },
    },
    {
      selector: "node.dimmed",
      style: { opacity: 0.18 },
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": "data(verdictColor)",
        "target-arrow-color": "data(verdictColor)",
        "target-arrow-shape": "triangle",
        "curve-style": "taxi",
        "taxi-direction": "horizontal",
        label: "data(badge)",
        "font-size": "10px",
        "font-weight": 700,
        color: "data(verdictColor)",
        "text-background-color": "var(--vp-c-bg)",
        "text-background-opacity": 0.85,
        "text-background-padding": "2px",
      },
    },
    {
      selector: "edge.problem",
      style: { "line-style": "solid", "z-index": 10 },
    },
    {
      selector: "edge.dimmed",
      style: { opacity: 0.12 },
    },
    {
      selector: ".hidden",
      style: { display: "none" },
    },
  ];
}
