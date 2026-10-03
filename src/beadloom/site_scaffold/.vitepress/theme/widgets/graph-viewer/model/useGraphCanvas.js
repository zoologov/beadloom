// beadloom:component=site-graph-viewer
// The Cytoscape instance behind the viewer's canvas, and what the viewer does to it.
//
// It creates the graph, has ELK lay it out in a worker (`shared/elk`) while the
// page stays responsive, draws it as ELK laid it out — every node in its place,
// every box at its size, every edge along its route with its node's fans bundled
// (`canvasLayout.js`) and a dot where bundled routes part (`bundleOverlay.js`) —
// reports taps, labels a hovered edge and marks every edge along the hovered
// line, shows only a set of node ids (and of contracts), marks a selection — the
// selected node, the nodes and edges its walk reached, their distance rings and
// risks, and what lies outside — and swaps the stylesheet when the theme
// changes. It decides nothing about which nodes are visible or selected: the
// viewer's state does.
//
// The layout's run (`layout`) keeps ELK's geometry — a box for every node and a
// route for every edge, in the graph's coordinates — beside the canvas, so what
// is drawn from it later reads the same layout the nodes were placed by: when a
// filter or a selection shows or hides nodes, every box is sized to it again.

import { onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { loadCytoscape } from "../../../shared/cytoscape/index.js";
import { elkGraphOf, layOut, warmUpLayout } from "../../../shared/elk/index.js";
import { bundleOverlay } from "./bundleOverlay.js";
import { applyGeometry, fitCompounds, layoutInputOf } from "./canvasLayout.js";

/** Every class a selection puts on the canvas, removed before the next one is marked. */
const SELECTION_CLASSES = [
  "is-selected",
  "is-selected-edge",
  "in-walk",
  "is-walk-edge",
  "is-dimmed",
  "is-outside",
  "is-risk",
];

/** The class of every edge drawn along the line under the pointer. */
const ALONG_HOVER = "is-along-hover";

/** Cytoscape's layout that places nothing, run when the graph is created. */
const UNPLACED = Object.freeze({ name: "null" });

/** The node data the impact mode sets: the node's distance from the selection. */
export const DISTANCE_DATA = "impactDistance";

/**
 * `{ cy, ready, layingOut, layout, bundles, hoveredEdges, layoutError, junctions,
 * mount, setStyle, showOnly, markSelection, resize }` over the container in
 * `containerRef`.
 *
 * `layingOut` is true while ELK runs; `layout` is the last run, `{ geometry,
 * source, ms }` (`shared/elk`, `layOut`), or null; `bundles` is its routes with
 * the fans bundled, `{ paths, trunks, buses, ms }` (`canvasLayout.js`), or null;
 * `hoveredEdges` the ids of the edges along the line under the pointer;
 * `layoutError` is the error a failed run gave, or null; `junctions()` the dots
 * drawn where routes part, `[{ x, y, edges }]`.
 */
export function useGraphCanvas(containerRef, { options, onNodeTap, onBackgroundTap }) {
  const cy = shallowRef(null);
  const ready = ref(false);
  const layingOut = ref(false);
  const layout = shallowRef(null);
  const bundles = shallowRef(null);
  const hoveredEdges = shallowRef([]);
  const layoutError = shallowRef(null);
  let overlay = null;
  let generation = 0;

  // Cytoscape reports no `mouseout` when the pointer leaves the canvas from an
  // edge, so a hovered label would stay; leaving the container clears it.
  function clearHover() {
    cy.value?.edges(".is-hovered").removeClass("is-hovered");
    cy.value?.edges(`.${ALONG_HOVER}`).removeClass(ALONG_HOVER);
    hoveredEdges.value = [];
  }

  // Cytoscape reports the one edge under the pointer; on a shared line every
  // edge drawn along it is what the reader points at.
  function hoverAlong(edge, position) {
    const ids = overlay ? overlay.along(edge.id(), position) : [edge.id()];
    cy.value.batch(() => {
      cy.value.edges(`.${ALONG_HOVER}`).removeClass(ALONG_HOVER);
      for (const id of ids) cy.value.getElementById(id).addClass(ALONG_HOVER);
    });
    hoveredEdges.value = ids;
  }

  function refreshOverlay() {
    overlay?.refresh();
  }

  function destroy() {
    ready.value = false;
    layingOut.value = false;
    layout.value = null;
    bundles.value = null;
    hoveredEdges.value = [];
    containerRef.value?.removeEventListener("mouseleave", clearHover);
    overlay?.destroy();
    overlay = null;
    cy.value?.destroy();
    cy.value = null;
  }

  async function mount(elements, style) {
    const mine = ++generation;
    const cytoscape = await loadCytoscape();
    if (mine !== generation || !containerRef.value) return false;
    destroy();
    // No layout on creation: ELK places every node, and Cytoscape's default grid
    // would only spend time spreading them over the canvas first.
    const instance = cytoscape({
      container: containerRef.value,
      elements,
      style,
      layout: UNPLACED,
      ...options,
    });
    instance.on("tap", "node", (event) => onNodeTap(event.target.id()));
    instance.on("tap", (event) => {
      if (event.target === instance) onBackgroundTap();
    });
    instance.on("mouseover", "edge", (event) => {
      event.target.addClass("is-hovered");
      hoverAlong(event.target, event.position);
    });
    instance.on("mouseout", "edge", clearHover);
    containerRef.value.addEventListener("mouseleave", clearHover);
    cy.value = instance;
    return place(instance, mine);
  }

  /** Lay `instance` out and place its nodes; false when a newer mount took over, or ELK failed. */
  async function place(instance, mine) {
    layingOut.value = true;
    layoutError.value = null;
    try {
      const run = await layOut(elkGraphOf(layoutInputOf(instance)));
      if (mine !== generation) return false;
      const drawn = await applyGeometry(instance, run.geometry);
      if (mine !== generation) return false;
      overlay = bundleOverlay(instance, containerRef.value, drawn.paths);
      overlay.refresh();
      layout.value = run;
      bundles.value = drawn;
    } catch (error) {
      if (mine === generation) layoutError.value = error;
      return false;
    } finally {
      if (mine === generation) layingOut.value = false;
    }
    ready.value = true;
    return true;
  }

  function setStyle(style) {
    cy.value?.style(style);
    refreshOverlay();
  }

  // A box is drawn around the children shown; whenever that set changes, every
  // box is sized to ELK's again.
  function fitBoxes() {
    if (cy.value && layout.value) fitCompounds(cy.value, layout.value.geometry);
  }

  /**
   * Show only the nodes in `ids`. When `contracts` is a set of contract keys, an
   * edge that carries a contract outside it is hidden as well, because two
   * services that stay on the map can share a contract the filters leave out.
   */
  function showOnly(ids, contracts = null) {
    cy.value?.batch(() => {
      cy.value.nodes().forEach((node) => node.toggleClass("is-hidden", !ids.has(node.id())));
      cy.value.edges().forEach((edge) => {
        const contract = edge.data("contract");
        edge.toggleClass("is-hidden", Boolean(contracts && contract && !contracts.has(contract)));
      });
    });
    fitBoxes();
    refreshOverlay();
  }

  function markNode(node, selection, outside) {
    const id = node.id();
    const distance = selection.distances.get(id);
    if (distance === undefined) {
      if (!selection.keep.has(id)) node.addClass(outside);
      return;
    }
    node.addClass("in-walk");
    const ring = selection.rings?.get(id);
    if (ring === undefined) return;
    node.addClass(`ring-${ring}`);
    node.data(DISTANCE_DATA, distance);
    if (selection.risks?.has(id)) node.addClass("is-risk");
  }

  /**
   * Mark `selection` on the canvas, or clear the marks when it is null.
   *
   * `selection` is `{ focus, distances, edges, keep, hide, rings, risks }`:
   * the walk's nodes by distance and its edge keys; `keep`, the nodes that are
   * not outside (the walk and its containers); `hide`, whether what is outside
   * is hidden rather than dimmed; and, in impact mode, `rings` (id to ring) and
   * `risks` (the ids to mark).
   */
  function markSelection(selection) {
    const instance = cy.value;
    if (!instance) return;
    instance.batch(() => {
      instance.elements().removeClass(SELECTION_CLASSES.join(" "));
      instance.nodes().forEach((node) => {
        node.removeClass(node.classes().filter((name) => name.startsWith("ring-")));
        node.removeData(DISTANCE_DATA);
      });
      if (!selection) return;
      const outside = selection.hide ? "is-outside" : "is-dimmed";
      instance.nodes().forEach((node) => markNode(node, selection, outside));
      instance.edges().forEach((edge) => {
        edge.addClass(selection.edges.has(edge.data("key")) ? "is-walk-edge" : outside);
      });
      const focus = instance.getElementById(selection.focus);
      if (focus.nonempty()) {
        focus.addClass("is-selected");
        focus.connectedEdges(".is-walk-edge").addClass("is-selected-edge");
      }
    });
    fitBoxes();
    refreshOverlay();
  }

  function resize() {
    cy.value?.resize();
  }

  // ELK takes longer to load than to lay a graph out; loading it while the data
  // file and Cytoscape load takes that time off the first drawing.
  onMounted(warmUpLayout);
  onBeforeUnmount(() => {
    generation += 1;
    destroy();
  });

  return {
    cy,
    ready,
    layingOut,
    layout,
    bundles,
    hoveredEdges,
    layoutError,
    junctions: () => overlay?.junctions() || [],
    mount,
    setStyle,
    showOnly,
    markSelection,
    resize,
  };
}
