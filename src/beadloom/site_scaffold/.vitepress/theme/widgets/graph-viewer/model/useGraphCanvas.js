// beadloom:component=site-graph-viewer
// The Cytoscape instance behind the viewer's canvas, and what the viewer does to it.
//
// It creates the graph, has ELK lay it out in a worker (`shared/elk`) while the
// page stays responsive, draws it as ELK laid it out — every node in its place,
// every box at its size, every edge along its route with its node's fans bundled
// (`canvasLayout.js`) and one arrowhead where lines share their last run
// (`sharedLines.js`) — draws the followed lines on top of everything they cross,
// with the label of the one under the pointer (`followedOverlay.js`), draws the
// map's counts over everything (`pillOverlay.js`), reports taps, marks every
// edge along the hovered line, brings the lines of the node under the pointer in
// front of the rest and fades the rest, shows only a set of node ids
// (and of contracts), marks a selection — the selected node, the nodes and edges
// its walk reached, their distance rings and risks, and what lies outside — and
// swaps the stylesheet when the theme changes. It decides nothing about which
// nodes are visible or selected: the viewer's state does.
//
// The layout's run (`layout`) keeps ELK's geometry — a box for every node and a
// route for every edge, in the graph's coordinates — beside the canvas, so what
// is drawn from it later reads the same layout the nodes were placed by: when a
// filter or a selection shows or hides nodes, every box is sized to it again.
//
// What is drawn of that layout is a level of the map (`canvasMap.js`): the boxes
// open where the reader zooms in and where a selection or a search needs them,
// closed elsewhere, with aggregated edges between what is drawn. The node under
// the pointer and the selected node have their outward edges drawn on top of the
// rest. Whenever the level changes, what the filters show and what the selection
// marks are marked again on what is drawn now, so a box opened later shows its
// children marked as everything else is. A loop's end (`loopLines.js`) is no
// node of the file: it is shown with its box and marked with nothing.

import { onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { loadCytoscape } from "../../../shared/cytoscape/index.js";
import { elkGraphOf, layOut, warmUpLayout } from "../../../shared/elk/index.js";
import { ALONG_HOVER, BEHIND, DISTANCE_DATA, HOVERED, IN_FRONT, SELECTION_CLASSES } from "./canvasMarks.js";
import { applyGeometry, fitCompounds, layoutInputOf } from "./canvasLayout.js";
import { canvasMap } from "./canvasMap.js";
import { followedOverlay } from "./followedOverlay.js";
import { pillOverlay } from "./pillOverlay.js";
import { sharedLines } from "./sharedLines.js";
import { COLLAPSED, LOOP_BOX, LOOP_END } from "../lib/levels.js";

/** Cytoscape's layout that places nothing, run when the graph is created. */
const UNPLACED = Object.freeze({ name: "null" });

/**
 * `{ cy, ready, layingOut, layout, bundles, hoveredEdges, layoutError, followed,
 * labelled, frames, droppedHeads, pills, tallies, outward, map, mount, setStyle, reveal,
 * showOnly, markSelection, resize }` over the container in `containerRef`.
 *
 * `tokens()` gives the resolved theme tokens now, which the followed lines are
 * drawn in.
 * `fitZoom()` gives the zoom of the whole-graph fit now, which the map's levels
 * are measured from. `reveal(source, ids)` draws the nodes in `ids` as themselves
 * with their own edges for `source` ("search", or a test), opening every box that
 * holds one and each one that is a box, from the next drawing on; `revealNow`
 * draws it at once; the selection reveals what it needs itself (`markSelection`).
 * `map()` is the map drawn now, or null.
 *
 * `layingOut` is true while ELK runs; `layout` is the last run, `{ geometry,
 * source, ms }` (`shared/elk`, `layOut`), or null; `bundles` is its routes with
 * the fans bundled, `{ paths, trunks, buses, ms }` (`canvasLayout.js`), or null;
 * `hoveredEdges` the ids of the edges along the line under the pointer;
 * `layoutError` is the error a failed run gave, or null; `followed()` the lines
 * drawn on top, `labelled()` the ones whose label is drawn and `frames()` what
 * drawing them cost (`followedOverlay.js`); `droppedHeads()` the line ends that
 * leave their arrowhead to another on their last run (`sharedLines.js`);
 * `pills()`, `tallies()` and `outward()` the map's counts drawn last (`pillOverlay.js`).
 */
export function useGraphCanvas(containerRef, { options, onNodeTap, onBackgroundTap, fitZoom, tokens }) {
  const cy = shallowRef(null);
  const ready = ref(false);
  const layingOut = ref(false);
  const layout = shallowRef(null);
  const bundles = shallowRef(null);
  const hoveredEdges = shallowRef([]);
  const layoutError = shallowRef(null);
  let shared = null;
  let followed = null;
  let pills = null;
  let map = null;
  // The node under the pointer, whose lines are drawn in front of the rest.
  let pointed = null;
  let generation = 0;
  // What the filters show and what the selection marks, kept to mark again on
  // whatever a later level draws.
  let shown = { ids: null, contracts: null };
  let marked = null;

  // Cytoscape reports no `mouseout` when the pointer leaves the canvas from an
  // edge, so a hovered label would stay; leaving the container clears it.
  function clearHover() {
    cy.value?.edges(`.${HOVERED}`).removeClass(HOVERED);
    cy.value?.edges(`.${ALONG_HOVER}`).removeClass(ALONG_HOVER);
    hoveredEdges.value = [];
    followed?.refresh();
    hoverNode(null);
  }

  // A node under the pointer has every edge of its drawn, whatever the budget,
  // and its outward edges, in front of the rest.
  function hoverNode(id) {
    pointed = id;
    const lifted = map?.setExempt("pointer", id);
    const exposed = map?.expose("pointer", id ? [id] : []);
    if (lifted || exposed) redraw();
    else if (cy.value) {
      cy.value.batch(() => markFront(cy.value));
      followed?.refresh();
    }
  }

  /** Bring the drawn lines of the node under the pointer in front of the rest, and fade the rest; none for an open box. */
  function markFront(instance) {
    instance.edges(`.${IN_FRONT}, .${BEHIND}`).removeClass(`${IN_FRONT} ${BEHIND}`);
    const node = pointed ? instance.getElementById(pointed) : null;
    if (!node || node.empty() || node.isParent()) return;
    const own = node.connectedEdges().filter((edge) => edge.visible());
    if (own.empty()) return;
    own.addClass(IN_FRONT);
    instance.edges().not(own).addClass(BEHIND);
  }

  // Cytoscape reports the one edge under the pointer; on a shared line every
  // edge drawn along it is what the reader points at.
  function hoverAlong(edge, position) {
    const ids = shared ? shared.along(edge.id(), position) : [edge.id()];
    cy.value.batch(() => {
      cy.value.edges(`.${ALONG_HOVER}`).removeClass(ALONG_HOVER);
      for (const id of ids) cy.value.getElementById(id).addClass(ALONG_HOVER);
    });
    hoveredEdges.value = ids;
    followed?.refresh();
  }

  function refreshOverlay() {
    shared?.refresh();
    followed?.refresh();
  }

  function destroy() {
    ready.value = false;
    layingOut.value = false;
    layout.value = null;
    bundles.value = null;
    hoveredEdges.value = [];
    containerRef.value?.removeEventListener("mouseleave", clearHover);
    shared = null;
    followed?.destroy();
    followed = null;
    pills?.destroy();
    pills = null;
    pointed = null;
    map?.destroy();
    map = null;
    shown = { ids: null, contracts: null };
    marked = null;
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
    // Cytoscape keeps each edge's drawn path keyed by its points alone. A line's
    // corners round at a size on screen, so they change with the zoom where its
    // points do not — a line with no arrowhead keeps its points — and a cached
    // path would keep the rounding it was first drawn with.
    instance.renderer().path2dEnabled(false);
    instance.on("tap", "node", (event) => onNodeTap(event.target.id()));
    instance.on("tap", (event) => {
      if (event.target === instance) onBackgroundTap();
    });
    instance.on("mouseover", "edge", (event) => {
      event.target.addClass(HOVERED);
      hoverAlong(event.target, event.position);
    });
    instance.on("mouseout", "edge", clearHover);
    instance.on("mouseover", "node", (event) => hoverNode(event.target.id()));
    instance.on("mouseout", "node", () => hoverNode(null));
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
      shared = sharedLines(instance, drawn.paths);
      followed = followedOverlay(instance, containerRef.value, { tokens });
      map = canvasMap(instance, run.geometry, { fitZoom, onLevel: redraw });
      // Laid over the followed lines, so no line is drawn over a count.
      pills = pillOverlay(instance, containerRef.value, { tokens, map: () => map });
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
    if (cy.value && layout.value) fitCompounds(cy.value, layout.value.geometry, (id) => map?.reachOf(id) ?? null);
  }

  /** Whether an edge of the data file is shown by the filters: both its ends, and its contract. */
  function isShown(edge) {
    const { ids, contracts } = shown;
    if (!ids) return true;
    const contract = edge.data("contract");
    if (contracts && contract && !contracts.has(contract)) return false;
    return ids.has(edge.data("source")) && ids.has(edge.data("target"));
  }

  /** Mark what the filters hide, on what is drawn now: a loop's end with its box. */
  function markShown(instance) {
    const { ids, contracts } = shown;
    if (!ids) return;
    instance.nodes().forEach((node) => node.toggleClass("is-hidden", !ids.has(node.data(LOOP_BOX) ?? node.id())));
    instance.edges().forEach((edge) => {
      const contract = edge.data("contract");
      edge.toggleClass("is-hidden", Boolean(contracts && contract && !contracts.has(contract)));
    });
  }

  /** Draw the level wanted now, and mark the filters and the selection on it. */
  function redraw() {
    const instance = cy.value;
    if (!instance) return;
    instance.batch(() => {
      map?.apply();
      markShown(instance);
      markWalk(instance, marked);
      markFront(instance);
    });
    fitBoxes();
    refreshOverlay();
  }

  /** Draw the nodes in `ids` as themselves for `source`, from the next drawing on. */
  function reveal(source, ids) {
    map?.reveal(source, ids);
  }

  /** Draw the nodes in `ids` as themselves for `source`, now, and their outward edges unless `edges` is false. */
  function revealNow(source, ids, { edges = true } = {}) {
    reveal(source, ids);
    map?.expose(source, edges ? ids : []);
    redraw();
  }

  /**
   * Show only the nodes in `ids`. When `contracts` is a set of contract keys, an
   * edge that carries a contract outside it is hidden as well, because two
   * services that stay on the map can share a contract the filters leave out.
   * An aggregated edge carries only the edges shown.
   */
  function showOnly(ids, contracts = null) {
    shown = { ids, contracts };
    map?.setShown(isShown);
    redraw();
  }

  function markNode(node, selection, outside) {
    const id = node.id();
    const distance = selection.distances.get(id);
    if (distance === undefined) {
      if (!selection.keep.has(id)) node.addClass(outside);
      // A closed box that holds a node of the walk is part of what the selection frames.
      else if (node.hasClass(COLLAPSED)) node.addClass("holds-walk");
      return;
    }
    node.addClass("in-walk");
    const ring = selection.rings?.get(id);
    if (ring === undefined) return;
    node.addClass(`ring-${ring}`);
    node.data(DISTANCE_DATA, distance);
    if (selection.risks?.has(id)) node.addClass("is-risk");
  }

  /** Whether `edge` is one the walk took: an aggregated edge is when it carries one. */
  function walked(edge, selection) {
    if (!map?.isAggregate(edge)) return selection.edges.has(edge.data("key"));
    return map.keysOf(edge).some((key) => selection.edges.has(key));
  }

  /** Mark `selection` on what is drawn now, or clear its marks when it is null. */
  function markWalk(instance, selection) {
    instance.elements().removeClass(SELECTION_CLASSES.join(" "));
    instance.nodes().forEach((node) => {
      node.removeClass(node.classes().filter((name) => name.startsWith("ring-")));
      node.removeData(DISTANCE_DATA);
    });
    if (!selection) return;
    const outside = selection.hide ? "is-outside" : "is-dimmed";
    instance.nodes().not(`.${LOOP_END}`).forEach((node) => markNode(node, selection, outside));
    instance.edges().forEach((edge) => edge.addClass(walked(edge, selection) ? "is-walk-edge" : outside));
    const focus = instance.getElementById(selection.focus);
    if (focus.nonempty()) {
      focus.addClass("is-selected");
      focus.connectedEdges(".is-walk-edge").addClass("is-selected-edge");
    }
  }

  /**
   * Mark `selection` on the canvas, or clear the marks when it is null.
   *
   * `selection` is `{ focus, distances, edges, keep, hide, rings, risks, reveal }`:
   * the walk's nodes by distance and its edge keys; `keep`, the nodes that are
   * not outside (the walk and its containers); `hide`, whether what is outside
   * is hidden rather than dimmed; in impact mode, `rings` (id to ring) and
   * `risks` (the ids to mark); and `reveal`, the nodes the selection draws as
   * themselves with their own edges, opening the boxes that hold them and the
   * ones that are boxes. Every edge of the selected
   * node is drawn, whatever the map's budget.
   */
  function markSelection(selection) {
    marked = selection;
    map?.reveal("selection", selection?.reveal || []);
    map?.setExempt("selection", selection?.focus || null);
    map?.expose("selection", selection?.focus ? [selection.focus] : []);
    map?.setWalk(selection ? [...selection.edges] : null);
    redraw();
  }

  function resize() {
    cy.value?.resize();
    map?.evaluate();
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
    followed: () => followed?.followed() || { edges: [], passes: [] },
    labelled: () => followed?.labelled() || [],
    frames: () => followed?.frames() || { frames: [] },
    droppedHeads: () => shared?.droppedHeads() || [],
    pills: () => pills?.pills() || { pills: [], dropped: [] },
    tallies: () => pills?.tallies() || {},
    outward: () => pills?.outward() || {},
    map: () => map,
    mount,
    setStyle,
    reveal,
    revealNow,
    showOnly,
    markSelection,
    resize,
  };
}
