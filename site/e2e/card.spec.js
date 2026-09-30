// The node card: every field the index holds, clickable edges, commands to copy (BDL-076 A3, US-3).
//
// Before A3 the card showed kind, layer, a symbol count, one aggregate doc
// status and the two dependency lists: no source, no tests, no findings, no
// activity or debt, and nothing to copy.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";

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

function field(page, name) {
  return page.locator(`${CARD} [data-card-field='${name}']`);
}

test("the card shows every field the data file holds for the node", async ({ page, request }) => {
  const data = await architectureData(request);
  const node = richest(data);
  expect((node.findings || []).length).toBeGreaterThan(0);

  await openArchitecture(page, `?focus=${node.id}`);

  await expect(field(page, "kind")).toContainText(node.kind);
  await expect(field(page, "summary")).toContainText(node.summary);
  await expect(field(page, "lifecycle")).toContainText(node.lifecycle);
  await expect(field(page, "layer")).not.toBeEmpty();
  await expect(field(page, "source")).toContainText(node.source);
  if (data.repository?.url) {
    const href = await field(page, "source").locator("a").getAttribute("href");
    expect(href).toBe(`${data.repository.url}/tree/${data.repository.ref || "HEAD"}/${node.source}`);
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

test("a field the index holds nothing for says none", async ({ page, request }) => {
  const data = await architectureData(request);
  const bare = data.nodes.find((n) => !(n.tags || []).length && !(n.findings || []).length);

  await openArchitecture(page, `?focus=${bare.id}`);

  await expect(field(page, "tags")).toContainText("none");
  await expect(field(page, "findings")).toContainText("none");
});

test("every edge kind the node has is listed by direction, and a click moves the selection", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const drawn = new Set(["depends_on", "uses", "consumes", "produces"]);
  const edgesOf = (id) => data.edges.filter((e) => drawn.has(e.kind) && (e.src === id || e.dst === id));
  const node = [...data.nodes].sort((a, b) => edgesOf(b.id).length - edgesOf(a.id).length)[0];
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
