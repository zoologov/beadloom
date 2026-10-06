// Edges: one style per kind, violations stand out, the legend lists what is drawn and draws it as the canvas does.
//
// In an earlier version the viewer drew two kinds of six and its legend listed a `part_of`
// line style that was never drawn. A violation was once also drawn thicker, and
// every line faded towards its source; now every line has one weight and one
// colour from end to end, and kinds differ by colour and dash alone.
//
// Every case reads the edges at full detail, every box open: at the whole-graph
// fit the viewer draws aggregated edges between closed boxes (`map.spec.js`).

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, openEveryBox, serveEveryEdgeKind, viewer } from "./support/viewer.js";
import { channelDistance, finalRunGroups, hasTargetHead } from "./support/look.js";

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
  await openEveryBox(page);

  const drawn = await viewer(page, "drawnEdgeKinds");
  expect(drawn).toEqual(expectedKeys(data));
  const legend = await page
    .locator("[data-legend-edge]")
    .evaluateAll((items) => items.map((item) => item.dataset.legendEdge).sort());
  expect(legend).toEqual(drawn);
});

test("each edge kind has its own line style, and a violation is red and dashed, at the weight of every other line", async ({
  page,
  request,
}) => {
  const data = await serveEveryEdgeKind(page, request);
  await openArchitecture(page);
  await openEveryBox(page);
  const drawn = await viewer(page, "drawnEdgeKinds");
  expect(drawn).toEqual(expectedKeys(data));
  expect(drawn).toEqual(["consumes", "depends_on", "produces", "uses", "violation"]);
  const styles = {};
  for (const key of drawn) styles[key] = await viewer(page, "edgeStyle", key);
  const dashes = Object.fromEntries(
    (await viewer(page, "lineLooks")).filter((look) => !look.aggregated).map((look) => [look.styleKey, look.dash])
  );

  // A dash is drawn in pixels on screen, so each kind's pattern keeps its proportions at
  // every zoom; a dotted kind is a pattern of dots.
  const proportion = (key) => {
    const [dash, gap] = dashes[key] || [];
    return dash === undefined ? "solid" : (dash / gap).toFixed(2);
  };
  const expected = { depends_on: "solid", uses: (1.5 / 2.5).toFixed(2), consumes: (6 / 3).toFixed(2), produces: (2 / 3).toFixed(2), violation: (8 / 4).toFixed(2) };
  for (const [key, pattern] of Object.entries(expected)) expect(proportion(key), key).toBe(pattern);
  expect(styles.consumes.colour).not.toBe(styles.produces.colour);
  expect(styles.violation.lineStyle).toBe("dashed");
  for (const key of drawn) expect(styles[key].width, key).toBe(styles.depends_on.width);
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
  await openEveryBox(page);
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

// Direction is read from the arrow at the target end alone: a line is one colour
// from end to end. Both themes, because a line's colour is mixed with the
// theme's background.
for (const colorScheme of ["light", "dark"]) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("every drawn edge ends in an arrow at its target, its own or one on the last run it shares, and none at its source", async ({
      page,
      request,
    }) => {
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      await openEveryBox(page);
      expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(
        colorScheme === "dark"
      );

      const looks = (await viewer(page, "lineLooks")).filter((look) => !look.aggregated);
      expect(new Set(looks.map((look) => look.styleKey))).toEqual(
        new Set(["consumes", "depends_on", "produces", "uses", "violation"])
      );
      expect(looks.filter((look) => look.sourceArrow !== "none").map((look) => look.id)).toEqual([]);
      // A line into an open box that its node's lines run on into is their stub: their heads are its
      // (`levels.spec.js`); and of two heads side by side on one border, too near for both at the scale drawn,
      // one gives way to the other (`heads.spec.js`).
      const gaveWay = new Set((await viewer(page, "droppedHeads")).filter((d) => d.end === "target").map((d) => d.id));
      const headless = finalRunGroups(looks).filter((group) => !group.some(hasTargetHead) && !group.every((look) => look.stub || gaveWay.has(look.id)));
      expect(headless.map((group) => group.map((look) => look.id).join(" + "))).toEqual([]);
    });

    test("every drawn edge is one colour from end to end, and its arrowhead is that colour", async ({
      page,
      request,
    }) => {
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      await openEveryBox(page);

      const looks = await viewer(page, "lineLooks");
      expect(looks.length).toBeGreaterThan(0);
      const wrong = looks.filter((look) => look.lineFill !== "solid" || channelDistance(look.arrowColour, look.colour) !== 0);
      expect(wrong.map((look) => look.id)).toEqual([]);
    });

    test("the legend draws each edge style in the colour the canvas draws it, with an arrowhead", async ({ page, request }) => {
      await serveEveryEdgeKind(page, request);
      await openArchitecture(page);
      await openEveryBox(page);

      const canvas = {};
      for (const look of await viewer(page, "lineLooks")) {
        if (!look.aggregated && !look.dimmed && !look.walk) canvas[look.styleKey] = look.colour;
      }
      const legend = await page.locator("[data-legend-edge]").evaluateAll((items) =>
        items.map((item) => ({
          key: item.dataset.legendEdge,
          line: getComputedStyle(item.querySelector("[data-legend-line]")).stroke,
          head: Boolean(item.querySelector("[data-legend-head]")),
        }))
      );
      expect(legend.length).toBeGreaterThan(0);
      const wrong = legend.filter(({ key, line, head }) => !head || !canvas[key] || channelDistance(line, canvas[key]) > 1);
      expect(wrong).toEqual([]);
    });
  });
}
