// beadloom:component=site-graph-viewer
// The overview's own routes: every aggregated line between two top-level ends, routed afresh between the fixed boxes.
//
// A route ELK computed runs between two nodes at full detail; the overview joins
// boxes, and the medoid of a pair's routes (`aggregateRoutes.js`) runs where its
// edges ran, which is beside the next pair's, under a title, and into its box
// after a bend too close for an arrowhead. So at the overview every line is
// routed again, all of them together, on the grid of tracks between the boxes
// (`overviewGrid.js`): from a port of one box to a port of the other, around
// every box and every title plate, with a straight run into each box. A route
// costs its length, and more for each bend, each line it crosses and each run
// beside another line; the cheapest is taken (A* over the cells and the
// direction a line enters them in). A title's plate is priced so high that a
// line runs under one only where no other way reaches its box: on a graph whose
// top level does not fit the canvas, plates larger than their boxes can cover
// every way in. Lines are routed shortest span first, and then each once more,
// now that it knows every other.
//
// Two lines never share a track, with one exception: lines that end at one box
// and agree on having an arrowhead there may share their last run and end in one
// port, so they end in one arrowhead (`heads.js`), and a line with a head never
// shares its last run with one without. Lines that reach a box separately stay a
// track apart. A line with no corner at all is accepted only when it is long
// enough for the arrowheads it carries, so two boxes nearer than that are joined
// around a corner instead. A line no route reaches under these rules — a small
// box whose every way out is closed by its neighbours' halos and lines — is
// routed once more with each refusal priced instead (`COST.forced`): it may run
// along another line, through a halo or through another box's margin, but it
// still enters no box, runs straight into its own, keeps a lane from every other
// line and keeps off every arrowhead. A line that finds no route even so, where
// the lines laid before it closed its ways in, is routed before them: its
// cheapest route through their room names the lines in its way, they are taken
// up, it is laid, and they are laid again around it, each kept where it still
// fits; where one of them then finds no route, the plan is put back as it was.
// No box moves; a line nothing can route even so keeps no route here, and its
// caller draws its medoid instead.
//
// A box can be drawn larger than its layout, to hold its title
// (`grownBoxes.js`): the drawn box is the obstacle, its ports lie only where a
// straight run reaches the laid-out box inside it, and the line is carried on
// along that run to the laid-out box's border. The drawn box may shrink back
// towards the laid-out one as the view is zoomed in, and the line, cut where it
// enters the drawn box, then only grows longer along its last run.
//
// The box that holds everything, where there is one, is a frame the lines keep
// inside (`overviewGrid.js`): no route leaves it to reach a sibling box. A pair
// with no way between its boxes inside the frame is named among those with no
// route, never routed round the outside.
//
// Everything here is pure and deterministic for its input: boxes, plates, pairs
// and lines in, routes out.

import { DX, DY, EPS, gridOf } from "./overviewGrid.js";

/**
 * What the overview's lines measure on screen, in pixels: the pitch of the
 * tracks, the deepest a halo reaches, the straight run before a box (an
 * arrowhead, a rounded corner and a little room), a corner's radius, an
 * arrowhead's length, and the line left between two arrowheads of one straight line.
 */
export const OVERVIEW_MARKS = Object.freeze({ pitch: 8, halo: 14, run: 15, corner: 6, head: 6, between: 2 });

/**
 * What a line costs, in pixels of its length: a bend, a crossing, a run beside
 * another line, a shared run, a port shared or crowded, a port off its side's
 * middle, a cell under a plate, each refusal a line routed a second time passes
 * over, and each line whose room a line routed through them takes.
 */
const COST = Object.freeze({ bend: 30, cross: 10, beside: 0.3, share: 2, shareOnce: 60, portBeside: 35, offCentre: 0.12, underPlate: 1000, forced: 400, inTheWay: 2000 });
/**
 * How a line is routed: by every rule; with what the rules refuse priced
 * instead; or through the room other lines keep too, at a price for each line
 * whose room it takes, to find which lines are in its way.
 */
const STRICT = 0;
const RELAXED = 1;
const THROUGH = 2;
/**
 * How far the search leans towards its target: above 1 a route is no longer
 * sure to be the cheapest, and is found among far fewer cells. At 1.5, measured
 * on three overview graphs and 200 generated ones, every route the plain search
 * found is found, no gap narrows and no arrowhead overlaps; at 2 arrowheads
 * start to lie under other lines.
 */
