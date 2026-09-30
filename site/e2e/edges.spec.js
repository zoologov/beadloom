// Edges: one style per kind, violations stand out, the legend lists what is drawn (BDL-076 A2).
//
// Before A2 the viewer drew two kinds of six and its legend listed a `part_of`
// line style that was never drawn.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";

/** The legend keys the data file calls for: each drawn edge kind, plus `violation`. */
function expectedKeys(data) {
  const keys = new Set();
  for (const e of data.edges) {
    if (e.kind === "part_of") continue;
    keys.add(e.kind);
    if (e.kind === "depends_on" && e.violation === true) keys.add("violation");
  }
  return [...keys].sort();
}

test("the legend lists exactly the edge kinds that are drawn", async ({ page, request }) => {
  const data = await architectureData(request);
  await openArchitecture(page);

  const drawn = await viewer(page, "drawnEdgeKinds");
  expect(drawn).toEqual(expectedKeys(data));
  const legend = await page
    .locator("[data-legend-edge]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendEdge).sort());
  expect(legend).toEqual(drawn);
});

/**
 * The data file with every drawn kind present: one `depends_on` edge marked as a
 * violation, and one `consumes` and one `produces` edge added, so the styles are
 * checked whether or not this repository's graph carries them today.
 */
async function serveEveryEdgeKind(page, request) {
  const data = await architectureData(request);
  const plain = data.edges.filter((e) => e.kind === "depends_on" && !e.violation);
  const [first, second] = plain;
  first.violation = true;
  data.edges.push({ src: second.src, dst: second.dst, kind: "consumes" });
  data.edges.push({ src: second.dst, dst: second.src, kind: "produces" });
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  return data;
}

test("each edge kind has its own line style, and a violation is red, dashed and thicker", async ({
  page,
  request,
}) => {
  const data = await serveEveryEdgeKind(page, request);
  await openArchitecture(page);
  const drawn = await viewer(page, "drawnEdgeKinds");
  expect(drawn).toEqual(expectedKeys(data));
  expect(drawn).toEqual(["consumes", "depends_on", "produces", "uses", "violation"]);
  const styles = {};
  for (const key of drawn) styles[key] = await viewer(page, "edgeStyle", key);

  const expected = { depends_on: "solid", uses: "dotted", consumes: "dashed", produces: "dashed" };
  for (const [key, lineStyle] of Object.entries(expected)) {
    expect(styles[key].lineStyle, key).toBe(lineStyle);
  }
  expect(styles.consumes.colour).not.toBe(styles.produces.colour);
  expect(styles.violation.lineStyle).toBe("dashed");
  expect(styles.violation.width).toBeGreaterThan(styles.depends_on.width);
  const [r, g, b] = styles.violation.colour.match(/\d+/g).map(Number);
  expect(r).toBeGreaterThan(g + 60);
  expect(r).toBeGreaterThan(b + 60);
  const legend = await page
    .locator("[data-legend-edge]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendEdge).sort());
  expect(legend).toEqual(drawn);
});

test("hovering an edge shows its label, and only while it is hovered", async ({ page }) => {
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  expect(await viewer(page, "shownEdgeLabels")).toEqual([]);

  // The pointer is over one edge, though not always the one whose midpoint it
  // aimed at, where edges run close together: exactly one label shows.
  const [, point] = await viewer(page, "edgeMidpoint");
  await page.mouse.move(point.x, point.y);
  await expect.poll(async () => (await viewer(page, "shownEdgeLabels")).length).toBe(1);

  await page.mouse.move(2, 2);
  await expect.poll(() => viewer(page, "shownEdgeLabels")).toEqual([]);
});
