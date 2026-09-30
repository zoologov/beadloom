// Impact mode: everything that depends on a node, by distance, with the risk marked (BDL-076 A3, US-6).
//
// Before A3 the viewer had no impact mode: a selection showed the node's own
// edges and nothing that reached it from further away.

import { test, expect } from "@playwright/test";
import {
  architectureData,
  openArchitecture,
  parentMap,
  unresolvedColours,
  viewer,
} from "./support/viewer.js";
import { DEPENDENCY_KINDS, impact, nearestOfKind, risksOf } from "./support/graph.js";

/** `rule-engine` when this graph has it; otherwise the node with the most dependents. */
function subjectOf(data) {
  if (data.nodes.some((n) => n.id === "rule-engine")) return "rule-engine";
  const reach = (id) => impact(data, id).distances.size;
  return data.nodes.map((n) => n.id).sort((a, b) => reach(b) - reach(a))[0];
}

/** What the summary must say, computed from the data file alone. */
function expectedSummary(data, subject) {
  const byId = new Map(data.nodes.map((n) => [n.id, n]));
  const parents = parentMap(data);
  const { distances } = impact(data, subject);
  const affected = [...distances.keys()].filter((id) => id !== subject).sort();
  const nearest = (kind) =>
    [...new Set(affected.map((id) => nearestOfKind(id, kind, byId, parents)).filter(Boolean))].sort();
  // A boundary is crossed by a dependency edge inside the affected set whose two
  // ends sit in different layers: `from` is the dependent's rank, `to` the dependency's.
  const crossings = new Map();
  for (const edge of data.edges) {
    if (!DEPENDENCY_KINDS.includes(edge.kind) || edge.src === edge.dst) continue;
    if (!distances.has(edge.dst) || !byId.has(edge.src)) continue;
    const from = byId.get(edge.src).layer_rank;
    const to = byId.get(edge.dst).layer_rank;
    if (typeof from !== "number" || typeof to !== "number" || from === to) continue;
    const key = `${from}->${to}`;
    crossings.set(key, (crossings.get(key) || 0) + 1);
  }
  return {
    distances: Object.fromEntries(distances),
    boundaries: Object.fromEntries([...crossings].sort()),
    affected,
    domains: nearest("domain"),
    services: nearest("service"),
    risky: affected.filter((id) => risksOf(byId.get(id)).length),
  };
}

test("impact mode rings every dependent by its distance and summarises them", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = expectedSummary(data, subject);
  expect(Math.max(...Object.values(expected.distances))).toBeGreaterThan(1);

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByRole("button", { name: "Impact", exact: true }).click();

  await expect.poll(() => viewer(page, "rings")).toEqual(expected.distances);
  const summary = await viewer(page, "impactSummary");
  expect(summary.affected).toEqual(expected.affected);
  expect(summary.domains).toEqual(expected.domains);
  expect(summary.services).toEqual(expected.services);
  expect(
    Object.fromEntries(summary.boundaries.map((b) => [`${b.fromRank}->${b.toRank}`, b.count]).sort())
  ).toEqual(expected.boundaries);
  expect(Object.keys(expected.boundaries).length).toBeGreaterThan(0);
  expect(new URL(page.url()).searchParams.get("view")).toBe("impact");

  const panel = page.getByTestId("impact-summary");
  await expect(panel.getByTestId("impact-count")).toHaveText(String(expected.affected.length));
  for (const domain of expected.domains) await expect(panel).toContainText(domain);
});

test("each affected node with no tests, stale docs or a finding is marked, and the card lists it", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = expectedSummary(data, subject);
  expect(expected.risky.length).toBeGreaterThan(0);

  await openArchitecture(page, `?focus=${subject}&view=impact`);

  await expect.poll(() => viewer(page, "riskIds")).toEqual(expected.risky);
  const listed = await page
    .getByTestId("impact-risks")
    .locator("[data-risk-node]")
    .evaluateAll((items) => items.map((item) => item.dataset.riskNode).sort());
  expect(listed).toEqual(expected.risky);
});

test("the mode says it is the graph's view and offers the two terminal commands", async ({
  page,
  request,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const source = data.nodes.find((n) => n.id === subject).source;

  await openArchitecture(page, `?focus=${subject}&view=impact`);
  const panel = page.getByTestId("impact-summary");

  await expect(panel).toContainText("graph view — not a reading of the code");
  await expect(panel).toContainText(`beadloom why ${subject}`);
  await expect(panel).toContainText(`beadloom impact ${source}`);
  await panel.getByRole("button", { name: `Copy: beadloom why ${subject}` }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(
    `beadloom why ${subject}`
  );
});

test("the rings are real colours, and leaving impact mode removes them", async ({ page, request }) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);

  await openArchitecture(page, `?focus=${subject}&view=impact`);
  await expect.poll(async () => Object.keys(await viewer(page, "rings")).length).toBeGreaterThan(1);
  expect(unresolvedColours(await viewer(page, "colours"))).toEqual([]);

  await page.getByRole("button", { name: "Impact", exact: true }).click();
  await expect.poll(() => viewer(page, "rings")).toEqual({});
  expect(await viewer(page, "riskIds")).toEqual([]);
});
