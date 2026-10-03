// The layers are the ones the project declares, named as it names them.
//
// The data file carries the declared layers, `[{ name, rank, tag, token }]`, and
// each node its layer's token and rank. Before the fix the viewer rebuilt the
// layers from the node tokens and never read the declaration, so the legend, the
// Layer filter and the card showed the tag token ("infra") where the project
// declared a name ("infrastructure"). The served file below renames every layer
// and gives its tag no `layer-` prefix, so a viewer that read the tags would
// show none of the declared names.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";
import { LACKING, requireShape } from "./support/shape.js";

const CARD = "[data-testid='node-card']";

/** The data file with each declared layer renamed, and its tag and every node's token rewritten. */
async function serveRenamedLayers(page, request) {
  const data = await architectureData(request);
  requireShape((data.layers || []).length > 1, LACKING.layers);
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
    requireShape(node, own ? LACKING.ownLayer : LACKING.inheritedLayer);

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
  requireShape(tokenOfRank.size > 0, LACKING.ownLayer);

  await openArchitecture(page);

  const legend = await page
    .locator("[data-legend-layer]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendLayer));
  expect(legend).toEqual([...tokenOfRank].sort(([a], [b]) => a - b).map(([, token]) => token));
});

// The colours come from the project's declared layers, by position, not from a
// palette keyed to one project's layer names: before slice 2 the viewer coloured
// four names of its own and drew every other project's layers in the grey of a
// node in no layer. Read on the portal as built, without renaming anything.
test("each declared layer is drawn in a colour of its own, apart from a node in no layer", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  requireShape((data.layers || []).length > 1, LACKING.layers);

  await openArchitecture(page);
  const borders = new Map(
    (await viewer(page, "colours"))
      .filter((entry) => entry.property === "border-color")
      .map((entry) => [entry.element, entry.value.replace(/\s+/g, "")])
  );
  // A status is drawn over the layer's colour, so a node with one says nothing here.
  const withStatus = new Set(Object.keys(await viewer(page, "statusLooks")));
  const drawn = data.nodes.filter((node) => borders.has(node.id) && !withStatus.has(node.id));
  const declaredRanks = new Set(data.layers.map((layer) => layer.rank));
  const coloursOfRank = new Map();
  for (const node of drawn.filter((n) => declaredRanks.has(n.layer_rank))) {
    if (!coloursOfRank.has(node.layer_rank)) coloursOfRank.set(node.layer_rank, new Set());
    coloursOfRank.get(node.layer_rank).add(borders.get(node.id));
  }
  const unlayered = new Set(
    drawn.filter((n) => typeof n.layer_rank !== "number").map((n) => borders.get(n.id))
  );
  // The tones repeat after five layers, so distinctness is asked of the top five.
  const topRanks = [...coloursOfRank.keys()].sort((a, b) => a - b).slice(0, 5);
  const colourOf = (rank) => [...coloursOfRank.get(rank)].join(" | ");

  expect(topRanks.length).toBeGreaterThan(1);
  expect([...coloursOfRank.values()].every((colours) => colours.size === 1)).toBe(true);
  expect(new Set(topRanks.map(colourOf)).size).toBe(topRanks.length);
  expect(topRanks.filter((rank) => unlayered.has(colourOf(rank)))).toEqual([]);
});