const GREED = 1.5;
/** The occupant a line drawn as itself leaves on a cell: no planned line runs along it. */
const FIXED = 0x7fffffff;
/** A fixed line keeps planned lines this share of a pitch away from running along it. */
const FIXED_REACH = 0.6;

/** `path` without repeated points and without a point in the middle of a straight run. */
function simplify(path) {
  const out = [];
  for (const p of path) {
    const last = out[out.length - 1];
    if (last && Math.abs(last.x - p.x) < EPS && Math.abs(last.y - p.y) < EPS) continue;
    out.push({ x: p.x, y: p.y });
    while (out.length >= 3) {
      const [a, b, c] = out.slice(-3);
      const cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
      const dot = (b.x - a.x) * (c.x - b.x) + (b.y - a.y) * (c.y - b.y);
      if (Math.abs(cross) < EPS && dot > 0) out.splice(out.length - 2, 1);
      else break;
    }
  }
  return out;
}

/** A binary heap of states by cost, cheapest first, in typed arrays that grow. The same pushes give the same pops, so a plan is the same for the same input. */
class Heap {
  constructor() {
    this.keys = new Float64Array(1024);
    this.values = new Int32Array(1024);
    this.size = 0;
  }
  push(key, value) {
    if (this.size === this.keys.length) {
      const [keys, values] = [new Float64Array(this.size * 2), new Int32Array(this.size * 2)];
      keys.set(this.keys);
      values.set(this.values);
      [this.keys, this.values] = [keys, values];
    }
    const { keys, values } = this;
    let i = this.size;
    this.size += 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (keys[parent] <= key) break;
      keys[i] = keys[parent];
      values[i] = values[parent];
      i = parent;
    }
    keys[i] = key;
    values[i] = value;
  }
  pop() {
    const { keys, values } = this;
    const top = values[0];
    this.size -= 1;
    const n = this.size;
    if (!n) return top;
    const key = keys[n];
    const value = values[n];
    let i = 0;
    for (;;) {
      let child = 2 * i + 1;
      if (child >= n) break;
      if (child + 1 < n && keys[child + 1] < keys[child]) child += 1;
      if (keys[child] >= key) break;
      keys[i] = keys[child];
      values[i] = values[child];
      i = child;
    }
    keys[i] = key;
    values[i] = value;
    return top;
  }
}

/**
 * The fewest turns a line heading `dir` must still make to arrive straight at a
 * box `dx` and `dy` away (0 where it is level with the box on that axis); `right`
 * and `down` are the directions that close the distance on each axis.
 */
function bendsLeft(dx, dy, right, down, dir) {
  if (dx > 0 && dy > 0) return 1;
  if (dx > 0) return dir === right ? 0 : dir % 2 === 1 ? 2 : 1;
  if (dy > 0) return dir === down ? 0 : dir % 2 === 0 ? 2 : 1;
  return 0;
}

/** How far apart `a` and `b` are, along both axes, with nothing between them counted. */
function spanOf(a, b) {
  return Math.max(b.x1 - a.x2, a.x1 - b.x2, 0) + Math.max(b.y1 - a.y2, a.y1 - b.y2, 0);
}

/**
 * The router over `grid` for `pairs` (`{ a, b, forward, backward }`, box indices
 * and counts): `{ route, mark, sharing, keepLedger }`, with the cells each line
 * occupies kept between calls. `fixed` are the polylines of lines drawn as
 * themselves, in pixels.
 */
