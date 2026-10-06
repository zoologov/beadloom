// beadloom:component=site-graph-viewer
// The overview's boxes drawn larger than their layout: which top-level nodes, how large, and where a line into one ends.
//
// At the overview a top-level node can be a sliver a few pixels across, too
// small for its title at any size it is tried at. Such a node is drawn as the
// least box that holds its title inside, at the largest of those sizes that
// keeps clear of every other box and inside the box that holds it, centred where
// its layout put it, so no node moves. Where no size keeps inside the box that
// holds it, the size that reaches out of it least is taken, and that box is
// drawn as much larger around it (`routes.js`, `compoundSizeOf`). A node no such
// box fits around keeps its laid-out box, and its title stands on a plate
// beside it.
//
// The drawn box is sized in pixels on screen at the scale the overview is
// planned at, and the overview's lines are routed around it, each reaching it
// straight across the room it adds and ending on the laid-out box
// (`overviewRoutes.js`). Zoomed in, the drawn box keeps about its size on screen,
// as its title does, so in the graph's units it shrinks towards the laid-out box
// until the two are one; it never grows past the box the lines were routed
// around. A line into it is drawn up to where it enters the drawn box, which is
// on its last run: as the box shrinks the run only grows longer along itself.
//
// Everything here is pure: boxes, sizes and paths in, boxes and paths out.

/** Two numbers closer than this are one. */
const EPS = 1e-9;

