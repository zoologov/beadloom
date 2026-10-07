// beadloom:component=site-graph-viewer
// Where each line's count stands: a pill on a free stretch of its own line, clear of every box, title, arrowhead and other pill.
//
// A line of the map that carries more than one edge says how many on a pill: a
// rounded label drawn over every line (`model/pillOverlay.js`), so no later line
// paints over it. A line that carries one edge needs none, unless it is asked to
// say its count whatever it is (`always`): the lines a reader is shown for a node
// under the pointer or selected, whose pills are placed before every other. The pill stands on
// its own line, at a point tried every few pixels along it (`pillPoints.js`), and only where it
// covers no node, no title, no arrowhead and no other pill, and is far enough
// from the line's ends to leave its arrowheads whole. Of the free points the one
// nearest the middle of the line wins, with a price for a corner under the pill
// and for each other line it would cover. After the lines asked to say their
// count, the heaviest lines are placed first. A
// line with no free point has no pill, and its count is in the note the viewer
// shows while the pointer is on the line; but a line asked to say its count says
// it anyway, clear of other pills only, or at its middle when even that finds no
// point (`crowded`): the count of the lines a reader is shown for a node is never missing.
//
// A pill keeps one size on screen. It is placed once per step of the map's scale
// (`model/canvasMap.js`, `scaleAt`) and drawn at that place at any zoom within
// the step, so it is given the room it takes at the step's largest. Nodes,
// titles, arrowheads and pills are filed in a grid of buckets, and the lines'
// segments, horizontal and vertical, in bands across their axis
// (`spatialIndex.js`), so a point tried is compared with what lies near it only:
// with many boxes open thousands of lines are drawn, and zoomed in a line runs
// thousands of pixels, across more buckets than it has points to try.
//
// Every function here is pure: lines, rectangles and a measure in, places out.

import { candidatesOf } from "./pillPoints.js";
import { lineIndex, orientationOf } from "./spatialIndex.js";

/** What a pill measures on screen, in pixels: its height, its text's padding each side and size, the gap kept to the next pill. */
export const PILL_MARKS = Object.freeze({ height: 16, paddingX: 6, font: 10.5, gap: 3 });
/** The fewest edges a line carries for a pill to say how many. */
export const PILL_MIN_WEIGHT = 2;

/** How far around a pill another line counts as covered, in pixels. */
const COVER_PX = 2;
/** What a point costs: per share of the line it lies from the middle, under a corner, per line it covers. */
const PRICE = Object.freeze({ offMiddle: 12, corner: 14, covers: 9 });
/** A pill placed at one step of the map's scale is drawn up to this much larger within the step. */
const STEP_ROOM = Math.sqrt(1.25);

/** The side of the buckets things are filed in, in pixels: a few pills across. */
const BUCKET_PX = 64;
/** The width of the bands the lines' segments are filed in, in pixels: a pill spans a few. */
const SEGMENT_BAND_PX = 8;
/** How far a segment filed as horizontal or vertical may lean off its axis, in pixels (`spatialIndex.js`, `orientationOf`). */
const LEAN_PX = 0.5;
/** Buckets per axis a bucket's key reserves, so that a key is one number: coordinates may be negative. */
const KEY_SPAN = 1 << 20;
const KEY_OFFSET = KEY_SPAN / 2;

const overlaps = (a, b, gap = 0) => a.x1 - gap < b.x2 && a.x2 + gap > b.x1 && a.y1 - gap < b.y2 && a.y2 + gap > b.y1;

/** Whether `see` says to stop, by returning true, for the key of a bucket rectangle `r` meets, in the order `x`, then `y`. */
function forBucketsOf(r, see) {
  const [x2, y2] = [Math.floor(r.x2 / BUCKET_PX), Math.floor(r.y2 / BUCKET_PX)];
  for (let x = Math.floor(r.x1 / BUCKET_PX); x <= x2; x += 1) {
    for (let y = Math.floor(r.y1 / BUCKET_PX); y <= y2; y += 1) if (see((x + KEY_OFFSET) * KEY_SPAN + y + KEY_OFFSET)) return true;
  }
  return false;
}

/** A grid of buckets that things with a rectangle are filed in: a map from a bucket's key to the items filed in it. */
function bucketsOf() {
  return new Map();
}

/** File `item` in `buckets` under every bucket `rect` meets. */
function fileIn(buckets, rect, item) {
  forBucketsOf(rect, (key) => {
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  });
}

/** Whether `test` holds for an item of `parts`, grids of buckets read as one, in a bucket `rect` meets. */
function someNear(parts, rect, test) {
  return forBucketsOf(rect, (key) => {
    for (const buckets of parts) {
      const items = buckets.get(key);
      if (items && items.some(test)) return true;
    }
    return false;
  });
}

