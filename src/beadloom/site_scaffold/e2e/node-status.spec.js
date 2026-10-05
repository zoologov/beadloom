// A node's status is drawn by the severity of what was found, as a mark in its corner.
//
// Version 2 of the data file carries each finding's severity. Before the fix the
// viewer read only `lint_clean`, which is false for a node with any finding, and
// drew every such node in the danger style of a violation, while
// `beadloom lint --strict` reported no error at all. Only an `error` finding is a
// violation; a node with `warn` findings only is drawn in a look of its own, and
// the legend names each status that is drawn.
//
// A status was once drawn as the node's border, double for a warning, over the
// layer's colour. Now it is a mark in the node's top right corner — filled for
// an error or stale docs, a ring for warn findings only — and the border keeps
// the layer's colour whatever the status.
//
// The statuses are read at full detail, every box open: at the whole-graph fit
// the viewer draws only the boxes at the top (`map.spec.js`).

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, openEveryBox, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";
import { cssColour } from "./support/look.js";

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

/** A status mark as drawn: `{ shape, colour }`, filled or a ring, read from the corner image; null when there is none. */
function markOf(look) {
  const image = decodeURIComponent(String(look.mark));
  const fill = image.match(/fill="(rgb\([^"]+\))"/);
  const ring = image.match(/stroke="(rgb\([^"]+\))"/);
  if (fill) return { shape: "filled", colour: fill[1].replace(/\s+/g, "") };
  if (ring) return { shape: "ring", colour: ring[1].replace(/\s+/g, "") };
  return null;
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
  requireShape(Object.values(expected).includes("warned"), "no node has warn-level findings only");

  await openArchitecture(page);
  await openEveryBox(page);

  const drawn = Object.fromEntries(
    Object.entries(await viewer(page, "statusLooks")).map(([id, look]) => [id, look.status])
  );
  expect(drawn).toEqual(expected);
  // When `beadloom lint --strict` finds no error, nothing is drawn as a
  // violation; when it finds one, the node is, and this holds either way.
  expect(Object.values(drawn).includes("violation")).toBe(errors.length > 0);
});

test("an error finding draws a violation, in a look apart from a warning's", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const cleanNodes = data.nodes.filter((n) => !(n.findings || []).length && n.doc_status !== "stale");
  let warned = Object.entries(expectedStatuses(data)).find(([, status]) => status === "warned")?.[0];
  requireShape(cleanNodes.length >= (warned ? 1 : 2), "fewer than two nodes have no finding and no stale doc");
  // A graph with no warned node is served one, on the last clean node, so the two looks are compared.
  if (!warned) {
    const served = cleanNodes.pop();
    served.findings = [{ rule: "served-warn-rule", severity: "warn", message: "served for the case" }];
    served.lint_clean = false;
    warned = served.id;
  }
  const clean = cleanNodes[0];
  clean.findings = [{ rule: "served-rule", severity: "error", message: "served for the case" }];
  clean.lint_clean = false;
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));

  await openArchitecture(page);
  await openEveryBox(page);
  const looks = await viewer(page, "statusLooks");

  expect(looks[clean.id].status).toBe("violation");
  expect(looks[warned].status).toBe("warned");
  expect(markOf(looks[clean.id])).not.toEqual(markOf(looks[warned]));
  expect(await legendStatuses(page)).toEqual(
    [...new Set(Object.values(looks).map((look) => look.status))].sort()
  );
});

test("the legend names each node status that is drawn, and no other", async ({ page, request }) => {
  const data = await architectureData(request);

  await openArchitecture(page);
  await openEveryBox(page);

  expect(await legendStatuses(page)).toEqual([...new Set(Object.values(expectedStatuses(data)))].sort());
});

test("a status is a mark in the node's corner — filled for an error or stale docs, a ring for warn findings — and the border keeps the layer's colour", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  // One node of each status, served on nodes that share a layer with a node that has none.
  const clean = data.nodes.filter((n) => !(n.findings || []).length && n.doc_status !== "stale" && !(data.nodes.some((m) => m.parent === n.id)));
  const byRank = new Map();
  for (const node of clean) {
    const rank = node.layer_rank ?? "none";
    byRank.set(rank, [...(byRank.get(rank) || []), node]);
  }
  const [rank] = [...byRank].find(([, nodes]) => nodes.length >= 4) || [null];
  requireShape(rank !== null, "no layer holds four leaves with no finding and no stale doc");
  const [plain, error, stale, warned] = byRank.get(rank);
  error.findings = [{ rule: "served-rule", severity: "error", message: "served for the case" }];
  error.lint_clean = false;
  stale.doc_status = "stale";
  warned.findings = [{ rule: "served-warn-rule", severity: "warn", message: "served for the case" }];
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  await openEveryBox(page);

  const looks = Object.fromEntries((await viewer(page, "nodeLooks")).map((look) => [look.id, look]));
  const danger = (await cssColour(page, "var(--vp-c-danger-1)")).replace(/\s+/g, "");
  const warning = (await cssColour(page, "var(--vp-c-warning-1)")).replace(/\s+/g, "");
  expect(markOf(looks[plain.id])).toBeNull();
  expect(markOf(looks[error.id])).toEqual({ shape: "filled", colour: danger });
  expect(markOf(looks[stale.id])).toEqual({ shape: "filled", colour: warning });
  expect(markOf(looks[warned.id])).toEqual({ shape: "ring", colour: warning });
  for (const node of [error, stale, warned]) {
    const { borderColour, borderWidth, borderStyle } = looks[node.id];
    expect({ borderColour, borderWidth, borderStyle }, node.id).toEqual({
      borderColour: looks[plain.id].borderColour,
      borderWidth: looks[plain.id].borderWidth,
      borderStyle: "solid",
    });
  }
  // The legend draws each mark as the canvas does.
  const legendMarks = await page.locator("[data-legend-status] [data-legend-mark]").evaluateAll((marks) =>
    marks.map((mark) => ({
      status: mark.closest("[data-legend-status]").dataset.legendStatus,
      shape: mark.dataset.legendMark,
      colour: getComputedStyle(mark).borderColor.replace(/\s+/g, ""),
      filled: getComputedStyle(mark).backgroundColor.replace(/\s+/g, "") === getComputedStyle(mark).borderColor.replace(/\s+/g, ""),
    }))
  );
  expect(legendMarks).toEqual([
    { status: "violation", shape: "filled", colour: danger, filled: true },
    { status: "stale", shape: "filled", colour: warning, filled: true },
    { status: "warned", shape: "ring", colour: warning, filled: false },
  ]);
});
