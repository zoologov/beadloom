// The browser tests' own reading of the counts a reader sees: a node's "+N", the lines a hover and a selection draw for it, and the number on each.
//
// Written apart from the viewer's code. The rule restated here is the one the
// viewer's reader is told: a node inside an open box says "+N" for its edges the
// map carries at rest on the lines of a box that holds it; pointing at the node
// or selecting it draws those N edges on lines of its own, the same lines either
// way, and every such line of the map says how many of them it carries, one
// included; while a node is selected, every line of its walk says how many of
// the walk's edges it carries, whatever else it carries. A box is a node whose
// edges are every edge with exactly one end inside it.
//
// The expected sets come from the data file (`map.js`); what was drawn comes
// from the test handle's readers, and is joined here by line.

import { drawnAs, levelOf, outwardOf } from "./map.js";
import { viewer, withAncestors } from "./viewer.js";

/** What a line of the map says for `forward` edges one way and `backward` the other: the reader's format. */
export const countText = (forward, backward) => [forward, backward].filter(Boolean).join(" + ");

/** Whether `id` is `node` or inside it. */
export const isWithin = (tree, id, node) => withAncestors([id], tree.parents).has(node);

/**
 * The keys of the edges of `node`: every drawn edge with exactly one end inside
 * it, `node` itself included; for a box, but an edge onto a box that holds it,
 * which is no neighbour of it.
 */
export function edgesOfNode(tree, edges, node) {
  const holders = tree.boxes.has(node) ? new Set(holdersOf(tree, node)) : new Set();
  return edges
    .filter((e) => isWithin(tree, e.src, node) !== isWithin(tree, e.dst, node) && !holders.has(e.src) && !holders.has(e.dst))
    .map((e) => e.key)
    .sort();
}

/** The boxes that hold `id`, outermost first. */
export function holdersOf(tree, id) {
  const chain = [];
  for (let cursor = tree.parents[id]; cursor; cursor = tree.parents[cursor]) chain.unshift(cursor);
  return chain;
}

/**
 * The keys of the outward edges of `node` (owner's ruling 14): those a level
 * with every box that holds it open, and `node` itself closed, carries on a line
 * of a box that holds it. Which other boxes are open changes none of them.
 */
export function outwardKeysOf(tree, edges, node) {
  const open = new Set(holdersOf(tree, node));
  return outwardOf(tree, open, edges, levelOf(tree, open, edges)).get(node) || [];
}

/**
 * Every line drawn now, as a reader reads it: `[{ id, map, ends, forwardKeys,
 * backwardKeys, label, pill, walk, front, dimmed }]`. `ends` are the two nodes
 * the line joins (a loop's box rather than its end); `map` marks a line of the
 * map's, whose `label` is the number it says and `pill` the number its pill
 * shows, or null where none is drawn, `crowded` when the pill covers something
 * for want of a free place.
 */
export async function drawnLines(page) {
  const looks = await viewer(page, "lineLooks");
  const routes = new Map((await viewer(page, "edgeRoutes")).map((route) => [route.id, route]));
  const maps = new Map([...(await viewer(page, "aggregatedEdges")), ...(await viewer(page, "ownLines"))].filter((e) => e.drawn).map((e) => [e.id, e]));
  const shown = (await viewer(page, "pills")).pills;
  const pills = new Map(shown.map((pill) => [pill.id, pill.text]));
  const crowded = new Set(shown.filter((pill) => pill.crowded).map((pill) => pill.id));
  return looks.map((look) => {
    const map = maps.get(look.id);
    const route = routes.get(look.id);
    return {
      id: look.id,
      map: Boolean(map),
      ends: map ? [...map.ends] : [route.source, route.target],
      forwardKeys: map ? map.forwardKeys : look.key ? [look.key] : [],
      backwardKeys: map ? map.backwardKeys : [],
      label: map ? map.label : null,
      pill: pills.get(look.id) ?? null,
      crowded: crowded.has(look.id),
      walk: look.walk,
      front: look.front,
      dimmed: look.dimmed,
    };
  });
}

