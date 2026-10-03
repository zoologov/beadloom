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

/**
 * What a level draws: `{ nodes, originals, pairs }`.
 *
 * `open` is the set of open boxes; `edges` the drawn edges to read (`drawnEdgesOf`,
 * or a filtered subset). `nodes` are the ids drawn as themselves; `originals` the
 * keys of the edges drawn as themselves, both of whose ends are, neither of them
 * a closed box; `pairs` maps
 * "a|b", the two drawn ends in sorted order, to `{ ends, forward, backward }`,
 * the keys of the edges drawn from `a` to `b` and from `b` to `a`. An edge inside
 * one closed box is not drawn, and neither is one onto the wrapper from inside a
 * closed box.
 */
export function levelOf(tree, open, edges) {
  const nodes = new Set(Object.keys(tree.parents).filter((id) => drawnAs(id, open, tree) === id));
  const closed = (id) => tree.boxes.has(id) && id !== tree.wrapper && !open.has(id);
  const originals = [];
  const pairs = new Map();
  for (const edge of edges) {
    const source = drawnAs(edge.src, open, tree);
    const target = drawnAs(edge.dst, open, tree);
    if (source === edge.src && target === edge.dst && !closed(source) && !closed(target)) {
      originals.push(edge.key);
      continue;
    }
    if (source === target || source === tree.wrapper || target === tree.wrapper) continue;
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

/** The smallest weight whose aggregated edges, with every heavier one, number at most `budget`; 0 when all fit. */
export function budgetThreshold(weights, budget = AGGREGATE_BUDGET) {
  if (weights.length <= budget) return 0;
  const distinct = [...new Set(weights)].sort((a, b) => a - b);
  for (const weight of distinct) {
    if (weights.filter((w) => w >= weight).length <= budget) return weight;
  }
  return Math.max(...distinct) + 1;
}

/** Each node's count of drawn edges, the ones whose ends are both in the file. */
export function degreesOf(data) {
  const degree = new Map();
  for (const { src, dst } of drawnEdgesOf(data)) {
    for (const id of [src, dst]) degree.set(id, (degree.get(id) || 0) + 1);
  }
  return degree;
}
