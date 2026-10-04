// beadloom:component=site-graph-viewer
// The canvas's side of the ELK layout: what it hands ELK, and how it draws what ELK gives back.
//
// ELK is told what Cytoscape would draw, and nothing about the canvas it is drawn
// on: each node's place in the containment tree and the size Cytoscape gives it,
// and each edge's ends. So one data file gives one layout, which the
// architecture page, a node page and full screen share whatever their shape.
//
// The answer is drawn as ELK computed it. Every leaf stands at the centre of its
// ELK box, through a `preset` layout; every compound is sized to its ELK box; and
// every edge follows its ELK route with its node's fans bundled (`lib/bundles.js`),
// its ends and corners given relative to the centres of its nodes
// (`lib/routes.js`). An edge into a box that holds its other end is the
// exception: Cytoscape always draws it as a loop inside the box.
//
// The bundling reads one layout and the graph it was computed for, and is kept
// beside that layout: a node page or full screen that draws the same layout
// draws the same bundles without computing them again.

import { bundleRoutes } from "../lib/bundles.js";
import { centreOf, compoundSizeOf, pathOf, segmentsOf } from "../lib/routes.js";

/** Node sizes as Cytoscape lays them out: the shape, without the label. */
const LAYOUT_DIMENSIONS = Object.freeze({ nodeDimensionsIncludeLabels: false });

/** What ELK needs of the canvas `cy` (`shared/elk`, `elkGraphOf`). */
export function layoutInputOf(cy) {
  const nodes = cy.nodes().map((node) => {
    const { w, h } = node.layoutDimensions(LAYOUT_DIMENSIONS);
    return {
      id: node.id(),
      parent: node.isChild() ? node.parent().id() : null,
      width: w,
      height: h,
      partition: node.data("partition"),
    };
  });
  const edges = cy.edges().map((edge) => ({
    id: edge.id(),
    source: edge.data("source"),
    target: edge.data("target"),
  }));
  return { nodes, edges };
}

/** Place every leaf of `cy` at the centre of its box in `geometry`; resolves when it is placed. */
function placeLeaves(cy, geometry) {
  const centre = (node) => {
    const box = geometry.boxes[node.id()];
    return box ? centreOf(box) : undefined;
  };
  return new Promise((resolve) => {
    const layout = cy.layout({
      name: "preset",
      positions: centre,
      eles: cy.nodes().filter((node) => !node.isParent()),
      fit: false,
      animate: false,
    });
    layout.one("layoutstop", resolve);
    layout.run();
  });
}

/** How far inside its drawn edge a compound's children area begins: its padding and half its border. */
function insetOf(compound) {
  return compound.pstyle("padding").pfValue + compound.pstyle("border-width").pfValue / 2;
}

/** Whether Cytoscape draws `edge` as a loop: it joins a node to itself or to a box that holds it. */
export function isLoop(edge) {
  const source = edge.source();
  const target = edge.target();
  return source.same(target) || source.ancestors().contains(target) || target.ancestors().contains(source);
}

/** The box Cytoscape draws `compound`'s children in, the way it measures them to size it; null when none is drawn. */
function childrenBoxOf(compound) {
  const box = compound.children().boundingBox({ includeLabels: false, includeOverlays: false, useCache: false });
  return box.w > 0 && box.h > 0 ? box : null;
}

/**
 * Size every compound of `cy` to its box in `geometry`, around the children it
 * draws now; call it again whenever a filter or a selection shows or hides a
 * node.
 *
 * Cytoscape computes a compound's box from the children it draws: a box with
 * half of its children hidden would move towards the other half, and one with
 * none would keep its place but take its stylesheet size. So each compound is
 * given ELK's room around the children it draws, measured as Cytoscape measures
 * them, and its box is computed again at once. The deepest boxes go first,
 * since a box's children include the boxes inside it, and each box's place is
 * fixed before all of its children can be hidden.
 */
export function fitCompounds(cy, geometry) {
  cy.nodes()
    .filter((node) => node.isParent() && geometry.boxes[node.id()])
    .sort((a, b) => b.ancestors().length - a.ancestors().length)
    .forEach((compound) => {
      const box = geometry.boxes[compound.id()];
      compound.data("box", compoundSizeOf(box, childrenBoxOf(compound), insetOf(compound)));
      compound.updateCompoundBounds(true);
    });
}

/** The bundles computed for each layout: one layout is one graph's, and its bundles are too. */
const bundlesByLayout = new WeakMap();

/**
 * What the bundling reads of `cy` and `geometry`: every node's container, the
 * edges drawn along a route, and the edges drawn as loops, which a node's degree
 * counts and nothing reroutes.
 */
function drawingOf(cy, geometry) {
  const nodes = cy.nodes().map((node) => ({ id: node.id(), parent: node.isChild() ? node.parent().id() : null }));
  const laidOut = cy.edges().filter((edge) => geometry.routes[edge.id()]);
  const ends = (edge) => ({ id: edge.id(), source: edge.source().id(), target: edge.target().id() });
  const edges = laidOut.filter((edge) => !isLoop(edge)).map(ends);
  const loops = laidOut.filter(isLoop).map(ends);
  const paths = Object.fromEntries(edges.map(({ id }) => [id, pathOf(geometry.routes[id])]));
  return { nodes, edges, loops, boxes: geometry.boxes, paths };
}

/**
 * The routes of `cy` with its fans bundled from `geometry`'s (`lib/bundles.js`):
 * `{ paths, trunks, buses, ms }`, `ms` the time the bundling took when it ran.
 */
function bundlesOf(cy, geometry) {
  if (!bundlesByLayout.has(geometry)) {
    const started = performance.now();
    const bundles = bundleRoutes(drawingOf(cy, geometry));
    bundlesByLayout.set(geometry, Object.freeze({ ...bundles, ms: performance.now() - started }));
  }
  return bundlesByLayout.get(geometry);
}

/** Draw every edge of `cy` but a loop along its route in `paths`, between the boxes of `geometry`. */
function routeEdges(cy, geometry, paths) {
  cy.batch(() => {
    cy.edges().forEach((edge) => {
      const path = paths[edge.id()];
      const sourceBox = geometry.boxes[edge.source().id()];
      const targetBox = geometry.boxes[edge.target().id()];
      if (!path || !sourceBox || !targetBox) return;
      const segments = segmentsOf(path, centreOf(sourceBox), centreOf(targetBox));
      if (segments) edge.data("route", segments);
    });
  });
}

/**
 * Draw `cy` as `geometry` lays it out: leaves placed, compounds sized, edges
 * routed with their fans bundled; resolves to the bundles when it is drawn.
 */
export async function applyGeometry(cy, geometry) {
  await placeLeaves(cy, geometry);
  fitCompounds(cy, geometry);
  const bundles = bundlesOf(cy, geometry);
  routeEdges(cy, geometry, bundles.paths);
  return bundles;
}
