// A node page opens the viewer on its node, and the reader walks away from there (BDL-076 A4, US-4).
//
// Before A4 a node page carried a scoped Mermaid C4 diagram of its own, with
// its own pan and zoom and none of the viewer's navigation, filters or card.

import { test, expect } from "@playwright/test";
import { architectureData, viewer, waitForViewer } from "./support/viewer.js";
import { neighbourhood } from "./support/graph.js";

const CARD = "[data-testid='node-card']";

/** The page of a node, relative to the site's base: its `url` without the leading slash. */
function pageOf(node) {
  return `${node.url.replace(/^\//, "")}.html`;
}

/** The node with a page whose one-step neighbourhood is largest, and which reaches out and in. */
function subjectOf(data, prefix) {
  const reach = (id) => neighbourhood(data, id, 1, "both").ids.length;
  return data.nodes
    .filter((n) => n.url && n.url.startsWith(prefix))
    .filter((n) => neighbourhood(data, n.id, 1, "out").ids.length > 1)
    .filter((n) => neighbourhood(data, n.id, 1, "in").ids.length > 1)
    .sort((a, b) => reach(b.id) - reach(a.id) || a.id.localeCompare(b.id))[0];
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
