// Full screen covers the viewer's whole space: toolbar, canvas and panel (BDL-076 A2).
//
// Before A2 only the canvas and the card went full screen; the controls and the
// legend stayed behind in the page.

import { test, expect } from "@playwright/test";
import { openArchitecture } from "./support/viewer.js";

/** Whether the element that is full screen now holds the toolbar, the canvas and the panel. */
function fullscreenContents(page) {
  return page.evaluate(() => {
    const element =
      document.fullscreenElement || document.querySelector("[data-fullscreen-fallback='on']");
    const holds = (selector) => {
      const target = document.querySelector(selector);
      return Boolean(element && target && element.contains(target));
    };
    return {
      active: Boolean(element),
      toolbar: holds("[role='toolbar']"),
      canvas: holds("[data-testid='graph-canvas']"),
      panel: holds("[data-testid='viewer-panel']"),
    };
  });
}

test("full screen holds the toolbar, the canvas and the panel", async ({ page }) => {
  await openArchitecture(page);
  await page.getByRole("button", { name: /full screen/i }).click();

  await expect.poll(() => fullscreenContents(page)).toEqual({
    active: true,
    toolbar: true,
    canvas: true,
    panel: true,
  });
});

test("the CSS fallback covers the same space when the Fullscreen API refuses", async ({ page }) => {
  await page.addInitScript(() => {
    Element.prototype.requestFullscreen = function refuse() {
      return Promise.reject(new Error("refused by the test"));
    };
  });
  await openArchitecture(page);
  await page.getByRole("button", { name: /full screen/i }).click();

  await expect.poll(() => fullscreenContents(page)).toEqual({
    active: true,
    toolbar: true,
    canvas: true,
    panel: true,
  });
});

test("the f key toggles full screen", async ({ page }) => {
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("f");
  await expect.poll(async () => (await fullscreenContents(page)).active).toBe(true);
});
