// beadloom:component=site-navigate-graph
// How a reader moves around the graph: pan, zoom, fit and centre.
//
// Dragging the canvas pans and never moves the node under the pointer, on any
// page and by any gesture. In an earlier version every node was grabbable,
// compound parents included, and a domain box covers its children's area, so a
// drag started almost anywhere inside it grabbed the box. Later an "Arrange"
// button made the leaves grabbable on purpose. A node stays where the layout put
// it now, because what is drawn between the nodes is read from that layout: no
// node is grabbable (`autoungrabify`), and every node is `pannable`, which
// passes a drag on it through to the viewport.
//
// Fitting and centring leave out the part of the canvas something lies over:
// in the page the viewer's panel covers the canvas's right edge, and a graph
// fitted to the whole canvas would put what the reader asked for under it. The
// zoom a fit of everything visible would take is also read on its own
// (`fitZoom`): the viewer's map measures how far the reader has zoomed in from it.

import { FIT_MAX_ZOOM, FIT_PADDING } from "../../../shared/map-levels/index.js";

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
/** How long a framing move takes, in milliseconds, when it is animated. */
export const FRAME_MS = 350;
/** The media query a reader who asks for less motion matches. */
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

/** Whether the reader asks for reduced motion. */
const reducedMotion = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(REDUCED_MOTION).matches;

/**
 * What a fit measures: the nodes' shapes, not their labels, and each edge's
 * route, not its stroke. Some labels keep one size on screen whatever the zoom
 * (the viewer's map titles its closed boxes so), and so does every line's width
 * and arrowhead; in the graph's units those grow as the view zooms out, and a
 * fit measured with them would depend on the zoom it was pressed at, which
 * matters once a line runs outside every node, as the overview's do. The
 * padding leaves room for a label or an arrowhead at the edge.
 */
const SHAPES_ONLY = Object.freeze({ includeLabels: false });

/** The box around `elements` a fit measures: every node's shape and every point of every edge's route. */
function shapesBoxOf(elements) {
  const box = elements.nodes().boundingBox(SHAPES_ONLY);
  let [x1, y1, x2, y2] = box.w || box.h ? [box.x1, box.y1, box.x2, box.y2] : [Infinity, Infinity, -Infinity, -Infinity];
  elements.edges().forEach((edge) => {
    for (const point of [edge.sourceEndpoint(), edge.targetEndpoint(), ...(edge.segmentPoints() || edge.controlPoints() || [])]) {
      [x1, y1, x2, y2] = [Math.min(x1, point.x), Math.min(y1, point.y), Math.max(x2, point.x), Math.max(y2, point.y)];
    }
  });
  if (!Number.isFinite(x1)) return box;
  return { x1, y1, x2, y2, w: x2 - x1, h: y2 - y1 };
}

/** The canvas's edges nothing lies over. */
const NO_INSET = Object.freeze({ right: 0 });

/**
 * Navigation over the graph `getCy()` returns.
 *
 * `panOnNodes()` makes a drag on any node of the graph pan the view; call it once
 * the graph holds its nodes. `fit(selector)` fits the visible elements the
 * selector names, or everything visible; `centre(id)` centres on a node, or on
 * what is visible when no node is named; `frame(target, { animate })` frames a
 * selection. `getInset()` says how many pixels at the canvas's right edge are
 * covered, and all three leave them out. `fitZoom({ drawing })` is the zoom
 * `fit()` would take now, without moving the view, measured once per `drawing`
 * when one is named. `lastMove()` is the last framing move, as `frame` made it.
 */
