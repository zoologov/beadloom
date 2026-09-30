// beadloom:component=site-shared
// Walks over a containment tree given as a map of node id to parent id.

/** Each parent's direct children, from a `{ id: parentId | null }` map. */
export function childrenOf(parents) {
  const children = new Map();
  for (const [id, parent] of Object.entries(parents)) {
    if (!parent) continue;
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push(id);
  }
  return children;
}

/** The ids in `ids` plus every ancestor of each. */
export function withAncestors(ids, parents) {
  const out = new Set();
  for (const id of ids) {
    for (let cursor = id; cursor && !out.has(cursor); cursor = parents[cursor]) {
      out.add(cursor);
    }
  }
  return out;
}

/** `root` and every node under it, at any depth. */
export function subtreeOf(root, children) {
  const out = new Set();
  const stack = [root];
  while (stack.length) {
    const id = stack.pop();
    if (out.has(id)) continue;
    out.add(id);
    stack.push(...(children.get(id) || []));
  }
  return out;
}