function routerOn(grid, pairs, fixed, marks) {
  const { xs, ys, nx, ny, interior, inside, covered, band, bandAxis, band2, band2Axis, crowded, near, ports, lead, stem } = grid;
  const cells = nx * ny;
  // Per axis: the first line through a cell (1-based; FIXED for a fixed line) and how many; where a line bends.
  const owner = [new Int32Array(cells), new Int32Array(cells)];
  const count = [new Uint16Array(cells), new Uint16Array(cells)];
  const corner = new Uint16Array(cells);
  // The box whose line first ran along a cell, per axis: lines of that box alike may share it.
  const trunk = [new Int32Array(cells).fill(-1), new Int32Array(cells).fill(-1)];
  const sharing = pairs.map(() => false);
  const ends = pairs.map((pair) => [pair.a, pair.b]);
  const headAt = (e, box) => (ends[e][0] === box ? pairs[e].backward > 0 : pairs[e].forward > 0);
  markFixed(grid, owner, fixed);

  const states = cells * 4;
  const best = new Float64Array(states);
  const from = new Int32Array(states);
  const seen = new Uint32Array(states);
  const done = new Uint32Array(states);
  const goalSeen = new Uint32Array(states);
  const goalCost = new Float64Array(states);
  // Whether the best way into a state has turned: a straight line must be long enough for its arrowheads.
  const turned = new Uint8Array(states);
  let stamp = 0;

  // The first and the last track within a lane of each track, per axis.
  const nearLow = [near[0][0], near[1][0]];
  const nearHigh = [near[0][1], near[1][1]];
  /** The line along `axis` through `cell`, 1-based, or 0: a used port's way in counts as its line's. */
  const occupied = (axis, cell) => owner[axis][cell] || (lead[cell] >= 0 ? owner[axis][lead[cell]] : 0);

  /**
   * The route of line `e`, or null, routed `how` (`STRICT`, `RELAXED` or
   * `THROUGH`); routed `THROUGH`, the lines whose room it takes are added to
   * `inTheWay`. With `kept`, a route the line had, that route where the line
   * may still run along it, else null, and no search.
   */
  function route(e, how = STRICT, inTheWay = null, kept = null) {
    const relaxed = how >= RELAXED;
    const [a, b] = ends[e];
    const target = grid.boxes[b];
    stamp += 1;
    /** Whether line `o` (1-based) may share a cell with line `e` by box `x`: both end at `x`, alike. */
    const sibling = (o, x) => o !== FIXED && x >= 0 && (x === a || x === b) && (ends[o - 1][0] === x || ends[o - 1][1] === x) && headAt(o - 1, x) === headAt(e, x);
    // Routed `THROUGH`: how many lines' room the cell being entered takes, and where to name them.
    let through = 0;
    let blamed = null;
    /**
     * Whether a line routed `THROUGH` may take the room line `o` (1-based) keeps
     * along `axis` at `cell`: not where `o` is a fixed line. Where it may, every
     * line on the cell, or on the way into the port the cell is, is counted and
     * named: one taken up leaves the others there.
     */
    const takes = (o, cell, axis) => {
      if (o === FIXED) return false;
      let lines = 0;
      for (const at of [cell, lead[cell]]) {
        const here = at >= 0 && ledger ? ledger.get(at * 2 + axis) : null;
        if (!here) continue;
        lines += here.length;
        if (blamed) for (const line of here) blamed.add(line);
      }
      if (blamed) blamed.add(o - 1);
      through += Math.max(1, lines);
      return true;
    };
    /** What entering cell `c` along `axis` adds, or -1 when the line may not enter it. */
    const entering = (c, axis) => {
      if (inside[c] || (interior[c] >= 0 && !relaxed)) return -1;
      through = 0;
      // Never, even priced, over the way into a port a line uses: its arrowhead is there.
      const into = lead[c] >= 0 ? owner[0][lead[c]] || owner[1][lead[c]] : 0;
      if (into && !(how === THROUGH && takes(into, lead[c], 0) && takes(into, lead[c], 1))) return -1;
      // A box's margin, priced on a second routing: a small box wedged between others has no other way out.
      let forced = interior[c] >= 0 ? 1 : 0;
      if (crowded[c]) {
        if (!relaxed) return -1;
        forced += 1;
      }
      const b1 = band[c];
      if (b1 >= 0) {
        const b2 = band2[c];
        const foreign = (b1 !== a && b1 !== b) || bandAxis[c] !== axis || (b2 >= 0 && ((b2 !== a && b2 !== b) || band2Axis[c] !== axis));
        if (foreign) {
          if (!relaxed) return -1;
          forced += 1;
        }
      }
      // A line along a track nearer than a lane to this one, beside this cell, leaves no room for a
      // second; nor does one that ends on this very track within a lane, ahead or behind. Never, even
      // priced: two lines nearer than a lane read as one. Most tracks have no such neighbour.
      const i = c % nx;
      const j = (c / nx) | 0;
      const across0 = nearLow[0][i] < nearHigh[0][i];
      const across1 = nearLow[1][j] < nearHigh[1][j];
      if (axis === 0) {
        if (across0) {
          for (let k = nearLow[0][i]; k <= nearHigh[0][i]; k += 1) {
            const other = k !== i ? occupied(0, c - i + k) : 0;
            if (other && !(how === THROUGH && takes(other, c - i + k, 0))) return -1;
          }
        }
        if (across1) {
          for (let k = nearLow[1][j]; k <= nearHigh[1][j]; k += 1) {
            const other = k !== j ? occupied(0, c + (k - j) * nx) : 0;
            if (other && other !== owner[0][c] && !(how === THROUGH && takes(other, c + (k - j) * nx, 0))) return -1;
          }
        }
      } else {
        if (across1) {
          for (let k = nearLow[1][j]; k <= nearHigh[1][j]; k += 1) {
            const other = k !== j ? occupied(1, c + (k - j) * nx) : 0;
            if (other && !(how === THROUGH && takes(other, c + (k - j) * nx, 1))) return -1;
          }
        }
        if (across0) {
          for (let k = nearLow[0][i]; k <= nearHigh[0][i]; k += 1) {
            const other = k !== i ? occupied(1, c - i + k) : 0;
            if (other && other !== owner[1][c] && !(how === THROUGH && takes(other, c - i + k, 1))) return -1;
          }
        }
      }
      let cost = covered[c] ? COST.underPlate : 0;
      const same = owner[axis][c];
      if (same) {
        if (!sibling(same, b1 >= 0 ? b1 : trunk[axis][c])) {
          // Never, even priced, along another line into the line's own box (a shared last run is one
          // arrowhead), nor along one on any box's stem, where its arrowhead is.
          if (!relaxed) return -1;
          if (b1 === a || b1 === b || stem[c] >= 0) {
            if (!(how === THROUGH && takes(same, c, axis))) return -1;
          } else forced += 1;
        }
        cost += COST.share;
      }
      const across = owner[1 - axis][c];
      if (across && !sibling(across, trunk[1 - axis][c])) {
        // Never across a line on the stem of a box it ends at, where its arrowhead is: a halo guards
        // a stem only where the box has room for one.
        const onItsStem = across !== FIXED && stem[c] >= 0 && (ends[across - 1][0] === stem[c] || ends[across - 1][1] === stem[c]);
        if (onItsStem && !(how === THROUGH && takes(across, c, 1 - axis))) return -1;
        if (corner[c] || b1 >= 0) {
          if (!relaxed) return -1;
          forced += 1;
        }
        cost += COST.cross;
      }
      return cost + forced * COST.forced + through * COST.inTheWay;
    };
    /** What a bend in cell `c` adds, or -1 where the line may not bend. */
    const turning = (c) => {
      // No bend on a stem of the line's own box, nor, but at a price on a second routing, in a
      // halo or where another line runs, but a sibling's.
      if (stem[c] >= 0 && (stem[c] === a || stem[c] === b)) return -1;
      const o0 = owner[0][c];
      const o1 = owner[1][c];
      if (band[c] >= 0 || (o0 && !sibling(o0, trunk[0][c])) || (o1 && !sibling(o1, trunk[1][c]))) return relaxed ? COST.forced + COST.bend : -1;
      return COST.bend;
    };
    if (kept) return fitsAlong(kept.states, entering, turning) ? kept : null;
    const beside = (c, axis) => {
      if (axis === 0) {
        const i = c % nx;
        return (i > 0 && owner[0][c - 1] ? 1 : 0) + (i < nx - 1 && owner[0][c + 1] ? 1 : 0);
      }
      const j = (c / nx) | 0;
      return (j > 0 && owner[1][c - nx] ? 1 : 0) + (j < ny - 1 && owner[1][c + nx] ? 1 : 0);
    };
    const portCost = (port, list) => {
      let cost = port.lead + port.off * COST.offCentre;
      for (const other of list) {
        if (other.side === port.side && Math.abs(other.slot - port.slot) === 1 && owner[port.dir % 2][other.cell]) cost += COST.portBeside;
      }
      if (owner[port.dir % 2][port.cell]) cost += COST.shareOnce;
      return cost;
    };
    const goals = new Map();
    for (const port of ports[b]) {
      const state = port.cell * 4 + ((port.dir + 2) % 4);
      goalSeen[state] = stamp;
      goalCost[state] = portCost(port, ports[b]);
      goals.set(state, port);
    }
    // What is left, leaned on: the distance to the target box and a bend for each turn the line must
    // still make, weighted by `GREED`, so a route is found among far fewer cells at little extra length.
    const heuristic = (c, dir) => {
      const x = xs[c % nx];
      const y = ys[(c / nx) | 0];
      const dx = Math.max(target.x1 - x, 0, x - target.x2);
      const dy = Math.max(target.y1 - y, 0, y - target.y2);
      return GREED * (dx + dy + bendsLeft(dx, dy, x < target.x1 ? 1 : 3, y < target.y1 ? 2 : 0, dir) * COST.bend);
    };
    // How long a line with no corner must be: an arrowhead at each end its edges arrive at, and a little line between two.
    const heads = (headAt(e, a) ? 1 : 0) + (headAt(e, b) ? 1 : 0);
    const shortest = heads * marks.head + (heads > 1 ? marks.between : 0);
    /** Whether the straight way into goal state `state` is too short for its arrowheads. */
    const tooShort = (state) => {
      let first = state;
      while (from[first] >= 0) first = from[first];
      const [start, goal] = [starts.get(first), goals.get(state)];
      return Math.hypot(goal.at.x - start.at.x, goal.at.y - start.at.y) < shortest;
    };
    const heap = new Heap();
    const starts = new Map();
    for (const port of ports[a]) {
      const add = entering(port.cell, port.dir % 2);
      if (add < 0) continue;
      const state = port.cell * 4 + port.dir;
      let g = portCost(port, ports[a]) + add;
      if (goalSeen[state] === stamp) g += goalCost[state];
      if (seen[state] === stamp && best[state] <= g) continue;
      seen[state] = stamp;
      best[state] = g;
      from[state] = -1;
      turned[state] = 0;
      starts.set(state, port);
      heap.push(g + heuristic(port.cell, port.dir), state);
    }
    let found = -1;
    while (heap.size) {
      const state = heap.pop();
      if (done[state] === stamp) continue;
      done[state] = stamp;
      if (goalSeen[state] === stamp) {
        if (!turned[state] && tooShort(state)) continue;
        found = state;
        break;
      }
      const c = (state / 4) | 0;
      const dir = state & 3;
      const i = c % nx;
      const j = (c / nx) | 0;
      for (let turn = -1; turn <= 1; turn += 1) {
        const d2 = (dir + turn + 4) % 4;
        let cost = 0;
        if (turn !== 0) {
          cost = turning(c);
          if (cost < 0) continue;
        } else {
          // Straight over a line of the same box: a crossing, where joining it would have been a bend.
          const o = owner[1 - (dir % 2)][c];
          if (o && band[c] < 0 && sibling(o, trunk[1 - (dir % 2)][c])) cost += COST.cross;
        }
        const i2 = i + DX[d2];
        const j2 = j + DY[d2];
        if (i2 < 0 || j2 < 0 || i2 >= nx || j2 >= ny) continue;
        const c2 = j2 * nx + i2;
        // A state already closed costs nothing more to look at.
        if (done[c2 * 4 + d2] === stamp) continue;
        const axis = d2 % 2;
        const add = entering(c2, axis);
        if (add < 0) continue;
        const step = axis === 0 ? Math.abs(ys[j2] - ys[j]) : Math.abs(xs[i2] - xs[i]);
        cost += add + step + beside(c2, axis) * COST.beside * step;
        const s2 = c2 * 4 + d2;
        let g2 = best[state] + cost;
        if (goalSeen[s2] === stamp) g2 += goalCost[s2];
        if (done[s2] === stamp || (seen[s2] === stamp && best[s2] <= g2)) continue;
        seen[s2] = stamp;
        best[s2] = g2;
        from[s2] = state;
        turned[s2] = turned[state] || turn !== 0 ? 1 : 0;
        heap.push(g2 + heuristic(c2, d2), s2);
      }
    }
    if (found < 0) return null;
    const path = [];
    for (let s = found; s >= 0; s = from[s]) path.push(s);
    path.reverse();
    if (inTheWay) {
      // The route found, entered once more to name the lines whose room it takes.
      blamed = inTheWay;
      for (const s of path) entering((s / 4) | 0, s & 1);
    }
    return { states: path, start: starts.get(path[0]), goal: goals.get(found), how };
  }

  /** Lay line `e` along `routed` (`sign` 1), or take it up again (`sign` -1). */
  function mark(e, routed, sign) {
    const list = routed.states;
    const n = list.length;
    for (let k = 0; k < n; k += 1) {
      const c = (list[k] / 4) | 0;
      const axis = list[k] & 1;
      // Each half of a line is its end's: lines of that box alike may run along it.
      const end = ends[e][k < n / 2 ? 0 : 1];
      const bends = k + 1 < n && (list[k + 1] & 1) !== axis;
      if (sign > 0) {
        if (trunk[axis][c] < 0 && !owner[axis][c]) trunk[axis][c] = end;
        if (bends && trunk[1 - axis][c] < 0 && !owner[1 - axis][c]) trunk[1 - axis][c] = end;
      } else if (count[0][c] + count[1][c] <= 2) {
        if (owner[0][c] === e + 1) trunk[0][c] = -1;
        if (owner[1][c] === e + 1) trunk[1][c] = -1;
      }
      const touch = (ax) => {
        count[ax][c] += sign;
        const here = ledger ? listed(c * 2 + ax) : null;
        if (here && sign > 0) here.push(e);
        else if (here) here.splice(here.indexOf(e), 1);
        if (sign > 0) {
          if (count[ax][c] > 1) sharing[e] = true;
          if (count[ax][c] > 1 && owner[ax][c] && owner[ax][c] !== FIXED) sharing[owner[ax][c] - 1] = true;
          if (!owner[ax][c]) owner[ax][c] = e + 1;
        } else if (count[ax][c] === 0) {
          if (owner[ax][c] !== FIXED) owner[ax][c] = 0;
        } else if (here && owner[ax][c] === e + 1) owner[ax][c] = here[0] + 1;
      };
      touch(axis);
      if (bends) {
        touch(1 - axis);
        corner[c] += sign;
      }
    }
  }

  // Per cell and axis, the lines laid along it, once `keepLedger` is called: a line that shares its
  // run may then be taken up, its cells passing to a line still on them.
  let ledger = null;
  const listed = (key) => {
    let here = ledger.get(key);
    if (!here) ledger.set(key, (here = []));
    return here;
  };
  /** Keep the ledger from now on, from `routes`, each line's route as laid (null for none). */
  function keepLedger(routes) {
    ledger = new Map();
    routes.forEach((routed, e) => {
      const list = routed ? routed.states : [];
      for (let k = 0; k < list.length; k += 1) {
        const [c, axis] = [(list[k] / 4) | 0, list[k] & 1];
        listed(c * 2 + axis).push(e);
        if (k + 1 < list.length && (list[k + 1] & 1) !== axis) listed(c * 2 + 1 - axis).push(e);
      }
    });
  }

  return { route, mark, sharing, keepLedger };
}