export function useGraphNavigation(getCy, { getInset = () => NO_INSET } = {}) {
  // The centre of the uncovered part of the canvas, in rendered pixels.
  function openCentre(cy, inset) {
    return { x: (cy.width() - inset.right) / 2, y: cy.height() / 2 };
  }

  function panOnNodes() {
    const cy = getCy();
    if (!cy) return;
    cy.nodes().panify();
  }

  function zoomBy(factor) {
    const cy = getCy();
    if (!cy) return;
    const centre = { x: cy.width() / 2, y: cy.height() / 2 };
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: centre });
  }

  /** The zoom that fits `box` into the uncovered canvas, or null when either has no size. */
  function zoomFitting(cy, box, inset) {
    const width = cy.width() - inset.right - 2 * FIT_PADDING;
    const height = cy.height() - 2 * FIT_PADDING;
    if (width <= 0 || height <= 0 || !box.w || !box.h) return null;
    const fitting = Math.min(width / box.w, height / box.h, FIT_MAX_ZOOM, cy.maxZoom());
    return Math.max(fitting, cy.minZoom());
  }

  /** What a fit with no selector frames: everything visible, or everything when nothing is. */
  function everythingVisible(cy) {
    const visible = cy.elements(":visible");
    return visible.nonempty() ? visible : cy.elements();
  }

  function fitTo(cy, target) {
    const inset = getInset();
    const box = shapesBoxOf(target);
    const zoom = zoomFitting(cy, box, inset);
    if (zoom === null) {
      cy.fit(target, FIT_PADDING);
      return;
    }
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
    fitTo(cy, chosen.nonempty() ? chosen : everythingVisible(cy));
  }

  // The last fit zoom measured for a named drawing, and what it was measured over.
  let measured = { key: null, zoom: null };

  /**
   * The zoom a fit of everything visible would take now. A caller that names the
   * drawing it asks about, `drawing`, a token that changes whenever what is drawn
   * does, has it measured once per drawing, canvas size and inset: measuring
   * reads every visible node's shape and every visible edge's route, which a
   * zoom or a pan of one drawing does not move.
   */
  function fitZoom({ drawing = null } = {}) {
    const cy = getCy();
    if (!cy) return 1;
    const inset = getInset();
    const key = drawing === null ? null : `${drawing}\n${cy.width()}x${cy.height()}\n${inset.right}`;
    if (key !== null && measured.key === key) return measured.zoom;
    const zoom = zoomFitting(cy, shapesBoxOf(everythingVisible(cy)), inset) ?? cy.zoom();
    measured = { key, zoom };
    return zoom;
  }

  /**
   * The last framing move: `{ animated, from, to, frames, done }`, the zoom it
   * left and the zoom it ends at, how many of Cytoscape's frames drew it (one
   * per step of an animated move, one for a move made at once), and `done` once
   * it has ended. It is counted where the move is made: a reader of the zoom
   * outside starts too late to see a move that a slow machine draws in two frames.
   */
  let move = null;

  /**
   * Frame `box`, `{ x1, y1, x2, y2 }` in the graph's coordinates, at no less than
   * `leastZoom`; where it does not fit at that zoom, centre on `focus`, a box too.
   * Animated when `animate` is true and the reader has not asked for reduced motion.
   */
  function frame({ box, focus, leastZoom = 0 }, { animate = false } = {}) {
    const cy = getCy();
    if (!cy || !box) return;
    const inset = getInset();
    const sized = { ...box, w: box.x2 - box.x1, h: box.y2 - box.y1 };
    const fitting = zoomFitting(cy, sized, inset) ?? cy.zoom();
    const zoom = Math.min(Math.max(fitting, leastZoom, cy.minZoom()), cy.maxZoom());
    const on = zoom > fitting + 1e-9 && focus ? focus : box;
    const centreOfOpen = openCentre(cy, inset);
    const pan = { x: centreOfOpen.x - zoom * ((on.x1 + on.x2) / 2), y: centreOfOpen.y - zoom * ((on.y1 + on.y2) / 2) };
    cy.stop(true, true);
    const from = cy.zoom();
    if (animate && !reducedMotion()) {
      const counted = { animated: true, from, to: zoom, frames: 0, done: false };
      move = counted;
      cy.animate(
        { zoom, pan },
        {
          duration: FRAME_MS,
          easing: "ease-in-out-cubic",
          step: () => {
            counted.frames += 1;
          },
          complete: () => {
            counted.done = true;
          },
        }
      );
      return;
    }
    cy.viewport({ zoom, pan });
    move = { animated: false, from, to: zoom, frames: 1, done: true };
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

  return {
    panOnNodes,
    zoomIn: () => zoomBy(ZOOM_STEP),
    zoomOut: () => zoomBy(1 / ZOOM_STEP),
    fit,
    fitZoom,
    frame,
    lastMove: () => (move ? { ...move } : null),
    centre,
  };
}
