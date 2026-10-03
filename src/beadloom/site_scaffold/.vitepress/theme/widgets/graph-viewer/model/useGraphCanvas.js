// beadloom:component=site-graph-viewer
// The Cytoscape instance behind the viewer's canvas, and what the viewer does to it.
//
// It creates the graph, lays it out, reports taps, labels a hovered edge, shows
// only a set of node ids (and of contracts), marks a selection — the selected node, the nodes and
// edges its walk reached, their distance rings and risks, and what lies outside
// — and swaps the stylesheet when the theme changes. It decides nothing about
// which nodes are visible or selected: the viewer's state does.

import { onBeforeUnmount, ref, shallowRef } from "vue";
import { LAYERED_LAYOUT, loadCytoscape } from "../../../shared/cytoscape/index.js";

function runLayout(cy) {
  return new Promise((resolve) => {
    const layout = cy.layout(LAYERED_LAYOUT);
    layout.one("layoutstop", resolve);
    layout.run();
  });
}

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

/** The node data the impact mode sets: the node's distance from the selection. */
export const DISTANCE_DATA = "impactDistance";

/** `{ cy, ready, mount, setStyle, showOnly, markSelection, resize }` over the container in `containerRef`. */
export function useGraphCanvas(containerRef, { options, onNodeTap, onBackgroundTap }) {
  const cy = shallowRef(null);
  const ready = ref(false);
  let generation = 0;

  // Cytoscape reports no `mouseout` when the pointer leaves the canvas from an
  // edge, so a hovered label would stay; leaving the container clears it.
  function clearHover() {
    cy.value?.edges(".is-hovered").removeClass("is-hovered");
  }

  function destroy() {
    ready.value = false;
    containerRef.value?.removeEventListener("mouseleave", clearHover);
    cy.value?.destroy();
    cy.value = null;
  }

  async function mount(elements, style) {
    const mine = ++generation;
    const cytoscape = await loadCytoscape();
    if (mine !== generation || !containerRef.value) return false;
    destroy();
    const instance = cytoscape({ container: containerRef.value, elements, style, ...options });
    instance.on("tap", "node", (event) => onNodeTap(event.target.id()));
    instance.on("tap", (event) => {
      if (event.target === instance) onBackgroundTap();
    });
    instance.on("mouseover", "edge", (event) => event.target.addClass("is-hovered"));
    instance.on("mouseout", "edge", (event) => event.target.removeClass("is-hovered"));
    containerRef.value.addEventListener("mouseleave", clearHover);
    cy.value = instance;
    await runLayout(instance);
    if (mine !== generation) return false;
    ready.value = true;
    return true;
  }

  function setStyle(style) {
    cy.value?.style(style);
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
  }

  function resize() {
    cy.value?.resize();
  }

  onBeforeUnmount(() => {
    generation += 1;
    destroy();
  });

  return { cy, ready, mount, setStyle, showOnly, markSelection, resize };
}
