// beadloom:component=site-graph-viewer
// The grid the overview's lines are routed on: tracks between the fixed boxes, what each crossing of two tracks may carry, and each box's ports.
//
// The overview's lines run on tracks: vertical and horizontal lines through the
// whole drawing, at least a pitch apart, one through the middle of every box
// that has room for it and the rest spread evenly between, so two lines on
// neighbouring tracks are always at least a pitch apart. The one exception is a
// track forced through the middle of a box too small for any other, and two
// tracks nearer than a lane carry one line between them. A line moves from one
// crossing of two tracks (a cell) to the next.
//
// Each box is an obstacle: no line enters it or the half pitch around it. Around
// it lies its halo, a band on each side, at most `halo` deep and under half the
// room to the next box, that only the box's own lines enter, and only straight
// at it, so a line arriving at a box has a straight run and nothing runs along
// its side. A title drawn outside its box stands on a plate, and the cells
// within half a pitch of a plate are covered: a line runs there only where no
// other way reaches its box (`overviewRoutes.js` prices it so), and never ends
// at a plate.
//
// A port is where a line leaves or reaches a box: the first cell outside the box
// on a track through one of its sides, a little in from its corners. Its stem is
// the stretch of cells straight out of it that a line of that box does not bend
// on, long enough for an arrowhead and a rounded corner.
//
// Everything here is pure, in pixels at the scale the overview is planned at.

/** Two numbers closer than this are one. */
export const EPS = 1e-6;

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

/** Directions: 0 up, 1 right, 2 down, 3 left. A direction's axis is 0 for a vertical move, 1 for a horizontal one. */
export const DX = Object.freeze([0, 1, 0, -1]);
export const DY = Object.freeze([-1, 0, 1, 0]);

/** A track pair closer than this share of a pitch carries one line between them. */
const TIGHT_SHARE = 0.6;
/** Two tracks through box middles closer than this share of a pitch are one. */
const MIDDLE_SHARE = 1;
/** How much of the room to the next box a halo may take: under half, so two halos never meet. */
const HALO_SHARE = 0.45;
/** How many pitches the grid reaches past the outermost boxes. */
const MARGIN_PITCHES = 6;
/** The most a port's range is inset from a side's corners, in pixels. */
const CORNER_INSET = 3;

/** The range ports may take along `side` (0 top, 1 right, 2 bottom, 3 left) of `box`, a little in from its corners. */
export function sideRange(box, side) {
  const [low, high] = side % 2 === 0 ? [box.x1, box.x2] : [box.y1, box.y2];
  const inset = Math.min(CORNER_INSET, (high - low) / 4);
  return [low + inset, high - inset];
}

/** The first index of the sorted `tracks` at or past `value`. */
export function lowerBound(tracks, value) {
  let low = 0;
  let high = tracks.length;
  while (low < high) {
    const middle = (low + high) >> 1;
    if (tracks[middle] < value) low = middle + 1;
    else high = middle;
  }
  return low;
}

/** Tracks between `min` and `max` at least `pitch` apart, one through the middle of each of `extents` that has room. */
export function tracksOf(min, max, extents, pitch) {
  const middles = [];
  for (const [a, b] of extents) {
    const middle = (a + b) / 2;
    if (middles.every((other) => Math.abs(other - middle) >= MIDDLE_SHARE * pitch)) middles.push(middle);
  }
  // A box none of those passes through gets one through its middle, however near the next.
  for (const [a, b] of extents) {
    const inset = Math.min(CORNER_INSET, (b - a) / 4);
    if (!middles.some((track) => track >= a + inset && track <= b - inset)) middles.push((a + b) / 2);
  }
  middles.sort((a, b) => a - b);
  const anchors = [min, ...middles, max];
  const tracks = [min];
  for (let k = 1; k < anchors.length; k += 1) {
    const gap = anchors[k] - anchors[k - 1];
    const steps = Math.max(1, Math.floor(gap / pitch));
    for (let s = 1; s < steps; s += 1) tracks.push(anchors[k - 1] + (gap * s) / steps);
    tracks.push(anchors[k]);
  }
  return Float64Array.from(tracks);
}

