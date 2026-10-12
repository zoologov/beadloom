// beadloom:component=site-shared-geometry
// The overview's boxes drawn larger than their layout: which top-level nodes, how large, and where a line into one ends.
//
// At the overview a top-level node can be a sliver a few pixels across, too
// small for its title at any size it is tried at. Such a node is drawn as the
// least box that holds its title inside, at the largest of those sizes that
// keeps clear of every other box and inside the box that holds it. The drawn box
// always holds the laid-out one, so no node is drawn anywhere its layout did not
// put it: centred on it where that keeps clear, otherwise as near that as it can,
// flush with a side of the laid-out box or just clear of a box beside it (the
// owner's ruling, 2026-10-11: a title is drawn inside its box, and the box grows
// rather than the title moving out). Where no size keeps inside the box that
// holds it, the size that reaches out of it least is taken, and that box is
// drawn as much larger around it (`routes.js`, `compoundSizeOf`) — never past
// the box the overview's plan keeps every drawn box in (`limit`), past which the
// whole-graph fit would land a step of the map's scale coarser than the one the
// titles were sized at. A node no such box fits around is drawn, when the plan
// asks for every title inside (`always`), at the least box for its title where
// it overlaps the other boxes least: the overview then draws two boxes nearer
// than it should, which its browser tests report, rather than a title outside.
//
// The drawn box is sized in pixels on screen at the scale the overview is
// planned at, and the overview's lines are routed around it, each reaching it
// straight across the room it adds and ending on the laid-out box
// (`shared/grid-routing/overviewRoutes.js`). Zoomed in, the drawn box keeps about its size on screen,
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

/** How much two rectangles overlap, as an area. */
const overlapOf = (a, b) => Math.max(0, Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1)) * Math.max(0, Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1));

/** How many of a place's nearest neighbours its room is weighed by, nearest first (`lessCrowded`). */
const NEAREST_WEIGHED = 4;

/**
 * Whether a place scored by `crowdingOf`, `a`, crowds its neighbours less than
 * `b`: it covers less of them; or as little, and it keeps more room from its
 * nearest neighbour, or as much from that one and more from the next, and so on.
 * One portal's box set beside two others, centred between them, left a line no
 * way past; grown away from the nearer, it did (measured).
 */
const lessCrowded = (a, b) => {
  if (Math.abs(a.covered - b.covered) > EPS) return a.covered < b.covered;
  for (let k = 0; k < NEAREST_WEIGHED; k += 1) {
    const [p, q] = [a.rooms[k] ?? Infinity, b.rooms[k] ?? Infinity];
    if (Math.abs(p - q) > EPS) return p > q;
  }
  return false;
};

/** How far apart rectangles `a` and `b` stand: the larger of their gaps along the two axes, 0 where they meet. */
const separationOf = (a, b) => Math.max(0, a.x1 - b.x2, b.x1 - a.x2, a.y1 - b.y2, b.y1 - a.y2);

/** How `box` crowds `others`: `{ covered, rooms }`, the area it overlaps them by and the room it keeps from each, least first. */
function crowdingOf(box, others) {
  return {
    covered: others.reduce((sum, rect) => sum + overlapOf(box, rect), 0),
    rooms: others.map((rect) => separationOf(box, rect)).sort((p, q) => p - q),
  };
}

/**
 * The places along one axis a span `extent` long may start at and still hold
 * `lo`..`hi`, nearest the centred one first: centred, flush with either end, and
 * just clear by `gap` of each span of `sides` (`[start, end]`) it may stand beside.
 */
function startsAlong(lo, hi, extent, sides, gap) {
  const centred = (lo + hi) / 2 - extent / 2;
  const [least, most] = [hi - extent, lo];
  if (least >= most - EPS) return [centred];
  const tries = [centred, least, most, ...sides.flatMap(([a, b]) => [b + gap, a - gap - extent])];
  const held = tries.filter((t) => t >= least - EPS && t <= most + EPS).map((t) => Math.min(most, Math.max(least, t)));
  return [...new Set(held)].sort((p, q) => Math.abs(p - centred) - Math.abs(q - centred) || p - q);
}

/**
 * Every box of `size` (`{ width, height }`) that holds `laid`, nearest the one
 * centred on it first: centred where it is larger than `laid` on an axis, else
 * flush with a side of `laid` or just clear by `gap` of a box of `others` near it.
 */
function placesOf(laid, size, others, gap) {
  const [width, height] = [Math.max(laid.x2 - laid.x1, size.width), Math.max(laid.y2 - laid.y1, size.height)];
  const reach = { x1: laid.x2 - width - gap, y1: laid.y2 - height - gap, x2: laid.x1 + width + gap, y2: laid.y1 + height + gap };
  const near = others.filter((other) => nearer(reach, other, 0));
  const xs = startsAlong(laid.x1, laid.x2, width, near.map((o) => [o.x1, o.x2]), gap);
  const ys = startsAlong(laid.y1, laid.y2, height, near.map((o) => [o.y1, o.y2]), gap);
  const [cx, cy] = [(laid.x1 + laid.x2) / 2 - width / 2, (laid.y1 + laid.y2) / 2 - height / 2];
  return xs
    .flatMap((x) => ys.map((y) => ({ x1: x, y1: y, x2: x + width, y2: y + height })))
    .sort((a, b) => Math.hypot(a.x1 - cx, a.y1 - cy) - Math.hypot(b.x1 - cx, b.y1 - cy));
}