/**
 * Whether a route along `states` enters every cell and bends in every cell it
 * bends in, by the rules `entering(cell, axis)` and `turning(cell)` apply now.
 */
function fitsAlong(states, entering, turning) {
  if (entering((states[0] / 4) | 0, states[0] & 1) < 0) return false;
  for (let k = 1; k < states.length; k += 1) {
    if ((states[k] & 3) !== (states[k - 1] & 3) && turning((states[k - 1] / 4) | 0) < 0) return false;
    if (entering((states[k] / 4) | 0, states[k] & 1) < 0) return false;
  }
  return true;
}

/**
 * Line `e`, which found no route among the others, routed before the lines in
 * its way: those whose room its cheapest route through them takes are taken up,
 * `e` is laid, and they are laid again in the order they were first routed in,
 * each along its old route where it still fits, else routed as it was first.
 * Kept where every one of them is laid again; else the plan is put back as it
 * was. Whether `e` was laid; rewrites `routes`.
 */
function routedFirst(e, router, routes, order) {
  const blamed = new Set();
  if (!router.route(e, THROUGH, blamed)) return false;
  const rank = new Map(order.map((line, k) => [line, k]));
  const inTheWay = [...blamed].filter((line) => line !== e && routes[line]).sort((p, q) => rank.get(p) - rank.get(q));
  for (const line of inTheWay) router.mark(line, routes[line], -1);
  const mine = router.route(e, RELAXED);
  const again = new Map();
  if (mine) {
    router.mark(e, mine, 1);
    for (const line of inTheWay) {
      const was = routes[line];
      const routed = router.route(line, STRICT, null, was) || router.route(line, was.how) || (was.how === STRICT ? router.route(line, RELAXED) : null);
      if (!routed) break;
      router.mark(line, routed, 1);
      again.set(line, routed);
    }
  }
  if (mine && again.size === inTheWay.length) {
    routes[e] = mine;
    for (const [line, routed] of again) routes[line] = routed;
    return true;
  }
  for (const [line, routed] of again) router.mark(line, routed, -1);
  if (mine) router.mark(e, mine, -1);
  for (const line of inTheWay) router.mark(line, routes[line], 1);
  return false;
}

