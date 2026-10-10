// The node card: every field the index holds, clickable edges, commands to copy.
//
// In an earlier version the card showed kind, layer, a symbol count, one aggregate doc
// status and the two dependency lists: no source, no tests, no findings, no
// activity or debt, and nothing to copy.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";
import { layerOfNode, layersOfData } from "./support/layers.js";
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
    node.activity?.lines_30d ?? node.activity?.commits_30d,
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
  await expect(field(page, "activity")).toContainText(node.activity.level);
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
  // In no layer by any reading: the first rule's keys, and the keys of every rule.
  layer: (node) => Object.assign(node, { layer: "", layer_rank: null, layer_rule: "", layer_rule_rank: null }),
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
    // A file written before lint's reach was carried: "none" stands alone.
    delete data.lint;
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, name)).toBe("none");
  });
}

// The activity line: changed lines in 30 days with the level, which is relative
// to the project; a node with no change
// says so in words rather than as a low count. A data file written before lines
// were counted is said in the commits it carries. One line or one commit is said
// in the singular.
const ACTIVITY_LINES = [
  { activity: { lines_30d: 1234, commits_30d: 3, level: "hot" }, says: "1234 lines changed in 30 days, hot" },
  { activity: { lines_30d: 0, commits_30d: 1, level: "cool" }, says: "0 lines changed in 30 days, cool" },
  { activity: { lines_30d: 1, commits_30d: 1, level: "cool" }, says: "1 line changed in 30 days, cool" },
  { activity: { lines_30d: 0, commits_30d: 0, level: "quiet" }, says: "no change in 30 days, quiet" },
  { activity: { lines_30d: 0, commits_30d: 0, level: "dormant" }, says: "no change in 90 days, dormant" },
  { activity: { commits_30d: 2, level: "cold" }, says: "2 commits in 30 days, cold" },
  { activity: { commits_30d: 1, level: "cold" }, says: "1 commit in 30 days, cold" },
];

for (const { activity, says } of ACTIVITY_LINES) {
  test(`the card's activity reads "${says}"`, async ({ page, request }) => {
    const data = await architectureData(request);
    const node = richest(data);
    node.activity = activity;
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, "activity")).toBe(says);
  });
}

/** How the card words where a node's layer comes from. */
const LAYER_ORIGINS = [
  { origin: "its own tag", own: true },
  { origin: "inherited through part_of", own: false },
];

