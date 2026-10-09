// beadloom:component=site-graph-edge
// Where a drawn line carries an arrowhead: the ends its edges arrive at, one head where lines share their last run, and the room it stands in.
//
// An edge of the data file arrives at its target; an aggregated edge of the map
// at each end the edges it carries arrive at (`headEndsOf`), but where a node's
// own line ends at an open box whose nodes its other lines run on into: there the
// line is a stub of theirs, under the bus that spreads them, and their heads
// carry the direction. An arrowhead carries the direction, since a line is one
// colour from end to end.
//
// Lines that reach one end along one final run are drawn as one line there, and
// end in one arrowhead rather than one per line drawn on top of each other,
// whose colours would fight. Lines that reach the end separately keep their own.
// Of the ends that coincide, the loudest look draws the head — a violation is
// never hidden under an import's head — then an edge of the file before a line
// of the map's, and among equals the first by id; every other drops its own
// (`droppedHeadsOf`).
//
// A head needs a straight run behind its tip, and so do the lines that leave
// their head to it: one of them bending into the shared run right behind the
// head bends into the head as much as its own line would. The room of an end is
// the straight run every line ending there has before its last corner
// (`headRoomsOf`); the head is sized to it (`lineMarks.js`).
//
// Every function here is pure: data and routes in, ends out.

import { VIOLATION_KEY, contractStyleKey } from "../model/edgeKinds.js";
import { AGGREGATE, STUB_AT } from "../../../shared/map-levels/index.js";

/** The class of a line whose target drops its arrowhead for another on its last run; the stylesheet draws none there. */
export const NO_TARGET_HEAD = "no-target-head";
/** The class of a line whose source drops its arrowhead for another on its first run. */
export const NO_SOURCE_HEAD = "no-source-head";

/** The looks whose head is drawn over any other's at a shared end: the ones that report a problem. */
const LOUD_LOOKS = new Set([VIOLATION_KEY, contractStyleKey("broken"), contractStyleKey("drift")]);
/** Two ends closer than this, in layout units, are one: a bus's lines can end a fraction of a unit apart. */
export const SAME_END = 1;

/** The data a drawn line carries for the room its ends have: `{ source, target }`, each `{ run, beside, arrival }` (`headRoomsOf`), `aside` when the end leaves beside another line's head (`departuresBeside`), or null where not known. */
export const HEAD_ROOM = "headRoom";


/** The ends of `edge` that carry an arrowhead: `{ source, target }`. */
export function headEndsOf(edge) {
  const stub = edge.data(STUB_AT);
  if (!edge.data(AGGREGATE)) return { source: false, target: stub === undefined || stub !== edge.data("target") };
  return {
    source: edge.data("backward") > 0 && stub !== edge.data("source"),
    target: edge.data("forward") > 0 && stub !== edge.data("target"),
  };
}

/** Two last runs whose directions' cosine is at least this arrive the same way: a few degrees apart at most. */
const SAME_WAY = 0.998;

/** The unit direction an end's last run arrives at its tip in. */
function wayOf({ tip, before }) {
  const length = Math.hypot(tip.x - before.x, tip.y - before.y) || 1;
  return { x: (tip.x - before.x) / length, y: (tip.y - before.y) / length };
}

/**
 * The ends of `ends` that share their last run, as a key per end: ends whose
 * tips lie within `SAME_END` of the first end of a group and whose last runs
 * arrive the same way take that group's key. Grouping by proximity rather than
 * by rounding keeps two ends a hair apart on either side of a rounding step
 * together; two lines that meet at one point from a little apart stay apart,
 * each with its own head, since a line into another's head from aside reads as
 * bent into it.
 */
