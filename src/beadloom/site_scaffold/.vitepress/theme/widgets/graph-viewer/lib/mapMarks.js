// beadloom:component=site-graph-viewer
// The map's marks and the size each keeps on screen: an aggregated edge's width and count, a closed box's title.
//
// A mark of the map carries the map's scale in its data, a power of 1.25 near
// 1 / zoom (`model/canvasMap.js`); multiplied by it, a size in pixels stays about
// that many pixels on screen at any zoom. A closed box's title fits inside the
// box when its estimated width and height do, and is drawn above it otherwise.
//
// Every function here is pure: an element's data in, a size or a text out.

import { HIDDEN_EDGES, MAP_SCALE } from "./levels.js";

/**
 * What the map's marks measure on screen, in pixels, at any zoom: an aggregated
 * edge's count and its width, a base and a step per doubling of the count, and a
 * closed box's title; how much of a closed box's tint shows; and how wide a
 * character of a title is and how tall a line, as shares of its size.
 */
export const MAP_MARKS = Object.freeze({
  countLabel: 11,
  baseWidth: 1.5,
  widthPerDoubling: 1.1,
  boxTitle: 14,
  collapsedOpacity: 0.16,
  characterWidth: 0.62,
  lineHeight: 1.25,
});

/** The factor a mark's sizes are multiplied by: the map's scale, 1 before the map has set it. */
export const scaleOf = (element) => element.data(MAP_SCALE) || 1;

/** An aggregated edge's width, in layout units: its screen width by its count, at the map's scale. */
export function aggregateWidthOf(edge) {
  const width = MAP_MARKS.baseWidth + MAP_MARKS.widthPerDoubling * Math.log2(edge.data("weight") || 1);
  return width * scaleOf(edge);
}

/** A node's title, with the count of its edges the budget leaves out on a line below. */
export function titleOf(node) {
  const hidden = node.data(HIDDEN_EDGES);
  return hidden ? `${node.data("label")}\n+${hidden}` : node.data("label");
}

/** How wide and how tall a closed box's title is drawn, in layout units, by estimate. */
export function titleSizeOf(node) {
  const lines = String(titleOf(node)).split("\n");
  const font = MAP_MARKS.boxTitle * scaleOf(node);
  const longest = Math.max(...lines.map((line) => line.length));
  return { width: longest * MAP_MARKS.characterWidth * font, height: lines.length * MAP_MARKS.lineHeight * font };
}

/** Whether a closed box's title fits inside it; the box's size is its data's (`lib/routes.js`, `compoundSizeOf`). */
export function titleFits(node) {
  const box = node.data("box");
  if (!box) return true;
  const title = titleSizeOf(node);
  return title.width <= box.width && title.height <= box.height;
}