// Where the file names every layer rule, the card names the rule that places the
// node beside where its tag comes from — by its title where the rule declares
// one, else "rule" and its name; a file without them names none.
for (const { origin, own } of LAYER_ORIGINS) {
  test(`the card names the node's layer and says it is ${origin}`, async ({ page, request }) => {
    const data = await architectureData(request);
    const layers = layersOfData(data);
    const ownsIt = (n, layer) => (layer.rule ? (n.tags || []).includes(layer.tag) : Boolean(n.layer));
    const node = data.nodes
      .filter((n) => {
        const layer = layerOfNode(n, data, layers);
        return layer && ownsIt(n, layer) === own;
      })
      .sort((a, b) => a.id.localeCompare(b.id))[0];
    requireShape(node, own ? LACKING.ownLayer : LACKING.inheritedLayer);
    // The declared name of the node's layer, not the tag token.
    const layer = layerOfNode(node, data, layers);
    const said = layer.rule ? `${layer.title || `rule ${layer.rule}`}, ${origin}` : origin;

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, "layer")).toBe(`${layer.name} (${said})`);
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
// remote, and each forge serves a path under its own route. The card renders the
// link it is given, whatever its form, and shows the source as plain text when it
// is given none. The repository block names a
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

// A portal built from a commit no remote branch holds links a branch the remote holds
// instead, and the card says so beside the link: the reader is looking at the branch,
// which may differ from what the page says.
const UNPUBLISHED = [
  { linked: "main", says: "built from an unpublished commit; links point at main" },
  { linked: COMMIT, says: `built from an unpublished commit; links point at ${COMMIT.slice(0, 12)}` },
];

/** Serve the data file with `sourceRef` as its `source_ref` (none when undefined); the node linked. */
async function serveSourceRef(page, request, sourceRef) {
  const data = await architectureData(request);
  const node = [...data.nodes].filter((n) => n.source).sort((a, b) => a.id.localeCompare(b.id))[0];
  node.source_url = `https://github.com/team/shop/tree/${sourceRef?.linked || COMMIT}/${node.source}`;
  if (sourceRef === undefined) delete data.source_ref;
  else data.source_ref = sourceRef;
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  return node;
}

for (const { linked, says } of UNPUBLISHED) {
  test(`a card built from an unpublished commit reads "${says}" beside the source link`, async ({
    page,
    request,
  }) => {
    const node = await serveSourceRef(page, request, { commit: COMMIT, linked, pushed: false });

    await openArchitecture(page, `?focus=${node.id}`);

    await expect(field(page, "source").locator("a")).toHaveAttribute("href", node.source_url);
    await expect(field(page, "source-ref")).toHaveText(says);
  });
}

for (const { state, sourceRef } of [
  { state: "a pushed commit", sourceRef: { commit: COMMIT, linked: COMMIT, pushed: true } },
  { state: "a file that names no source ref", sourceRef: undefined },
]) {
  test(`a card built from ${state} says nothing about the commit`, async ({ page, request }) => {
    const node = await serveSourceRef(page, request, sourceRef);

    await openArchitecture(page, `?focus=${node.id}`);

    await expect(field(page, "source").locator("a")).toHaveAttribute("href", node.source_url);
    await expect(field(page, "source-ref")).toHaveCount(0);
  });
}

// Every count on the card names what it was counted over. "none" under Rule
// findings is said against lint's totals for the project, so it is not read as
// "lint never ran", and the totals name both populations they hold: the findings
// on nodes, with how many nodes carry them, and the findings on none (the
// owner's wording of 2026-10-10). The box holding the whole project lists the
// findings lint binds to no node; a box's debt is its own and what is inside.

/** `count` followed by `one` when it is 1, and by `many` otherwise. */
const countOf = (count, one, many) => `${count} ${count === 1 ? one : many}`;

/** `count` findings lint binds to no node, each one its own. */
const nodelessFindings = (count) =>
  Array.from({ length: count }, (_, index) => ({
    rule: "inert-rule",
    severity: "warn",
    message: `cannot fire ${index}`,
    file: "",
    line: null,
  }));

/** Lint's reach as the card says it, from the data file's `lint`. */
function reachSaid({ errors, warnings, nodes_with_findings: nodes, nodeless }) {
  const totals = `${countOf(errors, "error", "errors")}, ${countOf(warnings, "warning", "warnings")}`;
  const onNodes = errors + warnings - nodeless.length;
  return `this project: ${totals} — ${onNodes} on ${countOf(nodes, "node", "nodes")}, ${nodeless.length} on none`;
}

/** The richest node that is not the project's own box, whose card lists no node-less finding. */
function richestOutsideTheProjectBox(data) {
  const box = projectBoxOf(data);
  return richest({ nodes: data.nodes.filter((n) => n !== box) });
}

const REACHES = [
  // This portal's own numbers as S4T measured them.
  { lint: { errors: 0, warnings: 69, nodes_with_findings: 27 }, nodeless: 36, says: "0 errors, 69 warnings — 33 on 27 nodes, 36 on none" },
  { lint: { errors: 1, warnings: 1, nodes_with_findings: 1 }, nodeless: 0, says: "1 error, 1 warning — 2 on 1 node, 0 on none" },
  { lint: { errors: 1, warnings: 0, nodes_with_findings: 0 }, nodeless: 1, says: "1 error, 0 warnings — 0 on 0 nodes, 1 on none" },
];

for (const { lint, nodeless, says } of REACHES) {
  test(`a card with no finding reads "none — this project: ${says}"`, async ({ page, request }) => {
    const data = await architectureData(request);
    const node = richestOutsideTheProjectBox(data);
    Object.assign(node, { findings: [], lint_clean: true });
    data.lint = { ...lint, nodeless: nodelessFindings(nodeless) };
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${node.id}`);

    expect(await fieldValue(page, "findings")).toBe(`none — this project: ${says}`);
  });
}

test("under a card's own findings the same line names both populations", async ({ page, request }) => {
  const data = await architectureData(request);
  const node = richestOutsideTheProjectBox(data);
  Object.assign(node, {
    findings: [{ rule: "tier-order", severity: "warn", message: "reaches up" }],
    lint_clean: false,
  });
  data.lint = { errors: 0, warnings: 69, nodes_with_findings: 27, nodeless: nodelessFindings(36) };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await openArchitecture(page, `?focus=${node.id}`);

  await expect(field(page, "findings").locator("p.bl-card-note")).toHaveText(
    "this project: 0 errors, 69 warnings — 33 on 27 nodes, 36 on none"
  );
});

test("the card says the project's lint totals as they are in the data file", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(data.lint, "the data file carries no lint totals; it was written before they were carried");
  const node = richestWithFindings(data);

  await openArchitecture(page, `?focus=${node.id}`);

  await expect(field(page, "findings")).toContainText(reachSaid(data.lint));
});

/** The one node that holds every other, as the viewer draws the project's box; null when there is none. */
function projectBoxOf(data) {
  const ids = new Set(data.nodes.map((n) => n.id));
  const roots = data.nodes.filter((n) => !n.parent || n.parent === n.id || !ids.has(n.parent));
  if (roots.length !== 1) return null;
  const [root] = roots;
  return data.nodes.some((n) => n.parent === root.id && n !== root) ? root : null;
}

const NODELESS = [
  { rule: "scenario-coverage", severity: "warn", message: "names no scenario", file: "docs/PRD.md", line: 12 },
  { rule: "inert-rule", severity: "error", message: "cannot fire", file: "", line: null },
];

test("the project box's card lists the findings bound to no node, and a leaf's card does not", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const box = projectBoxOf(data);
  requireShape(box, "no single node holds every other, so the project has no box of its own");
  const leaf = data.nodes.filter((n) => !data.nodes.some((m) => m.parent === n.id)).sort((a, b) => a.id.localeCompare(b.id))[0];
  data.lint = { errors: 1, warnings: 1, nodes_with_findings: 0, nodeless: NODELESS };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await openArchitecture(page, `?focus=${box.id}`);
  const listed = field(page, "findings").locator("[data-card-nodeless] li");
  await expect(listed).toHaveCount(NODELESS.length);
  await expect(field(page, "findings").locator("h5")).toHaveText("2 findings bound to no node");
  await expect(listed.nth(0)).toContainText("scenario-coverage");
  await expect(listed.nth(0)).toContainText("docs/PRD.md:12");
  await expect(listed.nth(1)).toContainText("cannot fire");

  await openArchitecture(page, `?focus=${leaf.id}`);
  await expect(field(page, "findings").locator("[data-card-nodeless]")).toHaveCount(0);
});

/** A box's debt inside it, as the card says it. */
function insideSaid(inside) {
  const said = `${inside.score} on ${countOf(inside.nodes, "node", "nodes")}`;
  const reasons = Object.entries(inside.by_reason).map(([reason, count]) => `${reason} ${count}`);
  return reasons.length ? `${said}: ${reasons.join(", ")}` : said;
}

test("a box's card says its own debt and the debt inside it, by reason, in Debt and in Inside", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const box = [...data.nodes]
    .filter((n) => n.debt?.inside && n.debt.inside.nodes > 0)
    .sort((a, b) => b.debt.inside.nodes - a.debt.inside.nodes || a.id.localeCompare(b.id))[0];
  requireShape(box, "no box holds a node that carries debt");

  await openArchitecture(page, `?focus=${box.id}`);

  const debt = field(page, "debt");
  await expect(debt.locator("[data-debt='own']")).toHaveText(new RegExp(`^own ${box.debt.score}\\b`));
  await expect(debt.locator("[data-debt='inside']")).toHaveText(`inside ${insideSaid(box.debt.inside)}`);
  await expect(field(page, "contents").locator("[data-contents-debt]")).toHaveText(
    `debt ${insideSaid(box.debt.inside)}`
  );
});

test("a leaf's card says its debt on one line, as before", async ({ page, request }) => {
  const data = await architectureData(request);
  const leaf = data.nodes
    .filter((n) => n.debt && !n.debt.inside && n.debt.score > 0)
    .sort((a, b) => a.id.localeCompare(b.id))[0];
  requireShape(leaf, "no leaf carries debt");

  await openArchitecture(page, `?focus=${leaf.id}`);

  await expect(field(page, "debt").locator("[data-debt]")).toHaveCount(0);
  expect(await fieldValue(page, "debt")).toBe(
    leaf.debt.reasons.length ? `${leaf.debt.score} (${leaf.debt.reasons.join(", ")})` : `${leaf.debt.score}`
  );
});
