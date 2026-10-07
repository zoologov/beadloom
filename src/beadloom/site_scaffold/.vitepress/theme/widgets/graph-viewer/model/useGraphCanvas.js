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
import { idRecord } from "../../../shared/ids/index.js";
import { elkGraphOf, layOut, warmUpLayout } from "../../../shared/elk/index.js";
import { ALONG_HOVER, BEHIND, DISTANCE_DATA, HOVERED, IN_FRONT, SELECTION_CLASSES, setClass } from "./canvasMarks.js";
import { applyGeometry, fitCompounds, layoutInputOf } from "./canvasLayout.js";
import { canvasMap } from "./canvasMap.js";
import { followedOverlay } from "./followedOverlay.js";
import { pillOverlay } from "./pillOverlay.js";
import { sharedLines } from "./sharedLines.js";
import { COLLAPSED, LOOP_BOX, LOOP_END, endsOfLine } from "../lib/levels.js";
import { GEOMETRY } from "../lib/stylesheet.js";

/** The marks of an element a selection leaves as it is. */
const NO_MARKS = Object.freeze({ classes: Object.freeze([]) });

/** Cytoscape's layout that places nothing, run when the graph is created. */
const UNPLACED = Object.freeze({ name: "null" });

/**
 * `{ cy, ready, layingOut, layout, bundles, hoveredEdges, layoutError, followed,
 * labelled, frames, droppedHeads, pills, tallies, outward, map, mount, setStyle, reveal,
 * showOnly, markSelection, resize }` over the container in `containerRef`.
 *
 * `tokens()` gives the resolved theme tokens now, which the followed lines are
 * drawn in.
 * `fitZoom({ drawing })` gives the zoom of the whole-graph fit now, which the
 * map's levels are measured from, measured once per `drawing` the map names.
 * `reveal(source, ids)` draws the nodes in `ids` as themselves
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
  // Whether drawing what the pointer rests on is waiting (`hoverNode`).
  let pointerQueued = false;
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
  // and its outward edges, in front of the rest. A pointer that leaves one node
  // for another reports both in one event, the node it leaves and the one it
  // comes to: what it rests on is drawn once, when the event is over, and the
  // node it left is never drawn in between.
  function hoverNode(id) {
    pointed = id;
    if (pointerQueued) return;
    pointerQueued = true;
    queueMicrotask(drawPointer);
  }

  function drawPointer() {
    pointerQueued = false;
    const lifted = map?.setExempt("pointer", pointed);
    const exposed = map?.expose("pointer", pointed ? [pointed] : []);
    // The pointer adds or takes lines, never a node: every box keeps its size, and no box opens or closes.
    if (lifted || exposed) redraw({ boxes: false });
    else if (cy.value) {
      cy.value.batch(() => markFront(cy.value));
      followed?.refresh();
    }
  }

  /**
   * Bring the drawn lines of the node under the pointer in front of the rest,
   * and fade the rest; none for an open box. Only a line whose mark changes is
   * marked again: Cytoscape restyles every line it is told of, and a pointer that
   * leaves one node for another leaves the rest faded as they were.
   */
  function markFront(instance) {
    const node = pointed ? instance.getElementById(pointed) : null;
    const own = node && node.nonempty() && !node.isParent() ? node.connectedEdges().filter((edge) => edge.visible()) : instance.collection();
    const front = new Set(own.map((edge) => edge.id()));
    instance.edges().forEach((edge) => {
      const inFront = front.has(edge.id());
      setClass(edge, IN_FRONT, inFront);
      setClass(edge, BEHIND, front.size > 0 && !inFront);
    });
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

  /**
   * The zoom crossed a step of the map's scale and drew no other level: every
   * mark of the map is restyled at the new scale. Cytoscape restyles an element
   * when its style is next read, which would be in the next frame's drawing,
   * where the counts are placed at the new scale too: more than a frame's work.
   * Reading every element's style now restyles them in the frame that found the
   * step, and leaves the next frame the drawing alone.
   */
  function rescaled() {
    refreshOverlay();
    cy.value?.elements().forEach((element) => element.pstyle("display"));
  }

  function destroy() {
    ready.value = false;
    layingOut.value = false;
    layout.value = null;
    bundles.value = null;
    hoveredEdges.value = [];
    containerRef.value?.removeEventListener("mouseleave", clearHover);
    shared = null;
    pointerQueued = false;
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
      // Each box keeps the room its title is drawn in above its children.
      const run = await layOut(elkGraphOf({ ...layoutInputOf(instance), boxTop: GEOMETRY.boxTitleRoom }));
      if (mine !== generation) return false;
      const drawn = await applyGeometry(instance, run.geometry);
      if (mine !== generation) return false;
      shared = sharedLines(instance, drawn.paths, { scale: () => map?.scale() ?? 1 });
      followed = followedOverlay(instance, containerRef.value, { tokens });
      map = canvasMap(instance, run.geometry, { fitZoom, onLevel: redraw, onRescale: rescaled });
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
    instance.nodes().forEach((node) => setClass(node, "is-hidden", !ids.has(node.data(LOOP_BOX) ?? node.id())));
    instance.edges().forEach((edge) => {
      const contract = edge.data("contract");
      setClass(edge, "is-hidden", Boolean(contracts && contract && !contracts.has(contract)));
    });
  }

  /**
   * Draw the level wanted now, and mark the filters and the selection on it;
   * every box sized to ELK's again unless `boxes` is false, as for a change that
   * draws no node and hides none, which keeps the boxes open now open.
   */
  function redraw({ boxes = true } = {}) {
    const instance = cy.value;
    if (!instance) return;
    instance.batch(() => {
      map?.apply({ sameLevel: !boxes });
      markShown(instance);
      markWalk(instance, marked);
      markFront(instance);
    });
    if (boxes) fitBoxes();
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

  /** The marks `selection` gives `node`: `{ classes, distance }`, the classes among `SELECTION_CLASSES` and a ring's, and its distance in impact mode. */
  function marksOfNode(node, selection, outside) {
    const id = node.id();
    const distance = selection.distances.get(id);
    if (distance === undefined) {
      // What a selected box holds is what was selected: drawn as it is, nothing dimmed.
      if (selection.inside?.has(id)) return NO_MARKS;
      if (!selection.keep.has(id)) return { classes: [outside] };
      // A closed box that holds a node of the walk is part of what the selection frames.
      return node.hasClass(COLLAPSED) ? { classes: ["holds-walk"] } : NO_MARKS;
    }
    const ring = selection.rings?.get(id);
    if (ring === undefined) return { classes: ["in-walk"] };
    return { classes: ["in-walk", `ring-${ring}`, ...(selection.risks?.has(id) ? ["is-risk"] : [])], distance };
  }

  /** Whether `edge` is one the walk took: an aggregated edge is when it carries one. */
  function walked(edge, selection) {
    if (!map?.isAggregate(edge)) return selection.edges.has(edge.data("key"));
    return map.keysOf(edge).some((key) => selection.edges.has(key));
  }

  /** The marks `selection` gives what is drawn now: element id to `{ classes, distance }`; none for a null selection. */
  function marksOf(instance, selection) {
    const marks = new Map();
    if (!selection) return marks;
    const outside = selection.hide ? "is-outside" : "is-dimmed";
    instance.nodes().not(`.${LOOP_END}`).forEach((node) => marks.set(node.id(), marksOfNode(node, selection, outside)));
    // A line between two parts of a selected box, or from one onto a box that holds it, is drawn as it is,
    // as the box's contents are.
    const inside = (edge) => {
      if (!selection.inside) return false;
      const { source, target } = endsOfLine(edge);
      const kept = (id) => selection.inside.has(id) || Boolean(selection.holders?.has(id));
      return kept(source) && kept(target) && (selection.inside.has(source) || selection.inside.has(target));
    };
    instance.edges().forEach((edge) => {
      if (!inside(edge)) marks.set(edge.id(), { classes: [walked(edge, selection) ? "is-walk-edge" : outside] });
    });
    const focus = instance.getElementById(selection.focus);
    if (focus.nonempty()) {
      const own = marks.get(focus.id()) || NO_MARKS;
      marks.set(focus.id(), { ...own, classes: [...own.classes, "is-selected"] });
      focus.connectedEdges().forEach((edge) => {
        const line = marks.get(edge.id());
        if (line?.classes.includes("is-walk-edge")) marks.set(edge.id(), { classes: [...line.classes, "is-selected-edge"] });
      });
    }
    return marks;
  }

  /**
   * Mark `selection` on what is drawn now, or clear its marks when it is null,
   * changing only the marks that differ from what each element carries.
   */
  function markWalk(instance, selection) {
    const marks = marksOf(instance, selection);
    instance.elements().forEach((element) => {
      const { classes, distance } = marks.get(element.id()) || NO_MARKS;
      for (const name of SELECTION_CLASSES) setClass(element, name, classes.includes(name));
      if (!element.isNode()) return;
      for (const name of element.classes()) if (name.startsWith("ring-") && !classes.includes(name)) setClass(element, name, false);
      for (const name of classes) if (name.startsWith("ring-")) setClass(element, name, true);
      if (distance !== undefined && element.data(DISTANCE_DATA) !== distance) element.data(DISTANCE_DATA, distance);
      else if (distance === undefined && element.data(DISTANCE_DATA) !== undefined) element.removeData(DISTANCE_DATA);
    });
  }

  /**
   * Mark `selection` on the canvas, or clear the marks when it is null.
   *
   * `selection` is `{ focus, distances, edges, keep, hide, rings, risks, reveal,
   * box, inside }`: the walk's nodes by distance and its edge keys; `keep`, the
   * nodes that are not outside (the walk and its containers); `hide`, whether
   * what is outside is hidden rather than dimmed; in impact mode, `rings` (id to
   * ring) and `risks` (the ids to mark); `reveal`, the nodes the selection draws
   * as themselves with their own edges, opening the boxes that hold them and the
   * ones that are boxes; and when a box is selected, `box`, opened at any zoom,
   * `inside`, everything it holds and itself, drawn unmarked, and `holders`, the
   * boxes that hold it, a line onto which from inside is drawn unmarked too. Every edge of
   * the selected node is drawn, whatever the map's budget, on the lines the
   * pointer on it draws, and the lines of its walk say how many of the walk's
   * edges they carry.
   */
  function markSelection(selection) {
    marked = selection;
    map?.reveal("selection", selection?.reveal || []);
    map?.reveal("selected box", selection?.box ? [selection.box] : [], { anyZoom: true });
    map?.setExempt("selection", selection?.focus || null);
    map?.expose("selection", selection?.focus ? [selection.focus] : [], { openBoxes: true });
    map?.setWalk(selection ? [...selection.edges] : null, selection?.focus || null);
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
    tallies: () => pills?.tallies() || idRecord(),
    outward: () => pills?.outward() || idRecord(),
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
