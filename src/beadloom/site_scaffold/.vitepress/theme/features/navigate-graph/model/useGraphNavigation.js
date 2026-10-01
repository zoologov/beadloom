// beadloom:component=site-navigate-graph
// How a reader moves around the graph: pan, zoom, fit, centre, and Arrange.
//
// Dragging the canvas pans and never moves the node under the pointer. In an
// earlier version every node was grabbable, compound parents included, and a domain box
// covers its children's area, so a drag started almost anywhere inside it
// grabbed the box. Now nodes are not grabbable (`autoungrabify`) and every node
// is `pannable`, which passes a drag on it through to the viewport. "Arrange"
// is the deliberate gesture for moving nodes: it makes the leaves grabbable,
// while a drag inside a box still pans.
//
// Fitting and centring leave out the part of the canvas something lies over:
// in the page the viewer's panel covers the canvas's right edge, and a graph
// fitted to the whole canvas would put what the reader asked for under it.

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
/** The closest a fit zooms in, so a lone node is framed rather than filling the canvas. */
export const FIT_MAX_ZOOM = 1.5;

/** The canvas's edges nothing lies over. */
const NO_INSET = Object.freeze({ right: 0 });

/**
 * Navigation over the graph `getCy()` returns.
 *
 * `fit(selector)` fits the visible elements the selector names, or everything
 * visible; `centre(id)` centres on a node, or on what is visible when no node
 * is named. `getInset()` says how many pixels at the canvas's right edge are
 * covered, and both leave them out.
 */
export function useGraphNavigation(getCy, { getInset = () => NO_INSET } = {}) {
  const arranging = ref(false);

  // The centre of the uncovered part of the canvas, in rendered pixels.
  function openCentre(cy, inset) {
    return { x: (cy.width() - inset.right) / 2, y: cy.height() / 2 };
  }

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

  function fitTo(cy, target) {
    const inset = getInset();
    const box = target.boundingBox();
    const width = cy.width() - inset.right - 2 * FIT_PADDING;
    const height = cy.height() - 2 * FIT_PADDING;
    if (width <= 0 || height <= 0 || !box.w || !box.h) {
      cy.fit(target, FIT_PADDING);
      return;
    }
    const fitting = Math.min(width / box.w, height / box.h, FIT_MAX_ZOOM, cy.maxZoom());
    const zoom = Math.max(fitting, cy.minZoom());
    const centre = openCentre(cy, inset);
    cy.viewport({
      zoom,
      pan: { x: centre.x - zoom * (box.x1 + box.w / 2), y: centre.y - zoom * (box.y1 + box.h / 2) },
    });
  }

  function fit(selector) {
    const cy = getCy();
    if (!cy) return;
    const chosen = typeof selector === "string" ? cy.elements(selector).filter(":visible") : cy.collection();
    const visible = chosen.nonempty() ? chosen : cy.elements(":visible");
    fitTo(cy, visible.nonempty() ? visible : cy.elements());
  }

  function centre(id) {
    const cy = getCy();
    if (!cy) return;
    const target = id ? cy.getElementById(id) : cy.elements(":visible");
    if (target.empty()) return;
    const box = target.boundingBox();
    const centreOfOpen = openCentre(cy, getInset());
    const zoom = cy.zoom();
    cy.pan({ x: centreOfOpen.x - zoom * (box.x1 + box.w / 2), y: centreOfOpen.y - zoom * (box.y1 + box.h / 2) });
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
