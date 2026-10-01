// Edges: one style per kind, violations stand out, the legend lists what is drawn.
//
// In an earlier version the viewer drew two kinds of six and its legend listed a `part_of`
// line style that was never drawn.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, serveEveryEdgeKind, viewer } from "./support/viewer.js";

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
  // Cytoscape reads where its canvas is on the page when the scroll event reaches
  // it; a pointer that arrives before that frame is placed by the old position.
  // Measured on a portal whose canvas starts below the fold: the first hover
  // missed in 4 of 6 runs, and none after two frames.
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  expect(await viewer(page, "shownEdgeLabels")).toEqual([]);

  // The pointer is over one edge, though not always the one whose midpoint it
  // aimed at, where edges run close together: exactly one label shows.
  const [, point] = await viewer(page, "edgeMidpoint");
  await page.mouse.move(point.x, point.y);
  await expect.poll(async () => (await viewer(page, "shownEdgeLabels")).length).toBe(1);

  await page.mouse.move(2, 2);
  await expect.poll(() => viewer(page, "shownEdgeLabels")).toEqual([]);
});

/** `[r, g, b]` of an `rgb(...)` or `rgba(...)` string. */
function rgbOf(colour) {
  return String(colour).match(/\d+(\.\d+)?/g).slice(0, 3).map(Number);
}

/** The Euclidean distance between two colours in rgb space. */
function colourDistance(a, b) {
  const [x, y] = [rgbOf(a), rgbOf(b)];
  return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]);
}

/** The background the viewer draws its edges on: the viewer root's own background colour. */
function viewerBackground(page) {
  return page.evaluate(
    () => getComputedStyle(document.querySelector("[data-fullscreen-fallback]")).backgroundColor
  );
}

// Direction is read from two cues on every edge: an arrow at the target end
// only, and a line that fades towards its source. Both themes, because the
// fade is mixed with the theme's background.
for (const colorScheme of ["light", "dark"]) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("every drawn edge carries an arrow at its target and none at its source", async ({
      page,
      request,
    }) => {
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(
        colorScheme === "dark"
      );

      const looks = await viewer(page, "edgeLooks");
      expect(new Set(looks.map((look) => look.styleKey))).toEqual(
        new Set(["consumes", "depends_on", "produces", "uses", "violation"])
      );
      const wrong = looks.filter((look) => look.targetArrow === "none" || look.sourceArrow !== "none");
      expect(wrong).toEqual([]);
    });

    test("every drawn edge fades towards its source and ends in its own colour at the target", async ({
      page,
      request,
    }) => {
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      const background = await viewerBackground(page);

      const looks = await viewer(page, "edgeLooks");
      expect(looks.length).toBeGreaterThan(0);
      const wrong = looks.filter((look) => {
        const source = look.stops[0];
        const target = look.stops[look.stops.length - 1];
        return (
          look.stops.length < 2 ||
          colourDistance(target, look.lineColour) !== 0 ||
          colourDistance(source, background) >= colourDistance(target, background)
        );
      });
      expect(wrong).toEqual([]);
    });
  });
}
