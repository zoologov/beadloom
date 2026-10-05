// beadloom:component=site-graph-viewer
// Indexes over a drawing: what lies near a place, without looking at everything.
//
// The edge bundling (`bundles.js`) and the route index a hover reads
// (`routeIndex.js`) ask two questions many times over one drawing: which boxes lie in this small
// window, and which segments run along this line. Asked of every box and every
// segment, each costs the size of the graph, and at an adopter's size (some 450
// boxes and 1,300 routes) the bundling took 100 to 230 ms that way.
//
// - `gridIndex` files a rectangle under the square cells it covers; a window
//   visits the boxes in the few cells it covers.
// - `lineIndex` files an axis-aligned segment under its orientation and the band
//   its fixed coordinate falls in; a line visits the segments in the bands its
//   clearance covers. A routed edge is orthogonal and its segments can span the
//   whole drawing: filed under every cell they cross, as the grid files a box,
//   they cost more than the index saves (measured in Node 18 on an adopter-sized
//   graph: 85 ms for the bundling against 17), while a band holds each once.
//
// A query visits each item once. An item cannot be removed: a caller that
// replaces one files the new one and skips the old one when it visits it.

/** Cells per axis a grid key reserves, so that a cell's key is one number. */
const KEY_SPAN = 1 << 20;
/** The cell index a grid key's zero stands for: coordinates may be negative. */
const KEY_OFFSET = KEY_SPAN / 2;
/** Two coordinates closer than this are one: a segment that keeps one is axis-aligned. */
const SAME = 0.5;

/** Whether two rectangles `{ x1, y1, x2, y2 }` meet, their borders included. */
function rectanglesMeet(a, b) {
  return a.x1 <= b.x2 && b.x1 <= a.x2 && a.y1 <= b.y2 && b.y1 <= a.y2;
}

/** The rectangle a segment from `a` to `b` covers, grown by `margin` on every side. */
export function segmentRect(a, b, margin = 0) {
  return {
    x1: Math.min(a.x, b.x) - margin,
    y1: Math.min(a.y, b.y) - margin,
    x2: Math.max(a.x, b.x) + margin,
    y2: Math.max(a.y, b.y) + margin,
  };
}

/**
 * An empty grid of `cellSize`-unit cells: `{ insert(item, rect), query(rect, visit) }`.
 *
 * `insert` files `item` under `rect`; `query` calls `visit(item, rect)` once for
 * every item whose rectangle meets `rect`.
 */
export function gridIndex(cellSize) {
  const cells = new Map();
  let stamp = 0;
  const cellOf = (value) => Math.floor(value / cellSize) + KEY_OFFSET;
  const forCells = (rect, each) => {
    const i2 = cellOf(rect.x2);
    const j2 = cellOf(rect.y2);
    for (let i = cellOf(rect.x1); i <= i2; i += 1) {
      for (let j = cellOf(rect.y1); j <= j2; j += 1) each(i * KEY_SPAN + j);
    }
  };
  return {
    insert(item, rect) {
      const entry = { item, rect, seen: 0 };
      forCells(rect, (key) => {
        const cell = cells.get(key);
        if (cell) cell.push(entry);
        else cells.set(key, [entry]);
      });
    },
    query(rect, visit) {
      stamp += 1;
      forCells(rect, (key) => {
        for (const entry of cells.get(key) || []) {
          if (entry.seen === stamp) continue;
          entry.seen = stamp;
          if (rectanglesMeet(entry.rect, rect)) visit(entry.item, entry.rect);
        }
      });
    },
  };
}

/** Whether the segment from `a` to `b` is horizontal, vertical, or neither (null). */
export function orientationOf(a, b) {
  if (Math.abs(a.y - b.y) < SAME) return "horizontal";
  if (Math.abs(a.x - b.x) < SAME) return "vertical";
  return null;
}

/**
 * An empty index of axis-aligned segments in `band`-unit bands:
 * `{ insert(item, a, b), along(orientation, at, clearance, lo, hi, visit) }`.
 *
 * `insert` files `item`, the segment from `a` to `b`, and ignores a segment that
 * is neither horizontal nor vertical. `along` calls `visit(item, a, b)` once for
 * every segment of `orientation` ("horizontal" or "vertical") whose fixed
 * coordinate lies within `clearance` of `at` and whose span meets `[lo, hi]`.
 */
export function lineIndex(band) {
  const lines = { horizontal: new Map(), vertical: new Map() };
  const bandOf = (value) => Math.floor(value / band);
  return {
    insert(item, a, b) {
      const orientation = orientationOf(a, b);
      if (!orientation) return;
      const horizontal = orientation === "horizontal";
      const fixed = horizontal ? a.y : a.x;
      const lo = horizontal ? Math.min(a.x, b.x) : Math.min(a.y, b.y);
      const hi = horizontal ? Math.max(a.x, b.x) : Math.max(a.y, b.y);
      const entry = { item, a, b, fixed, lo, hi };
      const key = bandOf(fixed);
      const entries = lines[orientation];
      if (entries.has(key)) entries.get(key).push(entry);
      else entries.set(key, [entry]);
    },
    along(orientation, at, clearance, lo, hi, visit) {
      const entries = lines[orientation];
      for (let key = bandOf(at - clearance); key <= bandOf(at + clearance); key += 1) {
        for (const entry of entries.get(key) || []) {
          if (Math.abs(entry.fixed - at) > clearance || entry.hi < lo || entry.lo > hi) continue;
          visit(entry.item, entry.a, entry.b);
        }
      }
    },
  };
}
