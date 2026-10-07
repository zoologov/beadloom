// beadloom:component=site-graph-viewer
// The grid the overview's lines are routed on: tracks between the fixed boxes, what each crossing of two tracks may carry, and each box's ports.
//
// The overview's lines run on tracks: vertical and horizontal lines through the
// whole drawing, at least a pitch apart, one through the middle of every box
// that has room for it and the rest spread evenly between, so two lines on
// neighbouring tracks are always at least a pitch apart. The one exception is a
// track forced through the middle of a box too small for any other, and tracks
// nearer each other than a lane carry one line between them, however many such
// tracks lie together. A line moves from one crossing of two tracks (a cell) to
// the next.
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
// on a track through the straight part of one of its sides, clear of its rounded
// corners (`corners.js`), so a line never ends in the air beside a corner's arc,
// and a little in from a corner however small the box. A box drawn
// larger than its layout to hold its title has ports only on the tracks through
// its laid-out box, its core, so a line into it runs straight on to the core
// however much of the drawn box is left around it (`grownBoxes.js`), and only
// where that track meets the drawn box on the straight part of its side. Its stem is
// the stretch of cells straight out of it that a line of that box does not bend
// on, long enough for an arrowhead and a rounded corner.
//
// The box that holds everything, where there is one, is drawn with a frame, and
// its inside is the only room the lines have: a line that left it to reach a
// sibling box and came back would read as leaving the project. Its frame is an
// outer wall, kept half a pitch from as a box is, so the tracks run inside it.
// Without one, the tracks reach a few pitches past the outermost boxes.
//
// A box nearer the frame than half a pitch has no track through its middle on
// that axis, so no ports on the two sides facing along it; where every track
// through its other sides runs on into a box standing across them, it would have
// no way out at all. Such a box gets a track through the stretch of a side that
// nothing standing across it covers, half a pitch clear of what does where there
// is room: the frame costs a box its ports only where a neighbour blocks them.
//
// Everything here is pure, in pixels at the scale the overview is planned at.

import { cornerRadiusOf } from "./corners.js";

/** Two numbers closer than this are one. */
export const EPS = 1e-6;

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

/** Directions: 0 up, 1 right, 2 down, 3 left. A direction's axis is 0 for a vertical move, 1 for a horizontal one. */
export const DX = Object.freeze([0, 1, 0, -1]);
export const DY = Object.freeze([-1, 0, 1, 0]);

/** Tracks closer than this share of a pitch carry one line between them. */
const TIGHT_SHARE = 0.6;
/** Two tracks through box middles closer than this share of a pitch are one. */
const MIDDLE_SHARE = 1;
/** How much of the room to the next box a halo may take: under half, so two halos never meet. */
const HALO_SHARE = 0.45;
/** How many pitches the grid reaches past the outermost boxes. */
const MARGIN_PITCHES = 6;
/** The least a port's range is inset from a side's corners, in pixels, where the side is long enough: a small box's corners are rounded less. */
const CORNER_INSET = 3;
/** How far a corner's radius may reach past the inset, in pixels, with the inset's ports kept. */
const CORNER_SLACK = 1;

/**
 * The range ports may take along `side` (0 top, 1 right, 2 bottom, 3 left) of
 * `box`, a little in from its corners, and on the straight part of that side of
 * `drawn`, the box drawn around it: past each corner's radius at the plan's
 * scale (`corners.js`). A box is drawn as itself unless the plan draws it larger.
 */
