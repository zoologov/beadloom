// beadloom:component=site-graph-viewer
// Where each line's count stands: a pill on a free stretch of its own line, clear of every box, title, arrowhead and other pill.
//
// A line of the map that carries more than one edge says how many on a pill: a
// rounded label drawn over every line (`model/pillOverlay.js`), so no later line
// paints over it. A line that carries one edge needs none, unless it is asked to
// say its count whatever it is (`always`): the lines a reader is shown for a node
// under the pointer or selected, whose pills are placed before every other. The pill stands on
// its own line, at a point tried every few pixels along it, and only where it
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
// titles, arrowheads, pills and lines are filed in a grid of buckets, so a point
// tried is compared with what lies near it only: with many boxes open thousands
// of lines are drawn.
//
// Every function here is pure: lines, rectangles and a measure in, places out.

/** What a pill measures on screen, in pixels: its height, its text's padding each side and size, the gap kept to the next pill. */
export const PILL_MARKS = Object.freeze({ height: 16, paddingX: 6, font: 10.5, gap: 3 });
/** The fewest edges a line carries for a pill to say how many. */
export const PILL_MIN_WEIGHT = 2;

/** How far apart the points tried along a line are, in pixels. */
const STEP_PX = 6;
/** The room an end keeps free of a pill, in pixels: an arrowhead (6 px) and a pixel more, or a little where it has none. */
const END_ROOM_PX = Object.freeze({ head: 7, bare: 2 });
/** How far around a pill another line counts as covered, in pixels. */
const COVER_PX = 2;
/** What a point costs: per share of the line it lies from the middle, under a corner, per line it covers. */
const PRICE = Object.freeze({ offMiddle: 12, corner: 14, covers: 9 });
/** A pill placed at one step of the map's scale is drawn up to this much larger within the step. */
const STEP_ROOM = Math.sqrt(1.25);

/** The side of the buckets things are filed in, in pixels: a few pills across. */
const BUCKET_PX = 64;

const overlaps = (a, b, gap = 0) => a.x1 - gap < b.x2 && a.x2 + gap > b.x1 && a.y1 - gap < b.y2 && a.y2 + gap > b.y1;

/** The keys of the buckets rectangle `r` meets. */
function bucketKeysOf(r) {
  const keys = [];
  for (let x = Math.floor(r.x1 / BUCKET_PX); x <= Math.floor(r.x2 / BUCKET_PX); x += 1) {
    for (let y = Math.floor(r.y1 / BUCKET_PX); y <= Math.floor(r.y2 / BUCKET_PX); y += 1) keys.push(`${x},${y}`);
  }
  return keys;
}

/** A grid of buckets that things with a rectangle are filed in: a map from a bucket's key to the items filed in it. */
function bucketsOf() {
  return new Map();
}

/** File `item` in `buckets` under every bucket `rect` meets. */
function fileIn(buckets, rect, item) {
  for (const key of bucketKeysOf(rect)) {
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  }
}

/** Whether `test` holds for an item of `parts`, grids of buckets read as one, in a bucket `rect` meets. */
function someNear(parts, rect, test) {
  for (const key of bucketKeysOf(rect)) {
    for (const buckets of parts) {
      const items = buckets.get(key);
      if (items && items.some(test)) return true;
    }
  }
  return false;
}

/** `see` each item of `parts`, grids of buckets read as one, in every bucket `rect` meets: an item in several, once per bucket. */
function visitNear(parts, rect, see) {
  for (const key of bucketKeysOf(rect)) {
    for (const buckets of parts) {
      const items = buckets.get(key);
      if (items) for (const item of items) see(item);
    }
  }
}

/** Whether segment `a`-`b` passes through rectangle `r` (Liang-Barsky). */
function crosses(a, b, r) {
  let [t0, t1] = [0, 1];
  const [dx, dy] = [b.x - a.x, b.y - a.y];
  for (const [p, q] of [[-dx, a.x - r.x1], [dx, r.x2 - a.x], [-dy, a.y - r.y1], [dy, r.y2 - a.y]]) {
    if (Math.abs(p) < 1e-9) {
      if (q < 0) return false;
      continue;
    }
    const t = q / p;
    if (p < 0) t0 = Math.max(t0, t);
    else t1 = Math.min(t1, t);
    if (t0 > t1) return false;
  }
  return true;
}

