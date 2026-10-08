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
import { architectureData, openArchitecture, openEveryBox, parentMap, viewer } from "./support/viewer.js";
import { LACKING, requireShape } from "./support/shape.js";
import { canvasBackground, channelDistance, drawnColours, legendSamples, over } from "./support/look.js";
import { treeOf } from "./support/map.js";
import { layerBoxesOf, layerOfNode, layerRulesOf, layersOfData, withoutLayerRules } from "./support/layers.js";

const CARD = "[data-testid='node-card']";

/** The data file with each declared layer renamed, and its tag and every node's token rewritten. */
async function serveRenamedLayers(page, request) {
  // The one order a file without every rule's keys names (`layer-rules` cases below read every rule).
  const data = withoutLayerRules(await architectureData(request));
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
  const data = withoutLayerRules(await architectureData(request));
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
// node in no layer. Read on the portal as built, without renaming anything. A
// layer is its rule's: each rule's layers take the tones by their
// own position, so a rule of six layers — Feature-Sliced Design's — has six, and
// before, the sixth repeated the first and this portal's site slices were all
// drawn in the tone of their service's layer.
test("each declared layer is drawn in a colour of its own within its rule, six tones for six layers, apart from a node in no layer", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const layers = layersOfData(data);
  requireShape(layers.length > 1, LACKING.layers);

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
  const coloursOf = new Map();
  for (const node of drawn) {
    const layer = layerOfNode(node, data, layers);
    if (!layer) continue;
    if (!coloursOf.has(layer)) coloursOf.set(layer, new Set());
    coloursOf.get(layer).add(borders.get(node.id));
  }
  // A box a scoped rule draws is in its layer's tone too, and carries no status.
  for (const box of layerBoxesOf(data).filter((b) => borders.has(b.id))) {
    const layer = layers.find((l) => l.rule === box.rule && l.rank === box.rank);
    if (!coloursOf.has(layer)) coloursOf.set(layer, new Set());
    coloursOf.get(layer).add(borders.get(box.id));
  }
  const unlayered = new Set(drawn.filter((n) => !layerOfNode(n, data, layers)).map((n) => borders.get(n.id)));
  const colourOf = (layer) => [...coloursOf.get(layer)].join(" | ");
  // The tones repeat after six layers, so distinctness is asked of each rule's top six.
  const rules = [...new Set(layers.map((layer) => layer.rule))];
  const topOf = (rule) => layers.filter((layer) => layer.rule === rule && coloursOf.has(layer)).slice(0, 6);

  expect([...coloursOf.keys()].length).toBeGreaterThan(1);
  expect([...coloursOf.values()].filter((colours) => colours.size !== 1).length).toBe(0);
  for (const rule of rules) {
    const top = topOf(rule);
    expect(new Set(top.map(colourOf)).size, `${rule ?? "the declared layers"}: ${top.map((l) => `${l.name} ${colourOf(l)}`).join(", ")}`).toBe(top.length);
    expect(top.filter((layer) => unlayered.has(colourOf(layer))).map((layer) => layer.label)).toEqual([]);
  }
  // A rule of six layers with a node in each is drawn in six tones, where the portal has one.
  const sixes = rules.filter((rule) => topOf(rule).length === 6);
  requireShape(sixes.length > 0, "no layer rule of six layers with a node drawn in each, as a Feature-Sliced frontend's");
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
      const layers = layersOfData(data);
      requireShape(layers.length > 0, "no declared layer; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml");
      // Each node by the name the legend gives its layer, and each box a scoped rule draws by its layer's.
      const layerOf = new Map(data.nodes.map((node) => [node.id, layerOfNode(node, data, layers)?.label]));
      for (const box of layerBoxesOf(data)) layerOf.set(box.id, layers.find((l) => l.rule === box.rule && l.rank === box.rank).label);
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

/**
 * Whether `node` is in a layer of `data`'s: its rule's, where the file carries
 * every rule; else the declared ranks, or, where none is declared, any rank.
 */
function inALayer(node, data) {
  if (layerRulesOf(data).length) return Boolean(layerOfNode(node, data));
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
  const [rule] = layerRulesOf(data);
  if (unlayered.size && rule) {
    const top = Math.min(...rule.layers.map((layer) => layer.rank));
    return { ...data, nodes: data.nodes.map((node) => (unlayered.has(node.id) ? { ...node, layer_rule: rule.name, layer_rule_rank: top } : node)) };
  }
  if (unlayered.size) {
    const layers = data.layers?.length ? data.layers : [{ name: "the one layer", rank: 0, tag: "the-one-layer", token: "the-one-layer" }];
    const rank = Math.min(...layers.map((layer) => layer.rank));
    return { ...data, layers, nodes: data.nodes.map((node) => (unlayered.has(node.id) ? { ...node, layer_rank: rank } : node)) };
  }
  const { wrapper } = treeOf(data);
  const [first, ...rest] = [...data.nodes].sort((a, b) => (a.id === wrapper) - (b.id === wrapper) || a.id.localeCompare(b.id));
  const { layer_rank: _rank, layer: _token, ...untokened } = first;
  const unlayeredFirst = rule ? { ...untokened, layer_rule: "", layer_rule_rank: null } : untokened;
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

// Every layer rule is drawn. Before, the viewer read the
// first rule by name and nothing else, so a project with a backend and a frontend
// drew its frontend in the tone of the backend layer that held it: on this portal
// the twenty site slices were drawn as "services", the Layer filter offered none
// of their layers and the card named none. A layer is now its rule's: the legend
// groups each rule's layers under its name, the filter names a layer with its
// rule's, the card names the rule beside the layer, and the lanes inside a box
// follow the rule its parts are placed by.

const LACKING_RULES = "fewer than two layer rules; a project with a backend and a frontend declares one for each";

test("the legend groups the layers per rule, each rule's top to bottom, under the rule's name", async ({ page, request }) => {
  const data = await architectureData(request);
  const rules = layerRulesOf(data);
  requireShape(rules.length > 1, LACKING_RULES);
  const layers = layersOfData(data);

  await openArchitecture(page);

  const groups = await page.locator("[data-legend-rule]").evaluateAll((items) =>
    items.map((item) => ({
      rule: item.dataset.legendRule,
      heading: item.querySelector(".bl-legend-group")?.textContent.trim(),
      layers: [...item.querySelectorAll("[data-legend-layer]")].map((layer) => [layer.dataset.legendLayer, layer.textContent.trim()]),
    }))
  );
  expect(groups).toEqual(
    rules.map((rule) => ({
      rule: rule.name,
      heading: `${rule.name} (top → bottom):`,
      layers: layers.filter((layer) => layer.rule === rule.name).map((layer) => [layer.label, layer.name]),
    }))
  );
});

test("the Layer filter offers each layer by its rule's name and its own, and keeps the nodes of the one chosen", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(layerRulesOf(data).length > 1, LACKING_RULES);
  const layers = layersOfData(data);
  // The last rule's busiest layer: on this portal a layer of the site's slices, which no filter offered before.
  const lastRule = layers[layers.length - 1].rule;
  const membersOf = (layer) => data.nodes.filter((node) => layerOfNode(node, data, layers) === layer).map((node) => node.id);
  const chosen = layers.filter((layer) => layer.rule === lastRule).sort((a, b) => membersOf(b).length - membersOf(a).length)[0];

  await openArchitecture(page);
  const select = page.getByLabel("Layer", { exact: true });
  const offered = await select.locator("option").evaluateAll((options) => options.map((option) => option.value));
  expect(offered).toEqual(["all", ...layers.map((layer) => `${layer.rule}: ${layer.name}`)]);
  await select.selectOption(chosen.label);

  await expect.poll(() => new URL(page.url()).searchParams.get("layer")).toBe(chosen.label);
  // What the filter keeps inside closed boxes is drawn once its boxes are open.
  await openEveryBox(page, { edges: false });
  const shown = new Set(await viewer(page, "visibleIds"));
  const members = membersOf(chosen);
  expect(members.length).toBeGreaterThan(0);
  expect(members.filter((id) => !shown.has(id))).toEqual([]);
  const others = data.nodes.filter((node) => shown.has(node.id) && !members.includes(node.id) && !data.nodes.some((n) => n.parent === node.id));
  expect(others.map((node) => node.id)).toEqual([]);
});

for (const own of [true, false]) {
  test(`the card names the layer and the rule that places a node whose layer is ${own ? "its own" : "inherited"}`, async ({ page, request }) => {
    const data = await architectureData(request);
    requireShape(layerRulesOf(data).length > 1, LACKING_RULES);
    const layers = layersOfData(data);
    // A node of the last rule where it has one, so the rule named is not the first rule by name.
    const candidates = data.nodes
      .filter((node) => {
        const layer = layerOfNode(node, data, layers);
        return layer && (node.tags || []).includes(layer.tag) === own;
      })
      .sort((a, b) => (b.layer_rule || "").localeCompare(a.layer_rule || "") || a.id.localeCompare(b.id));
    const node = candidates[0];
    requireShape(node, own ? LACKING.ownLayer : LACKING.inheritedLayer);
    const layer = layerOfNode(node, data, layers);

    await openArchitecture(page, `?focus=${node.id}`);

    const field = page.locator(`${CARD} [data-card-field='layer']`);
    await expect(field).toContainText(layer.name);
    await expect(field).toContainText(layer.rule);
    await expect(field).toContainText(own ? "its own tag" : "inherited through part_of");
  });
}

// Read on the graph with only its containment, so what orders the layers is the
// lanes and not the edges: a Feature-Sliced frontend imports downward, and ELK
// alone lays such slices out top to bottom whether or not they have lanes. And
// read without the project's frame, because ELK keeps lanes among the nodes at
// the top of the graph only (`shared/elk/graph.js`): inside a box it stacks only
// the layer boxes a scoped rule draws, which it is asked to.
test("lanes partition the siblings of one rule: at the top, and inside a scope by its layer boxes, each layer lies below the one above it", async ({ page, request }) => {
  const served = await architectureData(request);
  requireShape(layerRulesOf(served).length > 1, LACKING_RULES);
  const { wrapper } = treeOf(served);
  const nodes = served.nodes.filter((node) => node.id !== wrapper).map((node) => (node.parent === wrapper ? { ...node, parent: node.id } : node));
  const data = { ...served, nodes, edges: served.edges.filter((edge) => edge.kind === "part_of" && edge.dst !== wrapper && edge.src !== wrapper) };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  const layers = layersOfData(data);
  await openArchitecture(page);
  const { boxes } = await viewer(page, "elkGeometry");
  const parents = parentMap(data);
  // Each drawn node's layer: a node's own, a layer box's the layer it is drawn for.
  const layerOf = new Map(data.nodes.map((node) => [node.id, layerOfNode(node, data, layers)]));
  const scopes = new Set();
  for (const box of layerBoxesOf(data)) {
    layerOf.set(box.id, layers.find((l) => l.rule === box.rule && l.rank === box.rank));
    scopes.add(box.scope);
  }

  const crossed = [];
  const judged = new Set();
  let partitioned = 0;
  const siblingsOf = new Map();
  for (const [id, parent] of Object.entries(parents)) {
    if ((parent && !scopes.has(parent)) || !layerOf.get(id) || !boxes[id]) continue;
    if (!siblingsOf.has(parent)) siblingsOf.set(parent, []);
    siblingsOf.get(parent).push(id);
  }
  for (const [parent, ids] of siblingsOf) {
    // Of a box holding parts of two rules, the siblings of the rule that places most of them.
    const counts = new Map();
    for (const id of ids) counts.set(layerOf.get(id).rule, (counts.get(layerOf.get(id).rule) || 0) + 1);
    const rule = [...counts].sort(([, m], [, n]) => n - m)[0][0];
    const ofRule = ids.filter((id) => layerOf.get(id).rule === rule);
    for (const a of ofRule) {
      for (const b of ofRule) {
        const [la, lb] = [layerOf.get(a), layerOf.get(b)];
        if (la.rank >= lb.rank) continue;
        partitioned += 1;
        judged.add(parent ?? "the top");
        if (boxes[a].y2 > boxes[b].y1 + 1e-6) crossed.push(`${parent ?? "the top"}: ${a} (${la.name}) reaches below ${b} (${lb.name})`);
      }
    }
  }
  expect([...judged].sort()).toEqual(["the top", ...scopes].sort());
  expect(partitioned).toBeGreaterThan(0);
  expect(crossed).toEqual([]);
});

// A file that carries every rule's keys and declares one rule is drawn as the same
// file without them (the file keeps its schema version, and a viewer reading the old
// keys sees what it saw). The viewer reads the new keys where a file has them and
// the old ones where it has not; on a project of one layer rule the two readings
// must be one picture. The file is made from the served one by keeping its first
// rule by name, whose placement the old keys carry: a node's layer is its
// `layer_rank`. A rule scoped to a box would add its layer boxes, which
// `layer-boxes.spec.js` holds, so such a scope is left out here.

/** `data` reduced to its first layer rule, placed as the old keys place it. */
function firstRuleOnly(data) {
  const [first] = layerRulesOf(data);
  const nodes = data.nodes.map((node) => ({
    ...node,
    layer_rule: typeof node.layer_rank === "number" ? first.name : "",
    layer_rule_rank: typeof node.layer_rank === "number" ? node.layer_rank : null,
  }));
  const reduced = { ...data, nodes, layer_rules: [first] };
  return layerBoxesOf(reduced).length ? { ...reduced, layer_rules: [{ ...first, scope: "" }] } : reduced;
}

/** What one served file draws: every node's place, look and box, the legend, and the filter's values. */
async function drawingOf(page, data) {
  await page.unroute("**/architecture.data.json");
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  await openEveryBox(page, { edges: false });
  const looks = Object.fromEntries(
    (await viewer(page, "nodeLooks")).map((look) => [look.id, [look.parent, look.fill, look.borderColour, look.shape]])
  );
  return {
    positions: await viewer(page, "positions"),
    looks,
    legend: await page.locator("[data-legend-layer]").evaluateAll((items) => items.map((item) => [item.dataset.legendLayer, item.textContent.trim()])),
    filter: await page.getByLabel("Layer", { exact: true }).locator("option").evaluateAll((options) => options.map((option) => option.value)),
  };
}

test("a file of one layer rule is drawn the same with every rule's keys as without them", async ({ page, request }) => {
  const served = await architectureData(request);
  requireShape(layerRulesOf(served).length > 0, "no layer rule; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml");
  const oneRule = firstRuleOnly(served);

  const withKeys = await drawingOf(page, oneRule);
  const withoutKeys = await drawingOf(page, withoutLayerRules(oneRule));

  expect(withKeys.legend.length).toBeGreaterThan(1);
  expect(withKeys).toEqual(withoutKeys);
});
