// The browser tests' own reading of the data file: walks written independently of the viewer.
//
// A test that asked the viewer's own walk what the viewer should show would pass
// whatever the walk did. These helpers compute the expected sets from
// `architecture.data.json` directly, so a case compares the drawn state against
// an answer the viewer's code played no part in.

/** The edge kinds a neighbourhood follows: every kind drawn as a line. */
export const NEIGHBOURHOOD_KINDS = ["depends_on", "uses", "consumes", "produces"];

/** The edge kinds whose source depends on its target: what the impact walk follows backwards. */
export const DEPENDENCY_KINDS = ["depends_on", "uses", "consumes"];

/** The key the viewer gives a drawn edge: its kind, source and target. */
export function edgeKey(edge) {
  return `${edge.kind}:${edge.src}->${edge.dst}`;
}

/** `{ out, in }`: each node's edges of `kinds` in each direction, `[{ id, key }]`. */
export function adjacency(data, kinds) {
  const ids = new Set(data.nodes.map((n) => n.id));
  const out = new Map();
  const into = new Map();
  const push = (map, id, entry) => (map.get(id) || map.set(id, []).get(id)).push(entry);
  for (const edge of data.edges) {
    if (!kinds.includes(edge.kind) || !ids.has(edge.src) || !ids.has(edge.dst)) continue;
    if (edge.src === edge.dst) continue;
    push(out, edge.src, { id: edge.dst, key: edgeKey(edge) });
    push(into, edge.dst, { id: edge.src, key: edgeKey(edge) });
  }
  return { out, in: into };
}

/**
 * A breadth-first walk from `start`: `{ distances, edges }`.
 *
 * `distances` maps each reached id to its distance; `edges` holds the key of
 * every edge taken from a node closer than `maxDepth`.
 */
export function walk(start, step, maxDepth = Infinity) {
  const distances = new Map([[start, 0]]);
  const edges = new Set();
  let frontier = [start];
  for (let depth = 0; depth < maxDepth && frontier.length; depth += 1) {
    const next = [];
    for (const id of frontier) {
      for (const { id: other, key } of step(id)) {
        edges.add(key);
        if (distances.has(other)) continue;
        distances.set(other, depth + 1);
        next.push(other);
      }
    }
    frontier = next;
  }
  return { distances, edges };
}

/** The neighbourhood of `start` at `depth` (a number or Infinity) in `dir` (`in`, `out`, `both`). */
export function neighbourhood(data, start, depth, dir) {
  const adj = adjacency(data, NEIGHBOURHOOD_KINDS);
  const walks = [];
  if (dir !== "in") walks.push(walk(start, (id) => adj.out.get(id) || [], depth));
  if (dir !== "out") walks.push(walk(start, (id) => adj.in.get(id) || [], depth));
  const ids = new Set();
  const edges = new Set();
  for (const w of walks) {
    for (const id of w.distances.keys()) ids.add(id);
    for (const key of w.edges) edges.add(key);
  }
  return { ids: [...ids].sort(), edges: [...edges].sort() };
}

/** Every node that depends on `start`, transitively: `{ distances, edges }`. */
export function impact(data, start) {
  const adj = adjacency(data, DEPENDENCY_KINDS);
  return walk(start, (id) => adj.in.get(id) || []);
}

/** The node's nearest container of `kind`, the node itself included, or null. */
export function nearestOfKind(id, kind, byId, parents) {
  for (let cursor = id; cursor; cursor = parents[cursor]) {
    if (byId.get(cursor)?.kind === kind) return cursor;
  }
  return null;
}

/**
 * What a doc's sync status means for a change, by the impact mode's risks and
 * the sync engine's words for its states: `stale` was compared and found out of
 * date; `unpaired`, `unverified` and `missing` are states in which nothing
 * could be compared, which the engine must not report as the same word; `ok`
 * is no risk. A status this table does not name is treated as not checked.
 */
const DOC_RISK = Object.freeze({
  ok: null,
  stale: "stale docs",
  unpaired: "docs not checked",
  unverified: "docs not checked",
  missing: "docs not checked",
});

/**
 * The risks a change to `node` runs, as the labels the impact list shows.
 *
 * Written from the definition, not from the viewer: a node the test binding
 * covers with no test is untested (a node it does not cover says nothing); a
 * node's docs are judged one by one when the file lists them, and by the
 * aggregate `doc_status` of a version 1 file otherwise; any finding, of any
 * severity, is open. The labels are returned sorted.
 */
export function risksOf(node) {
  const risks = new Set();
  if (node.tests != null && node.tests.count === 0) risks.add("no bound tests");
  if (Array.isArray(node.docs)) {
    for (const doc of node.docs) {
      const risk = doc.status in DOC_RISK ? DOC_RISK[doc.status] : "docs not checked";
      if (risk) risks.add(risk);
    }
  } else if (node.doc_status === "stale") {
    risks.add("stale docs");
  }
  if (Array.isArray(node.findings) && node.findings.length > 0) risks.add("open findings");
  return [...risks].sort();
}
