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
import { architectureData, openArchitecture, openEveryBox, viewer } from "./support/viewer.js";
import { LACKING, requireShape } from "./support/shape.js";
import { canvasBackground, channelDistance, drawnColours, legendSamples, over } from "./support/look.js";
import { treeOf } from "./support/map.js";

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
  // Every node's border, at full detail: at the whole-graph fit only the boxes at the top are drawn.
  await openEveryBox(page);
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

// A node is drawn as the legend draws its layer: a border in the layer's tone
// over a tint of it. Before, only a box was: a box closed at the overview was
// tinted in its layer's tone while a node with nothing inside it was a card in
// the page's soft grey with a border in that tone, so at the whole-graph fit,
// where both are drawn as boxes side by side, a top-level node with nothing
// inside it read as another kind of thing than the boxes of its own layer beside
// it (owner, 2026-10-06), and every node inside an open box was grey. An open box keeps its own fainter tint (`look.spec.js`).
for (const colorScheme of ["light", "dark"]) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("every node is drawn in its layer's colour as the legend draws it, a node with nothing inside it as a box, at the overview and inside an open box", async ({
      page,
      request,
    }) => {
      const data = await architectureData(request);
      requireShape((data.layers || []).length > 0, "no declared layer; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml");
      const layerOf = new Map(data.nodes.map((node) => [node.id, data.layers.find((layer) => layer.rank === node.layer_rank)?.name]));
      await openArchitecture(page);
      const samples = await legendSamples(page);
      const background = await canvasBackground(page);

      const offLegend = async (state) => {
        const looks = await viewer(page, "nodeLooks");
        const drawn = drawnColours(looks, background);
        const kinds = { leaf: 0, box: 0 };
        const off = [];
        for (const look of looks) {
          const sample = samples.get(layerOf.get(look.id));
          // An open box is drawn fainter, so its nodes stand out on it; a node in no layer has no sample.
          if (!sample || (look.isParent && !look.collapsed)) continue;
          kinds[look.collapsed ? "box" : "leaf"] += 1;
          const wanted = over(sample.tone, drawn(look.parent), sample.share);
          if (channelDistance(drawn(look.id), wanted) > 1 || channelDistance(look.borderColour, sample.tone) > 0) {
            off.push(`${state} ${look.id} (${look.collapsed ? "box" : "leaf"}, ${layerOf.get(look.id)}): fill ${drawn(look.id)} for ${wanted}, border ${look.borderColour} for ${sample.tone}`);
          }
        }
        return { kinds, off };
      };

      const overview = await offLegend("overview");
      await openEveryBox(page, { edges: false });
      const detail = await offLegend("every box open");
      requireShape(overview.kinds.leaf + detail.kinds.leaf > 0, "no node with nothing inside it is drawn in a declared layer");
      expect([...overview.off, ...detail.off]).toEqual([]);
    });
  });
}

// A node in no layer is drawn in a neutral tone of its own (`UNLAYERED_TONE`),
// and before, the legend said nothing about it: on this portal the node of the
// documentation site, in no layer, was the one grey box with no key. The legend
// now names it, and only where the graph has such a node; the served file is read
// once as it is and once turned the other way, so both answers are asked on
// every portal, whether it declares layers or not. The box that holds everything
// is drawn as the project's frame whatever its layer, so it is no such node.

/** Whether `node` is in a layer of `data`'s: the declared ranks, or, where none is declared, any rank. */
function inALayer(node, data) {
  const declared = (data.layers || []).filter((layer) => typeof layer?.rank === "number").map((layer) => layer.rank);
  return typeof node.layer_rank === "number" && (!declared.length || declared.includes(node.layer_rank));
}

/** The ids of `data`'s nodes drawn in no layer's tone: those in no layer but the box that holds everything. */
function unlayeredOf(data) {
  const { wrapper } = treeOf(data);
  return data.nodes.filter((node) => node.id !== wrapper && !inALayer(node, data)).map((node) => node.id);
}

/**
 * `data` turned the other way: with a node drawn in no layer's tone, every such
 * node put in the first declared layer, or in one declared here where none is;
 * without one, the first node by id but the box that holds everything taken out
 * of its layer.
 */
function withTheOtherAnswer(data) {
  const unlayered = new Set(unlayeredOf(data));
  if (unlayered.size) {
    const layers = data.layers?.length ? data.layers : [{ name: "the one layer", rank: 0, tag: "the-one-layer", token: "the-one-layer" }];
    const rank = Math.min(...layers.map((layer) => layer.rank));
    return { ...data, layers, nodes: data.nodes.map((node) => (unlayered.has(node.id) ? { ...node, layer_rank: rank } : node)) };
  }
  const { wrapper } = treeOf(data);
  const [first, ...rest] = [...data.nodes].sort((a, b) => (a.id === wrapper) - (b.id === wrapper) || a.id.localeCompare(b.id));
  const { layer_rank: _rank, layer: _token, ...unlayeredFirst } = first;
  return { ...data, nodes: [unlayeredFirst, ...rest] };
}

for (const turned of [false, true]) {
  test(`the legend names 'no layer' exactly when a node is in no layer, in the colour such a node is drawn in${turned ? ", on the file turned the other way" : ""}`, async ({
    page,
    request,
  }) => {
    const served = await architectureData(request);
    const data = turned ? withTheOtherAnswer(served) : served;
    if (turned) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
    const unlayered = unlayeredOf(data);

    await openArchitecture(page);

    const entry = page.locator("[data-legend-unlayered]");
    await expect(entry).toHaveCount(unlayered.length ? 1 : 0);
    if (!unlayered.length) return;
    await expect(entry).toHaveText("no layer");
    // Its sample is drawn as such a node is: its border in the node's border colour.
    await openEveryBox(page, { edges: false });
    const sample = await entry.locator(".bl-legend-swatch").evaluate((swatch) => getComputedStyle(swatch).borderTopColor);
    const borders = (await viewer(page, "nodeLooks")).filter((look) => unlayered.includes(look.id)).map((look) => look.borderColour);
    expect(borders.length).toBeGreaterThan(0);
    expect(borders.filter((border) => channelDistance(border, sample) > 0)).toEqual([]);
  });
}
