// beadloom:component=site-graph-viewer
// The map's titles and the scale its marks keep one size on screen at: a closed box's title, a top-level node's, the project's plate and a grown box.
//
// What a box or a line says on screen — every line's weight, arrowheads and
// corners, every node's corners (`nodeCorners.js`), a closed box's title and a
// top-level node's — keeps one size on screen whatever the zoom: each carries
// the map's scale in its data, a power of 1.25 near 1 / zoom (`scaleAt`), and
// the stylesheet multiplies by it, so a zoom gesture restyles these elements
// only when the zoom crosses a step.
//
// A title is tried at a few sizes inside its box and otherwise stands above it
// on a plate (`lib/mapMarks.js`); which, is in the node's data (`mapTitle`),
// worked out again at each step of the scale. A top-level node that is not a box
// takes the map's title only while its own label would read smaller, and so does
// the box that holds everything, on a plate above it where the overview's plan
// kept the plate's room from its lines (`overviewPlan.js`).
//
// A top-level node the overview's plan draws larger than its layout, to hold its
// title (`overviewPlan.js`, `lib/grownBoxes.js`), carries its drawn box in its
// data (`mapBox`) while it is drawn closed, or as a leaf with its map title, and
// no edge of the file is drawn as itself into it, whose end the box would cover.
// The box is worked out again at each step of the scale: it keeps about its size
// on screen, as its title does, down to its laid-out box.
//
// The plan asks how a title would be drawn before it decides anything, and the
// map dresses its nodes with what the plan decided, so the titles come in two
// parts: `titleLooks`, which the plan is made with, and `titleDresser`, made
// with the plan. The map's drawing now, which both read, is handed to each call:
// `{ scale, hiddenAt, grownNow, ownEnds }`.

import { COLLAPSED, MAP_SCALE } from "../lib/levels.js";
import { MAP_BOX, MAP_MARKS, MAP_TITLE, brokenLabelOf, mapTitleOf, statusMarkInsetOf, statusMarkOf, titleBoxOf } from "../lib/mapMarks.js";
import { GEOMETRY } from "../lib/stylesheet.js";
import { giveData } from "./canvasMarks.js";
import { PROJECT_PLATE_SIDE } from "./overviewPlan.js";

/** The zoom step the map's marks are restyled at. */
export const SCALE_STEP = 1.25;

/** The map's scale at `zoom`: the power of `SCALE_STEP` nearest 1 / zoom. */
export function scaleAt(zoom) {
  return SCALE_STEP ** Math.round(Math.log(1 / zoom) / Math.log(SCALE_STEP));
}

/** A title's width in pixels at a size, measured in the font `cy`'s nodes are drawn in, bold. */
function titleMeasurer(cy) {
  const context = typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  return (text, px) => {
    if (!context) return String(text).length * px * 0.62;
    context.font = `700 ${px}px ${cy.nodes().first().style("font-family")}`;
    return context.measureText(String(text)).width;
  };
}

/**
 * How the titles of `cy`'s nodes would be drawn, `nodes` by id, in the box tree
 * `tree` laid out as `geometry`: `{ measure, lookOf, projectTitleAt,
 * leastBoxOf, breakable }`, what the overview's plan is made with.
 */
export function titleLooks(cy, { nodes, tree, geometry }) {
  const measure = titleMeasurer(cy);

  // Each node's label broken onto two lines, worked out once: null where it has no place to break.
  const brokenLabels = new Map();
  function brokenLabelFor(id) {
    if (!brokenLabels.has(id)) brokenLabels.set(id, brokenLabelOf(nodes.get(id).data("label"), measure));
    return brokenLabels.get(id);
  }

  /** A node's title as lines: its label, `broken` onto two where it breaks, and the count of its lines left out when there are any. */
  function linesOf(id, hidden, broken = false) {
    const label = (broken && brokenLabelFor(id)) || [String(nodes.get(id).data("label"))];
    return [...label, ...(hidden ? [`+${hidden}`] : [])];
  }

  /** The room node `id`'s status mark takes at each end of its title at `at` in a box `height` tall, in layout units. */
  function reservedOf(id, at, height) {
    if (!nodes.get(id).data("status")) return 0;
    return tree.boxes.has(id) ? statusMarkOf(at, height) + statusMarkInsetOf(at, height) : GEOMETRY.statusMark + GEOMETRY.statusMarkInset;
  }

  /**
   * The title node `id` is drawn with at `at` when `hidden` of its lines are left
   * out, in `drawn`, the box it is drawn as, or its laid-out box; null for its
   * own label. With `broken`, where the title fits on one line at no size, it is
   * drawn broken onto two; without, it is asked for on one line.
   */
  function lookOf(id, at, hidden, drawn, broken) {
    const node = nodes.get(id);
    const box = drawn || geometry.boxes[id];
    if (!node || !box) return null;
    const isBox = tree.boxes.has(id);
    const size = { width: box.x2 - box.x1, height: box.y2 - box.y1 };
    const reserved = reservedOf(id, at, size.height);
    const lines = broken ? linesOf(id, hidden, true) : null;
    return mapTitleOf(linesOf(id, hidden), size, at, measure, { reserved, natural: isBox ? null : GEOMETRY.nodeTitle, broken: lines });
  }

  /**
   * The title the box that holds everything stands on a plate with above it at
   * `at`, while its own, drawn inside at a node's title's size in layout units,
   * reads smaller than the smallest size a title is tried at: `{ px, inside,
   * width }`, at the size a title stands on a plate at, as a box's title does
   * that fits its box at none; or null.
   */
  function projectTitleAt(at) {
    if (GEOMETRY.nodeTitle / at >= Math.min(...MAP_MARKS.titleSizes)) return null;
    const px = MAP_MARKS.plateTitle;
    return { px, inside: false, width: measure(linesOf(tree.wrapper, 0)[0], px) * at };
  }

  /** The least box node `id` holds its title in at `px` and `at`: at least as tall as it was laid out, its status mark's room by the height it is drawn at. */
  const leastBoxOf = (id, px, at, hidden, broken = false) =>
    titleBoxOf(linesOf(id, hidden, broken), px, at, measure, (height) => reservedOf(id, at, Math.max(height, geometry.boxes[id].y2 - geometry.boxes[id].y1)));

  return { measure, lookOf, projectTitleAt, leastBoxOf, breakable: (id) => Boolean(brokenLabelFor(id)) };
}

