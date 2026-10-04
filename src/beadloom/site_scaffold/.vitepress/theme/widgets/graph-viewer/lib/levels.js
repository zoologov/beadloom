// beadloom:component=site-graph-viewer
// The map's levels: which boxes are open, what each node is drawn as, and which edges are drawn between them.
//
// The whole-graph view of a large graph is a cloud: every node and every edge at
// a scale where none can be told apart. So the overview draws it like a map. A
// box is open or closed; a closed box is drawn at its full size with nothing
// inside it, and every node inside it is drawn as it. An edge both of whose ends
// are drawn as themselves, neither of them a closed box, is drawn as itself;
// every other edge between two drawn ends is carried by one **aggregated edge**
// per unordered pair of those ends, with how many edges go each way, so two
// closed boxes are joined by one line whatever runs between them and their
// contents; an edge inside one closed box is not drawn.
//
// A level is a set of open boxes and nothing more: nothing is laid out again, so
// no box moves between levels. Which boxes are open is decided here as well:
//
// - **What is in view**: a box opens when the box holding it is open, it overlaps
//   the viewport, the view is zoomed in past a floor over the whole-graph fit, and
//   its larger side is at least a size on screen; it closes again below a share of
//   that size, so it does not flicker at the edge (`openInView`).
// - **What a selection needs**: a node the reader asked for is drawn as itself
//   with its own edges (`boxesRevealing`): every box that holds it is open, and
//   so is the node when it is a box, since an edge of a closed box is carried by
//   its pair's aggregated edge. A walk opens what every node it reaches needs,
//   except that a hub selected with nothing more opens only its own
//   (`selectionReveals`): opening every box a hub reaches draws nearly the whole
//   graph again.
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
/** The data an aggregated edge is told apart by. */
export const AGGREGATE = "aggregate";
/** The data a drawn end carries: how many of its aggregated edges the budget leaves out. */
export const HIDDEN_EDGES = "hiddenEdges";
/** The data every mark of the map carries: the factor that keeps its size on screen. */
export const MAP_SCALE = "mapScale";

/** What the levels are tuned by. */
export const LEVEL_OPTIONS = Object.freeze({
  /** A box opens when its larger side is at least this many pixels on screen. */
  openSide: 600,
  /** An open box closes when its larger side falls below this share of `openSide`. */
  closeShare: 0.8,
  /** A box opens only once the view is zoomed in past this many times the whole-graph fit. */
  fitFloor: 1.3,
  /** The most aggregated edges a level draws; the weakest beyond it are counted on their ends. */
  budget: 100,
  /** A node with at least this many drawn edges is a hub. */
  hubDegree: 20,
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
 * What a level draws, with the boxes in `open` open: `{ nodes, originals, pairs }`.
 *
 * `edges` are the drawn edges it reads, `{ id, source, target }`. `nodes` are the
 * ids drawn as themselves; `originals` the ids of the edges drawn as themselves,
 * both of whose ends are, neither of them a closed box;
 * `pairs` maps a pair's name to `{ name, ends, forward, backward }`: its two
 * drawn ends, and the ids of the edges it carries from the first to the second
 * and back.
 */
export function levelOf(tree, open, edges) {
  const drawnAs = drawnAsOf(tree, open);
  const nodes = new Set([...tree.parent.keys()].filter((id) => drawnAs(id) === id));
  const closed = (id) => tree.boxes.has(id) && id !== tree.wrapper && !open.has(id);
  const originals = [];
  const pairs = new Map();
  for (const edge of edges) {
    const source = drawnAs(edge.source);
    const target = drawnAs(edge.target);
    if (source === edge.source && target === edge.target && !closed(source) && !closed(target)) {
      originals.push(edge.id);
      continue;
    }
    if (source === target || source === tree.wrapper || target === tree.wrapper) continue;
    const { name, ends } = pairOf(source, target);
    if (!pairs.has(name)) pairs.set(name, { name, ends, forward: [], backward: [] });
    pairs.get(name)[source === ends[0] ? "forward" : "backward"].push(edge.id);
  }
  return { nodes, originals, pairs };
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
 * The boxes open by what is in view: `view` is `{ zoom, fitZoom, extent }`, the
 * zoom, the whole-graph fit's zoom and the graph's area on screen; `boxes` maps a
 * box to its `{ x1, y1, x2, y2 }`; `open` the boxes open now, which close only
 * below the smaller size.
 */
export function openInView(tree, boxes, open, view, options = LEVEL_OPTIONS) {
  const next = new Set();
  if (view.zoom < view.fitZoom * options.fitFloor) return next;
  const visit = (ids) => {
    for (const id of ids) {
      const box = boxes[id];
      if (!box || !overlaps(box, view.extent)) continue;
      const side = Math.max(box.x2 - box.x1, box.y2 - box.y1) * view.zoom;
      const needed = open.has(id) ? options.openSide * options.closeShare : options.openSide;
      if (side < needed) continue;
      next.add(id);
      visit(tree.childBoxes.get(id) || []);
    }
  };
  visit(tree.topBoxes);
  return next;
}

/**
 * The nodes a selection draws as themselves: its own node, and every node its
 * walk reached unless the node is a hub (`degree` at least `options.hubDegree`)
 * and the reader asked for nothing more than the selection (`wholeWalk` false).
 */
export function selectionReveals(focus, walked, { degree, wholeWalk }, options = LEVEL_OPTIONS) {
  if (!focus) return [];
  if (!wholeWalk && degree >= options.hubDegree) return [focus];
  return [focus, ...walked];
}
