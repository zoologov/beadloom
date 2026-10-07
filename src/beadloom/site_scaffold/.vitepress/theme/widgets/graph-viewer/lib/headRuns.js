// beadloom:component=site-graph-viewer
// The last run into a node made long enough for an arrowhead: a route's last bend moved back where nothing is in the way.
//
// ELK ends a line ten layout units after its last bend where the line arrives
// from the channel above its node, and a bus joins its edges in that channel
// (`buses.js`). An arrowhead needs a straight run behind its tip, its own length
// and half a head more, or the line reads as bent into the head; zoomed out to
// where a node is about readable, ten units is about five pixels, and a head is
// six. So after the bundling, the last bend of the lines that arrive at one
// point of a node from one direction is moved back along their last run, the
// segment before it with it, until the run is `headRun` long; or past a segment
// in the way, to where the run is clear, up to twice as far; or else as far as
// it goes with nothing in the way (`freeOf`). The moved segment may not cross a
// box other than its ends' and their holders', nor run along an edge that has no
// end in common with it closer than `headRunClearance`; no such edge may run
// along or across the length the last run gains, where it would run under the
// head; and the run before the moved segment is shortened, never turned round.
// Nor may the moved segment cross another line's last run nearer that line's
// tip than `headRun`, or than it crosses it now, whatever ends the two have in
// common: the room one head gains would be taken from the other's. Two edges
// each way between two nodes one above the other arrive in one gap from both
// sides, and a run lengthened into the lower node once crossed the edge going up
// two units behind its tip, under its arrowhead at every zoom.
//
// Lines that share their last run move together, so they still share it; a line
// that joins the shared run nearer the tip than the others limits how far they
// move; and a segment another line runs along as well, a source's bus or a
// trunk, does not move, since moving it would part the channel they share. No
// node moves, and a line whose run is long enough keeps its route. Where the run
// cannot be made long enough, the head is drawn smaller (`lineMarks.js`).
//
// Everything here is pure over the bundling's drawing (`bundleDrawing.js`):
// routes in, routes out.

import { BOX_INSET, near, sharesAnEnd, simplify } from "./bundleDrawing.js";

const distance = (p, q) => Math.hypot(q.x - p.x, q.y - p.y);

/** The unit direction of the axis-aligned run from `a` to `b`, or null when the run is not axis-aligned. */
function axisWay(a, b) {
  if (near(a.x, b.x) && !near(a.y, b.y)) return { x: 0, y: Math.sign(b.y - a.y) };
  if (near(a.y, b.y) && !near(a.x, b.x)) return { x: Math.sign(b.x - a.x), y: 0 };
  return null;
}

const shifted = (p, way, by) => ({ x: p.x - way.x * by, y: p.y - way.y * by });

/**
 * The arrivals of `drawing` at their targets, grouped by the point they end at
 * and the way their last run arrives: each group a list of `{ edge, points }`,
 * `points` the route as it stands.
 */
function arrivalGroups(drawing) {
  const groups = new Map();
  for (const [id, points] of drawing.routes) {
    const n = points.length;
    if (n < 2) continue;
    const way = axisWay(points[n - 2], points[n - 1]);
    const edge = way && drawing.edgeOf(id);
    if (!edge) continue;
    const tip = points[n - 1];
    // A number for the tip to the unit and the way, cheaper to file than a string.
    const key = (Math.round(tip.x) * 1048576 + Math.round(tip.y)) * 4 + (way.x ? 1 + way.x : 2 + way.y);
    let group = groups.get(key);
    if (!group) groups.set(key, (group = { way, members: [] }));
    group.members.push({ edge, points });
  }
  return groups.values();
}

/**
 * The routes of `members` with their last bend moved `by` back along `way`, or
 * null when a member's route cannot take it: its last bend is the route's start,
 * or the run before the moved segment would turn round or vanish.
 */
function movedBack(members, way, by) {
  const moved = [];
  for (const { edge, points } of members) {
    const n = points.length;
    if (n < 4) return null;
    const [before, from, bend, tip] = [points[n - 4], points[n - 3], points[n - 2], points[n - 1]];
    const across = axisWay(from, bend);
    const run = axisWay(before, from);
    if (!across || across.x * way.x + across.y * way.y !== 0 || !run) return null;
    const along = run.x * way.x + run.y * way.y;
    // The run before the moved segment arrives the way the last run does: moving back shortens it.
    if (along > 0 && distance(before, from) <= by + 1) return null;
    if (along === 0) return null;
    moved.push({ edge, points: simplify([...points.slice(0, n - 3), shifted(from, way, by), shifted(bend, way, by), tip]) });
  }
  return moved;
}

