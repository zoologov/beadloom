// URL state: filters, focus, depth, direction and the impact view round-trip (BDL-076 A2).
//
// Before A2 the filters lived in component refs, so a view could not be linked.
// The data mode is not a URL key: it is the page's (CONTEXT, A4), and a query
// cannot turn the architecture page into the landscape. Every key the query
// names below differs from its default, so an assertion on it fails when the
// viewer does not read it (BDL-076 R1 finding m3).

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer, waitForViewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

test("a linked view opens in the state its query names", async ({ page, request }) => {
  const data = await architectureData(request);
  // A feature directly inside a domain, or failing that a node of any kind; the
  // first domain need not hold one.
  const kinds = new Map(data.nodes.map((n) => [n.id, n.kind]));
  const inDomain = data.nodes.filter((n) => n.parent !== n.id && kinds.get(n.parent) === "domain");
  const member = inDomain.find((n) => n.kind === "feature") ?? inDomain[0];
  requireShape(member, "no node sits directly inside a domain");
  const [kind, domain, focus] = [member.kind, member.parent, member.id];
  const query = `?kind=${kind}&domain=${domain}&violations=1&focus=${focus}&depth=2&dir=in&view=impact`;

  await openArchitecture(page, query);

  await expect(page.getByLabel("Kind", { exact: true })).toHaveValue(kind);
  await expect(page.getByLabel("Domain", { exact: true })).toHaveValue(domain);
  await expect(page.getByLabel("Only flagged", { exact: true })).toBeChecked();
  expect(await viewer(page, "selection")).toBe(focus);
  expect(await viewer(page, "state")).toMatchObject({
    kind,
    domain,
    violations: true,
    focus,
    depth: "2",
    dir: "in",
    view: "impact",
  });
  expect((await viewer(page, "impactSummary"))?.focus).toBe(focus);
  await expect(page.getByTestId("impact-summary")).toBeVisible();
});

test("a query cannot switch the architecture page to another data mode", async ({ page }) => {
  await openArchitecture(page, "?mode=landscape");

  expect((await viewer(page, "state")).mode).toBe("architecture");
  await expect(page.getByLabel("Kind", { exact: true })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("mode")).toBe("landscape");
});

test("a change in the toolbar is written to the URL and survives a reload", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const layers = data.layers || [];
  requireShape(
    layers.length > 0,
    "no declared layer; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml"
  );
  const layer = layers[layers.length - 1].name;
  // A domain when the graph has one; the focus is any node's.
  const focus = (data.nodes.find((n) => n.kind === "domain") ?? data.nodes[0]).id;

  await openArchitecture(page, `?depth=3&dir=out&focus=${focus}`);
  await page.getByLabel("Layer", { exact: true }).selectOption(layer);
  await page.getByRole("searchbox", { name: "Search nodes" }).fill("graph");
  await page.getByRole("button", { name: "Impact", exact: true }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("layer")).toBe(layer);
  await expect.poll(() => new URL(page.url()).searchParams.get("q")).toBe("graph");
  await expect.poll(() => new URL(page.url()).searchParams.get("view")).toBe("impact");
  expect(new URL(page.url()).searchParams.get("depth")).toBe("3");

  await page.reload();
  await waitForViewer(page);
  await expect(page.getByLabel("Layer", { exact: true })).toHaveValue(layer);
  await expect(page.getByRole("searchbox", { name: "Search nodes" })).toHaveValue("graph");
  expect(await viewer(page, "state")).toMatchObject({
    layer,
    q: "graph",
    depth: "3",
    dir: "out",
    view: "impact",
  });
  await expect(page.getByTestId("impact-summary")).toBeVisible();
});