/** Mark the cells along every line of `fixed` (pixels) as taken along its axis. */
function markFixed({ xs, ys, nx, ny, cellAt }, owner, fixed) {
  const reach = FIXED_REACH * (xs.length > 1 ? Math.min(...Array.from(xs).slice(1).map((x, i) => x - xs[i])) : 1);
  for (const path of fixed) {
    for (let k = 1; k < path.length; k += 1) {
      const [p, q] = [path[k - 1], path[k]];
      const vertical = Math.abs(p.x - q.x) < Math.abs(p.y - q.y);
      const [i0, j0] = cellAt(Math.min(p.x, q.x), Math.min(p.y, q.y));
      const [i1, j1] = cellAt(Math.max(p.x, q.x), Math.max(p.y, q.y));
      for (let i = Math.max(0, i0 - 1); i <= Math.min(nx - 1, i1 + 1); i += 1) {
        for (let j = Math.max(0, j0 - 1); j <= Math.min(ny - 1, j1 + 1); j += 1) {
          const near = vertical ? Math.abs(xs[i] - p.x) < reach && j >= j0 && j <= j1 : Math.abs(ys[j] - p.y) < reach && i >= i0 && i <= i1;
          const axis = vertical ? 0 : 1;
          if (near && !owner[axis][j * nx + i]) owner[axis][j * nx + i] = FIXED;
        }
      }
    }
  }
}