/**
 * The points a pill may stand at along `line`, `[{ a, b, s, length, where, off }]`:
 * every few pixels, far enough from each end for its arrowhead and half the
 * pill `size`, nearest the line's middle first, then in the line's order.
 */
function candidatesOf(line, size) {
  const points = line.points;
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  const room = line.heads.map((head) => (head ? END_ROOM_PX.head : END_ROOM_PX.bare));
  const out = [];
  let along = 0;
  for (let i = 0; i < lengths.length; i += 1) {
    const [a, b] = [points[i], points[i + 1]];
    const reach = (Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? size.width : size.height) / 2;
    for (let s = STEP_PX / 2; s < lengths[i]; s += STEP_PX) {
      const where = along + s;
      if (where < room[0] + reach || where > total - room[1] - reach) continue;
      out.push({ a, b, s, length: lengths[i], reach, where, off: Math.abs(where - total / 2) / (total || 1) });
    }
    along += lengths[i];
  }
  return out.sort((x, y) => x.off - y.off || x.where - y.where);
}

/**
 * The best free point for a pill `size` (pixels) along `line`, or null. The
 * points are tried nearest the middle first, and the search stops once a point's
 * distance from the middle alone costs as much as the best found: no point
 * further out can be cheaper.
 */
function bestPointOf(line, size, { placed, blocked, segments }) {
  let best = null;
  for (const { a, b, s, length, reach, off } of candidatesOf(line, size)) {
    let price = off * PRICE.offMiddle;
    if (best && price >= best.price) break;
    const [x, y] = [a.x + ((b.x - a.x) * s) / length, a.y + ((b.y - a.y) * s) / length];
    const rect = { x1: x - size.width / 2, y1: y - size.height / 2, x2: x + size.width / 2, y2: y + size.height / 2 };
    const roomy = { x1: rect.x1 - PILL_MARKS.gap, y1: rect.y1 - PILL_MARKS.gap, x2: rect.x2 + PILL_MARKS.gap, y2: rect.y2 + PILL_MARKS.gap };
    if (someNear(placed, roomy, (other) => overlaps(rect, other, PILL_MARKS.gap)) || someNear(blocked, rect, (r) => overlaps(rect, r))) continue;
    if (s < reach || length - s < reach) price += PRICE.corner;
    if (best && price >= best.price) continue;
    const grown = { x1: rect.x1 - COVER_PX, y1: rect.y1 - COVER_PX, x2: rect.x2 + COVER_PX, y2: rect.y2 + COVER_PX };
    const covered = new Set();
    visitNear(segments, grown, (segment) => {
      if (segment.id !== line.id && crosses(segment.a, segment.b, grown)) covered.add(segment.id);
    });
    price += covered.size * PRICE.covers;
    if (!best || price < best.price) best = { price, x, y, rect };
  }
  return best;
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
  const filed = new Map();
  /** `items` filed in buckets once, by `add(buckets, item)`. */
  const fileOnce = (items, add) => {
    if (!filed.has(items)) {
      const buckets = bucketsOf();
      for (const item of items) add(buckets, item);
      filed.set(items, buckets);
    }
    return filed.get(items);
  };
  const addRect = (buckets, r) => {
    const rect = rectInPixels(r);
    fileIn(buckets, rect, rect);
  };
  const addRoute = (buckets, { id, points }) => {
    const pixels = points.map(inPixels);
    for (let k = 1; k < pixels.length; k += 1) {
      const [a, b] = [pixels[k - 1], pixels[k]];
      fileIn(buckets, { x1: Math.min(a.x, b.x), y1: Math.min(a.y, b.y), x2: Math.max(a.x, b.x), y2: Math.max(a.y, b.y) }, { id, a, b });
    }
  };
  const placed = [bucketsOf()];
  const pills = [];
  const dropped = [];
  // What a line asked to say its count may cover when nothing is free: everything but another pill.
  const nothing = [bucketsOf()];
  for (const stage of stages) {
    const context = { placed, blocked: stage.blocked.map((part) => fileOnce(part, addRect)), segments: stage.drawn.map((part) => fileOnce(part, addRoute)) };
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
