// Impact mode: everything that depends on a node, by distance, with the risk marked.
//
// In an earlier version the viewer had no impact mode: a selection showed the node's own
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
import { requireShape } from "./support/shape.js";

/** The node with the most dependents; between equals, the first by id. */
function subjectOf(data) {
  const reach = (id) => impact(data, id).distances.size;
  return data.nodes
    .map((n) => n.id)
    .sort()
    .sort((a, b) => reach(b) - reach(a))[0];
}

/** `subjectOf` when `holds` of it; otherwise the first node, by id, of which it does. */
function subjectWhere(data, holds) {
  const preferred = subjectOf(data);
  if (holds(preferred)) return preferred;
  return data.nodes.map((n) => n.id).sort().find(holds);
}

/** How many dependency steps away the farthest node a change to `id` reaches is. */
function farthest(data, id) {
  return Math.max(...impact(data, id).distances.values());
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
    risks: Object.fromEntries(
      affected.map((id) => [id, risksOf(byId.get(id))]).filter(([, risks]) => risks.length)
    ),
  };
}

/** The impact summary's risks, `{ id: labels }`, each list sorted. */
function listedRisks(summary) {
  return Object.fromEntries(summary.risky.map((entry) => [entry.id, [...entry.risks].sort()]));
}

test("impact mode rings every dependent by its distance and summarises them", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectWhere(data, (id) => farthest(data, id) > 1);
  requireShape(subject, "no change reaches a node two dependency steps away");
  const expected = expectedSummary(data, subject);

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
  expect(new URL(page.url()).searchParams.get("view")).toBe("impact");

  const panel = page.getByTestId("impact-summary");
  await expect(panel.getByTestId("impact-count")).toHaveText(String(expected.affected.length));
  for (const domain of expected.domains) await expect(panel).toContainText(domain);
});

test("the impact summary counts the dependencies that cross each layer boundary, by rank", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const crosses = (id) => Object.keys(expectedSummary(data, id).boundaries).length > 0;
  const subject = subjectWhere(data, crosses);
  requireShape(subject, "no change's dependents cross a boundary between two declared layers");
  const expected = expectedSummary(data, subject);

  await openArchitecture(page, `?focus=${subject}&view=impact`);

  await expect
    .poll(async () =>
      Object.fromEntries(
        ((await viewer(page, "impactSummary"))?.boundaries || [])
          .map((b) => [`${b.fromRank}->${b.toRank}`, b.count])
          .sort()
      )
    )
    .toEqual(expected.boundaries);
});

test("each affected node with no tests, stale docs or a finding is marked, and the card lists it", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = expectedSummary(data, subject);
  requireShape(
    expected.risky.length > 0,
    "no node a change reaches carries a risk: none lacks bound tests, has unchecked or stale docs, or has a finding"
  );

  await openArchitecture(page, `?focus=${subject}&view=impact`);

  await expect.poll(() => viewer(page, "riskIds")).toEqual(expected.risky);
  expect(listedRisks(await viewer(page, "impactSummary"))).toEqual(expected.risks);
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

// A doc nothing could check is not a stale doc: the sync engine keeps `unpaired`,
// `unverified` and `missing` apart from `stale`, and so does the impact list. A
// project's docs need not hold every state, so the served file gives one affected
// node each state, and nothing else at risk.
const DOC_STATES = [
  { status: "stale", label: "stale docs" },
  { status: "unpaired", label: "docs not checked" },
  { status: "unverified", label: "docs not checked" },
  { status: "missing", label: "docs not checked" },
];

for (const { status, label } of DOC_STATES) {
  test(`an affected node whose doc is ${status} is listed as "${label}"`, async ({ page, request }) => {
    const data = await architectureData(request);
    const subject = subjectOf(data);
    const target = expectedSummary(data, subject).affected[0];
    requireShape(target, "no node depends on another");
    const node = data.nodes.find((n) => n.id === target);
    node.docs = [{ path: "docs/served-for-the-case.md", status }];
    node.doc_status = status === "stale" ? "stale" : "fresh";
    node.tests = { files: [], file_count: 1, count: 1, placement: {} };
    node.findings = [];
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

    await openArchitecture(page, `?focus=${subject}&view=impact`);

    await expect.poll(async () => listedRisks(await viewer(page, "impactSummary"))[target]).toEqual([
      label,
    ]);
    await expect(page.locator(`[data-risk-node='${target}']`)).toContainText(label);
  });
}
