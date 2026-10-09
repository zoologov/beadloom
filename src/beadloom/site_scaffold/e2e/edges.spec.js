// Edges: one style per kind, violations stand out, the legend lists what is drawn and draws it as the canvas does.
//
// In an earlier version the viewer drew two kinds of six and its legend listed a `part_of`
// line style that was never drawn. A violation was once also drawn thicker, and
// every line faded towards its source; now every line has one weight and one
// colour from end to end, and kinds differ by colour and dash alone.
//
// Every case but the legend's reads the edges at full detail, every box open: at
// the whole-graph fit the viewer draws aggregated edges between closed boxes
// (`map.spec.js`). The legend is read at every level a reader reaches, because it
// names what the canvas draws there, aggregated lines included: a legend derived
// from the data file once left the overview drawing an indigo solid line the
// dotted `uses` sample did not describe.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, openEveryBox, serveEveryEdgeKind, viewer } from "./support/viewer.js";
import { channelDistance, finalRunGroups, hasTargetHead } from "./support/look.js";
import { centreOn, settled } from "./support/levels.js";
import { treeOf } from "./support/map.js";
import { requireShape } from "./support/shape.js";

/** How many presses of "Zoom in" the legend is read over at most, from the whole-graph fit: past the most the view zooms in. */
const LEGEND_ZOOM_STEPS = 30;

/** A dash pattern's proportion, dash to gap, or "solid": a dash is drawn in pixels on screen, so its proportion is what a zoom keeps. */
const proportionOf = (dash) => (dash.length ? (dash[0] / dash[1]).toFixed(2) : "solid");

/** The style key the viewer draws an edge of the architecture's data file with: the violation's, else its kind. */
const styleKeyOfEdge = (edge) => (edge.kind === "depends_on" && edge.violation === true ? "violation" : edge.kind);

/** The legend's entries as the browser paints them: `{ key: { colour, dash } }`, `dash` the sample's pattern, empty when solid. */
async function legendEntries(page) {
  const items = await page.locator("[data-legend-edge]").evaluateAll((items) =>
    items.map((item) => {
      const line = getComputedStyle(item.querySelector("[data-legend-line]"));
      return { key: item.dataset.legendEdge, colour: line.stroke, dash: line.strokeDasharray };
    })
  );
  return Object.fromEntries(items.map(({ key, colour, dash }) => [key, { colour, dash: dash === "none" ? [] : (dash.match(/[\d.]+/g) || []).map(Number) }]));
}

/**
 * What disagrees, at the level drawn now, between the lines on the canvas and the
 * edge legend: a line whose style has no entry, or is drawn in another colour or
 * dash than its entry's sample, and an entry no line is drawn in. A line of the
 * map's that carries edges of more than one style is drawn solid in the style it
 * carries most (RFC D8): its colour is its entry's, its dash solid.
 * `{ wrong, lines, keys }`, `keys` the styles drawn.
 */
async function legendAgainstCanvas(page, styleOf) {
  const looks = (await viewer(page, "lineLooks")).filter((look) => look.styleKey);
  const mapLines = [...(await viewer(page, "aggregatedEdges")), ...(await viewer(page, "ownLines"))].filter((line) => line.drawn);
  const several = new Set(mapLines.filter((line) => new Set([...line.forwardKeys, ...line.backwardKeys].map((key) => styleOf.get(key))).size > 1).map((line) => line.id));
  const legend = await legendEntries(page);
  const keys = [...new Set(looks.map((look) => look.styleKey))].sort();
  const wrong = new Set(Object.keys(legend).filter((key) => !keys.includes(key)).map((key) => `the legend's ${key}: no line is drawn in it`));
  for (const look of looks) {
    const entry = legend[look.styleKey];
    if (!entry) {
      wrong.add(`${look.styleKey}: drawn, and not in the legend`);
      continue;
    }
    if (channelDistance(look.colour, entry.colour) > 1) wrong.add(`${look.styleKey}: drawn ${look.colour}, its sample ${entry.colour}`);
    const wanted = several.has(look.id) ? "solid" : proportionOf(entry.dash);
    if (proportionOf(look.dash) !== wanted) wrong.add(`${look.styleKey}${look.aggregated ? " (aggregated)" : ""}: drawn ${proportionOf(look.dash)}, ${several.has(look.id) ? "a line of several styles" : "its sample"} ${wanted}`);
  }
  return { wrong: [...wrong], lines: looks.length, keys };
}

