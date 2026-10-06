// beadloom:component=site-graph-viewer
// The map's levels: which boxes are open, what each node is drawn as, and which edges are drawn between them.
//
// The whole-graph view of a large graph is a cloud: every node and every edge at
// a scale where none can be told apart. So the overview draws it like a map. A
// box is open or closed; a closed box is drawn at its full size with nothing
// inside it, and every node inside it is drawn as it. An edge is drawn at the
// lowest box that holds both its ends, between the two children of that box that
// hold them (`siblingsOf`): as itself only when those children are its own ends
// and neither is a box; otherwise it is carried by one **aggregated edge** per
// unordered pair of those children, with how many edges go each way. So two
// closed boxes are joined by one line whatever runs between them and their
// contents, and an open box keeps its outward edges aggregated at the box: it
// shows its nodes and the edges among them, and opening it moves no line between
// it and its siblings. An edge inside one closed box is not drawn. An edge
// between a node and a box that holds it (a loop) is drawn as itself once both
// its ends are drawn and neither is a closed box.
//
// A node's edges to the outside that a level does not draw at rest — carried by
// a line between boxes that hold it — are its **outward** edges (`outwardOf`):
// a node inside an open box carries their count, and the map draws them while
// the node is under the pointer or selected (`ownLinesOf`); an open box selected
// draws its own the same way (`outwardOfOpen`).
//
// A level is a set of open boxes and nothing more: nothing is laid out again, so
// no box moves between levels. Which boxes are open is decided here as well:
//
// - **What is readable**: a box opens when the box holding it is open, the view
//   is zoomed in past a floor over the whole-graph fit, and its nodes are
//   readable — its smallest child at least a height on screen; it closes again
//   below a share of that height, so it does not flicker at the edge. The view
//   opens the readable boxes it overlaps (`openInView`); a selection or a search
//   opens the readable boxes its nodes need wherever they are.
// - **What a selection needs**: a node the reader asked for is drawn as itself
//   with its own edges (`boxesRevealing`): every box that holds it is open, and
//   so is the node when it is a box, since an edge of a closed box is carried by
//   its pair's aggregated edge. A selection with nothing more asked opens only
//   what its own node needs, which is what the pointer on the node needs too, so
//   a click draws the node's edges on the lines a hover draws; a walk the reader
//   asked for — deeper, one way, the rest hidden, or the impact — opens what
//   every node it reaches needs (`selectionReveals`). A selected box opens at any
//   zoom (`openInView`, `forced`): the box is what the reader asked to see.
//
// One root that holds everything (a project's own box) is always open: closed, it
// would be the whole overview. An edge onto it from inside a closed box says
// nothing at the overview and is not drawn; it is drawn once its end is.
//
// When a level would draw more aggregated edges than a budget, the weakest are
// not drawn (`budgetOf`), ties at the cut broken by name so the budget is filled,
// and each end counts how many of its edges are hidden.
// Everything here is pure: ids and boxes in, sets and counts out.

/** The class of a box drawn closed: the stylesheet draws its title and tint, the map sets it. */
export const COLLAPSED = "is-collapsed";
/** The class of the one root that holds everything: the stylesheet draws it as the project's frame, the map sets it. */
export const PROJECT_BOX = "is-project";
/** The data an aggregated edge is told apart by. */
export const AGGREGATE = "aggregate";
/** The data a drawn end carries: how many of its aggregated edges the budget leaves out. */
export const HIDDEN_EDGES = "hiddenEdges";
/** The data every mark of the map carries: the factor that keeps its size on screen. */
export const MAP_SCALE = "mapScale";
/** The class of a loop's end: where the line of an edge into its node's own box meets the border (`model/loopLines.js`). */
export const LOOP_END = "loop-end";
/** The data a loop's line carries: the id of the box it ends at, which holds its other end. */
export const LOOP_OF = "loopOf";
/** The data a loop's end carries: the id of the box it stands on the border of. */
export const LOOP_BOX = "loopBox";

/**
 * The data a node's own line, or its edge drawn as itself, carries for the end
 * it draws no head at: the id of an open box its node's lines into the box's
 * nodes run on into, which carry the direction there (`model/canvasMap.js`).
 */
export const STUB_AT = "stubAt";

/** The ends of the edge drawn by `line`, by id, `{ source, target }`: a loop's box rather than its end. */
export function endsOfLine(line) {
  const box = (node) => node.data(LOOP_BOX) ?? node.id();
  return { source: box(line.source()), target: box(line.target()) };
}

