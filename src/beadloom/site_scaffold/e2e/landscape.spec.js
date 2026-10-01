// The landscape runs on the viewer core: its own filters, full screen and a card (BDL-076 A4).
//
// Before A4 the landscape was a component of its own: no test handle, filters
// in component refs, a card beside the canvas that did not go full screen, and
// every theme colour a `var(--vp-…)` string that Cytoscape drew as its
// fallback grey.

import { test, expect } from "@playwright/test";
import {
  collectRejectedStyles,
  unresolvedColours,
  viewer,
  waitForViewer,
} from "./support/viewer.js";
import {
  contractNeighbourhood,
  contractsOf,
  landscapeData,
  openLandscape,
  servicesWithEdges,
} from "./support/landscape.js";
import { LACKING, requireShape } from "./support/shape.js";

const CARD = "[data-testid='landscape-card']";

/** The service that takes part in the most contracts. */
function busiest(data) {
  return data.nodes
    .map((n) => n.id)
    .sort((a, b) => contractsOf(data, b).length - contractsOf(data, a).length || a.localeCompare(b))[0];
}

test("the landscape page draws every service of its data file in the viewer, in landscape mode", async ({
  page,
  request,
}) => {
  const data = await landscapeData(request);

  await openLandscape(page);

  expect(await viewer(page, "visibleIds")).toEqual(data.nodes.map((n) => n.id).sort());
  expect(await viewer(page, "state")).toMatchObject({ mode: "landscape" });
  const toolbar = page.getByRole("toolbar", { name: "Graph viewer tools" });
  for (const label of ["Protocol", "Verdict", "Only problems", "Depth", "Direction"]) {
    await expect(toolbar.getByLabel(label, { exact: true })).toBeVisible();
  }
  await expect(toolbar.getByLabel("Kind", { exact: true })).toHaveCount(0);
  // The owner's ruling after A4 (beadloom-ujzb.6): the landscape has an impact mode too.
  await expect(toolbar.getByRole("button", { name: "Impact", exact: true })).toBeVisible();
});

test("the verdict filter keeps the services its edges touch, and the view survives a reload", async ({
  page,
  request,
}) => {
  const data = await landscapeData(request);

  await openLandscape(page);
  await page.getByLabel("Verdict", { exact: true }).selectOption("healthy");
  await expect.poll(() => viewer(page, "visibleIds")).toEqual(servicesWithEdges(data, "healthy"));
  await expect.poll(() => new URL(page.url()).searchParams.get("verdict")).toBe("healthy");

  await page.reload();
  await waitForViewer(page);
  expect(await viewer(page, "state")).toMatchObject({ verdict: "healthy", problems: false });
  expect(await viewer(page, "visibleIds")).toEqual(servicesWithEdges(data, "healthy"));

  await page.getByLabel("Verdict", { exact: true }).selectOption("all");
  await page.getByLabel("Only problems", { exact: true }).check();
  await expect.poll(() => viewer(page, "visibleIds")).toEqual(servicesWithEdges(data, "broken"));
  await expect.poll(() => new URL(page.url()).searchParams.get("problems")).toBe("1");
});

test("a selected service shows its neighbourhood and a card with every contract it takes part in", async ({
  page,
  request,
}) => {
  const data = await landscapeData(request);
  const service = busiest(data);
  requireShape(service && contractsOf(data, service).length > 0, LACKING.landscape);

  await openLandscape(page, `?focus=${service}`);

  expect(await viewer(page, "selection")).toBe(service);
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(contractNeighbourhood(data, service));
  const card = page.locator(CARD);
  await expect(card.locator("h3")).toHaveText(service);
  for (const contract of contractsOf(data, service)) {
    const entry = card.locator(`[data-contract='${contract.contract_key}']`);
    await expect(entry).toContainText(contract.name || contract.contract_key);
    await expect(entry).toContainText(String(contract.verdict).toUpperCase());
  }
});

test("the landscape resolves every colour it draws, and no style is rejected", async ({
  page,
  request,
}) => {
  requireShape((await landscapeData(request)).nodes.length > 0, LACKING.landscapeService);
  const rejected = collectRejectedStyles(page);
  await openLandscape(page);

  const colours = await viewer(page, "colours");
  expect(colours.length).toBeGreaterThan(0);
  expect(unresolvedColours(colours)).toEqual([]);
  expect(rejected).toEqual([]);
});

test("full screen holds the landscape's toolbar, canvas and card", async ({ page, request }) => {
  const data = await landscapeData(request);
  requireShape(data.nodes.length > 0, LACKING.landscapeService);
  await openLandscape(page, `?focus=${busiest(data)}`);
  await page.getByRole("button", { name: /full screen/i }).click();

  await expect
    .poll(() =>
      page.evaluate(() => {
        const element =
          document.fullscreenElement || document.querySelector("[data-fullscreen-fallback='on']");
        const holds = (selector) => Boolean(element?.contains(document.querySelector(selector)));
        return {
          toolbar: holds("[role='toolbar']"),
          canvas: holds("[data-testid='graph-canvas']"),
          card: holds("[data-testid='landscape-card']"),
        };
      })
    )
    .toEqual({ toolbar: true, canvas: true, card: true });
});
