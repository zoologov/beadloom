// Impact on the landscape: every service a change reaches over the contracts (BDL-076, beadloom-ujzb.6).
//
// Before this bead the landscape offered no impact mode (A4): the toolbar had no
// "Impact" button, and a selection showed one step of the neighbourhood.
//
// A contract edge runs from a producer to a consumer. The consumer reads the
// message the producer publishes, calls the schema it serves, or declares that
// it consumes it, so a change to a service reaches the consumers of what it
// produces, and theirs, with no limit. The expected sets come from the served
// data file through `support/landscape.js`, never from the viewer's own walk.

import { test, expect } from "@playwright/test";
import { unresolvedColours, viewer } from "./support/viewer.js";
import {
  expectedContractImpact,
  grownLandscape,
  landscapeData,
  openLandscape,
  serveLandscape,
} from "./support/landscape.js";

const IMPACT = { name: "Impact", exact: true };

/** The served landscape, grown so a walk goes four contracts deep, and where it starts. */
async function grown(page, request) {
  const served = grownLandscape(await landscapeData(request));
  await serveLandscape(page, served.data);
  return served;
}

/** The impact summary's risks, `{ id: labels }`, each list sorted. */
function listedRisks(summary) {
  return Object.fromEntries(summary.risky.map((entry) => [entry.id, [...entry.risks].sort()]));
}

test("the landscape's Impact rings every service a change reaches over the contracts, however far", async ({
  page,
  request,
}) => {
  const { data, root } = await grown(page, request);
  const expected = expectedContractImpact(data, root);
  expect(Math.max(...Object.values(expected.distances))).toBeGreaterThan(3);

  await openLandscape(page, `?focus=${encodeURIComponent(root)}`);
  await page.getByRole("toolbar", { name: "Graph viewer tools" }).getByRole("button", IMPACT).click();

  await expect.poll(() => viewer(page, "rings")).toEqual(expected.distances);
  const summary = await viewer(page, "impactSummary");
  expect(summary.affected).toEqual(expected.affected);
  expect(new URL(page.url()).searchParams.get("view")).toBe("impact");
  const panel = page.getByTestId("impact-summary");
  await expect(panel.getByTestId("impact-count")).toHaveText(String(expected.affected.length));
  expect(unresolvedColours(await viewer(page, "colours"))).toEqual([]);

  await page.getByRole("button", IMPACT).click();
  await expect.poll(() => viewer(page, "rings")).toEqual({});
});

test("a change reaches the consumers of what a service produces, never its producers", async ({
  page,
  request,
}) => {
  const { data, root } = await grown(page, request);
  const subject = "svc-billing";
  const expected = expectedContractImpact(data, subject);

  await openLandscape(page, `?focus=${subject}&view=impact`);

  await expect.poll(() => viewer(page, "rings")).toEqual(expected.distances);
  const rings = await viewer(page, "rings");
  // The service that produces for it, and the one whose contract it consumes, are upstream.
  expect(rings).not.toHaveProperty(root);
  expect(rings).not.toHaveProperty("svc-outside");

  await openLandscape(page, "?focus=svc-archive&view=impact");
  expect((await viewer(page, "impactSummary")).affected).toEqual([]);
  await expect(page.getByTestId("impact-count")).toHaveText("0");
});

test("the summary names the contracts and protocols the change crosses and the broken ones on its path", async ({
  page,
  request,
}) => {
  const { data, root } = await grown(page, request);
  const expected = expectedContractImpact(data, root);
  expect(expected.broken.length).toBeGreaterThan(0);
  expect(expected.contracts).not.toContain("graphql:Rates");

  await openLandscape(page, `?focus=${encodeURIComponent(root)}&view=impact`);

  await expect.poll(async () => (await viewer(page, "impactSummary"))?.contracts).toEqual(expected.contracts);
  const summary = await viewer(page, "impactSummary");
  expect(summary.protocols).toEqual(expected.protocols);
  expect(summary.broken).toEqual(expected.broken);
  const panel = page.getByTestId("impact-summary");
  await expect(panel.getByTestId("impact-contract-count")).toHaveText(String(expected.contracts.length));
  for (const protocol of expected.protocols) await expect(panel).toContainText(protocol);
  const broken = await panel
    .locator("[data-broken-contract]")
    .evaluateAll((items) => items.map((item) => item.dataset.brokenContract).sort());
  expect(broken).toEqual(expected.broken);
});

test("each affected service with a broken or unverified contract is marked, and the list says which", async ({
  page,
  request,
}) => {
  const { data, root } = await grown(page, request);
  const expected = expectedContractImpact(data, root);
  expect(Object.values(expected.risks).flat()).toEqual(
    expect.arrayContaining(["broken contract", "unverified contract"])
  );

  await openLandscape(page, `?focus=${encodeURIComponent(root)}&view=impact`);

  await expect.poll(() => viewer(page, "riskIds")).toEqual(expected.risky);
  expect(listedRisks(await viewer(page, "impactSummary"))).toEqual(expected.risks);
  const listed = await page
    .getByTestId("impact-risks")
    .locator("[data-risk-node]")
    .evaluateAll((items) => items.map((item) => item.dataset.riskNode).sort());
  expect(listed).toEqual(expected.risky);
});

test("the landscape's impact says it is the graph's view and offers the commands a service's ref takes", async ({
  page,
  request,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  // A ref the shell would split is copied quoted: one service is renamed so.
  const quoted = "svc report's";
  const { data: plain, root } = grownLandscape(await landscapeData(request));
  const data = JSON.parse(JSON.stringify(plain).replaceAll('"svc-report"', JSON.stringify(quoted)));
  await serveLandscape(page, data);

  await openLandscape(page, `?focus=${encodeURIComponent(root)}&view=impact`);
  const panel = page.getByTestId("impact-summary");

  await expect(panel).toContainText("graph view — not a reading of the code");
  await expect(panel).toContainText(`beadloom why ${root}`);
  await expect(panel).toContainText(`beadloom ctx ${root}`);
  await expect(panel).not.toContainText("beadloom impact");
  await panel.getByRole("button", { name: `Copy: beadloom why ${root}` }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(`beadloom why ${root}`);

  await openLandscape(page, `?focus=${encodeURIComponent(quoted)}&view=impact`);
  await expect(page.getByTestId("impact-summary")).toContainText(`beadloom why 'svc report'\\''s'`);
});

test("on the landscape the portal serves, a change to a producer reaches its consumer", async ({
  page,
  request,
}) => {
  const data = await landscapeData(request);
  const producer = data.edges[0].src;
  const expected = expectedContractImpact(data, producer);
  expect(expected.affected.length).toBeGreaterThan(0);
  for (const contract of data.contracts) expect(contract).toHaveProperty("verdict_basis");

  await openLandscape(page, `?focus=${encodeURIComponent(producer)}&view=impact`);

  await expect.poll(() => viewer(page, "rings")).toEqual(expected.distances);
  expect(listedRisks(await viewer(page, "impactSummary"))).toEqual(expected.risks);
});