function sharedEndKeys(ends) {
  const cells = new Map();
  const keys = new Map();
  const cellOf = (x, y) => `${Math.floor(x / SAME_END)},${Math.floor(y / SAME_END)}`;
  ends.forEach((end, i) => {
    const way = wayOf(end);
    const [cx, cy] = [Math.floor(end.tip.x / SAME_END), Math.floor(end.tip.y / SAME_END)];
    let group = null;
    for (let dx = -1; dx <= 1 && !group; dx += 1) {
      for (let dy = -1; dy <= 1 && !group; dy += 1) {
        group = (cells.get(`${cx + dx},${cy + dy}`) || []).find(
          (g) => g.way.x * way.x + g.way.y * way.y >= SAME_WAY && Math.hypot(g.tip.x - end.tip.x, g.tip.y - end.tip.y) <= SAME_END
        );
      }
    }
    if (!group) {
      group = { key: `${i}`, tip: end.tip, way };
      const cell = cellOf(end.tip.x, end.tip.y);
      if (!cells.has(cell)) cells.set(cell, []);
      cells.get(cell).push(group);
    }
    keys.set(end, group.key);
  });
  return keys;
}

/** Whether end `a` draws the head before end `b`: the louder look first, then an edge of the file, then the first by id. */
function drawsBefore(a, b) {
  if (a.loud !== b.loud) return a.loud;
  // An edge of the file draws the head before a line of the map's that ends with it there.
  if (Boolean(a.mapLine) !== Boolean(b.mapLine)) return !a.mapLine;
  return a.id < b.id;
}

/**
 * The ends among `ends` that drop their arrowhead because another draws it:
 * each end is `{ id, end, tip, before, styleKey, headless }`, `end` "source" or
 * "target", `tip` the point the line ends at and `before` the point its last run
 * starts from. An end `headless` draws no head of its own, and is among them when
 * another line's head is drawn where it ends: a line that leaves a node where
 * another arrives, along that line's last run, ends at that head's base too.
 * The answer is a set of `${id}\n${end}`.
 */
export function droppedHeadsOf(ends) {
  const drawing = new Map();
  const dropped = new Set();
  const keys = sharedEndKeys(ends);
  for (const end of ends.filter((e) => !e.headless)) {
    const candidate = { ...end, loud: LOUD_LOOKS.has(end.styleKey) };
    const key = keys.get(end);
    const holder = drawing.get(key);
    if (!holder) {
      drawing.set(key, candidate);
    } else if (drawsBefore(candidate, holder)) {
      dropped.add(`${holder.id}\n${holder.end}`);
      drawing.set(key, candidate);
    } else {
      dropped.add(`${candidate.id}\n${candidate.end}`);
    }
  }
  // A line that starts where another arrives, along its last run, starts at that head's base.
  for (const end of ends.filter((e) => e.headless)) if (drawing.has(keys.get(end))) dropped.add(`${end.id}\n${end.end}`);
  return dropped;
}

/**
 * How far beside a head's tip, along the border it ends on, a line that leaves
 * that border would touch the head, in layout units: half the widest head drawn
 * where nodes are smallest on screen, with a line's half width and a clearance
 * (about 7 units where a node is 19 px tall).
 */
export const BESIDE_HEAD = 8;

/**
 * The ends among `ends` (as `droppedHeadsOf` reads them) that leave a node
 * beside where another line's head arrives: a headless end whose tip lies on the
 * same border as a drawn head's, within `BESIDE_HEAD` of it, its line leaving
 * the way that head's line arrives. Such a line would run along the head's side;
 * it starts at that head's base instead, as a line does that leaves where the
 * head arrives. `dropped` is `droppedHeadsOf`'s answer; the answer maps each
 * such end, `${id}\n${end}`, to the head's, the nearest.
 */
