// beadloom:component=site-graph-node
// A node of the architecture data file, and what the viewer reads off it.
//
// The fields are version 1's: `id`, `label`, `kind`, `summary`, `layer` (the
// node's own layer tag), `layer_rank` (its layer, inherited through `part_of`),
// `parent`, `doc_status`, `lint_clean` and the dependency lists.

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