/** What the levels are tuned by. */
export const LEVEL_OPTIONS = Object.freeze({
  /** A box opens when its smallest child is at least this many pixels tall on screen: a node a reader can read. */
  readable: 24,
  /**
   * An open box closes when its smallest child falls below this share of
   * `readable`, so a box at the edge does not flicker. Lower, the lines between
   * its nodes would be drawn where ELK's shortest last runs, ten layout units
   * after a bend, hold no whole arrowhead.
   */
  closeShare: 0.9,
  /** A box opens only once the view is zoomed in past this many times the whole-graph fit. */
  fitFloor: 1.3,
  /** The most aggregated edges a level draws; the weakest beyond it are counted on their ends. */
  budget: 100,
});

/**
 * The containment tree of `nodes`, `[{ id, parent }]` with `parent` null at a root:
 * `{ parent, boxes, wrapper, childBoxes, topBoxes, depth }`.
 *
 * `boxes` holds every node that holds another; `wrapper` is the one root that
 * holds everything, or null; `childBoxes` maps a box to the boxes directly in it;
 * `topBoxes` are the boxes right under the wrapper, or the boxes at the top when
 * there is none; `depth` maps each id to how many boxes hold it.
 */
export function boxTreeOf(nodes) {
  const parent = new Map(nodes.map((node) => [node.id, node.parent || null]));
  const boxes = new Set([...parent.values()].filter((id) => id !== null && parent.has(id)));
  const roots = nodes.filter((node) => !parent.get(node.id)).map((node) => node.id);
  const wrapper = roots.length === 1 && boxes.has(roots[0]) ? roots[0] : null;
  const childBoxes = new Map();
  for (const box of boxes) {
    const holder = parent.get(box);
    if (holder) childBoxes.set(holder, [...(childBoxes.get(holder) || []), box]);
  }
  const topBoxes = wrapper ? childBoxes.get(wrapper) || [] : roots.filter((id) => boxes.has(id));
  const depth = new Map();
  const depthOf = (id) => {
    if (!depth.has(id)) depth.set(id, parent.get(id) ? depthOf(parent.get(id)) + 1 : 0);
    return depth.get(id);
  };
  for (const id of parent.keys()) depthOf(id);
  return { parent, boxes, wrapper, childBoxes, topBoxes, depth };
}

/** The boxes that hold `id`, outermost first. */
export function holdersOf(tree, id) {
  const chain = [];
  for (let cursor = tree.parent.get(id); cursor; cursor = tree.parent.get(cursor)) chain.unshift(cursor);
  return chain;
}

/** Every box that holds a node of `ids`: what has to be open for each of them to be drawn as itself. */
export function boxesHolding(tree, ids) {
  const out = new Set();
  for (const id of ids) for (const box of holdersOf(tree, id)) out.add(box);
  return out;
}

/** The boxes open while each node of `ids` is drawn as itself with its own edges: its holders, and itself when it is a box. */
export function boxesRevealing(tree, ids) {
  const out = boxesHolding(tree, ids);
  for (const id of ids) if (tree.boxes.has(id)) out.add(id);
  return out;
}

/** `id => the node it is drawn as`: its outermost closed holder, or itself, with the boxes in `open` open. */
export function drawnAsOf(tree, open) {
  const memo = new Map();
  return (id) => {
    if (!memo.has(id)) {
      const closed = holdersOf(tree, id).find((box) => box !== tree.wrapper && !open.has(box));
      memo.set(id, closed ?? id);
    }
    return memo.get(id);
  };
}

/** The name of the unordered pair of `a` and `b`, and the two in the order the name gives them. */
function pairOf(a, b) {
  const ends = a < b ? [a, b] : [b, a];
  return { name: `${ends[0]}\n${ends[1]}`, ends };
}

/**
 * The two nodes an edge from `source` to `target` is drawn between: the
 * children of the lowest box holding both ends that hold one end each, an end
 * itself when it is such a child; null for a loop, an edge between a node and
 * a box that holds it.
 */
export function siblingsOf(tree, source, target) {
  const a = [...holdersOf(tree, source), source];
  const b = [...holdersOf(tree, target), target];
  let k = 0;
  while (k < a.length && k < b.length && a[k] === b[k]) k += 1;
  return k === a.length || k === b.length ? null : [a[k], b[k]];
}

/**
 * What a level draws, with the boxes in `open` open: `{ nodes, originals, pairs }`.
 *
 * `edges` are the drawn edges it reads, `{ id, source, target }`. `nodes` are the
 * ids drawn as themselves; `originals` the ids of the edges drawn as themselves:
 * an edge between two siblings neither of which is a box, and a loop both of
 * whose ends are drawn, neither of them a closed box; `pairs` maps a pair's
 * name to `{ name, ends, forward, backward }`: its two siblings, and the ids of
 * the edges it carries from the first to the second and back.
 */
