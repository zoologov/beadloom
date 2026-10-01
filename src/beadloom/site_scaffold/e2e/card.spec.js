// The node card: every field the index holds, clickable edges, commands to copy (BDL-076 A3, US-3).
//
// Before A3 the card showed kind, layer, a symbol count, one aggregate doc
// status and the two dependency lists: no source, no tests, no findings, no
// activity or debt, and nothing to copy.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";
import { LACKING, requireShape } from "./support/shape.js";

const CARD = "[data-testid='node-card']";

/** How many of the card's optional fields a node fills. */
function richness(node) {
  return [
    node.summary,
    (node.tags || []).length,
    node.source,
    (node.docs || []).length,
    node.tests?.count,
    (node.public_symbols?.names || []).length,
    (node.findings || []).length,
    node.activity?.commits_30d,
    node.debt,
    node.url,
  ].filter(Boolean).length;
}

function richest(data) {
  return [...data.nodes].sort((a, b) => richness(b) - richness(a) || a.id.localeCompare(b.id))[0];
}

/**
 * The richest node with a finding, so the card's findings are read as well; the
 * richest node when no node has a finding, whose card then holds none to read.
 */
function richestWithFindings(data) {
  const found = data.nodes.filter((n) => (n.findings || []).length > 0);
  return richest(found.length ? { nodes: found } : data);
}

function field(page, name) {
  return page.locator(`${CARD} [data-card-field='${name}']`);
}

test("the card shows every field the data file holds for the node", async ({ page, request }) => {
  const data = await architectureData(request);
  const node = richestWithFindings(data);

  await openArchitecture(page, `?focus=${node.id}`);

  await expect(field(page, "kind")).toContainText(node.kind);
  await expect(field(page, "summary")).toContainText(node.summary);
  await expect(field(page, "lifecycle")).toContainText(node.lifecycle);
  await expect(field(page, "layer")).not.toBeEmpty();
  await expect(field(page, "source")).toContainText(node.source);
  if (node.source_url) {
    await expect(field(page, "source").locator("a")).toHaveAttribute("href", node.source_url);
  } else {
    await expect(field(page, "source").locator("a")).toHaveCount(0);
  }
  for (const doc of node.docs) {
    await expect(field(page, "docs")).toContainText(doc.path);
    await expect(field(page, "docs")).toContainText(doc.status);
  }
  await expect(field(page, "tests")).toContainText(String(node.tests.count));
  for (const [placement, count] of Object.entries(node.tests.placement)) {
    await expect(field(page, "tests")).toContainText(`${placement}: ${count}`);
  }
  if (node.public_symbols.names.length) {
    await expect(field(page, "symbols")).toContainText(node.public_symbols.names[0]);
  }
  for (const finding of node.findings) {
    await expect(field(page, "findings")).toContainText(finding.rule);
    await expect(field(page, "findings")).toContainText(finding.message);
  }
  await expect(field(page, "activity")).toContainText(String(node.activity.commits_30d));
  if (node.debt) await expect(field(page, "debt")).toContainText(String(node.debt.score));
  await expect(field(page, "page").locator("a")).toHaveAttribute("href", new RegExp(`${node.url}(\\.html)?$`));
  await expect(field(page, "commands")).toContainText(`beadloom ctx ${node.id}`);
  await expect(field(page, "commands")).toContainText(`beadloom why ${node.id}`);
});

/** The text of a card field without its heading, whitespace collapsed. */
function fieldValue(page, name) {
  return field(page, name).evaluate((element) =>
    [...element.childNodes]
      .filter((child) => !/^H\d$/.test(child.nodeName))
      .map((child) => child.textContent)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim()
  );
}

/** For each field, how a node comes to hold nothing for it in a version 2 data file. */
const EMPTIED = {
  tags: (node) => Object.assign(node, { tags: [] }),
  layer: (node) => Object.assign(node, { layer: "", layer_rank: null }),
  docs: (node) => Object.assign(node, { docs: [] }),
  symbols: (node) => Object.assign(node, { public_symbols: { names: [], omitted: 0 } }),
  findings: (node) => Object.assign(node, { findings: [], lint_clean: true }),
};

