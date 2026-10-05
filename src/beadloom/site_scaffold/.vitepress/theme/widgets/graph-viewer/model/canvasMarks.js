// beadloom:component=site-graph-viewer
// The names a selection and a hover mark the canvas with: the classes and the data, named once.
//
// The canvas sets them (`useGraphCanvas.js`), the layers over the canvas read
// which edges they mark as followed (`followedOverlay.js`) and which fall back
// (`pillOverlay.js`), and the test handle
// reads them back (`testHandle.js`). Kept apart from the canvas, they can be read without
// loading it, which is how the handle stays loadable on a page of its own.

/** Every class a selection puts on the canvas, removed before the next one is marked. */
export const SELECTION_CLASSES = Object.freeze([
  "is-selected",
  "is-selected-edge",
  "in-walk",
  "is-walk-edge",
  "is-dimmed",
  "is-outside",
  "is-risk",
  "holds-walk",
]);

/** The class of the edge under the pointer. */
export const HOVERED = "is-hovered";

/** The class of every edge drawn along the line under the pointer. */
export const ALONG_HOVER = "is-along-hover";

/** The class of every line of the node under the pointer, drawn in front of the rest. */
export const IN_FRONT = "is-in-front";

/** The class of every other line while the pointer rests on a node: drawn fainter (`lib/edgePalette.js`, `behind`). */
export const BEHIND = "is-behind";

/** The edges a reader is following: on the line under the pointer, on a selection's walk, or of the node under the pointer. */
export const HIGHLIGHTED_EDGES = `.is-walk-edge, .${ALONG_HOVER}, .${HOVERED}, .${IN_FRONT}`;

/** The node data the impact mode sets: the node's distance from the selection. */
export const DISTANCE_DATA = "impactDistance";
