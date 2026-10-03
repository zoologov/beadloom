// beadloom:component=site-graph-viewer
// The read-only test handle, `window.__beadloomViewer`, exposed under automation only.
//
// The browser tests assert state rather than pixels, and read it here: the
// visible node ids, the selection, node positions, the viewport, the colours
// Cytoscape resolved, each node's status and its border, the edge styles it drew — each edge's arrows, the colours
// along its line and its opacity — and what a selection marked —
// the neighbourhood, the dimmed nodes, the impact rings and risks, and the
// impact summary the panel shows — and the layout: whether ELK ran for it or it
// was already laid out, and ELK's geometry, a box for every node and a route for
// every edge in the graph's coordinates — and the same drawn: each node's box
// and each edge's route as Cytoscape draws them — and the bundles: the routes
// with each node's fans bundled, the trunks and buses, the junction dots for the
// edges drawn now, and the edges along a hovered line. The handle exists only when
// `navigator.webdriver` is true, which a real reader's browser never reports,
// so the tested bundle and the deployed one are the same bundle.

import { isLoop } from "./canvasLayout.js";
import { DISTANCE_DATA } from "./useGraphCanvas.js";

const HANDLE = "__beadloomViewer";

const idsOf = (collection) => collection.map((element) => element.id()).sort();

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

const pointOf = ({ x, y }) => ({ x, y });

function drawnBoxOf(node) {
  const { x, y } = node.position();
  const halfWidth = node.outerWidth() / 2;
  const halfHeight = node.outerHeight() / 2;
  return { x1: x - halfWidth, y1: y - halfHeight, x2: x + halfWidth, y2: y + halfHeight };
}

function drawnRouteOf(edge) {
  const corners = edge.segmentPoints();
  return {
    id: edge.id(),
    source: edge.source().id(),
    target: edge.target().id(),
    routed: Boolean(corners),
    loop: isLoop(edge),
    points: [edge.sourceEndpoint(), ...(corners || edge.controlPoints() || []), edge.targetEndpoint()].map(pointOf),
    label: pointOf(edge.midpoint()),
  };
}

