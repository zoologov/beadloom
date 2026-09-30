// beadloom:component=site-graph-viewer
// The read-only test handle, `window.__beadloomViewer`, exposed under automation only.
//
// The browser tests assert state rather than pixels, and read it here: the
// visible node ids, the selection, node positions, the viewport, the colours
// Cytoscape resolved, and the edge styles it drew. The handle exists only when
// `navigator.webdriver` is true, which a real reader's browser never reports,
// so the tested bundle and the deployed one are the same bundle.

const HANDLE = "__beadloomViewer";

const COLOUR_PROPERTIES = {
  nodes: ["background-color", "border-color", "color"],
  edges: ["line-color", "target-arrow-color", "line-gradient-stop-colors"],
};

function pageBox(element, rect) {
  const box = element.renderedBoundingBox({ includeLabels: false, includeOverlays: false });
  return { x1: rect.left + box.x1, y1: rect.top + box.y1, x2: rect.left + box.x2, y2: rect.top + box.y2 };
}

function colourEntries(cy) {
  const entries = [];
  for (const group of ["nodes", "edges"]) {
    cy[group]().forEach((element) => {
      for (const property of COLOUR_PROPERTIES[group]) {
        for (const value of String(element.style(property)).split(/\s+(?=rgb|#|hsl)/)) {
          entries.push({ element: element.id(), property, value });
        }
      }
    });
  }
  return entries;
}

function readers(source) {
  const cy = () => source.cy();
  const rect = () => source.container().getBoundingClientRect();
  return {
    ready: () => Boolean(cy()) && source.ready(),
    visibleIds: () => cy().nodes().filter((node) => node.visible()).map((node) => node.id()).sort(),
    selection: () => source.selection() || null,
    state: () => ({ ...source.state() }),
    arranging: () => source.arranging(),
    positions: () => Object.fromEntries(cy().nodes().map((node) => [node.id(), { ...node.position() }])),
    pan: () => ({ ...cy().pan() }),
    zoom: () => cy().zoom(),
    boxes: () => {
      const r = rect();
      return Object.fromEntries(
        cy().nodes().map((node) => [
          node.id(),
          { ...pageBox(node, r), isParent: node.isParent(), parent: node.parent().nonempty() ? node.parent().id() : null },
        ])
      );
    },
    colours: () => colourEntries(cy()),
    drawnEdgeKinds: () => [...new Set(cy().edges().flatMap((edge) => [edge.data("kind"), edge.data("styleKey")]))].sort(),
    edgeStyle: (key) => {
      const edge = cy().edges().filter((e) => e.data("styleKey") === key)[0];
      if (!edge) return null;
      return { lineStyle: edge.style("line-style"), width: parseFloat(edge.style("width")), colour: edge.style("line-color") };
    },
    shownEdgeLabels: () => cy().edges().filter((edge) => Boolean(edge.style("label"))).map((edge) => edge.id()),
    edgeMidpoint: () => {
      const r = rect();
      const leaves = cy().nodes().filter((node) => !node.isParent() && node.visible()).map((node) => pageBox(node, r));
      const clear = ({ x, y }) =>
        x > r.left + 10 && x < r.right - 10 && y > r.top + 10 && y < r.bottom - 10 &&
        !leaves.some((b) => x >= b.x1 - 12 && x <= b.x2 + 12 && y >= b.y1 - 12 && y <= b.y2 + 12);
      const candidates = cy()
        .edges()
        .filter((edge) => edge.visible())
        .map((edge) => {
          const m = edge.renderedMidpoint();
          const s = edge.renderedSourceEndpoint();
          const t = edge.renderedTargetEndpoint();
          return { id: edge.id(), point: { x: r.left + m.x, y: r.top + m.y }, length: Math.hypot(t.x - s.x, t.y - s.y) };
        })
        .filter((candidate) => clear(candidate.point))
        .sort((a, b) => b.length - a.length);
      return candidates.length ? [candidates[0].id, candidates[0].point] : null;
    },
  };
}

/**
 * Expose the handle over `source` when the browser is automated; return its disposer.
 *
 * `source` gives `cy()`, `container()`, `ready()`, `selection()`, `state()`
 * and `arranging()`.
 */
export function exposeTestHandle(source) {
  if (typeof window === "undefined" || navigator.webdriver !== true) return () => {};
  Object.defineProperty(window, HANDLE, {
    value: Object.freeze(readers(source)),
    configurable: true,
    enumerable: false,
    writable: false,
  });
  return () => {
    delete window[HANDLE];
  };
}
