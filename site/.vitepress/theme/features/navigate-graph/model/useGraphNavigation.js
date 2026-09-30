// beadloom:component=site-navigate-graph
// How a reader moves around the graph: pan, zoom, fit, centre, and Arrange.
//
// Dragging the canvas pans and never moves the node under the pointer. Before
// BDL-076 every node was grabbable, compound parents included, and a domain box
// covers its children's area, so a drag started almost anywhere inside it
// grabbed the box. Now nodes are not grabbable (`autoungrabify`) and every node
// is `pannable`, which passes a drag on it through to the viewport. "Arrange"
// is the deliberate gesture for moving nodes: it makes the leaves grabbable,
// while a drag inside a box still pans.

import { ref } from "vue";

/** The Cytoscape options of the navigation model, given when the graph is created. */
export const NAVIGATION_OPTIONS = Object.freeze({
  autoungrabify: true,
  autounselectify: true,
  boxSelectionEnabled: false,
  userPanningEnabled: true,
  userZoomingEnabled: true,
  wheelSensitivity: 0.2,
  minZoom: 0.02,
  maxZoom: 4,
});

/** How much one zoom step changes the zoom level. */
export const ZOOM_STEP = 1.25;
/** Padding around the graph when it is fitted, in pixels. */
export const FIT_PADDING = 40;

/**
 * Navigation over the graph `getCy()` returns.
 *
 * `fit` fits what is visible; `centre(id)` centres on a node, or on what is
 * visible when no node is named.
 */
export function useGraphNavigation(getCy) {
  const arranging = ref(false);

  function applyArrangePolicy() {
    const cy = getCy();
    if (!cy) return;
    cy.autoungrabify(!arranging.value);
    cy.nodes().forEach((node) => {
      if (node.isParent() || !arranging.value) node.panify();
      else node.unpanify();
    });
  }

  function zoomBy(factor) {
    const cy = getCy();
    if (!cy) return;
    const centre = { x: cy.width() / 2, y: cy.height() / 2 };
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: centre });
  }

  function fit() {
    const cy = getCy();
    if (!cy) return;
    const visible = cy.elements(":visible");
    cy.fit(visible.nonempty() ? visible : cy.elements(), FIT_PADDING);
  }

  function centre(id) {
    const cy = getCy();
    if (!cy) return;
    const target = id ? cy.getElementById(id) : cy.elements(":visible");
    if (target.nonempty()) cy.center(target);
  }

  function toggleArrange() {
    arranging.value = !arranging.value;
    applyArrangePolicy();
  }

  return {
    arranging,
    applyArrangePolicy,
    zoomIn: () => zoomBy(ZOOM_STEP),
    zoomOut: () => zoomBy(1 / ZOOM_STEP),
    fit,
    centre,
    toggleArrange,
  };
}
