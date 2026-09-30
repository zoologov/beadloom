// A selected node's neighbourhood: depth, direction, and dim or hide (BDL-076 A3, US-1).
//
// Before A3 a selection marked the node and its own edges and nothing else:
// depth and direction were carried in the URL and read by nothing, and the rest
// of the graph stayed as it was.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, parentMap, viewer, withAncestors } from "./support/viewer.js";
import { neighbourhood } from "./support/graph.js";

const sorted = (ids) => [...ids].sort();

/**
 * The node the PRD names, `rule-engine`, when this graph has it; otherwise the
 * node whose outgoing neighbourhood grows most from depth 1 to depth 2, so the
 * case sees a second level whatever graph it runs on.
 */
function subjectOf(data) {
  if (data.nodes.some((n) => n.id === "rule-engine")) return "rule-engine";
  const growth = (id) =>
    neighbourhood(data, id, 2, "out").ids.length - neighbourhood(data, id, 1, "out").ids.length;
  return data.nodes.map((n) => n.id).sort((a, b) => growth(b) - growth(a))[0];
}

/** Every node that is neither in the walk nor a container of a node in it. */
function outside(data, walked) {
  const kept = withAncestors(walked, parentMap(data));
  return sorted(data.nodes.map((n) => n.id).filter((id) => !kept.has(id)));
}

test("depth 2 outgoing shows the node, what it reaches in two steps and those edges; the rest is dimmed", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, 2, "out");
  expect(expected.ids.length).toBeGreaterThan(neighbourhood(data, subject, 1, "out").ids.length);

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Depth", { exact: true }).selectOption("2");
  await page.getByLabel("Direction", { exact: true }).selectOption("out");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
  expect(await viewer(page, "dimmedIds")).toEqual(outside(data, expected.ids));
});

test("switching the direction to incoming shows the nodes that reach it", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, 2, "in");

  await openArchitecture(page, `?focus=${subject}&depth=2&dir=out`);
  await page.getByLabel("Direction", { exact: true }).selectOption("in");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
  expect(await viewer(page, "dimmedIds")).toEqual(outside(data, expected.ids));
});

test("'all' walks without a depth limit in both directions", async ({ page, request }) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, Infinity, "both");
  expect(expected.ids.length).toBeGreaterThan(neighbourhood(data, subject, 1, "both").ids.length);

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Depth", { exact: true }).selectOption("all");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
});

test("'Hide the rest' hides what the neighbourhood leaves out, and keeps its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, 1, "both");

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Hide the rest", { exact: true }).check();

  await expect
    .poll(() => viewer(page, "visibleIds"))
    .toEqual(sorted(withAncestors(expected.ids, parentMap(data))));
  expect(await viewer(page, "dimmedIds")).toEqual([]);
  expect(new URL(page.url()).searchParams.get("hide")).toBe("1");
});

test("clearing the selection shows the whole graph again", async ({ page, request }) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);

  await openArchitecture(page, `?focus=${subject}&depth=2`);
  await expect.poll(async () => (await viewer(page, "dimmedIds")).length).toBeGreaterThan(0);
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("Escape");

  await expect.poll(() => viewer(page, "dimmedIds")).toEqual([]);
  expect(await viewer(page, "neighbourhood")).toEqual({ ids: [], edges: [] });
});
