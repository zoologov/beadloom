// beadloom:component=site-shared
// Cytoscape.js with the ELK layout, loaded in the browser only and registered once.
//
// Both libraries touch the DOM at import time, so they are imported lazily:
// VitePress renders every page on the server first, where they cannot load.

let loading = null;

/** The `cytoscape` factory with the `elk` layout registered. */
export function loadCytoscape() {
  if (!loading) {
    loading = Promise.all([import("cytoscape"), import("cytoscape-elk")]).then(
      ([{ default: cytoscape }, { default: elk }]) => {
        cytoscape.use(elk);
        return cytoscape;
      }
    );
  }
  return loading;
}
