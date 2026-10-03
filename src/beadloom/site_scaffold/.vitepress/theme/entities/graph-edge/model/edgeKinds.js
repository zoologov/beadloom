// beadloom:component=site-graph-edge
// The edge kinds the viewer draws, how each one looks, and the legend they make.
//
// `part_of` is not drawn as a line: it is the nesting of a node inside its
// container's box. Every other kind has one line style, so a reader tells them
// apart without colour, and one tone, a theme token the stylesheet resolves.
// A `depends_on` edge the layer rule judged against the declared direction is a
// violation and is drawn red, dashed and thicker, whatever else it is.
//
// The legend is derived from the edges that are drawn (`legendKeysOf`), so it
// cannot list a kind the canvas does not show.
//
// A contract edge of the landscape is drawn by its look — healthy, drifting,
// broken or neutral — rather than by its kind, because on that map the health
// of a contract is what the reader looks for.

/** The containment kind: drawn as nesting, never as a line. */
export const CONTAINMENT_KIND = "part_of";

/** The key of the violation style in the legend and on the canvas. */
export const VIOLATION_KEY = "violation";

/** The kinds drawn as a line, in the order a card lists them. */
export const DRAWN_KINDS = Object.freeze(["depends_on", "uses", "consumes", "produces"]);

/** The style key of a contract edge's look (`healthy`, `drift`, `broken` or `neutral`). */
export function contractStyleKey(look) {
  return `contract-${look}`;
}

/**
 * Each drawn kind: its label, legend text, line style, dash pattern, arrow and
 * tone, and how the card titles its edges out of a node and into it.
 */
export const EDGE_STYLES = {
  depends_on: {
    label: "depends on",
    legend: "depends on (an import)",
    outgoing: "Depends on",
    incoming: "Depended on by",
    line: "solid",
    arrow: "triangle",
    tone: "text2",
  },
  uses: {
    label: "uses",
    legend: "uses at runtime (declared)",
    outgoing: "Uses at runtime (declared)",
    incoming: "Used at runtime by (declared)",
    line: "dotted",
    arrow: "vee",
    tone: "indigo",
  },
  consumes: {
    label: "consumes",
    legend: "consumes a contract",
    outgoing: "Consumes",
    incoming: "Consumed by",
    line: "dashed",
    dash: [6, 3],
    arrow: "triangle",
    tone: "green",
  },
  produces: {
    label: "produces",
    legend: "produces a contract",
    outgoing: "Produces",
    incoming: "Produced by",
    line: "dashed",
    dash: [2, 3],
    arrow: "triangle",
    tone: "purple",
  },
  [VIOLATION_KEY]: {
    label: "depends on, against the layers",
    legend: "violation: depends on against the declared layers",
    line: "dashed",
    dash: [8, 4],
    arrow: "triangle",
    tone: "danger",
  },
  [contractStyleKey("healthy")]: {
    label: "contract, healthy",
    legend: "contract, healthy",
    line: "solid",
    arrow: "triangle",
    tone: "green",
  },
  [contractStyleKey("drift")]: {
    label: "contract, drifting",
    legend: "contract, drifting",
    line: "dashed",
    dash: [6, 3],
    arrow: "triangle",
    tone: "warning",
  },
  [contractStyleKey("broken")]: {
    label: "contract, broken",
    legend: "contract, broken",
    line: "dashed",
    dash: [8, 4],
    arrow: "triangle",
    tone: "danger",
  },
  [contractStyleKey("neutral")]: {
    label: "contract, neutral",
    legend: "contract, neutral (external, expected, dead or unmapped)",
    line: "dotted",
    arrow: "triangle",
    tone: "gray",
  },
};

/** Whether an edge of this kind is drawn as a line. */
export function isDrawnKind(kind) {
  return DRAWN_KINDS.includes(kind);
}

/** Whether a data-file edge is a violation of the layer rule. */
export function isViolation(edge) {
  return edge.kind === "depends_on" && edge.violation === true;
}

/** The style key an edge is drawn with: a contract's look, else the violation style, else its kind. */
export function styleKeyOf(edge) {
  if (edge.look && Object.hasOwn(EDGE_STYLES, contractStyleKey(edge.look))) {
    return contractStyleKey(edge.look);
  }
  return isViolation(edge) ? VIOLATION_KEY : edge.kind;
}

/** The legend keys a set of edges calls for, sorted: each drawn kind, plus `violation`. */
export function legendKeysOf(edges) {
  const keys = new Set();
  for (const edge of edges) {
    if (!isDrawnKind(edge.kind)) continue;
    const key = styleKeyOf(edge);
    keys.add(key === VIOLATION_KEY ? edge.kind : key);
    if (key === VIOLATION_KEY) keys.add(VIOLATION_KEY);
  }
  return [...keys].sort();
}