/**
 * The lines' segments in pixels, `{ id, a, b }`, filed once: the horizontal and
 * vertical ones in bands across their axis, any other in a list read whole.
 */
function segmentIndexOf(routes, inPixels) {
  const index = lineIndex(SEGMENT_BAND_PX);
  const leaning = [];
  for (const { id, points } of routes) {
    const pixels = points.map(inPixels);
    for (let k = 1; k < pixels.length; k += 1) {
      const segment = { id, a: pixels[k - 1], b: pixels[k] };
      if (orientationOf(segment.a, segment.b)) index.insert(segment, segment.a, segment.b);
      else leaning.push(segment);
    }
  }
  return { index, leaning };
}

/**
 * `see` each segment of `parts` (`segmentIndexOf`) that may meet rectangle `r`,
 * every one that does among them, until `see` says to stop by returning true:
 * whether it did.
 */
function visitSegmentsNear(parts, r, see) {
  for (const { index, leaning } of parts) {
    if (index.along("horizontal", (r.y1 + r.y2) / 2, (r.y2 - r.y1) / 2 + LEAN_PX, r.x1, r.x2, see)) return true;
    if (index.along("vertical", (r.x1 + r.x2) / 2, (r.x2 - r.x1) / 2 + LEAN_PX, r.y1, r.y2, see)) return true;
    for (const segment of leaning) if (see(segment)) return true;
  }
  return false;
}

/** How a clip of a segment by one side of a rectangle (`crosses`) narrows its share `{ t0, t1 }` inside: false when none is left. */
function clipped(p, q, share) {
  if (Math.abs(p) < 1e-9) return !(q < 0);
  const t = q / p;
  if (p < 0) share.t0 = Math.max(share.t0, t);
  else share.t1 = Math.min(share.t1, t);
  return !(share.t0 > share.t1);
}

/** Whether segment `a`-`b` passes through rectangle `r` (Liang-Barsky). */
function crosses(a, b, r) {
  const share = { t0: 0, t1: 1 };
  const [dx, dy] = [b.x - a.x, b.y - a.y];
  return clipped(-dx, a.x - r.x1, share) && clipped(dx, r.x2 - a.x, share) && clipped(-dy, a.y - r.y1, share) && clipped(dy, r.y2 - a.y, share);
}

/**
 * The best free point for a pill `size` (pixels) along `line`, or null. The
 * points are tried nearest the middle first, and the search stops once a point's
 * distance from the middle alone costs as much as the best found: no point
 * further out can be cheaper. A point that surely covers as many lines as
 * make it dearer than the best found is turned down without the other tests,
 * and the walk passes over the points after it on its run that do as well
 * (`coveredAlong`): along a line in a bundle every point covers its neighbours.
 */
function bestPointOf(line, size, { placed, blocked, segments }) {
  let best = null;
  const covers = new Map();
  const triedOn = new Map();
  const points = candidatesOf(line, size);
  // The points of a run the search turns down as too dear, told to the walk so it passes over them.
  let passed;
  for (let next = points.next(); !next.done; next = points.next(passed)) {
    passed = undefined;
    const { a, b, s, length, reach, off, run } = next.value;
    let price = off * PRICE.offMiddle;
    if (best && price >= best.price) break;
    const [x, y] = [a.x + ((b.x - a.x) * s) / length, a.y + ((b.y - a.y) * s) / length];
    // A point that surely covers as many lines as make it too dear is turned down, and so is every point after
    // it on its side and its run that does: the points further out cost more, and the best found only falls.
    if (best) {
      // A run's intervals are found once a few of its points have been tested the long way: on a short run
      // finding them costs more than the tests they would spare.
      const tried = (triedOn.get(run) || 0) + 1;
      triedOn.set(run, tried);
      if (tried === TESTED_BEFORE_INTERVALS) covers.set(run, coveredAlong(line, a, b, size, segments));
      const count = covers.get(run);
      const [atPrice, bestPrice] = [price, best.price];
      const tooDear = (cx, cy) => atPrice + count(cx, cy) * PRICE.covers >= bestPrice;
      if (count && tooDear(x, y)) {
        passed = { run, past: tooDear, along: count.along, nextChange: count.nextChange };
        continue;
      }
    }
    const rect = { x1: x - size.width / 2, y1: y - size.height / 2, x2: x + size.width / 2, y2: y + size.height / 2 };
    const roomy = { x1: rect.x1 - PILL_MARKS.gap, y1: rect.y1 - PILL_MARKS.gap, x2: rect.x2 + PILL_MARKS.gap, y2: rect.y2 + PILL_MARKS.gap };
    if (someNear(placed, roomy, (other) => overlaps(rect, other, PILL_MARKS.gap)) || someNear(blocked, rect, (r) => overlaps(rect, r))) continue;
    if (s < reach || length - s < reach) price += PRICE.corner;
    if (best && price >= best.price) continue;
    const grown = { x1: rect.x1 - COVER_PX, y1: rect.y1 - COVER_PX, x2: rect.x2 + COVER_PX, y2: rect.y2 + COVER_PX };
    const covered = new Set();
    // Counting stops once the lines covered so far cost as much as the best found: this point cannot win.
    const beaten = visitSegmentsNear(segments, grown, (segment) => {
      if (segment.id === line.id || covered.has(segment.id) || !crosses(segment.a, segment.b, grown)) return false;
      covered.add(segment.id);
      return Boolean(best) && price + covered.size * PRICE.covers >= best.price;
    });
    if (beaten) continue;
    price += covered.size * PRICE.covers;
    if (!best || price < best.price) best = { price, x, y, rect };
  }
  return best;
}