/** `box` (`{ x1, y1, x2, y2 }`) grown to at least `size` (`{ width, height }`) on each axis, around its centre. */
export function grownAround(box, size) {
  const [x, y] = [(box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2];
  const [width, height] = [Math.max(box.x2 - box.x1, size.width), Math.max(box.y2 - box.y1, size.height)];
  return { x1: x - width / 2, y1: y - height / 2, x2: x + width / 2, y2: y + height / 2 };
}

/** Whether rectangles `a` and `b` come closer than `gap`. */
const nearer = (a, b, gap) => a.x1 - gap < b.x2 && a.x2 + gap > b.x1 && a.y1 - gap < b.y2 && a.y2 + gap > b.y1;

/** Whether rectangles `a` and `b` are one, within a hair of rounding. */
const same = (a, b) => Math.abs(a.x1 - b.x1) < EPS && Math.abs(a.y1 - b.y1) < EPS && Math.abs(a.x2 - b.x2) < EPS && Math.abs(a.y2 - b.y2) < EPS;

/** Whether rectangle `inner` lies within `outer`; any rectangle lies within none. */
const inside = (inner, outer) => !outer || (inner.x1 >= outer.x1 && inner.y1 >= outer.y1 && inner.x2 <= outer.x2 && inner.y2 <= outer.y2);

/**
 * Where segment `a`–`b` runs inside `box`: `[enter, leave]`, the shares of its
 * length at which it enters and leaves the closed box, or null when it misses it
 * (Liang and Barsky's clipping).
 */
function clipOf(a, b, box) {
  let [enter, leave] = [0, 1];
  const [dx, dy] = [b.x - a.x, b.y - a.y];
  for (const [p, q] of [[-dx, a.x - box.x1], [dx, box.x2 - a.x], [-dy, a.y - box.y1], [dy, box.y2 - a.y]]) {
    if (Math.abs(p) < EPS) {
      if (q < -EPS) return null;
      continue;
    }
    const t = q / p;
    if (p < 0) enter = Math.max(enter, t);
    else leave = Math.min(leave, t);
    if (enter > leave + EPS) return null;
  }
  return [enter, leave];
}

/** Whether any segment of the polylines `paths` runs inside `box`. */
export function crossesAny(box, paths) {
  return paths.some((path) => path.some((p, k) => k > 0 && clipOf(path[k - 1], p, box) !== null));
}

/**
 * The top-level nodes drawn larger than their layout, and how: a map from each
 * node's id to `{ px, box }`, the size its title is drawn at and its drawn box,
 * in layout units.
 *
 * `candidates` are the ids of the nodes whose title fits their laid-out box at
 * no size it is tried at, in the order they are decided; `boxes` every top-level
 * node's laid-out box by id; `leastBoxOf(id, px)` the least box that holds the
 * node's title inside at `px` (`mapMarks.js`, `titleBoxOf`), in layout units;
 * `sizes` the title sizes tried, largest first; `gaps` the room kept from every
 * other box, in layout units, tried in turn; `lines` the polylines of lines drawn
 * as themselves, which no drawn box may cover; `within` the box that holds them
 * all, or null.
 *
 * A node takes the first gap, and within it the largest size, at which its box
 * keeps that room from every other box, those already drawn larger included,
 * covers no line and stays within `within`; failing that, the first gap and the
 * smallest size at which it does all but the last; a node that takes none is
 * not in the map. A box no larger than the laid-out one keeps its layout, which
 * needs no room it does not have: `leastBoxOf` may hold a title another way,
 * broken onto two lines, that fits the node as laid out.
 */
export function grownBoxesOf(candidates, boxes, { leastBoxOf, sizes, gaps, lines = [], within = null }) {
  const drawn = new Map(Object.entries(boxes));
  const grown = new Map();
  for (const id of candidates) {
    const laid = boxes[id];
    if (!laid) continue;
    const clear = (box, gap) => [...drawn].every(([other, rect]) => other === id || !nearer(box, rect, gap)) && !crossesAny(box, lines);
    const tries = [
      ...gaps.flatMap((gap) => sizes.map((px) => ({ gap, px, held: true }))),
      ...gaps.flatMap((gap) => [...sizes].reverse().map((px) => ({ gap, px, held: false }))),
    ];
    let found = null;
    for (const { gap, px, held } of tries) {
      const box = grownAround(laid, leastBoxOf(id, px));
      if (same(box, laid) || (clear(box, gap) && (!held || inside(box, within)))) {
        found = { px, box };
        break;
      }
    }
    if (!found) continue;
    grown.set(id, found);
    drawn.set(id, found.box);
  }
  return grown;
}

/**
 * The box a grown node is drawn as when the least box for its title is `least`
 * (`{ width, height }`, layout units): that size around the laid-out box `laid`,
 * never smaller than `laid` and never larger than `planned`, the box the
 * overview's lines were routed around.
 */
export function drawnBoxOf(laid, planned, least) {
  const width = Math.min(planned.x2 - planned.x1, Math.max(laid.x2 - laid.x1, least.width));
  const height = Math.min(planned.y2 - planned.y1, Math.max(laid.y2 - laid.y1, least.height));
  return grownAround(laid, { width, height });
}

/** Whether `point` lies in the closed box `box`. */
const isIn = (point, box) => point.x >= box.x1 - EPS && point.x <= box.x2 + EPS && point.y >= box.y1 - EPS && point.y <= box.y2 + EPS;

/** `path` up to where it last enters `box`, which holds its last point; `path` itself when that point is outside. */
function cutAtEnd(path, box) {
  if (!box || !isIn(path[path.length - 1], box)) return path;
  let k = path.length - 1;
  while (k > 0 && isIn(path[k - 1], box)) k -= 1;
  if (k === 0) return null;
  const [a, b] = [path[k - 1], path[k]];
  const clip = clipOf(a, b, box);
  const t = clip ? clip[0] : 1;
  return [...path.slice(0, k), { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }];
}

/**
 * The part of `path` drawn outside the box its first point is in, `first`, and
 * the one its last point is in, `last`: from where it last leaves the one to
 * where it next enters the other. A null box cuts nothing; null when nothing of
 * the path lies outside them.
 */
export function pathOutside(path, first, last) {
  const fromStart = cutAtEnd([...path].reverse(), first);
  if (!fromStart) return null;
  const cut = cutAtEnd(fromStart.reverse(), last);
  return cut && cut.length >= 2 ? cut : null;
}
