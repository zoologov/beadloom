// The pointer gestures a browser test makes on the viewer's canvas, and the node it makes them on.
//
// Nodes on the canvas are never moved by the reader: ELK places them once and
// every drawn route is read from that layout, so a node a gesture moved would
// leave its routes behind. A drag on a node pans the view instead, and so does a
// press held long enough to count as a long press before the pointer moves.

import { viewer } from "./viewer.js";

/** How far from the canvas's edges a gesture starts, in pixels, so it ends on the canvas too. */
const EDGE_MARGIN = 80;
/** How long a long press holds the button before the pointer moves, in milliseconds. */
const LONG_PRESS_MS = 900;
/** How many intermediate pointer moves a gesture makes, so the canvas sees a drag and not a jump. */
const MOVE_STEPS = 12;
/** How long the view must stay still to count as settled, in milliseconds. */
const SETTLE_MS = 300;
/** The most times the view is read while waiting for it to settle. */
const SETTLE_TRIES = 20;

/** Drag from `from` by (`dx`, `dy`) without pausing. */
export async function drag(page, from, dx, dy) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + dx, from.y + dy, { steps: MOVE_STEPS });
  await page.mouse.up();
}

/** Press at `from`, hold past a long press, then drag by (`dx`, `dy`). */
export async function longPressDrag(page, from, dx, dy) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.waitForTimeout(LONG_PRESS_MS);
  await page.mouse.move(from.x + dx, from.y + dy, { steps: MOVE_STEPS });
  await page.mouse.up();
}

/** Every gesture a test makes on a node, by name. */
export const GESTURES = Object.freeze({ drag, "long press": longPressDrag });

/**
 * The centre of a visible leaf node the pointer reaches: well inside the canvas,
 * on no other leaf, and not under anything drawn over the canvas, such as the
 * panel. `{ id, x, y }` in page coordinates, or null when no leaf qualifies.
 */
export async function reachableLeaf(page) {
  const boxes = await viewer(page, "boxes");
  const visible = new Set(await viewer(page, "visibleIds"));
  return page.evaluate(
    ({ boxes: all, visibleIds, margin }) => {
      const canvas = document.querySelector("[data-testid='graph-canvas']");
      const area = canvas.getBoundingClientRect();
      const leaves = Object.entries(all).filter(([id, box]) => visibleIds.includes(id) && !box.isParent);
      const inside = (x, y) =>
        x > area.left + margin && y > area.top + margin && x < area.right - margin && y < area.bottom - margin;
      for (const [id, box] of leaves) {
        const x = (box.x1 + box.x2) / 2;
        const y = (box.y1 + box.y2) / 2;
        if (!inside(x, y)) continue;
        const onAnother = leaves.some(
          ([other, b]) => other !== id && x >= b.x1 && x <= b.x2 && y >= b.y1 && y <= b.y2
        );
        if (onAnother) continue;
        if (canvas.contains(document.elementFromPoint(x, y))) return { id, x, y };
      }
      return null;
    },
    { boxes, visibleIds: [...visible], margin: EDGE_MARGIN }
  );
}

/**
 * Resolve once the view has held still for `SETTLE_MS`: a button such as full
 * screen refits the graph after the page has changed, and a node's box read
 * before that refit is not where the node is drawn.
 */
async function viewSettled(page) {
  const view = async () => JSON.stringify([await viewer(page, "pan"), await viewer(page, "zoom")]);
  let last = await view();
  for (let tries = 0; tries < SETTLE_TRIES; tries += 1) {
    await page.waitForTimeout(SETTLE_MS);
    const now = await view();
    if (now === last) return;
    last = now;
  }
}

/** Click every button of the viewer's toolbar once, in the order the toolbar lists them; return how many. */
export async function pressEveryToolbarButton(page) {
  const buttons = page.locator("[role='toolbar'] button");
  const count = await buttons.count();
  for (let index = 0; index < count; index += 1) {
    await buttons.nth(index).click();
  }
  await viewSettled(page);
  return count;
}

/**
 * The position of every node that is not a box drawn open, by id: the leaves,
 * the boxes drawn closed, and the nodes inside those, which are not drawn and
 * keep their places.
 */
async function leafPositions(page) {
  const boxes = await viewer(page, "boxes");
  const positions = await viewer(page, "positions");
  return Object.fromEntries(Object.entries(positions).filter(([id]) => !boxes[id]?.isParent));
}

/**
 * Make every gesture on a reachable leaf, and report what each one did:
 * `{ [gesture]: { moved, panned } }`, where `moved` lists the leaves whose
 * position changed and `panned` says whether the view moved; null when no leaf
 * is within the pointer's reach.
 *
 * Only leaves are compared. A box is drawn around its children, so it moves
 * whenever a child does; and it can shift on its own while no leaf moves: an
 * outermost box moved 3.5 units during a drag that moved no leaf, measured in 2
 * of 6 runs on one adopter's node page.
 */
export async function gesturesOnALeaf(page) {
  const outcomes = {};
  for (const [name, gesture] of Object.entries(GESTURES)) {
    const leaf = await reachableLeaf(page);
    if (!leaf) return null;
    const positions = await leafPositions(page);
    const pan = await viewer(page, "pan");
    await gesture(page, leaf, 60, 40);
    const after = await leafPositions(page);
    outcomes[name] = {
      moved: Object.keys(positions).filter((id) => JSON.stringify(after[id]) !== JSON.stringify(positions[id])),
      panned: JSON.stringify(await viewer(page, "pan")) !== JSON.stringify(pan),
    };
  }
  return outcomes;
}