export function levelOf(tree, open, edges) {
  const drawnAs = drawnAsOf(tree, open);
  const nodes = new Set([...tree.parent.keys()].filter((id) => drawnAs(id) === id));
  const closed = (id) => tree.boxes.has(id) && id !== tree.wrapper && !open.has(id);
  const originals = [];
  const pairs = new Map();
  for (const edge of edges) {
    const siblings = siblingsOf(tree, edge.source, edge.target);
    if (!siblings) {
      if (nodes.has(edge.source) && nodes.has(edge.target) && !closed(edge.source) && !closed(edge.target)) originals.push(edge.id);
      continue;
    }
    const [source, target] = siblings;
    if (!nodes.has(source) || !nodes.has(target)) continue;
    if (source === edge.source && target === edge.target && !tree.boxes.has(source) && !tree.boxes.has(target)) {
      originals.push(edge.id);
      continue;
    }
    const { name, ends } = pairOf(source, target);
    if (!pairs.has(name)) pairs.set(name, { name, ends, forward: [], backward: [] });
    pairs.get(name)[source === ends[0] ? "forward" : "backward"].push(edge.id);
  }
  return { nodes, originals, pairs };
}

/** Whether `id` is `node` or inside it. */
const isWithin = (tree, id, node) => id === node || holdersOf(tree, id).includes(node);

/**
 * The outward edges of the drawn nodes of `level` (`levelOf`, for `open` and
 * `edges`): `Map(node => [edge ids])`. An edge is an outward edge of the node one
 * of its ends is drawn as when its other end lies outside that node and it is
 * neither drawn as itself nor carried by a pair with that node as an end: the
 * line that carries it at rest is a box's that holds the node. The box that
 * holds everything has none.
 */
export function outwardOf(tree, open, edges, level) {
  const drawnAs = drawnAsOf(tree, open);
  const carriedBy = new Map();
  for (const pair of level.pairs.values()) for (const id of [...pair.forward, ...pair.backward]) carriedBy.set(id, pair.ends);
  const originals = new Set(level.originals);
  const out = new Map();
  for (const edge of edges) {
    if (originals.has(edge.id) || !siblingsOf(tree, edge.source, edge.target)) continue;
    for (const [end, other] of [[edge.source, edge.target], [edge.target, edge.source]]) {
      const node = drawnAs(end);
      if (node === tree.wrapper || isWithin(tree, other, node) || (carriedBy.get(edge.id) || []).includes(node)) continue;
      if (!out.has(node)) out.set(node, []);
      out.get(node).push(edge.id);
    }
  }
  return out;
}

/**
 * The outward edges of the open box `box` at `level` (`levelOf`, for `edges`):
 * the edges with exactly one end inside it that the level draws neither as
 * themselves nor on a line with the box as an end, nor as a loop onto a box that
 * holds it — what a line of a box that holds it carries at rest, as
 * `outwardOf` reads them for a closed one.
 */
export function outwardOfOpen(tree, box, edges, level) {
  const carriedBy = new Map();
  for (const pair of level.pairs.values()) for (const id of [...pair.forward, ...pair.backward]) carriedBy.set(id, pair.ends);
  const originals = new Set(level.originals);
  return edges
    .filter((edge) => {
      const [from, to] = [isWithin(tree, edge.source, box), isWithin(tree, edge.target, box)];
      if (from === to || originals.has(edge.id) || !siblingsOf(tree, edge.source, edge.target)) return false;
      const other = from ? edge.target : edge.source;
      return !holdersOf(tree, box).includes(other) && !(carriedBy.get(edge.id) || []).includes(box);
    })
    .map((edge) => edge.id);
}

/**
 * The lines that draw the outward edges of the nodes in `exposed`: `{ originals,
 * pairs }`. `edges` maps an edge id to `{ id, source, target }`; `outward` is
 * `outwardOf`'s answer; `asItself(id)` says whether a drawn node can take an edge
 * of the file drawn as itself — a leaf the map draws at its laid-out size. An
 * outward edge between such a leaf and a node drawn as itself that takes one too
 * is drawn as itself; every other is carried by one line per pair of the exposed
 * node and the node the other end is drawn as, `{ name, ends, forward,
 * backward }` as a level's pairs are.
 */
export function ownLinesOf(tree, open, edges, outward, exposed, asItself) {
  const drawnAs = drawnAsOf(tree, open);
  const originals = new Set();
  const pairs = new Map();
  for (const node of exposed) {
    for (const id of outward.get(node) || []) {
      const edge = edges.get(id);
      const inside = isWithin(tree, edge.source, node);
      const other = drawnAs(inside ? edge.target : edge.source);
      if (other === tree.wrapper || holdersOf(tree, node).includes(other)) continue;
      const [source, target] = inside ? [node, other] : [other, node];
      if (source === edge.source && target === edge.target && asItself(source) && asItself(target)) {
        originals.add(id);
        continue;
      }
      const { name, ends } = pairOf(source, target);
      const key = `own\n${name}`;
      if (!pairs.has(key)) pairs.set(key, { name: key, ends, forward: [], backward: [] });
      const pair = pairs.get(key);
      if (![...pair.forward, ...pair.backward].includes(id)) pair[source === ends[0] ? "forward" : "backward"].push(id);
    }
  }
  return { originals, pairs };
}

