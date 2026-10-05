// beadloom:component=site-graph-viewer
// Where a drawn line carries an arrowhead: the ends its edges arrive at, and one head where lines share their last run.
//
// An edge of the data file arrives at its target; an aggregated edge of the map
// at each end the edges it carries arrive at (`headEndsOf`). An arrowhead carries
// the direction, since a line is one colour from end to end.
//
// Lines that reach one end along one final run are drawn as one line there, and
// end in one arrowhead rather than one per line drawn on top of each other,
// whose colours would fight. Lines that reach the end separately keep their own.
// Of the ends that coincide, the loudest look draws the head — a violation is
// never hidden under an import's head — and among equals the first by id; every
// other drops its own (`droppedHeadsOf`).
//
// Every function here is pure: data and routes in, ends out.

import { VIOLATION_KEY, contractStyleKey } from "../../../entities/graph-edge/index.js";
import { AGGREGATE } from "./levels.js";

/** The class of a line whose target drops its arrowhead for another on its last run; the stylesheet draws none there. */
export const NO_TARGET_HEAD = "no-target-head";
/** The class of a line whose source drops its arrowhead for another on its first run. */
export const NO_SOURCE_HEAD = "no-source-head";

/** The looks whose head is drawn over any other's at a shared end: the ones that report a problem. */
const LOUD_LOOKS = new Set([VIOLATION_KEY, contractStyleKey("broken"), contractStyleKey("drift")]);
/** Two ends closer than this, in layout units, are one. */
const SAME_END = 0.5;

/** The ends of `edge` that carry an arrowhead: `{ source, target }`. */
export function headEndsOf(edge) {
  if (!edge.data(AGGREGATE)) return { source: false, target: true };
  return { source: edge.data("backward") > 0, target: edge.data("forward") > 0 };
}

/** The key of an end: where its tip is and the way its last run arrives there. */
function endKey({ tip, before }) {
  const length = Math.hypot(tip.x - before.x, tip.y - before.y) || 1;
  const way = `${Math.round((tip.x - before.x) / length)},${Math.round((tip.y - before.y) / length)}`;
  return `${Math.round(tip.x / SAME_END)},${Math.round(tip.y / SAME_END)}|${way}`;
}

/** Whether end `a` draws the head before end `b`: the louder look first, then the first by id. */
function drawsBefore(a, b) {
  if (a.loud !== b.loud) return a.loud;
  return a.id < b.id;
}

/**
 * The ends among `ends` that drop their arrowhead because another draws it:
 * each end is `{ id, end, tip, before, styleKey }`, `end` "source" or "target",
 * `tip` the point the line ends at and `before` the point its last run starts
 * from. The answer is a set of `${id}\n${end}`.
 */
export function droppedHeadsOf(ends) {
  const drawing = new Map();
  const dropped = new Set();
  for (const end of ends) {
    const candidate = { ...end, loud: LOUD_LOOKS.has(end.styleKey) };
    const key = endKey(candidate);
    const holder = drawing.get(key);
    if (!holder) {
      drawing.set(key, candidate);
    } else if (drawsBefore(candidate, holder)) {
      dropped.add(`${holder.id}\n${holder.end}`);
      drawing.set(key, candidate);
    } else {
      dropped.add(`${candidate.id}\n${candidate.end}`);
    }
  }
  return dropped;
}
