// A node page opens the viewer on its node, and the reader walks away from there.
//
// In an earlier version a node page carried a scoped Mermaid C4 diagram of its own, with
// its own pan and zoom and none of the viewer's navigation, filters or card.

import { test, expect } from "@playwright/test";
import {
  SELECTED_VIEW,
  architectureData,
  flaggedIds,
  fullscreenView,
  openArchitecture,
  openEveryBox,
  parentMap,
  viewer,
  waitForViewer,
  withAncestors,
} from "./support/viewer.js";
import { neighbourhood } from "./support/graph.js";
import { gesturesOnALeaf, pressEveryToolbarButton } from "./support/pointer.js";
import { requireShape } from "./support/shape.js";

const CARD = "[data-testid='node-card']";

/** The page of a node, relative to the site's base: its `url` without the leading slash. */
function pageOf(node) {
  return `${node.url.replace(/^\//, "")}.html`;
}

/** Whether node `id` holds another: a box, whose page selects the box (`counts.spec.js`). */
function holdsAnother(data, id) {
  return Object.values(parentMap(data)).includes(id);
}

/**
 * The node holding no other with a page whose one-step neighbourhood is largest,
 * and which reaches out and in: under `prefix` when a node there qualifies, under
 * any page otherwise. A graph need not hold the kind the prefix names; a Go
 * service's packages, as `beadloom init` writes them, include no domain.
 */
function subjectOf(data, prefix) {
  const reach = (id) => neighbourhood(data, id, 1, "both").ids.length;
  const qualifying = data.nodes
    .filter((n) => n.url && !holdsAnother(data, n.id))
    .filter((n) => neighbourhood(data, n.id, 1, "out").ids.length > 1)
    .filter((n) => neighbourhood(data, n.id, 1, "in").ids.length > 1);
  const preferred = qualifying.filter((n) => n.url.startsWith(prefix));
  const subject = (preferred.length ? preferred : qualifying).sort(
    (a, b) => reach(b.id) - reach(a.id) || a.id.localeCompare(b.id)
  )[0];
  requireShape(subject, "no node with a page both depends on another node and has a dependent");
  return subject;
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
  // The selection opens the boxes its node needs; the neighbourhood is read with every box open.
  await openEveryBox(page, { edges: false });
  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(neighbourhood(data, node.id, 1, "both"));
  await expect(page.locator(`${CARD} [data-card-field='kind']`)).toContainText(node.kind);
  await expect(page.locator(".vp-doc .mermaid")).toHaveCount(0);
});

test("a box's page opens with the box selected, open and framed whole, and its card says what it holds", async ({ page, request }) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  // A box inside another: the box that holds everything is framed whole by any fit.
  const box = data.nodes.filter((n) => n.url && parents[n.id] && holdsAnother(data, n.id)).sort((a, b) => a.id.localeCompare(b.id))[0];
  requireShape(box, "no box inside another has a page");

  await page.goto(pageOf(box));
  await waitForViewer(page);

  expect(await viewer(page, "selection")).toBe(box.id);
  await expect.poll(() => viewer(page, "openBoxes")).toContain(box.id);
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const drawn = (await viewer(page, "boxes"))[box.id];
  const inside = Object.keys(parents).filter((id) => id !== box.id && withAncestors([id], parents).has(box.id)).length;
  expect({
    framed: drawn.x1 >= canvas.x && drawn.x2 <= canvas.x + canvas.width && drawn.y1 >= canvas.y && drawn.y2 <= canvas.y + canvas.height,
    inside: await page.locator(`${CARD} [data-card-field='contents'] [data-contents-inside]`).getAttribute("data-contents-inside"),
  }).toEqual({ framed: true, inside: String(inside) });
});

test("from the node page every toolbar control works and the selection moves freely", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = subjectOf(data, "/domains/");
  const next = neighbourhood(data, node.id, 1, "out").ids.find((id) => id !== node.id && !holdsAnother(data, id));

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
//.
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
    .filter((n) => n.url && n.url.startsWith("/other/") && !holdsAnother(data, n.id))
    .sort((a, b) => a.id.localeCompare(b.id))[0];
  requireShape(
    node,
    "no node has a page under other/; only a node of a kind other than service, domain and feature has one"
  );

  await page.goto(pageOf(node));
  await waitForViewer(page);

  expect(await viewer(page, "selection")).toBe(node.id);
  await openEveryBox(page, { edges: false });
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
  // What the filter keeps, over the whole graph: every box open (`filters.spec.js`).
  await openEveryBox(page);
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

test("on a node page the navigation buttons zoom and fit", async ({ page, request }) => {
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

  expect({ zoomedIn: zoomedIn > fitted, refitted }).toEqual({ zoomedIn: true, refitted: fitted });
});

test("on a node page a drag and a long press on a node pan the view and move no node, whatever toolbar button was pressed", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  await page.goto(pageOf(subjectOf(data, "/domains/")));
  await waitForViewer(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  expect(await pressEveryToolbarButton(page)).toBeGreaterThan(3);

  const outcomes = await gesturesOnALeaf(page);
  expect(outcomes, "a leaf node the pointer reaches").not.toBeNull();
  expect(outcomes).toEqual({
    drag: { moved: [], panned: true },
    "long press": { moved: [], panned: true },
  });
});