function readers(source) {
  const cy = () => source.cy();
  const rect = () => source.container().getBoundingClientRect();
  return {
    ready: () => Boolean(cy()) && source.ready(),
    visibleIds: () => cy().nodes().filter((node) => node.visible()).map((node) => node.id()).sort(),
    selection: () => source.selection() || null,
    state: () => ({ ...source.state() }),
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
    // Each node's box as drawn, in the graph's coordinates: its shape and its
    // border, without its label or Cytoscape's margin for antialiasing.
    nodeBoxes: () => Object.fromEntries(cy().nodes().map((node) => [node.id(), drawnBoxOf(node)])),
    colours: () => colourEntries(cy()),
    neighbourhood: () => ({
      ids: idsOf(cy().nodes(".in-walk")),
      edges: [...new Set(cy().edges(".is-walk-edge").map((edge) => edge.data("key")))].sort(),
    }),
    dimmedIds: () => idsOf(cy().nodes(".is-dimmed")),
    rings: () =>
      Object.fromEntries(
        cy()
          .nodes()
          .filter((node) => node.data(DISTANCE_DATA) !== undefined)
          .map((node) => [node.id(), node.data(DISTANCE_DATA)])
      ),
    riskIds: () => idsOf(cy().nodes(".is-risk")),
    // Each node drawn with a status, the status and the border it is drawn with.
    statusLooks: () =>
      Object.fromEntries(
        cy()
          .nodes()
          .filter((node) => Boolean(node.data("status")))
          .map((node) => [
            node.id(),
            {
              status: node.data("status"),
              borderColour: node.style("border-color"),
              borderStyle: node.style("border-style"),
            },
          ])
      ),
    impactSummary: () => {
      const summary = source.impactSummary();
      return summary ? JSON.parse(JSON.stringify(summary)) : null;
    },
    // How the drawn layout was had: `{ source, ms }`, "worker" when ELK ran for
    // this viewer and "cache" when the page had laid the same graph out already.
    layoutRun: () => {
      const run = source.layout();
      return run ? { source: run.source, ms: run.ms } : null;
    },
    // ELK's geometry: `{ boxes, routes }`, each box `{ x1, y1, x2, y2 }` and each
    // route `{ source, target, sections }`, a section a list of `{ x, y }` points.
    elkGeometry: () => {
      const run = source.layout();
      return run ? JSON.parse(JSON.stringify(run.geometry)) : null;
    },
    // Each drawn edge as Cytoscape draws it: `{ id, source, target, routed, loop,
    // points, label }`. A routed edge follows a route of corners, and `points` are
    // its ends and corners; any other edge is a curve, and `points` are its ends
    // and control points. `loop` says the edge joins a node to itself or to a box
    // that holds it; `label` is where its label sits. Graph coordinates.
    edgeRoutes: () => cy().edges().filter((edge) => edge.visible()).map(drawnRouteOf),
    // The routes with each node's fans bundled: `{ ms, routes, trunks, buses }`.
    // `routes` maps each routed edge's id to its polyline, graph coordinates;
    // a trunk is `{ node, box, direction, side, members }`, a bus `{ node, side,
    // direction, channel, members }`; `ms` is how long the bundling took.
    bundles: () => {
      const bundles = source.bundles();
      if (!bundles) return null;
      const { ms, paths: routes, trunks, buses } = bundles;
      return JSON.parse(JSON.stringify({ ms, routes, trunks, buses }));
    },
    // The junction dots drawn now, `[{ x, y, edges }]`: where the routes of the
    // edges drawn part, and which edges part there.
    junctions: () => source.junctions(),
    // The ids of the edges drawn along the line under the pointer.
    hoveredEdges: () => [...source.hoveredEdges()].sort(),
    drawnEdgeKinds: () => [...new Set(cy().edges().flatMap((edge) => [edge.data("kind"), edge.data("styleKey")]))].sort(),
    edgeStyle: (key) => {
      const edge = cy().edges().filter((e) => e.data("styleKey") === key)[0];
      if (!edge) return null;
      return { lineStyle: edge.style("line-style"), width: parseFloat(edge.style("width")), colour: edge.style("line-color") };
    },
    // Every edge's look as drawn: its arrow ends, the colours along its line
    // from the source end to the target end, and whether it is shown and how
    // opaque. How direction reads, and what a selection leaves out, are here.
    edgeLooks: () =>
      cy()
        .edges()
        .map((edge) => ({
          key: edge.data("key"),
          styleKey: edge.data("styleKey"),
          sourceArrow: edge.style("source-arrow-shape"),
          targetArrow: edge.style("target-arrow-shape"),
          lineColour: edge.style("line-color"),
          stops: String(edge.style("line-gradient-stop-colors")).split(/\s+(?=rgb|#|hsl)/),
          visible: edge.visible(),
          opacity: parseFloat(edge.style("opacity")),
        }))
        .sort((a, b) => String(a.key).localeCompare(String(b.key))),
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
 * `source` gives `cy()`, `container()`, `ready()`, `selection()`, `state()`,
 * `impactSummary()`, `layout()`, the canvas's last layout run, `bundles()`, its
 * routes with the fans bundled, `junctions()`, the dots drawn now, and
 * `hoveredEdges()`, the ids of the edges along the line under the pointer.
 * The handle is the last viewer's to install it, and the disposer removes it only
 * while it is still this one's, so a viewer that leaves the page does not take a
 * live neighbour's handle along.
 */
export function exposeTestHandle(source) {
  if (typeof window === "undefined" || navigator.webdriver !== true) return () => {};
  const handle = Object.freeze(readers(source));
  Object.defineProperty(window, HANDLE, {
    value: handle,
    configurable: true,
    enumerable: false,
    writable: false,
  });
  return () => {
    if (window[HANDLE] === handle) delete window[HANDLE];
  };
}
