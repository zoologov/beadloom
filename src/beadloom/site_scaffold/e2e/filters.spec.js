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
import { LACKING, requireShape } from "./support/shape.js";

const sorted = (ids) => [...ids].sort();

const NO_NESTING = "no node sits inside another: the graph has no part_of edge";

test("a kind filter keeps every node of that kind visible, with its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  // A feature inside a container when the graph has one; otherwise the kind the
  // most nodes inside a container are of, so the containers kept are seen.
  const nested = (kind) => data.nodes.filter((n) => n.kind === kind && parents[n.id]).length;
  const kind = nested("feature")
    ? "feature"
    : [...new Set(data.nodes.map((n) => n.kind))].sort((a, b) => nested(b) - nested(a) || a.localeCompare(b))[0];
  requireShape(nested(kind) > 0, NO_NESTING);
  const ofKind = data.nodes.filter((n) => n.kind === kind).map((n) => n.id);

  await openArchitecture(page);
  await page.getByLabel("Kind", { exact: true }).selectOption(kind);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(ofKind, parents))
  );
});

test("a domain filter keeps the domain's whole subtree", async ({ page, request }) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  // How far below a domain its subtree reaches.
  const reach = (domain) =>
    Math.max(...[...subtreeOf(domain, parents)].map((id) => depthOf(id, parents) - depthOf(domain, parents)));
  // The domain whose subtree reaches deepest, so the test sees more than direct children.
  const domain = data.nodes
    .filter((n) => n.kind === "domain")
    .map((n) => n.id)
    .sort((a, b) => reach(b) - reach(a) || a.localeCompare(b))[0];
  requireShape(domain && reach(domain) >= 2, "no domain holds a node two levels below it");
  const subtree = subtreeOf(domain, parents);

  await openArchitecture(page);
  await page.getByLabel("Domain", { exact: true }).selectOption(domain);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(subtree, parents))
  );
});

test("the search box keeps the matching nodes and their containers", async ({ page, request }) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  // A node two levels below the top, or failing that one level, so its containers are kept.
  const target =
    data.nodes.find((n) => parents[n.id] && parents[parents[n.id]]) ?? data.nodes.find((n) => parents[n.id]);
  requireShape(target, NO_NESTING);
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
  requireShape(declared && untagged(declared.layer_rank) > 0, LACKING.inheritedLayer);
  const members = data.nodes.filter((n) => n.layer_rank === declared.layer_rank).map((n) => n.id);

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
  requireShape(
    flagged.some((id) => parents[id] && !flagged.includes(parents[id])),
    "no flagged node (a rule violation or stale docs) sits inside a container that is not flagged"
  );

  await openArchitecture(page);
  await page.getByLabel("Only flagged", { exact: true }).check();

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(
    sorted(withAncestors(flagged, parents))
  );
});
