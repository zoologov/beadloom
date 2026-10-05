// beadloom:component=site-graph-viewer
// Where each line's count stands: a pill on a free stretch of its own line, clear of every box, title, arrowhead and other pill.
//
// A line of the map that carries more than one edge says how many on a pill: a
// rounded label drawn over every line (`model/pillOverlay.js`), so no later line
// paints over it. A line that carries one edge needs none. The pill stands on
// its own line, at a point tried every few pixels along it, and only where it
// covers no node, no title, no arrowhead and no other pill, and is far enough
// from the line's ends to leave its arrowheads whole. Of the free points the one
// nearest the middle of the line wins, with a price for a corner under the pill
// and for each other line it would cover. The heaviest lines are placed first. A
// line with no free point has no pill, and its count is in the note the viewer
// shows while the pointer is on the line.
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

/** A grid of buckets that things with a rectangle are filed in: `{ add(rect, item), near(rect) }`, `near` giving the items of every bucket the rectangle meets. */
function bucketsOf() {
  const buckets = new Map();
  const each = (r, visit) => {
    for (let x = Math.floor(r.x1 / BUCKET_PX); x <= Math.floor(r.x2 / BUCKET_PX); x += 1) {
      for (let y = Math.floor(r.y1 / BUCKET_PX); y <= Math.floor(r.y2 / BUCKET_PX); y += 1) visit(`${x},${y}`);
    }
  };
  return {
    add(rect, item) {
      each(rect, (key) => {
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push(item);
      });
    },
    near(rect) {
      const found = [];
      each(rect, (key) => {
        const items = buckets.get(key);
        if (items) for (const item of items) found.push(item);
      });
      return found;
    },
  };
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

/** The best free point for a pill `size` (pixels) along `line`, or null. */
function bestPointOf(line, size, { placed, blocked, segments }) {
  const points = line.points;
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  const room = line.heads.map((head) => (head ? END_ROOM_PX.head : END_ROOM_PX.bare));
  let best = null;
  let along = 0;
  for (let i = 0; i < lengths.length; i += 1) {
    const [a, b] = [points[i], points[i + 1]];
    const reach = (Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? size.width : size.height) / 2;
    for (let s = STEP_PX / 2; s < lengths[i]; s += STEP_PX) {
      const where = along + s;
      if (where < room[0] + reach || where > total - room[1] - reach) continue;
      const [x, y] = [a.x + ((b.x - a.x) * s) / lengths[i], a.y + ((b.y - a.y) * s) / lengths[i]];
      const rect = { x1: x - size.width / 2, y1: y - size.height / 2, x2: x + size.width / 2, y2: y + size.height / 2 };
      const roomy = { x1: rect.x1 - PILL_MARKS.gap, y1: rect.y1 - PILL_MARKS.gap, x2: rect.x2 + PILL_MARKS.gap, y2: rect.y2 + PILL_MARKS.gap };
      if (placed.near(roomy).some((other) => overlaps(rect, other, PILL_MARKS.gap)) || blocked.near(rect).some((r) => overlaps(rect, r))) continue;
      let price = (Math.abs(where - total / 2) / (total || 1)) * PRICE.offMiddle;
      if (s < reach || lengths[i] - s < reach) price += PRICE.corner;
      if (best && price >= best.price) continue;
      const grown = { x1: rect.x1 - COVER_PX, y1: rect.y1 - COVER_PX, x2: rect.x2 + COVER_PX, y2: rect.y2 + COVER_PX };
      const covered = new Set();
      for (const segment of segments.near(grown)) if (segment.id !== line.id && crosses(segment.a, segment.b, grown)) covered.add(segment.id);
      price += covered.size * PRICE.covers;
      if (!best || price < best.price) best = { price, x, y, rect };
    }
    along += lengths[i];
  }
  return best;
}

/**
 * The pills of `lines` at `scale` (layout units per pixel): `{ placed, dropped }`.
 *
 * Each line is `{ id, text, weight, points, heads }`: its count, how many edges
 * it carries, its route in the graph's coordinates and whether each end, first
 * and last, has an arrowhead. `drawn` are the routes of every line drawn,
 * `[{ id, points }]`; `blocked` the rectangles no pill may cover — nodes, titles,
 * arrowheads — in the graph's coordinates; `measure(text)` a pill text's width
 * in pixels. A placed pill is `{ id, text, x, y, width, height }`: its centre in
 * the graph's coordinates and its size on screen; `dropped` names the lines that
 * carry more than one edge and found no free point.
 */
export function pillPlacesOf({ lines, drawn, blocked, scale, measure }) {
  const inPixels = (p) => ({ x: p.x / scale, y: p.y / scale });
  const rectInPixels = (r) => ({ x1: r.x1 / scale, y1: r.y1 / scale, x2: r.x2 / scale, y2: r.y2 / scale });
  const context = { placed: bucketsOf(), blocked: bucketsOf(), segments: bucketsOf() };
  for (const rect of blocked.map(rectInPixels)) context.blocked.add(rect, rect);
  for (const { id, points } of drawn) {
    const pixels = points.map(inPixels);
    for (let k = 1; k < pixels.length; k += 1) {
      const [a, b] = [pixels[k - 1], pixels[k]];
      context.segments.add({ x1: Math.min(a.x, b.x), y1: Math.min(a.y, b.y), x2: Math.max(a.x, b.x), y2: Math.max(a.y, b.y) }, { id, a, b });
    }
  }
  const pills = [];
  const dropped = [];
  const order = lines
    .filter((line) => line.weight >= PILL_MIN_WEIGHT)
    .sort((a, b) => b.weight - a.weight || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  for (const line of order) {
    const width = Math.max(PILL_MARKS.height, measure(line.text) + 2 * PILL_MARKS.paddingX);
    const room = { width: width * STEP_ROOM, height: PILL_MARKS.height * STEP_ROOM };
    const best = bestPointOf({ ...line, points: line.points.map(inPixels) }, room, context);
    if (!best) {
      dropped.push(line.id);
      continue;
    }
    pills.push({ id: line.id, text: line.text, x: best.x * scale, y: best.y * scale, width, height: PILL_MARKS.height });
    context.placed.add(best.rect, best.rect);
  }
  return { placed: pills, dropped: dropped.sort() };
}