/** Code-unit order of two strings, which no locale changes. */
const byCodeUnits = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/**
 * The names of the aggregated edges a level leaves out to draw at most `budget`:
 * every one past the `budget` heaviest. `pairs` are `[{ name, weight }]`, the
 * weight being the edges a pair carries. Of pairs as heavy as each other the one
 * whose name comes first in code-unit order is drawn first; a pair's name is its
 * two ends in that order, so the same pairs are drawn whatever order they come
 * in, and a tie at the cut fills the budget rather than leaving it empty.
 */
export function budgetOf(pairs, budget) {
  if (pairs.length <= budget) return new Set();
  const ranked = [...pairs].sort((a, b) => b.weight - a.weight || byCodeUnits(a.name, b.name));
  return new Set(ranked.slice(budget).map((pair) => pair.name));
}

/** Whether `box` overlaps `extent`, both `{ x1, y1, x2, y2 }`. */
const overlaps = (box, extent) =>
  box.x2 > extent.x1 && box.x1 < extent.x2 && box.y2 > extent.y1 && box.y1 < extent.y2;

/**
 * The height of the smallest node each box holds directly, `Map(box =>
 * height)`, from `boxes`, each node's laid-out `{ x1, y1, x2, y2 }`: a box's
 * nodes are readable once that height is on screen.
 */
export function smallestChildOf(tree, boxes) {
  const smallest = new Map();
  for (const [id, holder] of tree.parent) {
    if (!holder || !boxes[id]) continue;
    smallest.set(holder, Math.min(smallest.get(holder) ?? Infinity, boxes[id].y2 - boxes[id].y1));
  }
  return smallest;
}

/** The zoom at which box `id`'s nodes are readable, for `smallest` (`smallestChildOf`); Infinity for a box with none. */
export function readableZoomOf(id, smallest, options = LEVEL_OPTIONS) {
  return smallest.has(id) ? options.readable / smallest.get(id) : Infinity;
}

/**
 * The boxes open at the view `view`: `{ zoom, fitZoom, extent }`, the zoom, the
 * whole-graph fit's zoom and the graph's area on screen. `boxes` maps a node to
 * its laid-out `{ x1, y1, x2, y2 }` and `smallest` a box to its smallest child's
 * height (`smallestChildOf`); `open` the boxes open now, which close only below
 * the smaller height; `wanted` the boxes a selection or a search needs, open
 * wherever they are once their nodes are readable, as the view opens the
 * readable boxes it overlaps; `forced` the boxes open at any zoom, each with
 * every box that holds it, whose children open as the children of any open box do.
 */
export function openInView(tree, boxes, smallest, open, view, wanted = new Set(), options = LEVEL_OPTIONS, forced = new Set()) {
  const next = new Set();
  const past = view.zoom >= view.fitZoom * options.fitFloor;
  const visit = (ids) => {
    for (const id of ids) {
      const box = boxes[id];
      if (!box) continue;
      if (!forced.has(id)) {
        if (!past || !(wanted.has(id) || overlaps(box, view.extent))) continue;
        const needed = readableZoomOf(id, smallest, options) * (open.has(id) ? options.closeShare : 1);
        if (view.zoom < needed) continue;
      }
      next.add(id);
      visit(tree.childBoxes.get(id) || []);
    }
  };
  visit(tree.topBoxes);
  return next;
}

/**
 * The least zoom at which node `id` is drawn as itself and readable: every box
 * that holds it open, past the floor over the fit `fitZoom`.
 */
export function zoomDrawingOf(tree, id, smallest, fitZoom, options = LEVEL_OPTIONS) {
  let zoom = fitZoom * options.fitFloor;
  for (const box of holdersOf(tree, id)) if (box !== tree.wrapper) zoom = Math.max(zoom, readableZoomOf(box, smallest, options));
  return zoom;
}

/**
 * The nodes a selection draws as themselves: its own node, and every node its
 * walk reached when the reader asked for more than the selection (`wholeWalk`).
 * With nothing more asked a selection opens what the pointer on its node would
 * need, so the node's edges are drawn on the lines a hover draws them on.
 */
export function selectionReveals(focus, walked, { wholeWalk }) {
  if (!focus) return [];
  return wholeWalk ? [focus, ...walked] : [focus];
}