/** How many points of a run are tested the long way before the stretches of it that cover lines are found (`coveredAlong`). */
const TESTED_BEFORE_INTERVALS = 8;
/** How far inside a line's reach a point must lie to be counted covered without the exact test, in pixels: far above rounding. */
const SURELY_PX = 1e-3;
/** How far off its axis a run may lean, in pixels, for the lines it surely covers to be found along it. */
const STRAIGHT_PX = 1e-6;

/**
 * How many other lines a pill `size` centred at a point of the run from `a` to
 * `b` of `line` surely covers, as `(x, y) => count`, or null where the run is
 * not horizontal or vertical. Along a straight run the points a line covers a
 * pill at form an interval, so the intervals are found once per run and a point
 * is looked up in them: a line is counted only where the point lies inside its
 * interval by far more than rounding, and never more lines than the exact test
 * finds (`crosses`).
 */
function coveredAlong(line, a, b, size, segments) {
  const horizontal = Math.abs(a.y - b.y) <= STRAIGHT_PX;
  if (!horizontal && Math.abs(a.x - b.x) > STRAIGHT_PX) return null;
  // Along the run (`along`) and across it (`across`): x and y for a horizontal run.
  const [along, across] = horizontal ? ["x", "y"] : ["y", "x"];
  const reach = { along: (horizontal ? size.width : size.height) / 2 + COVER_PX, across: (horizontal ? size.height : size.width) / 2 + COVER_PX };
  const fixed = { lo: Math.min(a[across], b[across]), hi: Math.max(a[across], b[across]) };
  const swept = horizontal
    ? { x1: Math.min(a.x, b.x) - reach.along, x2: Math.max(a.x, b.x) + reach.along, y1: fixed.lo - reach.across, y2: fixed.hi + reach.across }
    : { x1: fixed.lo - reach.across, x2: fixed.hi + reach.across, y1: Math.min(a.y, b.y) - reach.along, y2: Math.max(a.y, b.y) + reach.along };
  // Each other line's intervals, by its id.
  const spansOf = new Map();
  visitSegmentsNear(segments, swept, ({ id, a: c, b: d }) => {
    if (id === line.id) return false;
    // Only a segment that is a point or runs straight along an axis is placed by its box alone.
    if (Math.abs(c.x - d.x) > STRAIGHT_PX && Math.abs(c.y - d.y) > STRAIGHT_PX) return false;
    const box = { lo: Math.min(c[along], d[along]), hi: Math.max(c[along], d[along]) };
    const side = { lo: Math.min(c[across], d[across]), hi: Math.max(c[across], d[across]) };
    // It meets the pill across the run wherever on the run the pill stands, by a margin.
    if (!(side.lo < fixed.lo + reach.across - SURELY_PX && side.hi > fixed.hi - reach.across + SURELY_PX)) return false;
    if (!spansOf.has(id)) spansOf.set(id, []);
    spansOf.get(id).push([box.lo - reach.along + SURELY_PX, box.hi + reach.along - SURELY_PX]);
    return false;
  });
  // A line's intervals joined where they meet, so a point inside it is counted once.
  const spans = [...spansOf.values()].flatMap((own) => {
    own.sort((p, q) => p[0] - q[0]);
    const joined = [];
    for (const span of own) {
      const top = joined[joined.length - 1];
      if (top && span[0] <= top[1]) top[1] = Math.max(top[1], span[1]);
      else joined.push([...span]);
    }
    return joined;
  });
  const count = (x, y) => {
    const at = horizontal ? x : y;
    let covered = 0;
    for (const [lo, hi] of spans) if (lo < at && at < hi) covered += 1;
    return covered;
  };
  // Where the count may change next from `at` on, going `way` (1 or -1) along the run: the nearest end of
  // an interval past it. Between two such ends the count, and so whether a point is too dear, holds.
  count.along = along;
  count.nextChange = (at, way) => {
    let next = way * Infinity;
    for (const [lo, hi] of spans) for (const end of [lo, hi]) if ((end - at) * way > 0 && (end - next) * way < 0) next = end;
    return next;
  };
  return count;
}

