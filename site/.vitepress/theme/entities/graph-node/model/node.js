// beadloom:component=site-graph-node
// A node of the architecture data file, and what the viewer reads off it.
//
// Version 1's fields: `id`, `label`, `kind`, `summary`, `layer` (the node's own
// layer tag), `layer_rank` (its layer, inherited through `part_of`), `parent`,
// `doc_status`, `lint_clean` and the dependency lists. Version 2's card fields
// are read for the risk a change runs: `tests`, `docs` and `findings`. A field
// a version 1 file does not carry is no risk, because nothing says it is one.

/** A node is flagged when its docs are stale or the lint run found a violation on it. */
export function statusOf(node) {
  if (node.lint_clean === false) return "violation";
  if (node.doc_status === "stale") return "stale";
  return null;
}

export function isFlagged(node) {
  return statusOf(node) !== null;
}

/**
 * Each node's container, `{ id: parentId | null }`.
 *
 * A parent that is not itself a node of the file, or a node that names itself
 * (the root service is `part_of` itself), has none: Cytoscape rejects a dangling
 * or self parent, and a walk over it would never end.
 */
export function parentMapOf(nodes) {
  const ids = new Set(nodes.map((n) => n.id));
  const parents = {};
  for (const n of nodes) {
    parents[n.id] = n.parent && n.parent !== n.id && ids.has(n.parent) ? n.parent : null;
  }
  return parents;
}

/** The risks a node carries for a change, as the phrases the viewer shows. */
export const RISKS = Object.freeze({
  untested: "no bound tests",
  staleDocs: "stale docs",
  findings: "open findings",
});

/**
 * Why a change to this node is risky: no bound tests, stale docs, open rule findings.
 *
 * A doc is stale when any of its pairs is not `ok`, or when the node's
 * aggregate doc status says so.
 */
export function risksOf(node) {
  const risks = [];
  if (node.tests && node.tests.count === 0) risks.push(RISKS.untested);
  const staleDoc = (node.docs || []).some((doc) => doc.status !== "ok");
  if (staleDoc || node.doc_status === "stale") risks.push(RISKS.staleDocs);
  if ((node.findings || []).length) risks.push(RISKS.findings);
  return risks;
}

/** The node's nearest container of `kind`, the node itself included, or null. */
export function containerOfKind(id, kind, nodeById, parents) {
  for (let cursor = id; cursor; cursor = parents[cursor]) {
    if (nodeById.get(cursor)?.kind === kind) return cursor;
  }
  return null;
}