/**
 * Which distances a group's last bend may move back by: a filter over distances,
 * read once per member. Moved back `by`, a member's segment before its last bend
 * runs `by` further out along its last run, and its last run gains `by`; the
 * filter refuses a distance where
 *
 * - the moved segment runs along an edge with no end in common with it, closer
 *   than `clearance`, or crosses a box other than its ends' and their holders';
 * - the gained run runs along such an edge, crosses such a box, or is crossed by
 *   such an edge, which would then run under the head;
 * - the moved segment crosses the last run of a line outside the group nearer
 *   that line's tip than `headRun`, or than it crosses it as it stands: it would
 *   run under that line's head.
 *
 * And it refuses every distance where a line outside the group runs along a
 * member's segment as it stands, a source's bus or a trunk: moving the segment
 * would part the channel they share.
 */
function freeOf(drawing, members, way, furthest, clearance, headRun) {
  // Refused distances: open intervals, and everything from `below` up.
  const refused = [];
  let below = Infinity;
  const ids = new Set(members.map(({ edge }) => edge.id));
  let shared = false;
  const back = -(way.x + way.y);
  const across = way.x === 0 ? "horizontal" : "vertical";
  const along = across === "horizontal" ? "vertical" : "horizontal";
  const [fixed, moving] = across === "horizontal" ? ["y", "x"] : ["x", "y"];
  for (const { edge, points } of members) {
    const n = points.length;
    const [from, bend] = [points[n - 3], points[n - 2]];
    const related = (other) => sharesAnEnd(other, edge);
    const [sourceAndHolders, targetAndHolders] = [drawing.withHolders(edge.source), drawing.withHolders(edge.target)];
    // Where a coordinate along the way lies, as a distance moved back from the bend.
    const byAt = (value) => (value - bend[fixed]) * back;
    const lo = Math.min(from[moving], bend[moving]);
    const hi = Math.max(from[moving], bend[moving]);
    const line = bend[moving];
    const reach = { lo: bend[fixed] + Math.min(0, back * furthest), hi: bend[fixed] + Math.max(0, back * furthest) };
    // The moved segment beside a parallel segment of an unrelated edge, and the gained
    // run, along the last run's line past the bend, crossed by one.
    drawing.segmentsAlong(across, (reach.lo + reach.hi) / 2, (reach.hi - reach.lo) / 2 + clearance, lo, hi, (other, c, d) => {
      const [c1, c2] = c[moving] < d[moving] ? [c[moving], d[moving]] : [d[moving], c[moving]];
      const at = byAt(c[fixed]);
      const overlap = Math.min(hi, c2) - Math.max(lo, c1);
      // A line outside the group on the segment itself, a source's bus or a trunk: moving the segment would part them.
      if (overlap > 1 && Math.abs(at) < 1 && !ids.has(other.id)) shared = true;
      if (related(other)) return;
      if (overlap > 1) refused.push(at - clearance, at + clearance);
      if (at > 0 && c1 < line - 1 && c2 > line + 1) below = Math.min(below, at);
    });
    drawing.segmentsAlong(along, line, clearance, reach.lo, reach.hi, (other, c, d) => {
      if (related(other)) return;
      const [e1, e2] = [byAt(c[fixed]), byAt(d[fixed])];
      if (Math.max(e1, e2) > 0) below = Math.min(below, Math.max(0, Math.min(e1, e2)) + 1 + 1e-9);
    });
    // Another line's last run across the moved segment's way: its head's room, kept.
    drawing.segmentsAlong(along, (lo + hi) / 2, (hi - lo) / 2, reach.lo, reach.hi, (other, c, d) => {
      if (ids.has(other.id) || c[moving] <= lo + 1 || c[moving] >= hi - 1) return;
      const route = drawing.routes.get(other.id);
      const tip = route[route.length - 1];
      const [end, start] = near(d[fixed], tip[fixed]) && near(d[moving], tip[moving]) ? [d, c] : [c, d];
      if (!near(end[fixed], tip[fixed]) || !near(end[moving], tip[moving])) return;
      const [atTip, atStart] = [byAt(end[fixed]), byAt(start[fixed])];
      // Crossed now, the run keeps the room it has up to `headRun`; crossed only once moved, `headRun`.
      const crossedNow = Math.min(atTip, atStart) < 0 && Math.max(atTip, atStart) > 0;
      const room = crossedNow ? Math.min(headRun, Math.abs(atTip)) : headRun;
      // Past the tip the moved segment would run across the head's point: refused as near.
      if (atStart < atTip) refused.push(Math.max(atTip - room, atStart), atTip + room);
      else refused.push(atTip - room, Math.min(atTip + room, atStart));
    });
    // Boxes in the way of the moved segment or of the gained run.
    const swept =
      across === "horizontal"
        ? { x1: Math.min(lo, line), x2: Math.max(hi, line), y1: reach.lo, y2: reach.hi }
        : { x1: reach.lo, x2: reach.hi, y1: Math.min(lo, line), y2: Math.max(hi, line) };
    drawing.boxesIn(swept, (id, box) => {
      if (sourceAndHolders.has(id) || targetAndHolders.has(id)) return;
      const [b1, b2, c1, c2] = across === "horizontal" ? [box.y1, box.y2, box.x1, box.x2] : [box.x1, box.x2, box.y1, box.y2];
      const [inner1, inner2] = [byAt(b1 + BOX_INSET), byAt(b2 - BOX_INSET)];
      const [from1, to1] = inner1 < inner2 ? [inner1, inner2] : [inner2, inner1];
      if (hi > c1 + BOX_INSET && lo < c2 - BOX_INSET) refused.push(from1, to1);
      if (line > c1 + BOX_INSET && line < c2 - BOX_INSET) below = Math.min(below, from1 + 1e-9);
    });
  }
  if (shared) return () => false;
  return (by) => {
    if (by >= below) return false;
    for (let i = 0; i < refused.length; i += 2) if (by > refused[i] && by < refused[i + 1]) return false;
    return true;
  };
}

