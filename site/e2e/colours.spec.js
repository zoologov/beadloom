// Colours: every colour Cytoscape draws is a real value, in both themes (BDL-076 A2).
//
// Before A2 the stylesheet handed Cytoscape `var(--vp-…)` strings. Cytoscape
// accepts only literal colours, so it logged each one as invalid and drew it in
// its fallback grey, rgb(153,153,153).

import { test, expect } from "@playwright/test";
import { CYTOSCAPE_FALLBACK_COLOUR, openArchitecture, viewer } from "./support/viewer.js";

function unresolved(colours) {
  return colours.filter(
    (c) => c.value.replace(/\s+/g, "") === CYTOSCAPE_FALLBACK_COLOUR || /var\(/.test(c.value)
  );
}

test("no drawn colour is Cytoscape's fallback, and no style is rejected", async ({ page }) => {
  const rejected = [];
  page.on("console", (message) => {
    if (/style property .* is invalid/i.test(message.text())) rejected.push(message.text());
  });
  await openArchitecture(page);

  const colours = await viewer(page, "colours");
  expect(colours.length).toBeGreaterThan(0);
  expect(unresolved(colours)).toEqual([]);
  expect(rejected).toEqual([]);
});

test("switching to the dark theme rebuilds the colours from the dark tokens", async ({ page }) => {
  await openArchitecture(page);
  const light = await viewer(page, "colours");

  await page.getByRole("switch", { name: /dark theme/i }).first().click();
  await page.waitForFunction(() => document.documentElement.classList.contains("dark"));
  await expect.poll(async () => JSON.stringify(await viewer(page, "colours"))).not.toBe(
    JSON.stringify(light)
  );

  const dark = await viewer(page, "colours");
  expect(unresolved(dark)).toEqual([]);
});
