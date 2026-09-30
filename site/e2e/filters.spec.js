// Filters keep what nests inside a hidden parent (BDL-076 A2).
//
// Before A2 a filter hid compound parents with `display: none`, and Cytoscape
// hides the children of a hidden parent: `Kind = feature` showed nothing, and
// the domain filter kept direct children only.

import { test, expect } from "@playwright/test";
import {
  architectureData,
  depthOf,
  flaggedIds,
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

test("a layer filter keeps every node in that layer, inherited or its own, with its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  // The declared layer the most nodes are in without a tag of their own, so the
  // case sees the inherited layer and not only the nodes that name it.
  const untagged = (rank) => data.nodes.filter((n) => n.layer_rank === rank && !n.layer).length;
  const declared = data.nodes
    .filter((n) => n.layer && typeof n.layer_rank === "number")
    .sort((a, b) => untagged(b.layer_rank) - untagged(a.layer_rank) || a.id.localeCompare(b.id))[0];
  const members = data.nodes.filter((n) => n.layer_rank === declared.layer_rank).map((n) => n.id);
  expect(untagged(declared.layer_rank)).toBeGreaterThan(0);

  await openArchitecture(page);
  // The filter offers the declared names, not the tag tokens (BDL-076 R1 finding m2).
  const name = data.layers.find((layer) => layer.rank === declared.layer_rank).name;
  await page.getByLabel("Layer", { exact: true }).selectOption(name);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(members, parents))
  );
});

test("the flagged filter keeps every node with a violation or stale docs, with its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  const flagged = flaggedIds(data);
  expect(flagged.some((id) => parents[id] && !flagged.includes(parents[id]))).toBe(true);

  await openArchitecture(page);
  await page.getByLabel("Only flagged", { exact: true }).check();

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(flagged, parents))
  );
});
