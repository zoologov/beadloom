// The browser tests' own reading of the map: what each level draws, computed from the data file.
//
// A case that asked the viewer which edges it aggregated would pass whatever the
// viewer did. These helpers derive the answer from `architecture.data.json` and a
// set of open boxes alone: which node each node is drawn as, which edges are drawn
// as themselves, and which are carried by one aggregated edge per unordered pair
// of drawn ends, with how many go each way. The rules are the map's as the
// product states them, written again here rather than imported.

import { edgeKey, NEIGHBOURHOOD_KINDS } from "./graph.js";
import { parentMap } from "./viewer.js";

/** How many aggregated edges a level draws at most; weaker ones are counted on their box. */
export const AGGREGATE_BUDGET = 100;

/**
 * The containment tree: `{ parents, boxes, wrapper, topBoxes, depth }`.
 *
 * `wrapper` is the one root that holds everything, when the graph has one: it is
 * always open. `topBoxes` are the boxes directly under it, or the boxes at the
 * top when there is no wrapper; `depth` gives each node's depth below the top.
 */
export function treeOf(data) {
  const parents = parentMap(data);
  const boxes = new Set(Object.values(parents).filter(Boolean));
  const roots = Object.keys(parents).filter((id) => !parents[id]);
  const wrapper = roots.length === 1 && boxes.has(roots[0]) ? roots[0] : null;
  const topBoxes = [...boxes].filter((id) => parents[id] === wrapper || (!wrapper && !parents[id])).sort();
  const depth = (id) => {
    let d = 0;
    for (let cursor = parents[id]; cursor; cursor = parents[cursor]) d += 1;
    return d;
  };
  return { parents, boxes, wrapper, topBoxes, depth };
}

/** The node `id` is drawn as when the boxes in `open` are open: its outermost closed container, or itself. */
export function drawnAs(id, open, tree) {
  const chain = [];
  for (let cursor = tree.parents[id]; cursor; cursor = tree.parents[cursor]) chain.unshift(cursor);
  const closed = chain.find((box) => box !== tree.wrapper && !open.has(box));
  return closed ?? id;
}

/** The edges drawn as a line between two nodes of the file: `[{ src, dst, key }]`. */
export function drawnEdgesOf(data) {
  const ids = new Set(data.nodes.map((n) => n.id));
  return data.edges
    .filter((e) => NEIGHBOURHOOD_KINDS.includes(e.kind) && e.src !== e.dst && ids.has(e.src) && ids.has(e.dst))
    .map((e) => ({ src: e.src, dst: e.dst, key: edgeKey(e) }));
}

/** The boxes that hold `id`, outermost first, and `id` itself last. */
function chainOf(id, tree) {
  const chain = [id];
  for (let cursor = tree.parents[id]; cursor; cursor = tree.parents[cursor]) chain.unshift(cursor);
  return chain;
}

/**
 * The two nodes an edge from `src` to `dst` is drawn between, by the sibling
 * rule: the children of the lowest box holding both ends that hold one end each
 * (an end itself when it is such a child). Null for a loop, an edge between a
 * node and a box that holds it.
 */
export function siblingsOf(src, dst, tree) {
  const [a, b] = [chainOf(src, tree), chainOf(dst, tree)];
  let k = 0;
  while (k < a.length && k < b.length && a[k] === b[k]) k += 1;
  if (k === a.length || k === b.length) return null;
  return [a[k], b[k]];
}

/**
 * What a level draws: `{ nodes, originals, pairs }`.
 *
 * `open` is the set of open boxes; `edges` the drawn edges to read (`drawnEdgesOf`,
 * or a filtered subset). `nodes` are the ids drawn as themselves. An edge is
 * drawn at the lowest box that holds both its ends, between the two children of
 * that box that hold them: as itself only when those children are its own ends
 * and neither is a box, and otherwise carried by one aggregated edge per
 * unordered pair of them, so an open box keeps its outward edges at the box. An
 * edge between a node and a box that holds it is drawn as itself when both its
 * ends are drawn and neither is a closed box. An edge inside a closed box is not
 * drawn, and neither is one onto the wrapper from inside a closed box.
 * `originals` are the keys of the edges drawn as themselves; `pairs` maps
 * "a|b", the two ends in sorted order, to `{ ends, forward, backward }`, the
 * keys of the edges drawn from `a` to `b` and from `b` to `a`.
 */
