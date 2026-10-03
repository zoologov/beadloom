// beadloom:component=site-shared
// Cytoscape.js, loaded in the browser only and once.
//
// Cytoscape touches the DOM at import time, so it is imported lazily: VitePress
// renders every page on the server first, where it cannot load. The layout is
// not Cytoscape's: ELK runs in a worker of its own (`shared/elk`).

let loading = null;

/** The `cytoscape` factory. */
export function loadCytoscape() {
  loading ||= import("cytoscape").then(({ default: cytoscape }) => cytoscape);
  return loading;
}