/**
 * The top-level nodes drawn larger than their layout, and how: a map from each
 * node's id to `{ px, box }`, the size its title is drawn at and its drawn box,
 * in layout units.
 *
 * `candidates` are the ids of the nodes whose title fits their laid-out box at
 * no size it is tried at, in the order they are decided; `boxes` every top-level
 * node's laid-out box by id; `leastBoxOf(id, px)` the least box that holds the
 * node's title inside at `px` (`shared/map-levels/mapMarks.js`, `titleBoxOf`), in layout units;
 * `sizes` the title sizes tried, largest first; `gaps` the room kept from every
 * other box, in layout units, tried in turn; `lines` the polylines of lines drawn
 * as themselves, which no drawn box may cover; `within` the box that holds them
 * all, or null; `limit` a box no drawn box passes, or null.
 *
 * A drawn box always holds the node's laid-out box, and stands centred on it
 * where that keeps clear, otherwise as near that as it can: flush with a side of
 * the laid-out box, or just clear of a box beside it. A node takes the first gap,
 * and within it the largest size, at which its box keeps that room from every
 * other box, those already drawn larger included, covers no line and stays within
 * `within`; failing that, the first gap and the smallest size at which it does
 * all but the last; every box it takes stays within `limit`. With `always`, a
 * node no such box fits is drawn at the least box for its title at the smallest
 * size all the same, where it overlaps the other boxes least and keeps the most
 * room from them (`lessCrowded`): a title is never
 * drawn outside its box (the owner's ruling, 2026-10-11). Otherwise a node that
 * takes none is not in the map. A box no larger than the laid-out one keeps its
 * layout, which needs no room it does not have: `leastBoxOf` may hold a title
 * another way, broken onto two lines, that fits the node as laid out.
 */
export function grownBoxesOf(candidates, boxes, { leastBoxOf, sizes, gaps, lines = [], within = null, limit = null, always = false }) {
  const drawn = new Map(Object.entries(boxes));
  const grown = new Map();
  for (const id of candidates) {
    const laid = boxes[id];
    if (!laid) continue;
    const others = [...drawn].filter(([other]) => other !== id).map(([, rect]) => rect);
    const clear = (box, gap) => others.every((rect) => !nearer(box, rect, gap)) && !crossesAny(box, lines);
    // Centred first, at the largest size that keeps clear; only then off its centre, at the smallest size and
    // a lane from every other box, so a box moved aside takes no more of the room the lines need than its title does.
    const tries = [false, true].flatMap((aside) => {
      const kept = aside ? gaps.slice(0, 1) : gaps;
      return [
        ...kept.flatMap((gap) => (aside ? [...sizes].reverse() : sizes).map((px) => ({ gap, px, held: true, aside }))),
        ...kept.flatMap((gap) => [...sizes].reverse().map((px) => ({ gap, px, held: false, aside }))),
      ];
    });
    let found = null;
    for (const { gap, px, held, aside } of tries) {
      const least = leastBoxOf(id, px);
      if (same(grownAround(laid, least), laid)) {
        found = { px, box: laid };
        break;
      }
      const places = aside ? placesOf(laid, least, others, gap).slice(1) : [grownAround(laid, least)];
      const box = places.find((place) => clear(place, gap) && inside(place, limit) && (!held || inside(place, within)));
      if (box) {
        found = { px, box };
        break;
      }
    }
    if (!found && always) {
      const px = sizes[sizes.length - 1];
      const scored = placesOf(laid, leastBoxOf(id, px), others, gaps[gaps.length - 1] || 0).map((box) => ({ px, box, ...crowdingOf(box, others) }));
      found = scored.reduce((best, place) => (lessCrowded(place, best) ? place : best));
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
 * overview's lines were routed around. On each axis it reaches out past `laid`
 * on either side in the share `planned` does, so a box the plan stood off its
 * laid-out centre shrinks towards `laid` along the way it grew.
 */
export function drawnBoxOf(laid, planned, least) {
  const width = Math.min(planned.x2 - planned.x1, Math.max(laid.x2 - laid.x1, least.width));
  const height = Math.min(planned.y2 - planned.y1, Math.max(laid.y2 - laid.y1, least.height));
  const along = (lo, hi, plannedLo, plannedHi, extent) => {
    const [before, after] = [lo - plannedLo, plannedHi - hi];
    const share = before + after > EPS ? before / (before + after) : 0.5;
    const start = lo - (extent - (hi - lo)) * share;
    return [start, start + extent];
  };
  const [x1, x2] = along(laid.x1, laid.x2, planned.x1, planned.x2, width);
  const [y1, y2] = along(laid.y1, laid.y2, planned.y1, planned.y2, height);
  return { x1, y1, x2, y2 };
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
