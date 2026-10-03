// Colours: every colour Cytoscape draws is a real value, in both themes.
//
// In an earlier version the stylesheet handed Cytoscape `var(--vp-…)` strings. Cytoscape
// accepts only literal colours, so it logged each one as invalid and drew it in
// its fallback grey, rgb(153,153,153).

import { test, expect } from "@playwright/test";
import {
  collectRejectedStyles,
  openArchitecture,
  serveEveryEdgeKind,
  unresolvedColours,
  viewer,
} from "./support/viewer.js";

test("no drawn colour is Cytoscape's fallback, and no style is rejected", async ({ page }) => {
  const rejected = collectRejectedStyles(page);
  await openArchitecture(page);

  const colours = await viewer(page, "colours");
  expect(colours.length).toBeGreaterThan(0);
  expect(unresolvedColours(colours)).toEqual([]);
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
  expect(unresolvedColours(dark)).toEqual([]);
});


// Every drawn edge kind, the violation style included, in a page that opens in
// each theme: a project's graph may carry no violation, and then its own data
// would leave the violation colour and the dark theme's first build unread.
for (const colorScheme of ["light", "dark"]) {
  test.describe(`opened in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("with every edge kind drawn, no colour is the fallback and no style is rejected", async ({
      page,
      request,
    }) => {
      const rejected = collectRejectedStyles(page);
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(
        colorScheme === "dark"
      );

      const colours = await viewer(page, "colours");
      expect(new Set((await viewer(page, "edgeLooks")).map((look) => look.styleKey)).size).toBe(5);
      expect(unresolvedColours(colours)).toEqual([]);
      expect(rejected).toEqual([]);
    });
  });
}
