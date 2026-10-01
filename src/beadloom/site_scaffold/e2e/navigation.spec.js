// Navigation: dragging the canvas pans and never moves a node (BDL-076 A2).
//
// Before A2 every node was grabbable, compound parents included, so a drag that
// started inside a domain box moved the box and everything in it.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, parentMap, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

/** A point on the canvas, inside a compound parent's box, that lies on no other node. */
function pointInsideParentOnly(boxes, canvas) {
  const entries = Object.entries(boxes);
  const margin = 20;
  const onScreen = (x, y) =>
    x > canvas.x + margin &&
    y > canvas.y + margin &&
    x < canvas.x + canvas.width - margin &&
    y < canvas.y + canvas.height - margin;
  const parents = entries
    .filter(([, box]) => box.isParent && box.parent)
    .sort(([, a], [, b]) => (b.x2 - b.x1) * (b.y2 - b.y1) - (a.x2 - a.x1) * (a.y2 - a.y1));
  for (const [id, box] of parents) {
    const others = entries.filter(([other, b]) => other !== id && !isAncestor(other, id, boxes) && b);
    for (let fy = 0.15; fy < 0.95; fy += 0.07) {
      for (let fx = 0.05; fx < 0.95; fx += 0.05) {
        const x = box.x1 + (box.x2 - box.x1) * fx;
        const y = box.y1 + (box.y2 - box.y1) * fy;
        if (!onScreen(x, y)) continue;
        const covered = others.some(([, b]) => x >= b.x1 - 4 && x <= b.x2 + 4 && y >= b.y1 - 4 && y <= b.y2 + 4);
        if (!covered) return { id, x, y };
      }
    }
  }
  return null;
}

function isAncestor(candidate, id, boxes) {
  for (let cursor = boxes[id]?.parent; cursor; cursor = boxes[cursor]?.parent) {
    if (cursor === candidate) return true;
  }
  return false;
}

async function drag(page, from, dx, dy) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + dx, from.y + dy, { steps: 12 });
  await page.mouse.up();
}

test("a drag inside a domain box pans the view and moves no node", async ({ page, request }) => {
  const parents = parentMap(await architectureData(request));
  const containers = new Set(Object.values(parents).filter(Boolean));
  requireShape(
    [...containers].some((id) => parents[id]),
    "no container sits inside another container, so there is no box within a box to drag in"
  );
  await openArchitecture(page);
  const canvas = page.getByTestId("graph-canvas");
  await canvas.scrollIntoViewIfNeeded();
  const boxes = await viewer(page, "boxes");
  const point = pointInsideParentOnly(boxes, await canvas.boundingBox());
  expect(point, "a point inside a parent box and outside its children").not.toBeNull();

  const positionsBefore = await viewer(page, "positions");
  const panBefore = await viewer(page, "pan");
  await drag(page, point, 140, 90);

  expect(await viewer(page, "positions")).toEqual(positionsBefore);
  expect(await viewer(page, "pan")).not.toEqual(panBefore);
});

test("dragging a node moves it only while Arrange is on", async ({ page }) => {
  await openArchitecture(page);
  const canvas = page.getByTestId("graph-canvas");
  await canvas.scrollIntoViewIfNeeded();
  const area = await canvas.boundingBox();
  const boxes = await viewer(page, "boxes");
  const [leaf, box] = Object.entries(boxes).find(
    ([, b]) =>
      !b.isParent &&
      b.x1 > area.x + 60 &&
      b.y1 > area.y + 60 &&
      b.x2 < area.x + area.width - 120 &&
      b.y2 < area.y + area.height - 60
  );
  const centre = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };

  const before = (await viewer(page, "positions"))[leaf];
  await drag(page, centre, 60, 40);
  expect((await viewer(page, "positions"))[leaf]).toEqual(before);

  await page.getByRole("button", { name: "Arrange" }).click();
  expect(await viewer(page, "arranging")).toBe(true);
  const moved = (await viewer(page, "boxes"))[leaf];
  await drag(page, { x: (moved.x1 + moved.x2) / 2, y: (moved.y1 + moved.y2) / 2 }, 60, 40);
  expect((await viewer(page, "positions"))[leaf]).not.toEqual(before);
});

test("the keys and the buttons zoom, fit and clear the selection", async ({ page }) => {
  await openArchitecture(page);
  const canvas = page.getByTestId("graph-canvas");
  const fitted = await viewer(page, "zoom");

  await canvas.focus();
  await page.keyboard.press("+");
  const zoomedIn = await viewer(page, "zoom");
  expect(zoomedIn).toBeGreaterThan(fitted);
  await page.keyboard.press("-");
  await page.keyboard.press("-");
  expect(await viewer(page, "zoom")).toBeLessThan(zoomedIn);
  await page.keyboard.press("0");
  expect(await viewer(page, "zoom")).toBeCloseTo(fitted, 5);

  await page.getByRole("button", { name: "Zoom in" }).click();
  expect(await viewer(page, "zoom")).toBeGreaterThan(fitted);
  await page.getByRole("button", { name: "Fit" }).click();
  expect(await viewer(page, "zoom")).toBeCloseTo(fitted, 5);

  const [first] = await viewer(page, "visibleIds");
  await page.goto(`architecture.html?focus=${encodeURIComponent(first)}`);
  await page.waitForFunction(() => window.__beadloomViewer?.ready() === true);
  expect(await viewer(page, "selection")).toBe(first);
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("Escape");
  expect(await viewer(page, "selection")).toBeNull();
});

/**
 * Resolve once the page has not scrolled for 400 ms.
 *
 * Cytoscape ignores the wheel for 250 ms after the page scrolls, and lets it
 * scroll the page instead, so a wheel event sent sooner tests the page and not
 * the viewer.
 */
function scrollSettled(page) {
  return page.evaluate(
    () =>
      new Promise((resolve) => {
        let timer = setTimeout(resolve, 400);
        window.addEventListener(
          "scroll",
          () => {
            clearTimeout(timer);
            timer = setTimeout(resolve, 400);
          },
          { passive: true }
        );
      })
  );
}

// A trackpad pinch reaches the page as a wheel event with Control held.
const WHEEL_GESTURES = [
  { gesture: "the mouse wheel", modifier: null },
  { gesture: "a trackpad pinch", modifier: "Control" },
];
// Scrolling up (a negative delta) zooms in; scrolling down zooms out.
const WHEEL_DIRECTIONS = [
  { direction: "in", deltaY: -400, sign: 1 },
  { direction: "out", deltaY: 400, sign: -1 },
];

for (const { gesture, modifier } of WHEEL_GESTURES) {
  for (const { direction, deltaY, sign } of WHEEL_DIRECTIONS) {
    test(`${gesture} over the canvas zooms ${direction} and moves no node`, async ({ page }) => {
      await openArchitecture(page);
      const canvas = page.getByTestId("graph-canvas");
      await canvas.scrollIntoViewIfNeeded();
      const area = await canvas.boundingBox();
      await page.mouse.move(area.x + area.width / 2, area.y + area.height / 2);
      await scrollSettled(page);
      const zoomBefore = await viewer(page, "zoom");
      const positions = await viewer(page, "positions");

      if (modifier) await page.keyboard.down(modifier);
      await page.mouse.wheel(0, deltaY);
      if (modifier) await page.keyboard.up(modifier);

      await expect.poll(async () => Math.sign((await viewer(page, "zoom")) - zoomBefore)).toBe(sign);
      expect(await viewer(page, "positions")).toEqual(positions);
    });
  }
}
