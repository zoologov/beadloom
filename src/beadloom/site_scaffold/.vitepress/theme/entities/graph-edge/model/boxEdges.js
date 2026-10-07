// beadloom:component=site-graph-edge
// A box's edges to the outside, as the map draws them: how many go to and come from each node a line of the box joins it to.
//
// The map draws an edge at the lowest box that holds both its ends, between the
// two children of that box that hold one end each, so a box's edges to the
// outside run on one line per node beside it. This counts them that way, for
// the card of a selected box: what it holds, and how many of its edges go out to
// and come in from each node its lines reach. An edge onto a box that holds it is
// drawn as itself, not on a line of the box's, and is not counted.

import { isDrawnKind } from "./edgeKinds.js";

/** Code-unit order of two strings, which no locale changes. */
const byCodeUnits = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** `id` and the boxes that hold it, outermost first, by `parents` (`{ id: parent | null }`). */
function chainOf(id, parents) {
  const chain = [id];
  for (let cursor = parents[id]; cursor; cursor = parents[cursor]) chain.unshift(cursor);
  return chain;
}

/**
 * What box `box` holds and where its edges go: `{ inside, out, in }`, `inside`
 * how many nodes it holds at any depth, `out` and `in` the nodes its lines join
 * it to, `[{ id, count }]` in code-unit order of id, with how many of its drawn
 * edges go out to each and come in from each. Null when `box` holds no node.
 */
export function boxEdgesOf(box, edges, parents) {
  const within = (id) => chainOf(id, parents).includes(box);
  const held = Object.keys(parents).filter((id) => id !== box && within(id));
  if (!held.length) return null;
  const counts = { out: new Map(), in: new Map() };
  for (const edge of edges) {
    if (!isDrawnKind(edge.kind) || edge.src === edge.dst || !(edge.src in parents) || !(edge.dst in parents)) continue;
    const [from, to] = [within(edge.src), within(edge.dst)];
    if (from === to) continue;
    const [a, b] = [chainOf(edge.src, parents), chainOf(edge.dst, parents)];
    let k = 0;
    while (k < a.length && k < b.length && a[k] === b[k]) k += 1;
    const other = from ? b[k] : a[k];
    if (other === undefined) continue;
    const side = from ? counts.out : counts.in;
    side.set(other, (side.get(other) || 0) + 1);
  }
  const listed = (map) => [...map].sort(([a], [b]) => byCodeUnits(a, b)).map(([id, count]) => ({ id, count }));
  return { inside: held.length, out: listed(counts.out), in: listed(counts.in) };
}
