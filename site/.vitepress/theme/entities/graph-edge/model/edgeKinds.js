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

/** The containment kind: drawn as nesting, never as a line. */
export const CONTAINMENT_KIND = "part_of";

/** The key of the violation style in the legend and on the canvas. */
export const VIOLATION_KEY = "violation";

/** Each drawn kind: its label, legend text, line style, dash pattern, arrow and tone. */
export const EDGE_STYLES = {
  depends_on: {
    label: "depends on",
    legend: "depends on (an import)",
    line: "solid",
    arrow: "triangle",
    tone: "text2",
  },
  uses: {
    label: "uses",
    legend: "uses at runtime (declared)",
    line: "dotted",
    arrow: "vee",
    tone: "indigo",
  },
  consumes: {
    label: "consumes",
    legend: "consumes a contract",
    line: "dashed",
    dash: [6, 3],
    arrow: "triangle",
    tone: "green",
  },
  produces: {
    label: "produces",
    legend: "produces a contract",
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
};

/** Whether an edge of this kind is drawn as a line. */
export function isDrawnKind(kind) {
  return kind !== VIOLATION_KEY && Object.hasOwn(EDGE_STYLES, kind);
}

/** Whether a data-file edge is a violation of the layer rule. */
export function isViolation(edge) {
  return edge.kind === "depends_on" && edge.violation === true;
}

/** The style key an edge is drawn with: the violation style overrides its kind. */
export function styleKeyOf(edge) {
  return isViolation(edge) ? VIOLATION_KEY : edge.kind;
}

/** The legend keys a set of edges calls for, sorted: each drawn kind, plus `violation`. */
export function legendKeysOf(edges) {
  const keys = new Set();
  for (const edge of edges) {
    if (!isDrawnKind(edge.kind)) continue;
    keys.add(edge.kind);
    if (isViolation(edge)) keys.add(VIOLATION_KEY);
  }
  return [...keys].sort();
}
