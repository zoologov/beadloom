// URL state: filters, focus, depth, direction and the impact view round-trip.
//
// In an earlier version the filters lived in component refs, so a view could not
// be linked. The data mode is not a URL key: it is the page's, and a query cannot
// turn the architecture page into the landscape. Every key the query
// names below differs from its default, so an assertion on it fails when the
// viewer does not read it.

import { test, expect } from "@playwright/test";
import {
  architectureData,
  openArchitecture,
  openEveryBox,
  parentMap,
  viewer,
  waitForViewer,
  withAncestors,
} from "./support/viewer.js";
import { layerOfNode, layerRulesOf, layersOfData } from "./support/layers.js";
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
  // The names the Layer filter offers: every rule's, said with the rule's where there is more than one.
  const layers = layersOfData(data);
  requireShape(
    layers.length > 0,
    "no declared layer; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml"
  );
  const layer = layers[layers.length - 1].label;
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

// A link shared from a portal that drew one layer rule names a layer by its bare
// name (`?layer=domains`). Where two or more rules are drawn, the Layer filter's
// values say the rule's name as well (`architecture-layers: domains`), so such a
// link matched no value: the canvas was filtered to nothing and the select held
// a value it did not offer. A bare name is read as the layer of the rule that
// has it, and where more than one rule has a layer of that name, as the first
// rule's by name: the file lists the rules by name. The URL then carries the
// value the filter offers.

const LACKING_RULES = "fewer than two layer rules; a project with a backend and a frontend declares one for each";
const sorted = (ids) => [...ids].sort();

/** Open `?layer=<bare>` and hold that the filter reads it as `expected`, and shows that layer's nodes. */
async function opensOnLayer(page, data, bare, expected) {
  const layers = layersOfData(data);
  const members = data.nodes.filter((node) => layerOfNode(node, data, layers)?.label === expected.label).map((node) => node.id);
  await openArchitecture(page, `?layer=${encodeURIComponent(bare)}`);
  await openEveryBox(page);

  await expect(page.getByLabel("Layer", { exact: true })).toHaveValue(expected.label);
  await expect.poll(() => new URL(page.url()).searchParams.get("layer")).toBe(expected.label);
  expect(members.length).toBeGreaterThan(0);
  await expect.poll(() => viewer(page, "visibleIds")).toEqual(sorted(withAncestors(members, parentMap(data))));
}

test("a link naming a layer by its bare name opens on that layer where two or more rules are drawn", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(layerRulesOf(data).length > 1, LACKING_RULES);
  const layers = layersOfData(data);
  const populated = (layer) => data.nodes.some((node) => layerOfNode(node, data, layers) === layer);
  // A layer whose name no other rule's layer has, and that holds a node.
  const unique = layers.find((layer) => populated(layer) && layers.filter((other) => other.name === layer.name).length === 1);
  requireShape(Boolean(unique), "no populated layer whose name only one rule has");
  expect(unique.label).not.toBe(unique.name);

  await opensOnLayer(page, data, unique.name, unique);
});

test("a bare layer name two rules share opens on the first rule's layer by name", async ({ page, request }) => {
  const served = await architectureData(request);
  const rules = layerRulesOf(served);
  requireShape(rules.length > 1, LACKING_RULES);
  const servedLayers = layersOfData(served);
  const populated = (layer) => served.nodes.some((node) => layerOfNode(node, served, servedLayers) === layer);
  const [first, second] = rules;
  const shared = servedLayers.find((layer) => layer.rule === first.name && populated(layer));
  const renamed = servedLayers.find((layer) => layer.rule === second.name);
  requireShape(Boolean(shared) && Boolean(renamed), "the first rule places no node, or the second declares no layer");
  // The second rule's top layer renamed to a name the first rule's layer has: nothing else moves.
  const data = {
    ...served,
    layer_rules: served.layer_rules.map((rule) =>
      rule.name !== second.name
        ? rule
        : { ...rule, layers: rule.layers.map((layer) => (layer.rank === renamed.rank ? { ...layer, name: shared.name, token: shared.name } : layer)) }
    ),
  };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  const expected = layersOfData(data).find((layer) => layer.rule === first.name && layer.name === shared.name);
  expect(layersOfData(data).filter((layer) => layer.name === shared.name).map((layer) => layer.rule)).toEqual([first.name, second.name]);

  await opensOnLayer(page, data, shared.name, expected);
});