/**
 * `end` of a line, on the border of a box drawn larger than its laid-out box
 * `core`, carried on along the line's last run, from `before`, to the core's
 * border: a port of such a box lies on a track through the core.
 */
function intoCore(end, before, core) {
  if (Math.abs(before.x - end.x) < EPS) return { x: end.x, y: before.y < end.y ? core.y1 : core.y2 };
  return { x: before.x < end.x ? core.x1 : core.x2, y: end.y };
}

/** The polyline of a routed line, from its first box's border to its second's. */
function polylineOf(grid, routed) {
  const { xs, nx, ys } = grid;
  const points = [routed.start.at];
  for (let k = 0; k < routed.states.length; k += 1) {
    const c = (routed.states[k] / 4) | 0;
    const last = k === routed.states.length - 1;
    if (last || (routed.states[k + 1] & 3) !== (routed.states[k] & 3)) points.push({ x: xs[c % nx], y: ys[(c / nx) | 0] });
  }
  points.push(routed.goal.at);
  return simplify(points);
}

/**
 * The routes of the overview for `input`, every length in layout units:
 * `{ unit, boxes: [{ id, x1, y1, x2, y2, core }], plates: [{ x1, y1, x2, y2 }],
 * pairs: [{ name, a, b, forward, backward }], fixed: [[{ x, y }]], frame: { x1,
 * y1, x2, y2 } }`. `unit` is how many layout units a pixel is where the overview
 * is planned; a box is the box drawn, and `core`, where it has one, the laid-out
 * box inside it that a box drawn larger to hold its title was laid out as; `a`
 * and `b` are box ids, `forward` and `backward` how many edges the pair carries
 * each way; `fixed` the routes of lines drawn as themselves, which no planned
 * line runs along; and `frame`, or none, the box that holds every box, whose
 * inside every route keeps to. `marks` are the sizes on screen (`OVERVIEW_MARKS`).
 *
 * `{ paths, failed }`: each routed pair's polyline by its name, from a border of
 * box `a` to a border of box `b`, of its core where it has one; and the names of
 * the pairs no route was found for.
 */
