// beadloom:component=site-graph-viewer
// The read-only test handle, `window.__beadloomViewer`, exposed under automation only.
//
// The browser tests assert state rather than pixels, and read it here: the
// visible node ids, the selection, node positions, the viewport, the colours
// Cytoscape resolved, each node's look — its fill, its border, its title and
// its status mark — and each line's — its weight, dash, colour, arrowheads and
// corners — and what a selection marked — the neighbourhood, the dimmed nodes,
// the impact rings and risks, and the impact summary the panel shows — and the
// layout: whether ELK ran for it or it was already laid out, and ELK's geometry,
// a box for every node and a route for every edge in the graph's coordinates —
// and the same drawn: each node's box and each edge's route as Cytoscape draws
// them — and the bundles: the routes with each node's fans bundled, the trunks
// and buses, and the edges along a hovered line — and the followed lines drawn
// on top, the passes they are drawn in and what each frame cost — and the map:
// the boxes open and closed, each aggregated edge with what it carries each way
// and whether the budget draws it, and the counts of hidden edges on the boxes.
//
// It does one thing besides reading: `revealNodes(ids)` draws the nodes in `ids`
// as themselves with their own edges, opening every box that holds one and each
// one that is a box, as a selection does for its own node. A reader opens boxes by zooming in, one region at a time; a case
// that reads the whole graph at full detail, or one level after another, opens
// them all at once with it. The handle exists only when `navigator.webdriver` is
// true, which a real reader's browser never reports, so the tested bundle and
// the deployed one are the same bundle.

import { idRecord } from "../../../shared/ids/index.js";
import { isLoop } from "./canvasLayout.js";
import { DISTANCE_DATA } from "./canvasMarks.js";
import { AGGREGATE, COLLAPSED, HIDDEN_EDGES } from "../lib/levels.js";
import { titleFits } from "../lib/mapMarks.js";

const HANDLE = "__beadloomViewer";

const idsOf = (collection) => collection.map((element) => element.id()).sort();

