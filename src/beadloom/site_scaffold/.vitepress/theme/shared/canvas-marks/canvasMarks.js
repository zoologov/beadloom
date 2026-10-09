// beadloom:component=site-shared-canvas-marks
// The names a selection and a hover mark the canvas with: the classes and the data, named once, and how a class or data is set.
//
// A class or data is set on an element only where that changes it, since
// Cytoscape restyles an element for every one it is given (`setClass`,
// `giveData`); the map draws its levels with them (`widgets/graph-viewer/model/canvasMap.js`).
//
// The canvas sets them (`widgets/graph-viewer/model/useGraphCanvas.js`), the layers over the canvas read
// which edges they mark as followed (`features/follow-edge/model/followedOverlay.js`) and which fall back
// (`features/edge-pills/model/pillOverlay.js`), and the test handle
// reads them back (`widgets/graph-viewer/model/testHandle.js`). Kept apart from the canvas, they can be read without
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

/** The class of every other line while the pointer rests on a node: drawn fainter (`entities/graph-edges/lib/edgePalette.js`, `behind`). */
export const BEHIND = "is-behind";

/** The edges a reader is following: on the line under the pointer, on a selection's walk, or of the node under the pointer. */
export const HIGHLIGHTED_EDGES = `.is-walk-edge, .${ALONG_HOVER}, .${HOVERED}, .${IN_FRONT}`;

/** The node data the impact mode sets: the node's distance from the selection. */
export const DISTANCE_DATA = "impactDistance";

/**
 * Give `element` the class `name` when `on`, and take it away otherwise, only
 * where that changes it: Cytoscape restyles every element it adds a class to or
 * takes one from, whether it had the class or not, and a box with everything it
 * holds, so marking every element of the map on each drawing restyled them all.
 */
export function setClass(element, name, on) {
  if (element.hasClass(name) !== on) element.toggleClass(name, on);
}

/** Whether two values of an element's data are the same: one value, or plain data equal field by field. */
function sameData(a, b) {
  if (a === b) return true;
  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Give `element` the data in `values`, a key whose value is undefined taken
 * away, and have it restyled only when one of them differs from what it holds:
 * Cytoscape restyles an element for every value it is given, the same or not,
 * and a box with everything it holds, so giving the box that holds everything
 * its unchanged scale on every drawing restyled every node of the map.
 */
export function giveData(element, values) {
  const changed = {};
  const gone = [];
  for (const [key, value] of Object.entries(values)) {
    const now = element.data(key);
    if (value === undefined) {
      if (now !== undefined) gone.push(key);
    } else if (!sameData(now, value)) changed[key] = value;
  }
  if (gone.length) element.removeData(gone.join(" "));
  if (Object.keys(changed).length) element.data(changed);
  else if (gone.length) element.updateStyle();
}
