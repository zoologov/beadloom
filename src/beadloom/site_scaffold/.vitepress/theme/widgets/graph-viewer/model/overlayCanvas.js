// beadloom:component=site-graph-viewer
// A canvas over Cytoscape's, for what the viewer draws on top of the graph in the graph's coordinates.
//
// What Cytoscape cannot draw itself — a followed line on top of everything it
// crosses, every casing under every line (`followedOverlay.js`) — is drawn on a
// canvas of its own, laid over the container, that takes no pointer event, so it
// never takes one from the graph. Its owner draws on it whenever Cytoscape renders; `begin`
// sizes it to the container at the screen's pixel ratio and wipes what it last
// drew. A canvas left empty since it was last wiped is not wiped again, so an
// overlay with nothing to show costs no fill per frame.

/**
 * A canvas laid over `container`, named `layer`: `{ begin, inGraph, drew, remove }`.
 *
 * `begin()` readies it for a frame and returns its 2D context; `inGraph(cy)` sets
 * that context to draw in `cy`'s graph coordinates; `drew()` notes that the frame
 * left something on it; `remove()` takes it out of the page.
 */
export function overlayCanvas(container, layer) {
  const canvas = document.createElement("canvas");
  Object.assign(canvas.style, {
    position: "absolute",
    top: "0",
    left: "0",
    zIndex: "1",
    pointerEvents: "none",
  });
  canvas.dataset.layer = layer;
  container.appendChild(canvas);
  const context = canvas.getContext("2d");
  let marked = false;

  function begin() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    const ratio = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      // Resizing a canvas wipes it.
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      marked = false;
    }
    context.setTransform(1, 0, 0, 1, 0, 0);
    if (marked) context.clearRect(0, 0, canvas.width, canvas.height);
    marked = false;
    return context;
  }

  function inGraph(cy) {
    const ratio = window.devicePixelRatio || 1;
    const zoom = cy.zoom();
    const pan = cy.pan();
    context.setTransform(ratio * zoom, 0, 0, ratio * zoom, ratio * pan.x, ratio * pan.y);
    return context;
  }

  return {
    begin,
    inGraph,
    drew() {
      marked = true;
    },
    remove() {
      canvas.remove();
    },
  };
}