for (const [name, empty] of Object.entries(EMPTIED)) {
  test(`the card says none where the data file holds no ${name} for the node`, async ({
    page,
    request,
  }) => {
    const data = await architectureData(request);
    const node = richest(data);
    empty(node);
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, name)).toBe("none");
  });
}

/** How the card words where a node's layer comes from. */
const LAYER_ORIGINS = [
  { origin: "its own tag", own: true },
  { origin: "inherited through part_of", own: false },
];

for (const { origin, own } of LAYER_ORIGINS) {
  test(`the card names the node's layer and says it is ${origin}`, async ({ page, request }) => {
    const data = await architectureData(request);
    const node = data.nodes
      .filter((n) => typeof n.layer_rank === "number" && Boolean(n.layer) === own)
      .sort((a, b) => a.id.localeCompare(b.id))[0];
    requireShape(node, own ? LACKING.ownLayer : LACKING.inheritedLayer);
    // The declared name of the node's layer, not the tag token (BDL-076 R1 finding m2).
    const layer = data.layers.find((l) => l.rank === node.layer_rank).name;

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, "layer")).toBe(`${layer} (${origin})`);
  });
}

test("every edge kind the node has is listed by direction, and a click moves the selection", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const drawn = new Set(["depends_on", "uses", "consumes", "produces"]);
  const edgesOf = (id) => data.edges.filter((e) => drawn.has(e.kind) && (e.src === id || e.dst === id));
  // The node with the most drawn edges among those with one going out, so the click has a target.
  const node = data.nodes
    .filter((n) => edgesOf(n.id).some((e) => e.src === n.id))
    .sort((a, b) => edgesOf(b.id).length - edgesOf(a.id).length)[0];
  requireShape(node, "no drawn edge: no depends_on, uses, consumes or produces edge between two nodes");
  const outgoing = edgesOf(node.id).find((e) => e.src === node.id);

  await openArchitecture(page, `?focus=${node.id}`);
  const listed = await field(page, "edges")
    .locator("[data-edge-target]")
    .evaluateAll((items) => items.map((i) => `${i.dataset.edgeKind}:${i.dataset.edgeDirection}:${i.dataset.edgeTarget}`));
  const expected = edgesOf(node.id).map((e) =>
    e.src === node.id ? `${e.kind}:out:${e.dst}` : `${e.kind}:in:${e.src}`
  );
  expect([...new Set(listed)].sort()).toEqual([...new Set(expected)].sort());

  await field(page, "edges")
    .locator(`[data-edge-direction='out'][data-edge-target='${outgoing.dst}']`)
    .first()
    .click();
  await expect.poll(() => viewer(page, "selection")).toBe(outgoing.dst);
});

