// The layers are the ones the project declares, named as it names them (BDL-076 R1 finding m2).
//
// The data file carries the declared layers, `[{ name, rank, tag, token }]`, and
// each node its layer's token and rank. Before the fix the viewer rebuilt the
// layers from the node tokens and never read the declaration, so the legend, the
// Layer filter and the card showed the tag token ("infra") where the project
// declared a name ("infrastructure"). The served file below renames every layer
// and gives its tag no `layer-` prefix, so a viewer that read the tags would
// show none of the declared names.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture } from "./support/viewer.js";

const CARD = "[data-testid='node-card']";

/** The data file with each declared layer renamed, and its tag and every node's token rewritten. */
async function serveRenamedLayers(page, request) {
  const data = await architectureData(request);
  expect(data.layers.length).toBeGreaterThan(1);
  const tokens = new Map();
  data.layers = data.layers.map((layer, index) => {
    const token = `zone-${index}`;
    tokens.set(layer.token, token);
    return { ...layer, name: `Declared tier ${index + 1}`, tag: token, token };
  });
  for (const node of data.nodes) {
    if (node.layer) node.layer = tokens.get(node.layer);
    if (node.tags) node.tags = node.tags.map((tag) => tokens.get(tag.replace(/^layer-/, "")) || tag);
  }
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  return data;
}

const nameOfRank = (data, rank) => data.layers.find((layer) => layer.rank === rank).name;

test("the legend names the declared layers, top to bottom", async ({ page, request }) => {
  const data = await serveRenamedLayers(page, request);

  await openArchitecture(page);

  const legend = await page
    .locator("[data-legend-layer]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendLayer));
  expect(legend).toEqual([...data.layers].sort((a, b) => a.rank - b.rank).map((l) => l.name));
});

test("the Layer filter offers the declared names and keeps the nodes in that layer", async ({
  page,
  request,
}) => {
  const data = await serveRenamedLayers(page, request);
  const layer = data.layers[data.layers.length - 1];

  await openArchitecture(page);
  const offered = await page
    .getByLabel("Layer", { exact: true })
    .locator("option")
    .evaluateAll((options) => options.map((option) => option.value));
  await page.getByLabel("Layer", { exact: true }).selectOption(layer.name);

  expect(offered).toEqual(["all", ...data.layers.map((l) => l.name)]);
  await expect.poll(() => new URL(page.url()).searchParams.get("layer")).toBe(layer.name);
});

for (const own of [true, false]) {
  test(`the card names the declared layer of a node whose layer is ${own ? "its own" : "inherited"}`, async ({
    page,
    request,
  }) => {
    const data = await serveRenamedLayers(page, request);
    const node = data.nodes
      .filter((n) => typeof n.layer_rank === "number" && Boolean(n.layer) === own)
      .sort((a, b) => a.id.localeCompare(b.id))[0];

    await openArchitecture(page, `?focus=${node.id}`);

    await expect(page.locator(`${CARD} [data-card-field='layer']`)).toContainText(
      nameOfRank(data, node.layer_rank)
    );
  });
}

test("a file that declares no layer names falls back to the nodes' tokens", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  delete data.layers;
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  const tokenOfRank = new Map();
  for (const node of data.nodes) {
    if (node.layer && !tokenOfRank.has(node.layer_rank)) tokenOfRank.set(node.layer_rank, node.layer);
  }

  await openArchitecture(page);

  const legend = await page
    .locator("[data-legend-layer]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendLayer));
  expect(legend).toEqual([...tokenOfRank].sort(([a], [b]) => a - b).map(([, token]) => token));
});