const COLOUR_PROPERTIES = {
  nodes: ["background-color", "border-color", "color"],
  edges: ["line-color", "target-arrow-color", "source-arrow-color"],
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

/** Whether `edge` is an aggregated edge of the map rather than an edge of the data file. */
const isAggregate = (edge) => Boolean(edge.data(AGGREGATE));

function drawnRouteOf(edge) {
  const corners = edge.segmentPoints();
  return {
    id: edge.id(),
    key: edge.data("key") ?? null,
    source: edge.source().id(),
    target: edge.target().id(),
    aggregated: isAggregate(edge),
    routed: Boolean(corners),
    loop: isLoop(edge),
    points: [edge.sourceEndpoint(), ...(corners || edge.controlPoints() || []), edge.targetEndpoint()].map(pointOf),
    label: pointOf(edge.midpoint()),
  };
}

/** An aggregated edge of the map as the handle reports it; its look only while it is drawn. */
function aggregateOf({ element, pair }, map) {
  const drawn = Boolean(element && element.inside() && !pair.hidden);
  const { forward, backward } = map.keysEachWay(pair);
  const route = drawn ? drawnRouteOf(element) : null;
  return {
    id: element ? element.id() : null,
    ends: [...pair.ends],
    forwardKeys: forward,
    backwardKeys: backward,
    members: [...pair.forward, ...pair.backward],
    weight: pair.weight,
    drawn,
    walk: drawn && element.hasClass("is-walk-edge"),
    label: drawn ? element.style("label") : null,
    sourceArrow: drawn ? element.style("source-arrow-shape") : null,
    targetArrow: drawn ? element.style("target-arrow-shape") : null,
    width: drawn ? parseFloat(element.style("width")) : null,
    fontSize: drawn ? parseFloat(element.style("font-size")) : null,
    routed: drawn && route.routed,
    points: route ? route.points : [],
  };
}

/** A number list of a style, as Cytoscape gives it in one string. */
const numbersOf = (value) => String(value).split(/\s+/).filter(Boolean).map(parseFloat);

/** An edge's look as the handle reports it (`lineLooks`). */
function lineLookOf(edge) {
  return {
    id: edge.id(),
    key: edge.data("key") ?? null,
    aggregated: isAggregate(edge),
    styleKey: edge.data("styleKey") ?? null,
    width: parseFloat(edge.style("width")),
    lineStyle: edge.style("line-style"),
    dash: edge.style("line-style") === "dashed" ? numbersOf(edge.style("line-dash-pattern")) : [],
    lineFill: edge.style("line-fill"),
    colour: edge.style("line-color"),
    sourceArrow: edge.style("source-arrow-shape"),
    targetArrow: edge.style("target-arrow-shape"),
    arrowScale: parseFloat(edge.style("arrow-scale")),
    arrowColour: edge.style("target-arrow-color"),
    cornerRadii: edge.data("route") ? numbersOf(edge.style("segment-radii")) : [],
    walk: edge.hasClass("is-walk-edge"),
    dimmed: edge.hasClass("is-dimmed"),
    points: drawnRouteOf(edge).points,
  };
}

/** A node's look as the handle reports it (`nodeLooks`). */
function nodeLookOf(node) {
  return {
    id: node.id(),
    parent: node.isChild() ? node.parent().id() : null,
    isParent: node.isParent(),
    collapsed: node.hasClass(COLLAPSED),
    status: node.data("status") || null,
    borderWidth: parseFloat(node.style("border-width")),
    borderColour: node.style("border-color"),
    borderStyle: node.style("border-style"),
    fill: node.style("background-color"),
    fillOpacity: parseFloat(node.style("background-opacity")),
    labelColour: node.style("color"),
    labelValign: node.style("text-valign"),
    labelMarginY: parseFloat(node.style("text-margin-y")),
    fontSize: parseFloat(node.style("font-size")),
    mark: String(node.style("background-image")),
  };
}

function readers(source) {
  const cy = () => source.cy();
  const rect = () => source.container().getBoundingClientRect();
  const originals = () => cy().edges().filter((edge) => !isAggregate(edge));
  return {
    ready: () => Boolean(cy()) && source.ready(),
    visibleIds: () => cy().nodes().filter((node) => node.visible()).map((node) => node.id()).sort(),
    selection: () => source.selection() || null,
    state: () => ({ ...source.state() }),
    // Every node's position, whether it is drawn or inside a closed box, which
    // keeps it where it was: no level moves a node.
    positions: () =>
      idRecord((source.map()?.allNodes() || cy().nodes()).map((node) => [node.id(), { ...node.position() }])),
    pan: () => ({ ...cy().pan() }),
    zoom: () => cy().zoom(),
    boxes: () => {
      const r = rect();
      return idRecord(
        cy().nodes().map((node) => [
          node.id(),
          { ...pageBox(node, r), isParent: node.isParent(), parent: node.parent().nonempty() ? node.parent().id() : null },
        ])
      );
    },
    // Each node's box as drawn, in the graph's coordinates: its shape and its
    // border, without its label or Cytoscape's margin for antialiasing.
    nodeBoxes: () => idRecord(cy().nodes().map((node) => [node.id(), drawnBoxOf(node)])),
    colours: () => colourEntries(cy()),
    neighbourhood: () => ({
      ids: idsOf(cy().nodes(".in-walk")),
      edges: [...new Set(originals().filter(".is-walk-edge").map((edge) => edge.data("key")))].sort(),
    }),
    dimmedIds: () => idsOf(cy().nodes(".is-dimmed")),
    rings: () =>
      idRecord(
        cy()
          .nodes()
          .filter((node) => node.data(DISTANCE_DATA) !== undefined)
          .map((node) => [node.id(), node.data(DISTANCE_DATA)])
      ),
    riskIds: () => idsOf(cy().nodes(".is-risk")),
    // Each node drawn with a status, the status, the border it is drawn with and its corner mark.
    statusLooks: () =>
      idRecord(
        cy()
          .nodes()
          .filter((node) => Boolean(node.data("status")))
          .map((node) => [
            node.id(),
            {
              status: node.data("status"),
              borderColour: node.style("border-color"),
              borderStyle: node.style("border-style"),
              mark: String(node.style("background-image")),
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
    // Each drawn edge as Cytoscape draws it: `{ id, key, source, target,
    // aggregated, routed, loop, points, label }`. `key` names an edge of the data
    // file as a walk names it, and is null for an edge of the map's, which
    // `aggregated` marks. A routed edge follows a route of corners, and `points`
    // are its ends and corners; any other edge is a curve, and `points` are its
    // ends and control points. `loop` says the edge joins a node to itself or to
    // a box that holds it; `label` is where its label sits. Graph coordinates.
    edgeRoutes: () => cy().edges().filter((edge) => edge.visible()).map(drawnRouteOf),
    // The boxes drawn open, by id.
    openBoxes: () => source.map()?.openBoxes() || [],
    // The level drawn: `{ fitZoom, zoom, scale, extent, open, collapsed }`: the
    // whole-graph fit's zoom the levels are measured from, the zoom, the map's
    // scale, the graph's area on screen, the open boxes, and each closed box
    // `{ id, label, fontSize, outside }`, `outside` when its title is drawn
    // outside it because the box is too small for it.
    level: () => {
      const map = source.map();
      if (!map) return null;
      const collapsed = map.collapsedBoxes().map((node) => ({
        id: node.id(),
        label: node.style("label"),
        fontSize: parseFloat(node.style("font-size")),
        outside: !titleFits(node),
      }));
      return {
        fitZoom: map.fitZoom(),
        zoom: cy().zoom(),
        scale: map.scale(),
        extent: { ...cy().extent() },
        open: map.openBoxes(),
        collapsed: collapsed.sort((a, b) => a.id.localeCompare(b.id)),
      };
    },
    // Every aggregated edge of the level drawn: `{ id, ends, forwardKeys,
    // backwardKeys, members, weight, drawn, walk, label, sourceArrow, targetArrow,
    // width, fontSize, routed, points }`. `ends` are its two drawn ends in sorted
    // order and the keys are the edges it carries from the first to the second and
    // back; `members` their ids; `drawn` false when the budget leaves it out; `walk`
    // when a selection's walk takes one of its edges. Its look and its route, in
    // graph coordinates, only while it is drawn.
    aggregatedEdges: () => {
      const map = source.map();
      if (!map) return [];
      return map
        .aggregates()
        .map((entry) => aggregateOf(entry, map))
        .sort((a, b) => a.ends.join("|").localeCompare(b.ends.join("|")));
    },
    // Each drawn node whose aggregated edges the budget leaves out: `{ id: { count, label } }`.
    hiddenEdgeCounts: () =>
      idRecord(
        cy()
          .nodes()
          .filter((node) => node.data(HIDDEN_EDGES) > 0)
          .map((node) => [node.id(), { count: node.data(HIDDEN_EDGES), label: node.style("label") }])
      ),
    // The handle's one action: draw the nodes in `ids` as themselves, opening every
    // box that holds one and each one that is a box, until it is called again;
    // `[]` lets them close.
    revealNodes: (ids) => source.revealNodes(ids),
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
    // The lines drawn on top now, followed under the pointer or on a selection's
    // walk: `{ edges, passes }`, each line `{ id, colour, casing, width }` — its
    // colour, the colour of the casing it is drawn over and its width in layout
    // units — and each pass of a frame in order, `{ name, edges }`, with the ids
    // it draws. Empty when nothing is followed.
    followed: () => JSON.parse(JSON.stringify(source.followed())),
    // What drawing the layer over the canvas cost, at Cytoscape's every drawing:
    // `{ frames }`, each recent frame `{ at, ms, drawn }`, when it was drawn
    // (`performance.now()`), how long it took and how many lines it drew.
    frames: () => JSON.parse(JSON.stringify(source.frames())),
    // The line ends that draw no arrowhead because another line on their last
    // run draws it: `[{ id, end }]`, `end` "source" or "target".
    droppedHeads: () => JSON.parse(JSON.stringify(source.droppedHeads())),
    // The ids of the edges drawn along the line under the pointer.
    hoveredEdges: () => [...source.hoveredEdges()].sort(),
    drawnEdgeKinds: () => [...new Set(originals().flatMap((edge) => [edge.data("kind"), edge.data("styleKey")]))].sort(),
    edgeStyle: (key) => {
      const edge = originals().filter((e) => e.data("styleKey") === key)[0];
      if (!edge) return null;
      return { lineStyle: edge.style("line-style"), width: parseFloat(edge.style("width")), colour: edge.style("line-color") };
    },
    // Every edge of the data file drawn now, and its look: its arrow ends, its
    // colour, and whether it is shown and how opaque. What a selection leaves
    // out is here. An aggregated edge is not an edge of the file
    // (`aggregatedEdges`); every drawn line's whole look is `lineLooks`.
    edgeLooks: () =>
      originals()
        .map((edge) => ({
          key: edge.data("key"),
          styleKey: edge.data("styleKey"),
          sourceArrow: edge.style("source-arrow-shape"),
          targetArrow: edge.style("target-arrow-shape"),
          lineColour: edge.style("line-color"),
          visible: edge.visible(),
          opacity: parseFloat(edge.style("opacity")),
        }))
        .sort((a, b) => String(a.key).localeCompare(String(b.key))),
    // Every edge drawn now, of the data file or of the map, and its look as
    // Cytoscape resolved it: `{ id, key, aggregated, styleKey, width, lineStyle,
    // dash, lineFill, colour, sourceArrow, targetArrow, arrowScale, arrowColour,
    // cornerRadii, walk, dimmed, points }`. Sizes are in layout units; `dash` is
    // the dash pattern a dashed line is drawn with, `cornerRadii` the radius of
    // each corner of a routed edge, and `points` its route as drawn (`edgeRoutes`).
    lineLooks: () => cy().edges().filter((edge) => edge.visible()).map(lineLookOf),
    // Every node drawn now and its look: `{ id, parent, isParent, collapsed,
    // status, borderWidth, borderColour, borderStyle, fill, fillOpacity,
    // labelColour, labelValign, labelMarginY, fontSize, mark }`, `mark` the
    // corner image a status is drawn with, or "none".
    nodeLooks: () => cy().nodes().filter((node) => node.visible()).map(nodeLookOf),
    // The canvases the viewer draws over Cytoscape's, by name, in the order they lie on the page.
    overlayLayers: () => [...source.container().querySelectorAll("canvas[data-layer]")].map((canvas) => canvas.dataset.layer),
    // The edges whose label is drawn: a count or a badge Cytoscape draws, and the
    // label of the line under the pointer, drawn on top (`followed`).
    shownEdgeLabels: () =>
      [...new Set([...cy().edges().filter((edge) => Boolean(edge.style("label"))).map((edge) => edge.id()), ...source.labelled()])].sort(),
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
 * routes with the fans bundled, `followed()`, `labelled()` and `frames()`, the
 * lines drawn on top, the ones labelled and what drawing them cost,
 * `droppedHeads()`, the ends that leave their arrowhead to another,
 * `hoveredEdges()`, the ids of the edges along the line under the pointer,
 * `map()`, the map drawn now (`canvasMap.js`), and `revealNodes(ids)`, which draws
 * the nodes in `ids` as themselves.
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