/** The depth of each side's halo of `box` (top, right, bottom, left): at most `depth`, under half the room to the next obstacle. */
function haloOf(box, obstacles, depth) {
  const room = [Infinity, Infinity, Infinity, Infinity];
  for (const other of obstacles) {
    if (other === box) continue;
    const overX = other.x2 > box.x1 && other.x1 < box.x2;
    const overY = other.y2 > box.y1 && other.y1 < box.y2;
    if (overX && other.y2 <= box.y1 + 1) room[0] = Math.min(room[0], box.y1 - other.y2);
    if (overX && other.y1 >= box.y2 - 1) room[2] = Math.min(room[2], other.y1 - box.y2);
    if (overY && other.x1 >= box.x2 - 1) room[1] = Math.min(room[1], other.x1 - box.x2);
    if (overY && other.x2 <= box.x1 + 1) room[3] = Math.min(room[3], box.x1 - other.x2);
  }
  return room.map((gap) => clamp(gap * HALO_SHARE, 0, depth));
}

/** The extent every obstacle spans, `{ minX, minY, maxX, maxY }`. */
function extentOf(obstacles) {
  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const box of obstacles) {
    minX = Math.min(minX, box.x1);
    minY = Math.min(minY, box.y1);
    maxX = Math.max(maxX, box.x2);
    maxY = Math.max(maxY, box.y2);
  }
  return { minX, minY, maxX, maxY };
}

/**
 * The grid for `boxes` and `plates` (each `{ x1, y1, x2, y2 }`, pixels) with
 * `marks` (`{ pitch, halo, run, corner }`); `degree(b)` is how many lines box
 * `b` takes, so the busiest boxes get the first tracks through their middles.
 *
 * `{ xs, ys, nx, ny, interior, covered, band, bandAxis, band2, band2Axis, crowded,
 * tight, ports, stem, cellAt }`: the tracks; per cell, the box whose margin it is
 * in (-1 for none), whether a plate covers it, the one or two boxes whose
 * halo it is in and the axis a line of that box crosses it along (2 for none),
 * and whether it is in three halos; per track, whether it is nearer its next than
 * a lane; each box's ports `[{ cell, dir, at, lead, off, side, slot }]`; per
 * cell, the box whose stem it is on; and the cell nearest a point.
 */
