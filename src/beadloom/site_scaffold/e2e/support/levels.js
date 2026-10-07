// The browser tests' own reading of the map's levels: when a box opens, what a reader can read, and how the view gets there.
//
// Written apart from the viewer's code. The rule a box opens by is the owner's
// (ruling 12): a box opens once its nodes are readable, its smallest child at
// least `READABLE_PX` tall on screen, and closes again below `CLOSE_SHARE` of
// that (the RFC's 0.8 would draw lines between nodes where ELK's shortest last
// runs hold no whole arrowhead); the view must be zoomed in past `FIT_FLOOR`
// times the whole-graph fit first, so the fit itself is always the overview.
// Sizes are read from ELK's boxes (`elkGeometry`), which no level changes.

import { expect } from "@playwright/test";
import { smallestChildOf } from "./map.js";
import { drag } from "./pointer.js";
import { viewer } from "./viewer.js";

/** A node is readable at this height on screen, in pixels (owner's ruling 12). */
export const READABLE_PX = 24;
/** An open box closes only below this share of the height it opened at. */
export const CLOSE_SHARE = 0.9;
/** A box opens only once the view is zoomed in this far past the whole-graph fit. */
export const FIT_FLOOR = 1.3;
/** How far inside the canvas's edges a point the pointer aims at lies, in pixels. */
const MARGIN_PX = 20;

export const twoFrames = (page) => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));

/** Whether `box` overlaps `extent`, both `{ x1, y1, x2, y2 }`. */
export const inView = (box, extent) => box.x2 > extent.x1 && box.x1 < extent.x2 && box.y2 > extent.y1 && box.y1 < extent.y2;

/**
 * The boxes that break the opening rule at the view `level` reports (`level`):
 * open where they should not be, or closed where they should be open. A box is
 * judged where the box that holds it is open; `smallest` maps a box to its
 * smallest child's height in layout units (`smallestChildOf`).
 */
export function againstReadability(level, tree, boxes, smallest) {
  const past = level.zoom >= FIT_FLOOR * level.fitZoom - 1e-9;
  const open = new Set(level.open);
  const judged = [...tree.boxes].filter((id) => id !== tree.wrapper && (!tree.parents[id] || tree.parents[id] === tree.wrapper || open.has(tree.parents[id])));
  return judged.filter((id) => {
    if (!boxes[id] || !smallest.has(id)) return false;
    const height = smallest.get(id) * level.zoom;
    const seen = past && inView(boxes[id], level.extent);
    if (seen && height >= READABLE_PX && !open.has(id)) return true;
    return open.has(id) && !(seen && height >= READABLE_PX * CLOSE_SHARE - 1e-9);
  }).map((id) => `${id} ${open.has(id) ? "open" : "closed"} with nodes ${(smallest.get(id) * level.zoom).toFixed(1)} px tall`);
}

/** The zoom at which the smallest child of every box holding `id` is readable: the zoom at which `id` is drawn as itself. */
export function readableZoomOf(id, tree, boxes) {
  const smallest = smallestChildOf(tree, boxes);
  let zoom = 0;
  for (let box = tree.parents[id]; box && box !== tree.wrapper; box = tree.parents[box]) zoom = Math.max(zoom, READABLE_PX / smallest.get(box));
  return zoom;
}

/** Drag the view so the node `id` is at the middle of the canvas, where the zoom buttons zoom. */
export async function centreOn(page, id) {
  const canvas = page.getByTestId("graph-canvas");
  await canvas.scrollIntoViewIfNeeded();
  await twoFrames(page);
  const area = await canvas.boundingBox();
  const b = (await viewer(page, "boxes"))[id];
  const from = { x: (b.x1 + b.x2) / 2, y: (b.y1 + b.y2) / 2 };
  const [dx, dy] = [area.x + area.width / 2 - from.x, area.y + area.height / 2 - from.y];
  // A press that does not move is a tap, which would select the node: drag only when it is off the middle.
  if (Math.hypot(dx, dy) > MARGIN_PX) await drag(page, from, dx, dy);
  await twoFrames(page);
}

/** Press "Zoom in" until `done()` answers true, at most `steps` times; whether it did. */
export async function zoomInUntil(page, done, steps = 40) {
  for (let taken = 0; taken < steps; taken += 1) {
    if (await done()) return true;
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
  }
  return done();
}

/** Open the box `id` the way a reader does: centred and zoomed into until it opens. */
export async function zoomIntoBox(page, id) {
  await centreOn(page, id);
  const opened = await zoomInUntil(page, async () => (await viewer(page, "openBoxes")).includes(id));
  expect(opened, `${id} opens by zooming into it`).toBe(true);
}

/** Wait until the view has held still for two frames in a row, as after a selection's frame. */
export async function settled(page) {
  await expect
    .poll(async () => {
      const before = JSON.stringify([await viewer(page, "zoom"), await viewer(page, "pan")]);
      await twoFrames(page);
      return before === JSON.stringify([await viewer(page, "zoom"), await viewer(page, "pan")]) && (await viewer(page, "ready"));
    })
    .toBe(true);
}

/**
 * The lines drawn now that are not routed square: `[id]`, each a line with no
 * route (a curve Cytoscape draws, such as its loop into a box that holds the
 * node) or with a run that is neither horizontal nor vertical.
 */
export function unroutedLines(looks, tolerance = 0.5) {
  return looks
    .filter((look) => !look.cornerRadii.length || look.points.slice(1).some((p, i) => Math.abs(p.x - look.points[i].x) > tolerance && Math.abs(p.y - look.points[i].y) > tolerance))
    .map((look) => `${look.key ?? look.id}${look.cornerRadii.length ? " (a slanted run)" : " (no route)"}`);
}