export function levelOf(tree, open, edges) {
  const nodes = new Set(Object.keys(tree.parents).filter((id) => drawnAs(id, open, tree) === id));
  const closed = (id) => tree.boxes.has(id) && id !== tree.wrapper && !open.has(id);
  const originals = [];
  const pairs = new Map();
  for (const edge of edges) {
    const siblings = siblingsOf(edge.src, edge.dst, tree);
    if (!siblings) {
      if (nodes.has(edge.src) && nodes.has(edge.dst) && !closed(edge.src) && !closed(edge.dst)) originals.push(edge.key);
      continue;
    }
    const [source, target] = siblings;
    if (!nodes.has(source) || !nodes.has(target)) continue;
    if (source === edge.src && target === edge.dst && !tree.boxes.has(source) && !tree.boxes.has(target)) {
      originals.push(edge.key);
      continue;
    }
    const ends = [source, target].sort();
    const name = ends.join("|");
    if (!pairs.has(name)) pairs.set(name, { ends, forward: [], backward: [] });
    pairs.get(name)[source === ends[0] ? "forward" : "backward"].push(edge.key);
  }
  for (const pair of pairs.values()) {
    pair.forward.sort();
    pair.backward.sort();
  }
  return { nodes, originals: originals.sort(), pairs };
}

/**
 * The outward edges of each drawn node that a level does not draw at rest
 * (owner's ruling 14, the "+N" mark): `Map(id => [keys])`. An edge is the
 * outward edge of the drawn node one of its ends is drawn as when its other
 * end is outside that node and it is neither drawn as itself nor carried by an
 * aggregated edge with that node as an end. `level` is `levelOf`'s answer for
 * the same `open` and `edges`.
 */
export function outwardOf(tree, open, edges, level) {
  const drawnEnd = new Map();
  for (const pair of level.pairs.values()) for (const key of [...pair.forward, ...pair.backward]) drawnEnd.set(key, pair.ends);
  const originals = new Set(level.originals);
  const out = new Map();
  for (const edge of edges) {
    if (originals.has(edge.key) || !siblingsOf(edge.src, edge.dst, tree)) continue;
    for (const [end, other] of [[edge.src, edge.dst], [edge.dst, edge.src]]) {
      const node = drawnAs(end, open, tree);
      if (node === tree.wrapper || chainOf(other, tree).includes(node)) continue;
      if ((drawnEnd.get(edge.key) || []).includes(node)) continue;
      if (!out.has(node)) out.set(node, []);
      out.get(node).push(edge.key);
    }
  }
  for (const keys of out.values()) keys.sort();
  return out;
}

/** The height of the smallest node each box holds directly, in layout units, from ELK's boxes: what decides when a box opens. */
export function smallestChildOf(tree, boxes) {
  const smallest = new Map();
  for (const [id, parent] of Object.entries(tree.parents)) {
    if (!parent || !boxes[id]) continue;
    const height = boxes[id].y2 - boxes[id].y1;
    smallest.set(parent, Math.min(smallest.get(parent) ?? Infinity, height));
  }
  return smallest;
}

/** Code-unit order of two strings, which no locale changes. */
const byCodeUnits = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/**
 * The names, "a|b", of the pairs a level leaves out to draw at most `budget`:
 * every pair past the `budget` heaviest, `pairs` being `[{ ends, weight }]`. Of
 * pairs as heavy as each other, the one whose ends come first in code-unit order
 * is drawn first, so a tie at the cut fills the budget rather than emptying it.
 */
export function budgetLeftOut(pairs, budget = AGGREGATE_BUDGET) {
  const ranked = [...pairs].sort(
    (a, b) => b.weight - a.weight || byCodeUnits(a.ends[0], b.ends[0]) || byCodeUnits(a.ends[1], b.ends[1])
  );
  return new Set(ranked.slice(budget).map((pair) => pair.ends.join("|")));
}

/** Each node's count of drawn edges, the ones whose ends are both in the file. */
export function degreesOf(data) {
  const degree = new Map();
  for (const { src, dst } of drawnEdgesOf(data)) {
    for (const id of [src, dst]) degree.set(id, (degree.get(id) || 0) + 1);
  }
  return degree;
}