export function gridOf(boxes, plates, marks, degree) {
  const { pitch } = marks;
  const obstacles = [...boxes, ...plates];
  const { minX, minY, maxX, maxY } = extentOf(obstacles);
  const pad = MARGIN_PITCHES * pitch;
  const busiestFirst = boxes.map((box, b) => ({ box, b })).sort((p, q) => degree(q.b) - degree(p.b) || p.b - q.b);
  const xs = tracksOf(minX - pad, maxX + pad, busiestFirst.map(({ box }) => [box.x1, box.x2]), pitch);
  const ys = tracksOf(minY - pad, maxY + pad, busiestFirst.map(({ box }) => [box.y1, box.y2]), pitch);
  const nx = xs.length;
  const ny = ys.length;
  const cells = nx * ny;
  const half = pitch / 2;
  const tightOf = (tracks) => Uint8Array.from(tracks, (value, i) => (i + 1 < tracks.length && tracks[i + 1] - value < TIGHT_SHARE * pitch ? 1 : 0));

  const interior = new Int32Array(cells).fill(-1);
  const covered = new Uint8Array(cells);
  const band = new Int32Array(cells).fill(-1);
  const bandAxis = new Uint8Array(cells);
  const band2 = new Int32Array(cells).fill(-1);
  const band2Axis = new Uint8Array(cells);
  const crowded = new Uint8Array(cells);

  obstacles.forEach((box, b) => {
    const isPlate = b >= boxes.length;
    const [hTop, hRight, hBottom, hLeft] = isPlate ? [0, 0, 0, 0] : haloOf(box, obstacles, marks.halo);
    const [portX1, portX2] = sideRange(box, 0);
    const [portY1, portY2] = sideRange(box, 1);
    const i0 = lowerBound(xs, box.x1 - Math.max(hLeft, half) - EPS);
    const j0 = lowerBound(ys, box.y1 - Math.max(hTop, half) - EPS);
    for (let i = i0; i < nx && xs[i] <= box.x2 + Math.max(hRight, half) + EPS; i += 1) {
      for (let j = j0; j < ny && ys[j] <= box.y2 + Math.max(hBottom, half) + EPS; j += 1) {
        const [x, y] = [xs[i], ys[j]];
        const c = j * nx + i;
        const inX = x >= box.x1 - half && x <= box.x2 + half;
        const inY = y >= box.y1 - half && y <= box.y2 + half;
        if (inX && inY) {
          if (isPlate) covered[c] = 1;
          else if (interior[c] < 0) interior[c] = b;
          continue;
        }
        if (isPlate || (!inX && !inY)) continue;
        const beyond = inX ? (y < box.y1 ? box.y1 - y > hTop : y - box.y2 > hBottom) : x < box.x1 ? box.x1 - x > hLeft : x - box.x2 > hRight;
        if (beyond) continue;
        const axis = inX ? (x >= portX1 - EPS && x <= portX2 + EPS ? 0 : 2) : y >= portY1 - EPS && y <= portY2 + EPS ? 1 : 2;
        if (band[c] < 0) {
          band[c] = b;
          bandAxis[c] = axis;
        } else if (band2[c] < 0) {
          band2[c] = b;
          band2Axis[c] = axis;
        } else crowded[c] = 1;
      }
    }
  });

  const ports = boxes.map((box, b) => portsOf(box, b, { xs, ys, nx, ny, interior }));
  const stem = new Int32Array(cells).fill(-1);
  const reachNeeded = marks.run - marks.corner / 2;
  ports.forEach((list, b) => {
    for (const port of list) {
      let c = port.cell;
      for (let reach = port.lead; reach < reachNeeded; ) {
        if (stem[c] < 0) stem[c] = b;
        const [i, j] = [c % nx, (c / nx) | 0];
        const [i2, j2] = [i + DX[port.dir], j + DY[port.dir]];
        if (i2 < 0 || j2 < 0 || i2 >= nx || j2 >= ny) break;
        reach += port.dir % 2 === 0 ? Math.abs(ys[j2] - ys[j]) : Math.abs(xs[i2] - xs[i]);
        c = j2 * nx + i2;
      }
    }
  });

  const cellAt = (x, y) => [clamp(lowerBound(xs, x - half), 0, nx - 1), clamp(lowerBound(ys, y - half), 0, ny - 1)];
  return { xs, ys, nx, ny, interior, covered, band, bandAxis, band2, band2Axis, crowded, tight: [tightOf(xs), tightOf(ys)], ports, stem, cellAt };
}

/** The ports of `box`, obstacle `b` of `grid`: on each track through a side, the first cell outside it. */
function portsOf(box, b, { xs, ys, nx, ny, interior }) {
  const ports = [];
  const [portX1, portX2] = sideRange(box, 0);
  const [portY1, portY2] = sideRange(box, 1);
  const centre = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };
  for (let i = lowerBound(xs, portX1 - EPS); i < nx && xs[i] <= portX2 + EPS; i += 1) {
    for (const dir of [0, 2]) {
      let j = dir === 0 ? lowerBound(ys, box.y1) - 1 : lowerBound(ys, box.y2 + EPS);
      while (j >= 0 && j < ny && interior[j * nx + i] === b) j += DY[dir];
      if (j < 0 || j >= ny) continue;
      const at = { x: xs[i], y: dir === 0 ? box.y1 : box.y2 };
      ports.push({ cell: j * nx + i, dir, at, lead: Math.abs(ys[j] - at.y), off: Math.abs(xs[i] - centre.x), side: dir + 4 * b, slot: i });
    }
  }
  for (let j = lowerBound(ys, portY1 - EPS); j < ny && ys[j] <= portY2 + EPS; j += 1) {
    for (const dir of [1, 3]) {
      let i = dir === 3 ? lowerBound(xs, box.x1) - 1 : lowerBound(xs, box.x2 + EPS);
      while (i >= 0 && i < nx && interior[j * nx + i] === b) i += DX[dir];
      if (i < 0 || i >= nx) continue;
      const at = { x: dir === 3 ? box.x1 : box.x2, y: ys[j] };
      ports.push({ cell: j * nx + i, dir, at, lead: Math.abs(xs[i] - at.x), off: Math.abs(ys[j] - centre.y), side: dir + 4 * b, slot: j });
    }
  }
  return ports;
}
