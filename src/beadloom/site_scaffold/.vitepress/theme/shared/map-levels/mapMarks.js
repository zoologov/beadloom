// beadloom:component=site-shared-map-levels
// The map's marks and the size each keeps on screen: a box's title and its plate, a closed box's status mark.
//
// A mark of the map carries the map's scale in its data, a power of 1.25 near
// 1 / zoom (`widgets/graph-viewer/model/canvasMap.js`); multiplied by it, a size in pixels stays about
// that many pixels on screen at any zoom. So does every line, which is drawn at
// one weight whatever it carries (`entities/graph-edge/lib/lineMarks.js`).
//
// A title is tried inside its box at 14, 12.5, 11 and 10 px, the largest that
// fits with a little room around it and clear of the box's status mark; a title
// that fits at none stands above its box at 12.5 px on a plate, an opaque
// rectangle with a thin border, so no line is read through it — or below the
// box, or beside it, where above it would cover another box or another plate. The overview's
// routes keep clear of every plate (`shared/grid-routing/overviewRoutes.js`), and the plate is where
// `plateOf` says: a title's width is measured with the font it is drawn in. At
// the overview a top-level node too small for its title is drawn at the least
// box that holds it (`titleBoxOf`, `shared/geometry/grownBoxes.js`). Where no such box fits
// its title on one line, its name is broken onto two at a hyphen, an
// underscore, a slash, a dot, a colon or a space (`brokenLabelOf`), in its box
// or in the least box that holds it so; a plate is left only where neither fits.
//
// Every function here is pure: sizes and a text in, a size or a place out.

import { HIDDEN_EDGES, MAP_SCALE } from "./levels.js";

/**
 * What the map's marks measure on screen, in pixels, at any zoom: the sizes a
 * title is tried at inside its box, largest first, the size it stands on a plate
 * at, the room it keeps from its box's edges, the height of a line of it as a
 * share of its size; a plate's padding, border and gap above its box; and a
 * status mark on a closed box and how far in from its corner it sits. A closed
 * box's tint is its layer's, as any node's (`entities/layer`, `LAYER_FILL_SHARE`).
 */
export const MAP_MARKS = Object.freeze({
  titleSizes: Object.freeze([14, 12.5, 11, 10]),
  plateTitle: 12.5,
  titleInset: 6,
  lineHeight: 1.25,
  platePadding: 3,
  plateBorder: 1,
  plateGap: 3,
  statusMark: 7,
  statusMarkInset: 4,
});

/** The data a node of the map carries for its title: `{ px, inside, width, side, scale }` (`mapTitleOf`), `scale` the one it was laid out at. */
export const MAP_TITLE = "mapTitle";
/** The data a node of the map drawn larger than its layout carries: its drawn box's `{ width, height }`, layout units, its border included (`shared/geometry/grownBoxes.js`). */
export const MAP_BOX = "mapBox";
/** The data a closed box carries for what its edges do: `{ incoming, outgoing }`. */
export const TALLY = "tally";
/** The data a drawn node inside an open box carries: how many of its outward edges are not drawn at rest, its "+N" (`levels.js`, `outwardOf`). */
export const OUTWARD = "outward";

/** The factor a mark's sizes are multiplied by: the map's scale, 1 before the map has set it. */
export const scaleOf = (element) => element.data(MAP_SCALE) || 1;

/** A node's title, with the count of its edges the budget leaves out on a line below; as its map title breaks it, when it does. */
export function titleOf(node) {
  const broken = node.data(MAP_TITLE)?.lines;
  if (broken) return broken.join("\n");
  const hidden = node.data(HIDDEN_EDGES);
  return hidden ? `${node.data("label")}\n+${hidden}` : node.data("label");
}

/** The characters a title may be broken after, each kept at the end of the first line. */
const BREAK_AFTER = new Set(["-", "_", "/", ".", ":"]);

/**
 * `label` broken onto two lines where its wider line is narrowest by
 * `measure(line, px)`: after a hyphen, an underscore, a slash, a dot or a colon,
 * which stays on the first line, or at a space, which is dropped; null when it
 * has no such place, or only at an end.
 */
export function brokenLabelOf(label, measure, px = MAP_MARKS.titleSizes[0]) {
  const text = String(label);
  let best = null;
  for (let i = 1; i < text.length - 1; i += 1) {
    const at = text[i] === " " ? [text.slice(0, i), text.slice(i + 1)] : BREAK_AFTER.has(text[i]) ? [text.slice(0, i + 1), text.slice(i + 1)] : null;
    if (!at || !at[0].trim() || !at[1].trim()) continue;
    const widest = widthOf(at, px, measure);
    if (!best || widest < best.widest) best = { lines: at, widest };
  }
  return best ? best.lines : null;
}

/** How wide the widest of `lines` is at `px`, in pixels, by `measure(line, px)`. */
const widthOf = (lines, px, measure) => Math.max(...lines.map((line) => measure(line, px)));

/**
 * Where a title of `lines` goes in `box` (`{ width, height }`, layout units) at
 * `scale`: `{ px, inside }`, the size on screen it is drawn at and whether it is
 * inside, and `lines` when it is drawn as `broken` rather than as `lines`.
 * `reserved` is the room a status mark takes at each end, in layout units;
 * `measure(line, px)` gives a line's width in pixels. `broken`, the same title
 * on more lines, is tried at every size only once `lines` fits at none.
 */
