// A node page opens the viewer on its node, and the reader walks away from there (BDL-076 A4, US-4).
//
// Before A4 a node page carried a scoped Mermaid C4 diagram of its own, with
// its own pan and zoom and none of the viewer's navigation, filters or card.

import { test, expect } from "@playwright/test";
import {
  SELECTED_VIEW,
  architectureData,
  flaggedIds,
  fullscreenView,
  openArchitecture,
  parentMap,
  viewer,
  waitForViewer,
  withAncestors,
} from "./support/viewer.js";
import { neighbourhood } from "./support/graph.js";

const CARD = "[data-testid='node-card']";

/** The page of a node, relative to the site's base: its `url` without the leading slash. */
function pageOf(node) {
  return `${node.url.replace(/^\//, "")}.html`;
}

/**
 * The node with a page whose one-step neighbourhood is largest, and which reaches
 * out and in: under `prefix` when a node there qualifies, under any page otherwise.
 * A graph need not hold the kind the prefix names; a Go service's packages, as
 * `beadloom init` writes them, include no domain.
 */
function subjectOf(data, prefix) {
  const reach = (id) => neighbourhood(data, id, 1, "both").ids.length;
  const qualifying = data.nodes
    .filter((n) => n.url)
    .filter((n) => neighbourhood(data, n.id, 1, "out").ids.length > 1)
    .filter((n) => neighbourhood(data, n.id, 1, "in").ids.length > 1);
  const preferred = qualifying.filter((n) => n.url.startsWith(prefix));
  return (preferred.length ? preferred : qualifying).sort(
    (a, b) => reach(b.id) - reach(a.id) || a.id.localeCompare(b.id)
  )[0];
}

test("a node page opens with its node selected, its neighbourhood marked and its card open", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");

  await page.goto(pageOf(node));
  await waitForViewer(page);

  expect(await viewer(page, "selection")).toBe(node.id);
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(neighbourhood(data, node.id, 1, "both"));
  await expect(page.locator(`${CARD} [data-card-field='kind']`)).toContainText(node.kind);
  await expect(page.locator(".vp-doc .mermaid")).toHaveCount(0);
});

test("from the node page every toolbar control works and the selection moves freely", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");
  const next = neighbourhood(data, node.id, 1, "out").ids.find((id) => id !== node.id);

  await page.goto(pageOf(node));
  await waitForViewer(page);

  await page.getByLabel("Depth", { exact: true }).selectOption("2");
  await page.getByLabel("Direction", { exact: true }).selectOption("out");
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(neighbourhood(data, node.id, 2, "out"));

  await page
    .locator(`${CARD} [data-card-field='edges'] [data-edge-direction='out'][data-edge-target='${next}']`)
    .first()
    .click();
  await expect.poll(() => viewer(page, "selection")).toBe(next);
  await expect.poll(() => new URL(page.url()).searchParams.get("focus")).toBe(next);
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(neighbourhood(data, next, 2, "out"));

  await page.getByRole("button", { name: "Impact" }).click();
  await expect.poll(async () => (await viewer(page, "impactSummary"))?.focus ?? null).toBe(next);
});

// On a node page the selection's default is the page's own node, so a cleared
// selection has to be written to the URL, or a reload brings the node back
// (BDL-076 R1 finding m1).
test("a selection cleared on a node page stays cleared after a reload", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");

  await page.goto(pageOf(node));
  await waitForViewer(page);
  expect(await viewer(page, "selection")).toBe(node.id);
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("Escape");
  await expect.poll(() => viewer(page, "selection")).toBe(null);

  await page.reload();
  await waitForViewer(page);

  expect(await viewer(page, "selection")).toBe(null);
  expect(await viewer(page, "neighbourhood")).toEqual({ ids: [], edges: [] });
  await expect(page.locator(CARD)).toHaveCount(0);
});

test("a page under other/ opens focused on its node the same way", async ({ page, request }) => {
  const data = await architectureData(request);
  const node = data.nodes
    .filter((n) => n.url && n.url.startsWith("/other/"))
    .sort((a, b) => a.id.localeCompare(b.id))[0];
  expect(node, "this graph has a node whose page is under other/").toBeTruthy();

  await page.goto(pageOf(node));
  await waitForViewer(page);

  expect(await viewer(page, "selection")).toBe(node.id);
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(neighbourhood(data, node.id, 1, "both"));
});

test("a filter on a node page keeps what it keeps on the architecture page", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");

  await page.goto(pageOf(node));
  await waitForViewer(page);
  await page.getByLabel("Only flagged", { exact: true }).check();

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    [...withAncestors(flaggedIds(data), parentMap(data))].sort()
  );
});

test("full screen on a node page shows its tools, its card and its legend", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");

  await page.goto(pageOf(node));
  await waitForViewer(page);
  await page.getByRole("button", { name: /full screen/i }).click();

  await expect
    .poll(() => fullscreenView(page, SELECTED_VIEW))
    .toEqual({
      active: true,
      fills: true,
      shown: { toolbar: true, canvas: true, card: true, legend: true },
    });
});

/** Each control of the viewer's toolbar, as its role and accessible name: `button "Fit"`. */
async function toolbarControls(page) {
  const snapshot = await page.locator("[role='toolbar']").first().ariaSnapshot();
  return [...snapshot.matchAll(/- (button|combobox|checkbox|searchbox|radio|switch) "([^"]+)"/g)]
    .map(([, role, name]) => `${role} "${name}"`)
    .sort();
}

test("a node page's toolbar offers every control the architecture page's toolbar offers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");
  await openArchitecture(page, `?focus=${node.id}`);
  const onArchitecturePage = await toolbarControls(page);

  await page.goto(pageOf(node));
  await waitForViewer(page);

  expect(onArchitecturePage.length).toBeGreaterThan(10);
  expect(await toolbarControls(page)).toEqual(onArchitecturePage);
});

test("on a node page the navigation buttons zoom and fit, and Arrange turns node dragging on", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");
  await page.goto(pageOf(node));
  await waitForViewer(page);
  const fit = page.getByRole("button", { name: "Fit", exact: true });
  const rounded = async () => Number((await viewer(page, "zoom")).toFixed(6));
  await fit.click();
  const fitted = await rounded();

  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  const zoomedIn = await rounded();
  await fit.click();
  const refitted = await rounded();
  await page.getByRole("button", { name: "Arrange", exact: true }).click();

  expect({ zoomedIn: zoomedIn > fitted, refitted, arranging: await viewer(page, "arranging") }).toEqual({
    zoomedIn: true,
    refitted: fitted,
    arranging: true,
  });
});