/**
 * Read the legend against the canvas at every level a reader reaches: the
 * whole-graph fit, each level the presses of "Zoom in" towards the largest
 * top-level box draw, up to the most the view zooms in, every box open with the
 * edges drawn as the map draws them at rest, and every edge drawn as itself.
 * `{ wrong, read }`, `read` what each level drew.
 */
async function legendAtEveryLevel(page, data) {
  const styleOf = new Map(data.edges.map((edge) => [`${edge.kind}:${edge.src}->${edge.dst}`, styleKeyOfEdge(edge)]));
  const tree = treeOf(data);
  const wrong = [];
  const read = [];
  const levelNow = async () => JSON.stringify([await viewer(page, "openBoxes"), (await viewer(page, "lineLooks")).length]);
  const look = async (state) => {
    await settled(page);
    const found = await legendAgainstCanvas(page, styleOf);
    const open = (await viewer(page, "openBoxes")).length;
    read.push(`${state}: ${found.lines} line(s), ${open} box(es) open, ${found.keys.join(" ") || "no style"}`);
    wrong.push(...found.wrong.map((w) => `${state}: ${w}`));
  };
  await look("at the fit");
  const held = (box) => Object.keys(tree.parents).filter((id) => tree.parents[id] === box).length;
  const target = [...tree.topBoxes].sort((a, b) => held(b) - held(a) || (a < b ? -1 : 1))[0];
  if (target) await centreOn(page, target);
  let last = await levelNow();
  for (let step = 0; step < LEGEND_ZOOM_STEPS; step += 1) {
    const zoom = await viewer(page, "zoom");
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await settled(page);
    if ((await viewer(page, "zoom")) === zoom) break;
    // A press that opens no box and draws no other line draws the level read last.
    const level = await levelNow();
    if (level !== last) await look(`zoom in ${step + 1}`);
    last = level;
  }
  await openEveryBox(page, { edges: false });
  await look("every box open");
  await openEveryBox(page);
  await look("every edge as itself");
  return { wrong, read };
}

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

for (const served of ["as served", "with every edge kind"]) {
  test(`at every level the legend names each line drawn, in its colour and its dash, and nothing else, on the graph ${served}`, async ({ page, request }) => {
    const data = served === "as served" ? await architectureData(request) : await serveEveryEdgeKind(page, request);
    requireShape(data.edges.some((edge) => edge.kind !== "part_of"), "no edge drawn as a line");
    await openArchitecture(page);
    const { wrong, read } = await legendAtEveryLevel(page, data);
    test.info().annotations.push({ type: "measured", description: read.join("; ") });

    expect(wrong).toEqual([]);
  });
}

test("an aggregated line that carries edges of one kind keeps that kind's dash, as its legend sample is drawn", async ({ page, request }) => {
  // Every edge of the served graph made a `uses` edge: each line the overview aggregates carries one kind.
  const data = await architectureData(request);
  const drawn = data.edges.filter((edge) => edge.kind !== "part_of");
  requireShape(drawn.length > 0, "no edge drawn as a line");
  for (const edge of drawn) {
    edge.kind = "uses";
    delete edge.violation;
  }
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);

  const aggregated = (await viewer(page, "lineLooks")).filter((look) => look.aggregated);
  requireShape(aggregated.length > 0, "no aggregated line at the whole-graph fit");
  const { uses } = await legendEntries(page);
  expect(uses).toBeTruthy();
  const wrong = aggregated.filter((look) => look.styleKey !== "uses" || proportionOf(look.dash) !== proportionOf(uses.dash)).map((look) => `${look.id}: ${look.styleKey} ${proportionOf(look.dash)}`);
  test.info().annotations.push({ type: "measured", description: `${aggregated.length} aggregated line(s) at the fit; the sample's dash ${proportionOf(uses.dash)}` });

  expect(wrong).toEqual([]);
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
