// beadloom:component=site-shared
// An id for a thing the viewer makes itself, which no id of the data file has.
//
// The data file's ids are whatever a project named its nodes, so no name the
// viewer picks for one of its own things (ELK's root graph, a Cytoscape edge) is
// out of the data's reach. Each such id is therefore chosen against the ids it
// shares a space with: the preferred name, primed until none of them has it.
//
// The segment imports nothing, so a module that runs without VitePress (the
// layout's graph, a page of the theme's modules alone) can use it.

/** `base`, or `base` followed by as many primes (`'`) as it takes to be none of `taken`. */
export function freshId(base, taken) {
  let id = base;
  while (taken.has(id)) id += "'";
  return id;
}