test("the card copies the ctx and why commands", async ({ page, request, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const data = await architectureData(request);
  const node = richest(data);
  await openArchitecture(page, `?focus=${node.id}`);

  for (const command of [`beadloom ctx ${node.id}`, `beadloom why ${node.id}`]) {
    await field(page, "commands").getByRole("button", { name: `Copy: ${command}` }).click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(command);
  }
});

// The data file carries at most 50 public names per node and counts the rest
// (`PUBLIC_SYMBOL_CAP`, pinned by the Python tests). The card names the total,
// says when it shows only the first names, and lists exactly the names it holds.
const SYMBOL_CAP = 50;
const SYMBOL_CASES = [
  { omitted: 7, summary: `${SYMBOL_CAP + 7} names, the first ${SYMBOL_CAP} shown` },
  { omitted: 0, summary: `${SYMBOL_CAP} names` },
];

for (const { omitted, summary } of SYMBOL_CASES) {
  test(`the card lists the ${SYMBOL_CAP} names it holds and reads "${summary}" when ${omitted} are left out`, async ({
    page,
    request,
  }) => {
    const data = await architectureData(request);
    const node = richest(data);
    const names = Array.from({ length: SYMBOL_CAP }, (_, i) => `name_${String(i).padStart(3, "0")}`);
    node.public_symbols = { names, omitted };
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${node.id}`);
    const symbols = field(page, "symbols");

    await expect(symbols.locator("summary")).toHaveText(summary);
    const listed = await symbols.locator("code").evaluateAll((items) => items.map((i) => i.textContent));
    expect(listed).toEqual(names);
  });
}

/** The node that holds the most entries of `listOf(node)`, the first by id on a tie. */
function holdingMost(data, listOf) {
  return [...data.nodes].sort(
    (a, b) => listOf(b).length - listOf(a).length || a.id.localeCompare(b.id)
  )[0];
}

// Two list fields the card's full-field case reads only by their "none": each
// tag, and each test file bound to the node itself, are shown by name.
const LISTED_FIELDS = [
  {
    field: "tags",
    listOf: (node) => node.tags || [],
    read: (el) => el.locator("code"),
    lacking: "no node carries a tag",
  },
  {
    field: "tests",
    listOf: (node) => node.tests?.files || [],
    read: (el) => el.locator("li code"),
    lacking: "no test file is bound to a node itself",
  },
];

for (const { field: name, listOf, read, lacking } of LISTED_FIELDS) {
  test(`the card lists every entry of the node's ${name} by name`, async ({ page, request }) => {
    const data = await architectureData(request);
    const node = holdingMost(data, listOf);
    requireShape(listOf(node).length > 0, lacking);

    await openArchitecture(page, `?focus=${node.id}`);

    const shown = await read(field(page, name)).evaluateAll((items) => items.map((i) => i.textContent));
    expect(shown).toEqual(listOf(node));
  });
}

// The link from a node's source is decided by the generator, which knows the
// remote, and each forge serves a path under its own route (BDL-076 R1 finding
// M1). The card renders the link it is given, whatever its form, and shows the
// source as plain text when it is given none. The repository block names a
// GitHub repository in every case, so a card that still built GitHub's route
// from it would link somewhere else.
const COMMIT = "0123456789abcdef0123456789abcdef01234567";
const SOURCE_LINKS = [
  { forge: "GitHub", link: (path) => `https://github.com/team/shop/tree/${COMMIT}/${path}` },
  { forge: "GitLab", link: (path) => `https://gitlab.com/team/shop/-/tree/${COMMIT}/${path}` },
  { forge: "Bitbucket", link: (path) => `https://bitbucket.org/team/shop/src/${COMMIT}/${path}` },
  { forge: "Gitea", link: (path) => `https://codeberg.org/team/shop/src/commit/${COMMIT}/${path}` },
  {
    forge: "Azure DevOps",
    link: (path) => `https://dev.azure.com/team/sales/_git/shop?path=/${path}&version=GC${COMMIT}`,
  },
];

async function serveSourceLink(page, request, sourceUrl) {
  const data = await architectureData(request);
  const node = [...data.nodes].filter((n) => n.source).sort((a, b) => a.id.localeCompare(b.id))[0];
  node.source_url = sourceUrl(node.source);
  data.repository = { url: "https://github.com/someone-else/elsewhere", ref: "ffffffff" };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  return node;
}

for (const { forge, link } of SOURCE_LINKS) {
  test(`the card links the source to the ${forge} address the data file gives`, async ({
    page,
    request,
  }) => {
    const node = await serveSourceLink(page, request, link);

    await openArchitecture(page, `?focus=${node.id}`);

    await expect(field(page, "source").locator("a")).toHaveAttribute("href", node.source_url);
    await expect(field(page, "source")).toContainText(node.source);
  });
}

test("the card shows the source without a link when the data file gives none", async ({
  page,
  request,
}) => {
  // A host the generator does not recognise: `beadloom docs site` writes no link.
  const node = await serveSourceLink(page, request, () => "");

  await openArchitecture(page, `?focus=${node.id}`);

  await expect(field(page, "source").locator("code")).toHaveText(node.source);
  await expect(field(page, "source").locator("a")).toHaveCount(0);
});
