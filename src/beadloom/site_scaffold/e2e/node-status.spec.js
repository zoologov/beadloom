// A node's status is drawn by the severity of what was found (BDL-076 R1 finding m6).
//
// Version 2 of the data file carries each finding's severity. Before the fix the
// viewer read only `lint_clean`, which is false for a node with any finding, and
// drew every such node in the danger style of a violation, while
// `beadloom lint --strict` reported no error at all. Only an `error` finding is a
// violation; a node with `warn` findings only is drawn in a look of its own, and
// the legend names each status that is drawn.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";

/**
 * Each flagged node's status, from the data file alone: an error finding is a
 * violation; otherwise stale docs; otherwise any finding is a warning.
 */
function expectedStatuses(data) {
  const statuses = {};
  for (const node of data.nodes) {
    const findings = node.findings || [];
    if (findings.some((finding) => finding.severity === "error")) statuses[node.id] = "violation";
    else if (node.doc_status === "stale") statuses[node.id] = "stale";
    else if (findings.length) statuses[node.id] = "warned";
  }
  return statuses;
}

const legendStatuses = (page) =>
  page.locator("[data-legend-status]").evaluateAll((items) => items.map((i) => i.dataset.legendStatus).sort());

test("a node with warn findings only is drawn as a warning, not as a violation", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const expected = expectedStatuses(data);
  const errors = data.nodes.flatMap((n) => n.findings || []).filter((f) => f.severity === "error");
  expect(Object.values(expected)).toContain("warned");

  await openArchitecture(page);

  const drawn = Object.fromEntries(
    Object.entries(await viewer(page, "statusLooks")).map(([id, look]) => [id, look.status])
  );
  expect(drawn).toEqual(expected);
  // `beadloom lint --strict` finds no error on this repository today, so nothing
  // is drawn as a violation; the day it does, the node is, and this still holds.
  expect(Object.values(drawn).includes("violation")).toBe(errors.length > 0);
});

test("an error finding draws a violation, in a look apart from a warning's", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const warned = Object.entries(expectedStatuses(data)).find(([, status]) => status === "warned")[0];
  const clean = data.nodes.find((n) => !(n.findings || []).length && n.doc_status !== "stale");
  clean.findings = [{ rule: "served-rule", severity: "error", message: "served for the case" }];
  clean.lint_clean = false;
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await openArchitecture(page);
  const looks = await viewer(page, "statusLooks");

  expect(looks[clean.id].status).toBe("violation");
  expect(looks[warned].status).toBe("warned");
  expect(looks[clean.id].borderColour).not.toBe(looks[warned].borderColour);
  expect(looks[clean.id].borderStyle).not.toBe(looks[warned].borderStyle);
  expect(await legendStatuses(page)).toEqual(
    [...new Set(Object.values(looks).map((look) => look.status))].sort()
  );
});

test("the legend names each node status that is drawn, and no other", async ({ page, request }) => {
  const data = await architectureData(request);

  await openArchitecture(page);

  expect(await legendStatuses(page)).toEqual([...new Set(Object.values(expectedStatuses(data)))].sort());
});
