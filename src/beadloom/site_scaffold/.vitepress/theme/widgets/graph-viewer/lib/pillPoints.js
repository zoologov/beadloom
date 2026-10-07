// beadloom:component=site-graph-viewer
// The points along a line a pill may stand at, nearest the line's middle first, made as a search asks for them.
//
// A line's count stands on a pill on the line itself (`pillPlaces.js`), at one
// of the points tried every few pixels along it, far enough from each end to
// leave its arrowheads whole; the point nearest the middle that is free and
// cheap wins. Zoomed in, a line runs thousands of pixels and has hundreds of
// such points, and the search mostly stops near the middle, or turns down a
// whole stretch of points at once: the points are made one at a time, walking
// out from the middle both ways, and a stretch the search turns down is passed
// over without being made, and without asking at each of its points where the
// search says where its answer may change.
//
// Every function here is pure: a line and a size in, points out.

/** How far apart the points tried along a line are, in pixels. */
const STEP_PX = 6;
/** How near two places along a run are taken to be one, in pixels: far below a step, far above rounding. */
const SAME_PX = 1e-6;
/** The room an end keeps free of a pill, in pixels: an arrowhead (6 px) and a pixel more, or a little where it has none. */
const END_ROOM_PX = Object.freeze({ head: 7, bare: 2 });

/**
 * The points a pill may stand at along `line`, `{ a, b, s, length, where, off,
 * run }` one after another, `run` the index of the segment from `a` to `b`:
 * every few pixels, far enough from each end for its arrowhead and half the
 * pill `size`, nearest the line's middle first, then in the line's order. They
 * are made as they are asked for, walking out from the middle both ways: a
 * search that stops near the middle of a long line makes the few it reads, not
 * every one along it. The search may answer a point with `{ run, past(x, y) }`:
 * the points after it on its side of the middle and on that run that `past`
 * holds for are then passed over without being made. Where it adds `along`, the
 * axis the run lies on ("x" or "y"), and `nextChange(at, way)`, the nearest
 * place past `at` going `way` (1 or -1) along that axis where `past` may change,
 * the points before that place are passed over at once, without asking `past`.
 */
export function* candidatesOf(line, size) {
  const points = line.points;
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  // Where each segment starts along the line, summed in the line's order as the places along it are.
  const starts = [];
  let total = 0;
  for (const length of lengths) {
    starts.push(total);
    total += length;
  }
  const middle = total / 2;
  const room = line.heads.map((head) => (head ? END_ROOM_PX.head : END_ROOM_PX.bare));
  const reachOf = (i) => (Math.abs(points[i + 1].x - points[i].x) >= Math.abs(points[i + 1].y - points[i].y) ? size.width : size.height) / 2;
  const offOf = (where) => Math.abs(where - middle) / (total || 1);
  // A point is the `k`-th step of segment `i`: `s` is half a step and `k` steps along it, as the line's
  // order counts them; it may stand there when far enough from both ends.
  const stepOf = (k) => STEP_PX / 2 + k * STEP_PX;
  const lastStepOf = (i) => {
    let k = Math.floor((lengths[i] - STEP_PX / 2) / STEP_PX);
    while (k >= 0 && stepOf(k) >= lengths[i]) k -= 1;
    return k;
  };
  const pointAt = ({ i, k }) => {
    const s = stepOf(k);
    const where = starts[i] + s;
    return { a: points[i], b: points[i + 1], s, length: lengths[i], reach: reachOf(i), where, off: offOf(where), run: i };
  };
  const free = ({ i, k }) => {
    const where = starts[i] + stepOf(k);
    return !(where < room[0] + reachOf(i) || where > total - room[1] - reachOf(i));
  };
  // The first point at or past the middle, and the walk on from it towards the end; the last before it, and back.
  let j = 0;
  while (j < lengths.length - 1 && starts[j + 1] <= middle) j += 1;
  let k0 = 0;
  while (lengths.length && k0 <= lastStepOf(j) && starts[j] + stepOf(k0) < middle) k0 += 1;
  const onward = (at) => (at.k < lastStepOf(at.i) ? { i: at.i, k: at.k + 1 } : nextSegment(at.i + 1, 1));
  const backward = (at) => (at.k > 0 ? { i: at.i, k: at.k - 1 } : nextSegment(at.i - 1, -1));
  function nextSegment(i, way) {
    for (; i >= 0 && i < lengths.length; i += way) {
      const last = lastStepOf(i);
      if (last >= 0) return { i, k: way > 0 ? 0 : last };
    }
    return null;
  }
  const settle = (at, step) => {
    while (at && !free(at)) at = step(at);
    return at;
  };
  if (!lengths.length) return;
  let right = settle(k0 <= lastStepOf(j) ? { i: j, k: k0 } : nextSegment(j + 1, 1), onward);
  let left = settle(k0 > 0 ? { i: j, k: k0 - 1 } : nextSegment(j - 1, -1), backward);
  // A point's centre, as the search finds it from the point.
  const centreOf = ({ i, k }) => {
    const s = stepOf(k);
    return [points[i].x + ((points[i + 1].x - points[i].x) * s) / lengths[i], points[i].y + ((points[i + 1].y - points[i].y) * s) / lengths[i]];
  };
  // The last point of `at`'s run going `step`'s way whose centre lies before `passed.nextChange`'s next place:
  // `past` holds for it as it holds for `at`.
  const lastBeforeChange = (at, step, passed) => {
    if (!passed.nextChange) return at;
    const { i, k } = at;
    const [from, to] = [points[i][passed.along], points[i + 1][passed.along]];
    if (from === to) return at;
    const onwards = step === onward;
    const way = Math.sign(to - from) * (onwards ? 1 : -1);
    const here = centreOf(at)[passed.along === "x" ? 0 : 1];
    // A point on a place where `past` may change says nothing of the points after it.
    if (Math.abs(passed.nextChange(here - way * SAME_PX, way) - here) <= SAME_PX) return at;
    const change = passed.nextChange(here, way);
    if (!Number.isFinite(change)) return { i, k: onwards ? lastStepOf(i) : 0 };
    // How far along the segment the change lies, and the last step strictly before it, by more than rounding.
    const s = ((change - from) / (to - from)) * lengths[i];
    const far = onwards ? Math.ceil((s - SAME_PX - STEP_PX / 2) / STEP_PX) - 1 : Math.floor((s + SAME_PX - STEP_PX / 2) / STEP_PX) + 1;
    const clamped = Math.min(Math.max(far, 0), lastStepOf(i));
    return (clamped - k) * (onwards ? 1 : -1) > 0 ? { i, k: clamped } : at;
  };
  const passOver = (at, step, passed) => {
    while (at && passed && at.i === passed.run && passed.past(...centreOf(at))) at = settle(step(lastBeforeChange(at, step, passed)), step);
    return at;
  };
  // The distance from the middle falls up to it and rises after it: taking the nearer of the two walks each
  // time is the order by distance, the earlier of two at one distance first.
  while (left || right) {
    const [l, r] = [left && pointAt(left), right && pointAt(right)];
    if (!r || (l && l.off <= r.off)) {
      const passed = yield l;
      left = passOver(settle(backward(left), backward), backward, passed);
    } else {
      const passed = yield r;
      right = passOver(settle(onward(right), onward), onward, passed);
    }
  }
}