export function sideRange(box, side, drawn = box) {
  const [low, high] = side % 2 === 0 ? [box.x1, box.x2] : [box.y1, box.y2];
  const [drawnLow, drawnHigh] = side % 2 === 0 ? [drawn.x1, drawn.x2] : [drawn.y1, drawn.y2];
  const inset = Math.min(CORNER_INSET, (high - low) / 4);
  const radius = cornerRadiusOf(drawn.x2 - drawn.x1, drawn.y2 - drawn.y1, 1);
  // A corner the inset already all but clears keeps the inset's ports: a port in the last of its arc holds
  // the box's corners that little rounder instead (`corners.js`), unseen, and no line moves for it.
  const corner = radius > inset + CORNER_SLACK ? radius : 0;
  return [Math.max(low + inset, drawnLow + corner), Math.min(high - inset, drawnHigh - corner)];
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

/**
 * Tracks between `min` and `max` at least `pitch` apart, one through the middle
 * of each of `extents` that has room. An extent `[a, b, low, high]` is a box's
 * span and the range its ports take along it (`sideRange`): a box none of the
 * tracks crosses that range at gets one through its middle. A middle at or past
 * `min` or `max` takes no track: a box that close to a frame has no ports on that
 * axis, rather than a line on the frame.
 */
export function tracksOf(min, max, extents, pitch) {
  const middles = [];
  const within = (middle) => middle > min + EPS && middle < max - EPS;
  for (const [a, b] of extents) {
    const middle = (a + b) / 2;
    if (within(middle) && middles.every((other) => Math.abs(other - middle) >= MIDDLE_SHARE * pitch)) middles.push(middle);
  }
  // A box none of those passes through gets one through its middle, however near the next.
  for (const [a, b, low = a + Math.min(CORNER_INSET, (b - a) / 4), high = b - Math.min(CORNER_INSET, (b - a) / 4)] of extents) {
    if (within((a + b) / 2) && !middles.some((track) => track >= low && track <= high)) middles.push((a + b) / 2);
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

/**
 * The extent the tracks span, `{ minX, minY, maxX, maxY }`: inside `frame`, half
 * a pitch in from it, where there is one; else every obstacle's extent and
 * `MARGIN_PITCHES` more on each side.
 */
function trackExtentOf(obstacles, frame, pitch) {
  if (frame) {
    const half = pitch / 2;
    return { minX: frame.x1 + half, minY: frame.y1 + half, maxX: frame.x2 - half, maxY: frame.y2 - half };
  }
  const pad = MARGIN_PITCHES * pitch;
  const { minX, minY, maxX, maxY } = extentOf(obstacles);
  return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad };
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
 * `b` takes, so the busiest boxes get the first tracks through their middles;
 * `cores[b]`, where there is one, is the laid-out box inside box `b`, drawn
 * larger, whose sides its ports and its tracks are taken from; `frame`, where
 * there is one, the box that holds them all, whose inside the tracks keep to.
 * A box with no way out on these tracks gets one more (`freedTracksOf`).
 *
 * `{ xs, ys, nx, ny, interior, inside, covered, band, bandAxis, band2, band2Axis,
 * crowded, near, ports, lead, stem, cellAt }`: the tracks; per cell, the box whose
 * margin it is in (-1 for none) and whether it lies in the box itself, whether a
 * plate covers it, the one or two boxes whose
 * halo it is in and the axis a line of that box crosses it along (2 for none),
 * and whether it is in three halos; per axis and track, the first and the last
 * track nearer it than a lane (`[low, high]`); each box's ports `[{ cell, dir,
 * at, lead, off, side, slot }]`; per cell of a box's margin, the port cell
 * whose way in it lies on (-1 for none), where an arriving line's arrowhead is;
 * per cell, the box whose stem it is on; and the cell nearest a point.
 */
export function gridOf(boxes, plates, marks, degree, cores = [], frame = null) {
  const { pitch } = marks;
  const extent = trackExtentOf([...boxes, ...plates], frame, pitch);
  const busiestFirst = boxes.map((box, b) => ({ box: cores[b] || box, b })).sort((p, q) => degree(q.b) - degree(p.b) || p.b - q.b);
  const xs = tracksOf(extent.minX, extent.maxX, busiestFirst.map(({ box, b }) => [box.x1, box.x2, ...sideRange(box, 0, boxes[b])]), pitch);
  const ys = tracksOf(extent.minY, extent.maxY, busiestFirst.map(({ box, b }) => [box.y1, box.y2, ...sideRange(box, 1, boxes[b])]), pitch);
  const grid = gridOn(xs, ys, boxes, plates, marks, cores);
  const freed = freedTracksOf(grid, boxes, cores, extent, marks);
  if (!freed.xs.length && !freed.ys.length) return grid;
  return gridOn(withTracks(xs, freed.xs), withTracks(ys, freed.ys), boxes, plates, marks, cores);
}

/** The sorted `tracks` with `more` among them. */
function withTracks(tracks, more) {
  return Float64Array.from([...tracks, ...more].sort((a, b) => a - b));
}

/** How far out of a side a box standing across it is looked for, in pitches past the half pitch every box keeps: a little past a line's straight run into it. */
const ACROSS_PITCHES = 2;

/**
 * Tracks that give a way out to each box of `grid` none of whose ports has one,
 * every port's first cell lying inside another box: on each side something
 * stands across within `reach`, one through the middle of the widest stretch of
 * the side's port range, inside the `extent` the tracks span, that none of
 * those boxes covers, nor their half pitch where that leaves a stretch.
 * `{ xs, ys }`, the tracks to add on each axis.
 */
function freedTracksOf(grid, boxes, cores, extent, marks) {
  const freed = { xs: [], ys: [] };
  const half = marks.pitch / 2;
  const reach = half + ACROSS_PITCHES * marks.pitch;
  boxes.forEach((box, b) => {
    if (grid.ports[b].some((port) => !grid.inside[port.cell])) return;
    const core = cores[b] || box;
    for (let side = 0; side < 4; side += 1) {
      const vertical = side % 2 === 0;
      const [low, high] = sideRange(core, side, box);
      const range = vertical ? [Math.max(low, extent.minX), Math.min(high, extent.maxX)] : [Math.max(low, extent.minY), Math.min(high, extent.maxY)];
      if (range[1] < range[0]) continue;
      const across = boxes.filter((other, k) => k !== b && standsAcross(other, box, side, range, reach));
      if (!across.length) continue;
      const spans = (margin) => across.map((other) => (vertical ? [other.x1 - margin, other.x2 + margin] : [other.y1 - margin, other.y2 + margin]));
      const stretch = widestOutside(range, spans(half)) || widestOutside(range, spans(0));
      if (!stretch) continue;
      const middle = (stretch[0] + stretch[1]) / 2;
      const [tracks, list] = vertical ? [grid.xs, freed.xs] : [grid.ys, freed.ys];
      if (![...tracks, ...list].some((track) => Math.abs(track - middle) < EPS)) list.push(middle);
    }
  });
  return freed;
}

/** Whether `other` stands across `side` of `box`, beyond it within `reach`, over the stretch `range` of the side. */
function standsAcross(other, box, side, range, reach) {
  const [low, high] = range;
  if (side % 2 === 0 ? other.x2 <= low || other.x1 >= high : other.y2 <= low || other.y1 >= high) return false;
  if (side === 0) return other.y2 <= box.y1 + EPS && other.y2 >= box.y1 - reach;
  if (side === 2) return other.y1 >= box.y2 - EPS && other.y1 <= box.y2 + reach;
  if (side === 1) return other.x1 >= box.x2 - EPS && other.x1 <= box.x2 + reach;
  return other.x2 <= box.x1 + EPS && other.x2 >= box.x1 - reach;
}

/** The widest stretch of `range` outside every one of `spans`, `[low, high]`, or null where they cover it all. */
function widestOutside(range, spans) {
  let best = null;
  let from = range[0];
  for (const [a, b] of [...spans].sort((p, q) => p[0] - q[0])) {
    if (a > from && (!best || a - from > best[1] - best[0])) best = [from, Math.min(a, range[1])];
    from = Math.max(from, b);
    if (from >= range[1]) break;
  }
  if (from < range[1] && (!best || range[1] - from > best[1] - best[0])) best = [from, range[1]];
  return best && best[1] > best[0] - EPS ? best : null;
}

/** The grid on tracks `xs` and `ys` (`gridOf`). */
function gridOn(xs, ys, boxes, plates, marks, cores) {
  const { pitch } = marks;
  const obstacles = [...boxes, ...plates];
  const nx = xs.length;
  const ny = ys.length;
  const cells = nx * ny;
  const half = pitch / 2;
  const nearOf = (tracks) => {
    const [low, high] = [new Int32Array(tracks.length), new Int32Array(tracks.length)];
    for (let i = 0; i < tracks.length; i += 1) {
      let [a, b] = [i, i];
      while (a > 0 && tracks[i] - tracks[a - 1] < TIGHT_SHARE * pitch) a -= 1;
      while (b + 1 < tracks.length && tracks[b + 1] - tracks[i] < TIGHT_SHARE * pitch) b += 1;
      [low[i], high[i]] = [a, b];
    }
    return [low, high];
  };

  const interior = new Int32Array(cells).fill(-1);
  const inside = new Uint8Array(cells);
  const covered = new Uint8Array(cells);
  const band = new Int32Array(cells).fill(-1);
  const bandAxis = new Uint8Array(cells);
  const band2 = new Int32Array(cells).fill(-1);
  const band2Axis = new Uint8Array(cells);
  const crowded = new Uint8Array(cells);

  obstacles.forEach((box, b) => {
    const isPlate = b >= boxes.length;
    const [hTop, hRight, hBottom, hLeft] = isPlate ? [0, 0, 0, 0] : haloOf(box, obstacles, marks.halo);
    const portBox = (!isPlate && cores[b]) || box;
    const [portX1, portX2] = sideRange(portBox, 0, box);
    const [portY1, portY2] = sideRange(portBox, 1, box);
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
          if (!isPlate && x >= box.x1 && x <= box.x2 && y >= box.y1 && y <= box.y2) inside[c] = 1;
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

  const lead = new Int32Array(cells).fill(-1);
  const ports = boxes.map((box, b) => portsOf(box, b, { xs, ys, nx, ny, interior }, lead, cores[b] || box));
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
  return { xs, ys, nx, ny, interior, inside, covered, band, bandAxis, band2, band2Axis, crowded, near: [nearOf(xs), nearOf(ys)], ports, lead, stem, cellAt };
}

/**
 * The ports of `box`, obstacle `b` of `grid`: on each track through a side of
 * `core`, the box it was laid out as, clear of `box`'s rounded corners
 * (`sideRange`), the first cell outside `box`. Each margin
 * cell between the side and a port is noted in `lead` with the port's cell.
 */
function portsOf(box, b, { xs, ys, nx, ny, interior }, lead, core) {
  const ports = [];
  const [portX1, portX2] = sideRange(core, 0, box);
  const [portY1, portY2] = sideRange(core, 1, box);
  const centre = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };
  for (let i = lowerBound(xs, portX1 - EPS); i < nx && xs[i] <= portX2 + EPS; i += 1) {
    for (const dir of [0, 2]) {
      let j = dir === 0 ? lowerBound(ys, box.y1) - 1 : lowerBound(ys, box.y2 + EPS);
      const walked = [];
      while (j >= 0 && j < ny && interior[j * nx + i] === b) {
        walked.push(j * nx + i);
        j += DY[dir];
      }
      if (j < 0 || j >= ny) continue;
      for (const cell of walked) lead[cell] = j * nx + i;
      const at = { x: xs[i], y: dir === 0 ? box.y1 : box.y2 };
      ports.push({ cell: j * nx + i, dir, at, lead: Math.abs(ys[j] - at.y), off: Math.abs(xs[i] - centre.x), side: dir + 4 * b, slot: i });
    }
  }
  for (let j = lowerBound(ys, portY1 - EPS); j < ny && ys[j] <= portY2 + EPS; j += 1) {
    for (const dir of [1, 3]) {
      let i = dir === 3 ? lowerBound(xs, box.x1) - 1 : lowerBound(xs, box.x2 + EPS);
      const walked = [];
      while (i >= 0 && i < nx && interior[j * nx + i] === b) {
        walked.push(j * nx + i);
        i += DX[dir];
      }
      if (i < 0 || i >= nx) continue;
      for (const cell of walked) lead[cell] = j * nx + i;
      const at = { x: dir === 3 ? box.x1 : box.x2, y: ys[j] };
      ports.push({ cell: j * nx + i, dir, at, lead: Math.abs(xs[i] - at.x), off: Math.abs(ys[j] - centre.y), side: dir + 4 * b, slot: j });
    }
  }
  return ports;
}
