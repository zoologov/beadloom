// Filters keep what nests inside a hidden parent (BDL-076 A2).
//
// Before A2 a filter hid compound parents with `display: none`, and Cytoscape
// hides the children of a hidden parent: `Kind = feature` showed nothing, and
// the domain filter kept direct children only.

import { test, expect } from "@playwright/test";
import {
  architectureData,
  depthOf,
  openArchitecture,
  parentMap,
  subtreeOf,
  viewer,
  withAncestors,
} from "./support/viewer.js";

const sorted = (ids) => [...ids].sort();

test("a kind filter keeps every node of that kind visible, with its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  const features = data.nodes.filter((n) => n.kind === "feature").map((n) => n.id);
  expect(features.some((id) => parents[id])).toBe(true);

  await openArchitecture(page);
  await page.getByLabel("Kind", { exact: true }).selectOption("feature");

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(features, parents))
  );
});

test("a domain filter keeps the domain's whole subtree", async ({ page, request }) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  const domains = data.nodes.filter((n) => n.kind === "domain").map((n) => n.id);
  // The domain holding the deepest node, so the test sees more than direct children.
  const deepest = data.nodes.map((n) => n.id).sort((a, b) => depthOf(b, parents) - depthOf(a, parents))[0];
  const domain = domains.find((d) => subtreeOf(d, parents).has(deepest)) ?? domains[0];
  const subtree = subtreeOf(domain, parents);
  expect([...subtree].some((id) => depthOf(id, parents) - depthOf(domain, parents) >= 2)).toBe(true);

  await openArchitecture(page);
  await page.getByLabel("Domain", { exact: true }).selectOption(domain);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(subtree, parents))
  );
});

test("the search box keeps the matching nodes and their containers", async ({ page, request }) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  const target = data.nodes.find((n) => parents[n.id] && parents[parents[n.id]]);
  const query = target.id;
  const matches = data.nodes
    .filter((n) => n.id.toLowerCase().includes(query.toLowerCase()))
    .map((n) => n.id);

  await openArchitecture(page);
  await page.getByRole("searchbox", { name: "Search nodes" }).fill(query);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(sorted(withAncestors(matches, parents)));
});
