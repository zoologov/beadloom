// URL state: filters, focus, depth, direction and mode round-trip (BDL-076 A2).
//
// Before A2 the filters lived in component refs, so a view could not be linked.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer, waitForViewer } from "./support/viewer.js";

test("a linked view opens in the state its query names", async ({ page, request }) => {
  const data = await architectureData(request);
  const domain = data.nodes.find((n) => n.kind === "domain").id;
  const focus = data.nodes.find((n) => n.parent === domain && n.kind === "feature").id;
  const query = `?kind=feature&domain=${domain}&focus=${focus}&depth=2&dir=in&mode=architecture`;

  await openArchitecture(page, query);

  await expect(page.getByLabel("Kind", { exact: true })).toHaveValue("feature");
  await expect(page.getByLabel("Domain", { exact: true })).toHaveValue(domain);
  expect(await viewer(page, "selection")).toBe(focus);
  expect(await viewer(page, "state")).toMatchObject({
    kind: "feature",
    domain,
    focus,
    depth: "2",
    dir: "in",
    mode: "architecture",
  });
});

test("a change in the toolbar is written to the URL and survives a reload", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const layer = data.nodes.find((n) => n.layer).layer;

  await openArchitecture(page, "?depth=3&dir=out");
  await page.getByLabel("Layer", { exact: true }).selectOption(layer);
  await page.getByRole("searchbox", { name: "Search nodes" }).fill("graph");
  await expect.poll(() => new URL(page.url()).searchParams.get("layer")).toBe(layer);
  await expect.poll(() => new URL(page.url()).searchParams.get("q")).toBe("graph");
  expect(new URL(page.url()).searchParams.get("depth")).toBe("3");

  await page.reload();
  await waitForViewer(page);
  await expect(page.getByLabel("Layer", { exact: true })).toHaveValue(layer);
  await expect(page.getByRole("searchbox", { name: "Search nodes" })).toHaveValue("graph");
  expect(await viewer(page, "state")).toMatchObject({ layer, q: "graph", depth: "3", dir: "out" });
});