/**
 * The titles and grown boxes the map dresses its nodes with, as `looks`
 * (`titleLooks`) draws them and the overview's `planner` decided them, in the
 * box tree `tree`: `{ grownBoxesNow, dressTitle, dressBox }`.
 */
export function titleDresser(looks, planner, tree) {
  const hiddenOf = (hiddenAt, id) => hiddenAt.get(id) || 0;
  /** The title node `id` is drawn with: broken where the overview's plan breaks it. */
  const lookOf = (id, at, hidden, drawn = null) => looks.lookOf(id, at, hidden, drawn, planner.isBroken(id));

  /** The scale node `id`'s marks are laid out at now: the map's, `scale`, or the overview plan's when the view is zoomed out past it. */
  function titleScaleOf(id, scale) {
    const planned = planner.titleScale();
    return (planner.isTop(id) || id === tree.wrapper) && planned ? Math.min(scale, planned) : scale;
  }

  /**
   * The box each node the plan draws larger than its layout is drawn as now,
   * among the nodes `drawn` with the boxes `openNow` open: while it is closed or
   * a leaf with its map title, and no edge of the file is drawn into it at rest.
   */
  function grownBoxesNow(drawn, openNow, { scale, hiddenAt, ownEnds }) {
    const now = new Map();
    for (const id of drawn) {
      if (!planner.isGrown(id) || ownEnds.has(id) || (tree.boxes.has(id) && openNow.has(id))) continue;
      const at = titleScaleOf(id, scale);
      const box = planner.drawnBoxAt(id, at, hiddenOf(hiddenAt, id));
      if (!tree.boxes.has(id) && !lookOf(id, at, hiddenOf(hiddenAt, id), box)) continue;
      now.set(id, box);
    }
    return now;
  }

  /**
   * Give the drawn node `node` the title it is drawn with now: a closed box's, or
   * a top-level node's while it reads larger. A top-level node's title is laid
   * out at the scale the overview's plan decided titles at whenever the view is
   * zoomed out past it, so it keeps the room the plan's routes left it and
   * shrinks with its box, rather than growing onto a plate the routes run under.
   */
  function dressTitle(node, { scale, hiddenAt, grownNow }) {
    const id = node.id();
    const at = titleScaleOf(id, scale);
    if (id === tree.wrapper) return dressProjectTitle(node, at, scale);
    const mapped = node.hasClass(COLLAPSED) || (planner.isTop(id) && !tree.boxes.has(id));
    const title = mapped ? lookOf(id, at, hiddenOf(hiddenAt, id), grownNow.get(id)) : null;
    giveData(node, title ? { [MAP_TITLE]: { ...title, side: planner.plateSideOf(id), scale: at }, [MAP_SCALE]: scale } : { [MAP_TITLE]: undefined });
  }

  /**
   * Give the box that holds everything, `node`, its title on a plate above it at
   * `at` while its own reads smaller than a title is drawn at the map's scale,
   * and only where the overview's plan kept the plate's room from its lines.
   */
  function dressProjectTitle(node, at, scale) {
    const title = planner.hasProjectPlate() && looks.projectTitleAt(scale) ? looks.projectTitleAt(at) : null;
    giveData(node, title ? { [MAP_TITLE]: { ...title, side: PROJECT_PLATE_SIDE, scale: at }, [MAP_SCALE]: scale } : { [MAP_TITLE]: undefined });
  }

  /** Give the drawn node `node` the box it is drawn as now, from `grownNow`, when the plan draws it larger than its layout. */
  function dressBox(node, grownNow) {
    const box = grownNow.get(node.id());
    giveData(node, { [MAP_BOX]: box ? { width: box.x2 - box.x1, height: box.y2 - box.y1 } : undefined });
  }

  return { grownBoxesNow, dressTitle, dressBox };
}