export function planOverview(input, marks = OVERVIEW_MARKS) {
  const unit = input.unit || 1;
  const inPixels = (box) => ({ x1: box.x1 / unit, y1: box.y1 / unit, x2: box.x2 / unit, y2: box.y2 / unit });
  const boxes = input.boxes.map(inPixels);
  const cores = input.boxes.map((box) => (box.core ? inPixels(box.core) : null));
  const plates = (input.plates || []).map(inPixels);
  const frame = input.frame ? inPixels(input.frame) : null;
  const indexOf = new Map(input.boxes.map((box, b) => [box.id, b]));
  const known = input.pairs.filter((pair) => indexOf.has(pair.a) && indexOf.has(pair.b) && pair.a !== pair.b);
  const pairs = known.map((pair) => ({ ...pair, a: indexOf.get(pair.a), b: indexOf.get(pair.b) }));
  const failed = input.pairs.filter((pair) => !known.includes(pair)).map((pair) => pair.name);
  const paths = new Map();
  if (!boxes.length || !pairs.length) return { paths, failed };

  const degree = new Map();
  for (const pair of pairs) for (const b of [pair.a, pair.b]) degree.set(b, (degree.get(b) || 0) + 1);
  const grid = { ...gridOf(boxes, plates, marks, (b) => degree.get(b) || 0, cores, frame), boxes };
  const fixed = (input.fixed || []).map((path) => path.map((p) => ({ x: p.x / unit, y: p.y / unit })));
  const router = routerOn(grid, pairs, fixed, marks);
  const byName = (p, q) => (pairs[p].name < pairs[q].name ? -1 : pairs[p].name > pairs[q].name ? 1 : 0);
  const order = pairs
    .map((_, e) => e)
    .sort((p, q) => spanOf(boxes[pairs[p].a], boxes[pairs[p].b]) - spanOf(boxes[pairs[q].a], boxes[pairs[q].b]) || pairs[q].forward + pairs[q].backward - (pairs[p].forward + pairs[p].backward) || byName(p, q));
  const routes = pairs.map(() => null);
  for (const e of order) {
    routes[e] = router.route(e);
    if (routes[e]) router.mark(e, routes[e], 1);
  }
  // Once more, each line taken up and laid again now that it knows every other.
  for (const e of order) {
    if (!routes[e] || router.sharing[e]) continue;
    router.mark(e, routes[e], -1);
    routes[e] = router.route(e) || routes[e];
    router.mark(e, routes[e], 1);
  }
  // A line no route reached, routed with what the rules refuse priced instead.
  for (const e of order) {
    if (routes[e]) continue;
    routes[e] = router.route(e, RELAXED);
    if (routes[e]) router.mark(e, routes[e], 1);
  }
  // A line still without one, routed before the lines in its way; lines moved for one may open a way for the next.
  if (routes.some((routed) => !routed)) router.keepLedger(routes);
  let moved = false;
  for (const e of order) {
    if (routes[e]) continue;
    if (moved && (routes[e] = router.route(e, RELAXED))) router.mark(e, routes[e], 1);
    else moved = routedFirst(e, router, routes, order) || moved;
  }
  pairs.forEach((pair, e) => {
    if (!routes[e]) {
      failed.push(pair.name);
      return;
    }
    const path = polylineOf(grid, routes[e]);
    const n = path.length;
    if (cores[pair.a]) path[0] = intoCore(path[0], path[1], cores[pair.a]);
    if (cores[pair.b]) path[n - 1] = intoCore(path[n - 1], path[n - 2], cores[pair.b]);
    paths.set(pair.name, path.map((p) => ({ x: p.x * unit, y: p.y * unit })));
  });
  return { paths, failed: failed.sort() };
}