/**
 * What the lines of `node` (the lines it is an end of) draw of the edges `keys`:
 * `{ lines, keys, twice }` — each such line by id, `{ forward, backward, map,
 * label, pill }`, how many of `keys` it carries each way; every key drawn, in
 * order; and the keys drawn by more than one of them.
 */
export function linesCarrying(lines, node, keys) {
  const wanted = new Set(keys);
  const out = { lines: {}, keys: [], twice: [] };
  const seen = new Set();
  for (const line of lines) {
    if (!line.ends.includes(node)) continue;
    const forward = line.forwardKeys.filter((key) => wanted.has(key));
    const backward = line.backwardKeys.filter((key) => wanted.has(key));
    if (!forward.length && !backward.length) continue;
    out.lines[line.id] = { forward: forward.length, backward: backward.length, map: line.map, label: line.label, pill: line.pill };
    for (const key of [...forward, ...backward]) {
      if (seen.has(key)) out.twice.push(key);
      seen.add(key);
    }
  }
  out.keys = [...seen].sort();
  return out;
}

/**
 * The lines of `carrying` (`linesCarrying`) whose number is not the count of
 * the edges they carry for the reader: a line of the map that says nothing, or
 * says or shows another number. A line of the file joins two nodes and is one edge.
 */
export function wrongNumbers(carrying) {
  const wrong = [];
  for (const [id, line] of Object.entries(carrying.lines)) {
    if (!line.map) continue;
    const wanted = countText(line.forward, line.backward);
    if (line.label !== wanted || line.pill !== wanted) wrong.push(`${id} carries ${wanted}, says ${line.label ?? "nothing"}, its pill ${line.pill ?? "none"}`);
  }
  return wrong;
}

/**
 * The lines of a selection's walk drawn now whose number is not the count of
 * the walk's edges, `walkKeys`, they carry: `[text]`. A line of the file is one
 * edge and says nothing.
 */
export function wrongWalkNumbers(lines, walkKeys) {
  const walk = new Set(walkKeys);
  const wrong = [];
  for (const line of lines) {
    if (!line.walk || !line.map) continue;
    const wanted = countText(line.forwardKeys.filter((key) => walk.has(key)).length, line.backwardKeys.filter((key) => walk.has(key)).length);
    if (line.label !== wanted || line.pill !== wanted) wrong.push(`${line.ends.join("|")} carries ${wanted || "none"} of the walk, says ${line.label ?? "nothing"}, its pill ${line.pill ?? "none"}`);
  }
  return wrong;
}

/** The node each end of `keys` is drawn as now, with the boxes in `open` open: the keys whose ends are drawn as two different nodes. */
export function keysBetweenDrawn(tree, edges, keys, open) {
  const byKey = new Map(edges.map((e) => [e.key, e]));
  return keys.filter((key) => {
    const edge = byKey.get(key);
    const [a, b] = [drawnAs(edge.src, open, tree), drawnAs(edge.dst, open, tree)];
    return a !== b && a !== tree.wrapper && b !== tree.wrapper;
  });
}

/**
 * The nodes the lines of box `box` lead to, by the map's sibling rule, and how
 * many of its edges go each way: `{ inside, out: { id: count }, in: { id: count } }`,
 * `inside` the nodes it holds at any depth. An edge onto a box that holds it is
 * not on its lines.
 */
export function boxSummaryOf(tree, edges, box) {
  const inside = Object.keys(tree.parents).filter((id) => id !== box && isWithin(tree, id, box)).length;
  const summary = { inside, out: {}, in: {} };
  const chainOf = (id) => [...holdersOf(tree, id), id];
  for (const edge of edges) {
    const [from, to] = [isWithin(tree, edge.src, box), isWithin(tree, edge.dst, box)];
    if (from === to) continue;
    const [a, b] = [chainOf(edge.src), chainOf(edge.dst)];
    let k = 0;
    while (k < a.length && k < b.length && a[k] === b[k]) k += 1;
    const other = from ? b[k] : a[k];
    // An edge onto a box that holds this one is a loop, drawn as itself: no line of the box's carries it.
    if (other === undefined) continue;
    const side = from ? summary.out : summary.in;
    side[other] = (side[other] || 0) + 1;
  }
  return summary;
}