/**
 * Lengthen the last run of every group of arrivals in `drawing` towards
 * `options.headRun`, in steps of `options.headRunStep`, rewriting the routes it
 * moves; answer the groups moved, each `{ members, by }`: the ids of the edges
 * whose last bend moved, and how far back.
 */
export function lengthenHeadRuns(drawing, options) {
  const moved = [];
  for (const { way, members } of arrivalGroups(drawing)) {
    const runs = members.map(({ points }) => distance(points[points.length - 2], points[points.length - 1]));
    const shortest = Math.min(...runs);
    // A run a step short of the length asked for gains too little to move a route for.
    if (shortest >= options.headRun - options.headRunStep - 1e-6) continue;
    // Only the lines that bend nearest the tip move; one that joins further back limits how far.
    const nearest = members.filter((_, i) => runs[i] < shortest + 1);
    if (nearest.some(({ points }) => points.length < 4)) continue;
    const further = runs.filter((run) => run >= shortest + 1);
    const limit = Math.min(...further, Infinity) - shortest;
    const wanted = Math.min(options.headRun - shortest, limit);
    const steps = stepsFor(wanted, Math.min(wanted + options.headRun, limit), options.headRunStep);
    if (!steps.length) continue;
    const free = freeOf(drawing, nearest, way, Math.max(...steps), options.headRunClearance, options.headRun);
    for (const by of steps.filter(free)) {
      const candidate = movedBack(nearest, way, by);
      if (!candidate) continue;
      for (const { edge, points } of candidate) drawing.setRoute(edge, points);
      moved.push({ members: candidate.map(({ edge }) => edge.id), by });
      break;
    }
  }
  return moved;
}

/**
 * The distances a last bend is tried at, in order: `wanted`, then further out
 * up to `furthest`, where the run past a segment in the way is clear, then
 * nearer down to one `step`, as far as the run goes.
 */
function stepsFor(wanted, furthest, step) {
  const steps = [];
  // Past a segment in the way, a coarser step: a clear run there is one ELK channel or more further on.
  for (let by = wanted; by <= furthest + 1e-6; by += by === wanted ? step : 2 * step) steps.push(by);
  for (let by = wanted - step; by >= step - 1e-6; by -= step) steps.push(by);
  return steps;
}