export function titleLayoutOf(lines, box, scale, measure, reserved = 0, broken = null) {
  const inset = MAP_MARKS.titleInset * scale;
  const room = { width: box.width - 2 * Math.max(inset, reserved), height: box.height - inset };
  const fits = (form) => (px) =>
    widthOf(form, px, measure) * scale <= room.width && form.length * MAP_MARKS.lineHeight * px * scale <= room.height;
  const px = MAP_MARKS.titleSizes.find(fits(lines));
  if (px !== undefined) return { px, inside: true };
  const brokenPx = broken ? MAP_MARKS.titleSizes.find(fits(broken)) : undefined;
  return brokenPx === undefined ? { px: MAP_MARKS.plateTitle, inside: false } : { px: brokenPx, inside: true, lines: broken };
}

/**
 * The title a node of the map is drawn with at `scale`, or null when its own
 * label reads larger: `{ px, inside, width }`, `width` its widest line in layout
 * units, and `lines` when it is drawn `broken` (`titleLayoutOf`). A box always
 * takes the map's title; a node that is not a box takes it only while its own
 * label, `natural` layout units, would be smaller on screen.
 */
export function mapTitleOf(lines, box, scale, measure, { reserved = 0, natural = null, broken = null } = {}) {
  const layout = titleLayoutOf(lines, box, scale, measure, reserved, broken);
  if (natural !== null && natural / scale >= layout.px) return null;
  return { ...layout, width: widthOf(layout.lines || lines, layout.px, measure) * scale };
}

/** How much larger than exact the least box for a title is made, as a share: so a title measured to fit it does, whatever the rounding. */
const LEAST_BOX_SLACK = 1e-6;

/**
 * The least box, `{ width, height }` in layout units at `scale`, that holds a
 * title of `lines` inside at `px`, as `titleLayoutOf` fits one: its widest line
 * and the room it keeps from the box's edges, or at each end the room
 * `reservedAt(height)` says a status mark takes in a box that tall.
 */
export function titleBoxOf(lines, px, scale, measure, reservedAt = () => 0) {
  const inset = MAP_MARKS.titleInset * scale;
  const height = lines.length * MAP_MARKS.lineHeight * px * scale + inset;
  const width = widthOf(lines, px, measure) * scale + 2 * Math.max(inset, reservedAt(height));
  return { width: width * (1 + LEAST_BOX_SLACK), height: height * (1 + LEAST_BOX_SLACK) };
}

/** How far a title on a plate is drawn above its box's top, in layout units: its plate's border, padding and gap. */
export const plateLiftOf = (scale) => (MAP_MARKS.plateBorder + MAP_MARKS.platePadding + MAP_MARKS.plateGap) * scale;

/** The sides of its box a plate is tried on, in order. */
export const PLATE_SIDES = Object.freeze(["above", "below", "right", "left"]);

/**
 * The plate a title of `lines` stands on `side` (one of `PLATE_SIDES`) of `box`
 * (`{ x1, y1, x2, y2 }`), at `px` on screen and `scale`: `{ x1, y1, x2, y2 }` in
 * layout units, its padding and border included.
 */
export function plateOf(box, side, lines, px, scale, measure) {
  const frame = (MAP_MARKS.platePadding + MAP_MARKS.plateBorder) * scale;
  const width = widthOf(lines, px, measure) * scale + 2 * frame;
  const height = lines.length * MAP_MARKS.lineHeight * px * scale + 2 * frame;
  const gap = MAP_MARKS.plateGap * scale;
  const middle = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };
  if (side === "right" || side === "left") {
    const x1 = side === "right" ? box.x2 + gap : box.x1 - gap - width;
    return { x1, y1: middle.y - height / 2, x2: x1 + width, y2: middle.y + height / 2 };
  }
  const y1 = side === "below" ? box.y2 + gap : box.y1 - gap - height;
  return { x1: middle.x - width / 2, y1, x2: middle.x + width / 2, y2: y1 + height };
}

/** The most of a closed box's height its status mark, and the room above the mark, take: a box at the overview can be a few pixels tall. */
const MARK_HEIGHT_SHARE = 0.3;
const MARK_INSET_SHARE = 0.12;

const boxHeightOf = (node) => node.data(MAP_BOX)?.height ?? node.data("box")?.height ?? Infinity;

/** A closed box's status mark's side at `scale` for a box `height` tall, in layout units: its size on screen, within a share of the box. */
export const statusMarkOf = (scale, height) => Math.min(MAP_MARKS.statusMark * scale, MARK_HEIGHT_SHARE * height);

/** How far a closed box's status mark sits in from its top right corner at `scale`, in layout units. */
export const statusMarkInsetOf = (scale, height) => Math.min(MAP_MARKS.statusMarkInset * scale, MARK_INSET_SHARE * height);

/** A closed box's status mark's side, in layout units. */
export const boxMarkOf = (node) => statusMarkOf(scaleOf(node), boxHeightOf(node));

/** How far a closed box's status mark sits in from its top right corner, in layout units. */
export const boxMarkInsetOf = (node) => statusMarkInsetOf(scaleOf(node), boxHeightOf(node));
