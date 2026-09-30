// beadloom:component=site-graph-viewer
// The Cytoscape instance behind the viewer's canvas, and what the viewer does to it.
//
// It creates the graph, lays it out, reports taps, labels a hovered edge, shows
// only a set of node ids, marks the selected node and its edges, and swaps the
// stylesheet when the theme changes. It decides nothing about which nodes are
// visible or selected: the viewer's state does.

import { onBeforeUnmount, ref, shallowRef } from "vue";
import { LAYERED_LAYOUT, loadCytoscape } from "../../../shared/cytoscape/index.js";

function runLayout(cy) {
  return new Promise((resolve) => {
    const layout = cy.layout(LAYERED_LAYOUT);
    layout.one("layoutstop", resolve);
    layout.run();
  });
}

/** `{ cy, ready, mount, setStyle, showOnly, highlight, resize }` over the container in `containerRef`. */
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

  function showOnly(ids) {
    cy.value?.batch(() => {
      cy.value.nodes().forEach((node) => node.toggleClass("is-hidden", !ids.has(node.id())));
    });
  }

  function highlight(id) {
    const instance = cy.value;
    if (!instance) return;
    instance.batch(() => {
      instance.elements().removeClass("is-selected is-selected-edge");
      const node = id ? instance.getElementById(id) : null;
      if (node?.nonempty()) {
        node.addClass("is-selected");
        node.connectedEdges().addClass("is-selected-edge");
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

  return { cy, ready, mount, setStyle, showOnly, highlight, resize };
}