export function departuresBeside(ends, dropped) {
  const heads = ends.filter((end) => !end.headless && !dropped.has(`${end.id}\n${end.end}`));
  const out = new Map();
  for (const end of ends.filter((e) => e.headless && !dropped.has(`${e.id}\n${e.end}`))) {
    const way = wayOf(end);
    let nearest = null;
    for (const head of heads) {
      if (head.id === end.id) continue;
      const other = wayOf(head);
      if (other.x * way.x + other.y * way.y < SAME_WAY) continue;
      // Along the way, the two tips are on one border; across it, within reach of each other.
      const along = (head.tip.x - end.tip.x) * way.x + (head.tip.y - end.tip.y) * way.y;
      const across = Math.abs((head.tip.x - end.tip.x) * way.y - (head.tip.y - end.tip.y) * way.x);
      if (Math.abs(along) <= SAME_END && across <= BESIDE_HEAD && (!nearest || across < nearest.across)) nearest = { head, across };
    }
    if (nearest) out.set(`${end.id}\n${end.end}`, `${nearest.head.id}\n${nearest.head.end}`);
  }
  return out;
}

/**
 * The heads among `ends` (as `droppedHeadsOf` reads them) that give way to a
 * head beside them on the same border, arriving the same way, too near for both
 * at `least`, the narrowest a head is drawn now, in layout units, with `gap`
 * between them: of two such heads the one drawn first keeps its own
 * (`drawsBefore`). Lines that reach a side separately stay separate, and where
 * the zoom leaves no room for two heads side by side, the one that gives way ends
 * behind the other's base, beside it as a line leaving beside a head does
 * (`departuresBeside`). `dropped` is the ends already dropped; the answer maps
 * each end that gives way, `${id}\n${end}`, to the head it gives way to.
 */
export function crowdedHeadsOf(ends, dropped, least, gap) {
  const heads = ends.filter((end) => !end.headless && !dropped.has(`${end.id}\n${end.end}`));
  const borders = new Map();
  for (const end of heads) {
    const way = wayOf(end);
    const key = `${Math.round(way.x)},${Math.round(way.y)}|${Math.round(end.tip.x * way.x + end.tip.y * way.y)}`;
    if (!borders.has(key)) borders.set(key, []);
    borders.get(key).push({ end, way, across: end.tip.x * way.y - end.tip.y * way.x });
  }
  const out = new Map();
  const keyOf = (end) => `${end.id}\n${end.end}`;
  for (const row of borders.values()) {
    row.sort((a, b) => a.across - b.across);
    for (let i = 1; i < row.length; i += 1) {
      const [a, b] = [row[i - 1], row[i]];
      const apart = b.across - a.across;
      // Ends a unit apart or nearer share a tip, and one head already (`droppedHeadsOf`).
      if (apart <= SAME_END || apart > least + gap || out.has(keyOf(a.end))) continue;
      const loud = (end) => ({ ...end, loud: LOUD_LOOKS.has(end.styleKey) });
      const [gives, keeps] = drawsBefore(loud(a.end), loud(b.end)) ? [b, a] : [a, b];
      out.set(keyOf(gives.end), keyOf(keeps.end));
    }
  }
  return out;
}

/**
 * The room each of `ends` has for an arrowhead: each end is `{ id, end, tip,
 * before, corner, beside, arrival }`, `before` the point its last run starts
 * from, `corner` how far from the tip that run is straight (to its last corner,
 * or to a line that crosses it), `beside` how far the nearest line beside that
 * run lies and `arrival` whether that line arrives there with a head. Ends at one
 * tip from one direction share the least of their rooms. The answer maps
 * `${id}\n${end}` to `{ run, beside, arrival }`, layout units (`HEAD_ROOM`).
 */
export function headRoomsOf(ends) {
  const least = new Map();
  const keys = sharedEndKeys(ends);
  for (const end of ends) {
    const key = keys.get(end);
    const room = least.get(key) || { run: Infinity, beside: Infinity, arrival: false };
    const closer = end.beside < room.beside;
    least.set(key, {
      run: Math.min(room.run, end.corner),
      beside: closer ? end.beside : room.beside,
      arrival: closer ? end.arrival : room.arrival,
    });
  }
  return new Map(ends.map((end) => [`${end.id}\n${end.end}`, least.get(keys.get(end))]));
}
