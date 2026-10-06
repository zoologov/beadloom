// The served architecture data file with two edges more: the same graph, laid out another way.
//
// A rule of the viewer's read on one data file holds on one layout of it. Two
// `depends_on` edges added to a portal's data once moved its layout enough that
// three rules held on the file before and failed on the file after: a line had
// no room for its arrowhead, a title stood on a plate, and opening a box moved
// two pills. So a case about what the layout decides runs a second time over the
// served file with two edges more, added as a change that adds a dependency adds
// them: from two nodes into one they did not depend on, each in another
// top-level box than it.
//
// Which two is derived from the file, never named, so the same file gives the
// same graph on every run and any portal can be perturbed: into the leaf most
// depended on, from the two leaves that depend on the most others and not yet on
// it, in two top-level boxes other than its own and each other's. Every name in
// the file is kept; only the two edges and their ends' lists of them are new.

import { treeOf } from "./map.js";

/** The kind of the edges added: the one a change that adds a dependency adds. */
const ADDED_KIND = "depends_on";

/** The top-level box that holds `id`, or `id` itself at the top. */
function topOf(id, tree) {
  let cursor = id;
  while (tree.parents[cursor] && tree.parents[cursor] !== tree.wrapper) cursor = tree.parents[cursor];
  return cursor;
}

/** How many `depends_on` edges each node has, out (`outgoing`) and in (`incoming`). */
function degreesOf(data) {
  const outgoing = new Map();
  const incoming = new Map();
  for (const edge of data.edges.filter((e) => e.kind === ADDED_KIND)) {
    outgoing.set(edge.src, (outgoing.get(edge.src) || 0) + 1);
    incoming.set(edge.dst, (incoming.get(edge.dst) || 0) + 1);
  }
  return { outgoing, incoming };
}

/** `ids` by `count` most first, then by id, so the order is the same on every run. */
const byMost = (ids, count) => [...ids].sort((a, b) => (count.get(b) || 0) - (count.get(a) || 0) || (a < b ? -1 : a > b ? 1 : 0));

/**
 * `data` with two `depends_on` edges more, and the edges added:
 * `{ data, added: [{ src, dst }] }`. Null when the file holds no such pair of
 * nodes: a graph of fewer than three top-level boxes with leaves in them.
 */
export function withTwoMoreEdges(data) {
  const tree = treeOf(data);
  const leaves = data.nodes.map((n) => n.id).filter((id) => !tree.boxes.has(id) && id !== tree.wrapper && tree.parents[id]);
  const { outgoing, incoming } = degreesOf(data);
  const linked = new Set(data.edges.map((e) => `${e.src}\n${e.dst}`));
  for (const target of byMost(leaves, incoming)) {
    const sources = [];
    for (const source of byMost(leaves, outgoing)) {
      const box = topOf(source, tree);
      if (source === target || linked.has(`${source}\n${target}`) || box === topOf(target, tree)) continue;
      if (sources.some((other) => topOf(other, tree) === box)) continue;
      sources.push(source);
      if (sources.length === 2) break;
    }
    if (sources.length < 2) continue;
    const added = sources.map((src) => ({ src, dst: target }));
    const extend = (node) => {
      const out = added.filter((e) => e.src === node.id).map((e) => e.dst);
      const into = added.filter((e) => e.dst === node.id).map((e) => e.src);
      if (!out.length && !into.length) return node;
      return {
        ...node,
        depends_on: [...(node.depends_on || []), ...out],
        depended_on_by: [...(node.depended_on_by || []), ...into],
      };
    };
    return {
      data: {
        ...data,
        nodes: data.nodes.map(extend),
        edges: [...data.edges, ...added.map((e) => ({ ...e, kind: ADDED_KIND, violation: false }))],
      },
      added,
    };
  }
  return null;
}