/** The middle of the polyline `points` along its length, and the rectangle a pill `size` there covers. */
function middleOf(points, size) {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  let left = lengths.reduce((sum, length) => sum + length, 0) / 2;
  let at = points[0];
  for (let i = 0; i < lengths.length; i += 1) {
    if (left <= lengths[i]) {
      const share = lengths[i] ? left / lengths[i] : 0;
      at = { x: points[i].x + (points[i + 1].x - points[i].x) * share, y: points[i].y + (points[i + 1].y - points[i].y) * share };
      break;
    }
    left -= lengths[i];
  }
  return { x: at.x, y: at.y, rect: { x1: at.x - size.width / 2, y1: at.y - size.height / 2, x2: at.x + size.width / 2, y2: at.y + size.height / 2 } };
}

/**
 * The pills of `lines` at `scale` (layout units per pixel): `{ placed, dropped }`.
 *
 * Each line is `{ id, text, weight, always, points, heads }`: its count, how
 * many edges it carries, whether it says its count even when it is one, its
 * route in the graph's coordinates and whether each end, first and last, has an
 * arrowhead. `drawn` are the routes of every line drawn,
 * `[{ id, points }]`; `blocked` the rectangles no pill may cover — nodes, titles,
 * arrowheads — in the graph's coordinates; `measure(text)` a pill text's width
 * in pixels. A placed pill is `{ id, text, x, y, width, height, crowded }`: its
 * centre in the graph's coordinates, its size on screen, and whether it stands
 * where it covers something, a line asked to say its count having no free point;
 * `dropped` names the lines that were to say their count and have no pill.
 */
export function pillPlacesOf({ lines, drawn, blocked, scale, measure }) {
  return pillStagesOf({ stages: [{ lines, drawn: [drawn], blocked: [blocked] }], scale, measure });
}

/**
 * The pills of the lines of `stages`, placed stage after stage at `scale`, as
 * `pillPlacesOf` places them: `{ placed, dropped }`. Each stage is `{ lines,
 * drawn, blocked }`, its lines placed among its own routes and rectangles and
 * clear of every pill an earlier stage placed, so what a stage reads decides
 * where its pills stand and nothing a later stage reads does. A stage's `drawn`
 * and `blocked` are each a list of parts, and a part two stages share is filed once.
 */
export function pillStagesOf({ stages, scale, measure }) {
  const inPixels = (p) => ({ x: p.x / scale, y: p.y / scale });
  const rectInPixels = (r) => ({ x1: r.x1 / scale, y1: r.y1 / scale, x2: r.x2 / scale, y2: r.y2 / scale });
  /** Each part filed once, by `file(part)`, in `filed`: a part two stages share is the same list. */
  const once = (filed, part, file) => {
    if (!filed.has(part)) filed.set(part, file(part));
    return filed.get(part);
  };
  const [rectGrids, segmentIndexes] = [new Map(), new Map()];
  const rectGridOf = (rects) => {
    const buckets = bucketsOf();
    for (const r of rects) {
      const rect = rectInPixels(r);
      fileIn(buckets, rect, rect);
    }
    return buckets;
  };
  const placed = [bucketsOf()];
  const pills = [];
  const dropped = [];
  // What a line asked to say its count may cover when nothing is free: everything but another pill.
  const nothing = [bucketsOf()];
  for (const stage of stages) {
    const context = {
      placed,
      blocked: stage.blocked.map((part) => once(rectGrids, part, rectGridOf)),
      segments: stage.drawn.map((part) => once(segmentIndexes, part, (routes) => segmentIndexOf(routes, inPixels))),
    };
    const order = stage.lines
      .filter((line) => line.weight >= PILL_MIN_WEIGHT || line.always)
      .sort((a, b) => Number(Boolean(b.always)) - Number(Boolean(a.always)) || b.weight - a.weight || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    for (const line of order) {
      const width = Math.max(PILL_MARKS.height, measure(line.text) + 2 * PILL_MARKS.paddingX);
      const room = { width: width * STEP_ROOM, height: PILL_MARKS.height * STEP_ROOM };
      const inScreen = { ...line, points: line.points.map(inPixels) };
      let best = bestPointOf(inScreen, room, context);
      const crowded = !best && Boolean(line.always);
      if (crowded) best = bestPointOf(inScreen, room, { ...context, blocked: nothing }) || middleOf(inScreen.points, room);
      if (!best) {
        dropped.push(line.id);
        continue;
      }
      pills.push({ id: line.id, text: line.text, x: best.x * scale, y: best.y * scale, width, height: PILL_MARKS.height, crowded });
      fileIn(placed[0], best.rect, best.rect);
    }
  }
  return { placed: pills, dropped: dropped.sort() };
}
