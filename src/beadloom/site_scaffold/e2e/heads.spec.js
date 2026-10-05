// A line enters its arrowhead correctly, at every zoom at which the line is drawn.
//
// An earlier viewer drew every head at one size on a run that ELK ends ten
// layout units after the line's last bend: from about zoom 0.6 down the head was
// longer than its run, so the line came into the side of it; at zoom 1 the head
// fitted with the corner rounding into its base. A line that left its head to
// another on a shared last run was drawn on to the tip, past the head's sides,
// and in another colour through it. A measure of "a straight run at least as long
// as the head", taken at zoom 1 only, passed all of it.
//
// Now a head stands on a straight line of its own: its length and half a head
// more, behind its tip, over every line that ends there. The viewer moves the
// last bend of a route back where nothing is in the way, and where it cannot, a
// head is drawn smaller, down to a smallest size, as it is where a line runs
// beside it or across its run; a line that leaves its head to another ends at
// that head's base, and a dashed line ends a dash inside its head.
//
// A head the drawing leaves no room for — a line that bends, crosses or runs
// beside it nearer than even the smallest head needs — is not failed but noted on
// the case ("no room for a head"): what is in its way is a route or a level, and
// such heads are reported to be decided, not hidden. So is what is wrong because
// of a loop ("a loop's head or line"): Cytoscape draws a line from a node to a
// box that holds it from the node across the box to the box's border, wherever
// that border meets other lines, and the levels decide when such a line is drawn.
// Everything else wrong with a head fails the case.
//
// What the cases cannot see. They read the drawn lines through the test handle
// and measure them with their own restatement of how Cytoscape draws a line and
// its head (`support/heads.js`); they compare no pixels. The definition was
// confirmed against rendered pixels when it was made: each head drawn alone, its
// ink read back, showed no ink off the head and its straight line where the
// geometry passed it. The zooms are reached with the zoom buttons, so each is
// held within half a zoom step of the one named.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { headsOf, loopHeads, roomlessHeads, wrongHeads } from "./support/heads.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, openEveryBox, viewer } from "./support/viewer.js";

/** An arrowhead's full length on screen, in pixels. */
const HEAD_PX = 6;
/** The smallest length the viewer draws an arrowhead at, in pixels, where its run has no room for the full one. */
const SMALLEST_HEAD_PX = 4;
/** The zoom step of the buttons, and the step the viewer restyles its marks at. */
const STEP = 1.25;
/** The viewer's smallest zoom (the navigation's `minZoom`): a fit held at it does not fit the canvas. */
const MIN_ZOOM = 0.02;
/** The zooms every head is read at with every box open. */
const ZOOMS = [0.3, 0.545, 0.8, 1, 1.5, 2];
const SIZES = { head: HEAD_PX, smallest: SMALLEST_HEAD_PX, step: STEP };

const twoFrames = (page) => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));

/** Press the zoom buttons until the view is within half a step of `target`. */
async function zoomNear(page, target) {
  for (let press = 0; press < 40; press += 1) {
    const zoom = await viewer(page, "zoom");
    const steps = Math.log(target / zoom) / Math.log(STEP);
    if (Math.abs(steps) <= 0.5 + 1e-6) break;
    await page.getByRole("button", { name: steps > 0 ? "Zoom in" : "Zoom out", exact: true }).click();
  }
  await twoFrames(page);
  return viewer(page, "zoom");
}

/** Every drawn head now and what is wrong with it. */
async function headsNow(page) {
  const view = { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
  return headsOf(await viewer(page, "lineLooks"), view, SIZES);
}

/**
 * The heads now that the viewer drew wrong, and note on the case those the
 * drawing leaves no room for: a line that bends, crosses or runs beside a head
 * too near for even the smallest head. Those are reported, not failed: what is
 * in their way is a route or a level, not the head.
 */
async function wrongNow(page, where) {
  const heads = await headsNow(page);
  requireShape(heads.length > 0, "no drawn line ends in an arrowhead");
  const notes = { "no room for a head": roomlessHeads(heads), "a loop's head or line": loopHeads(heads) };
  for (const [type, listed] of Object.entries(notes)) {
    if (listed.length) test.info().annotations.push({ type, description: `${where}: ${listed.length} of ${heads.length}: ${listed.join(" | ")}` });
  }
  return wrongHeads(heads);
}

/** The node that depends on the most others. */
function busiestSource(data) {
  const counts = new Map();
  for (const edge of data.edges.filter((e) => e.kind === "depends_on")) counts.set(edge.src, (counts.get(edge.src) || 0) + 1);
  const [busiest] = [...counts].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0] || [];
  requireShape(Boolean(busiest), "no node depends on another");
  return busiest;
}

const GRAPHS = [
  { name: "this portal's architecture graph", tag: [], data: async (request) => architectureData(request) },
  {
    name: "an adopter-sized architecture graph",
    tag: [ADOPTER_SIZED],
    data: async (request) => adopterSizedGraph(await architectureData(request)),
  },
];

for (const graph of GRAPHS) {
  test.describe(graph.name, { tag: graph.tag }, () => {
    test("with every box open, every arrowhead is entered straight, is whole and keeps clear of other lines, at every zoom from 0.3 to 2", async ({
      page,
      request,
    }) => {
      const data = await graph.data(request);
      if (graph.tag.length) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      await openEveryBox(page);
      const found = {};
      for (const zoom of ZOOMS) {
        const reached = await zoomNear(page, zoom);
        found[zoom] = { zoom: Number(reached.toFixed(3)), wrong: await wrongNow(page, `every box open, zoom ${reached.toFixed(3)}`) };
      }
      expect(found).toEqual(Object.fromEntries(ZOOMS.map((zoom) => [zoom, { zoom: found[zoom].zoom, wrong: [] }])));
    });

    test("as the overview is zoomed into, every drawn arrowhead is entered straight, whole and clear", async ({ page, request }) => {
      const data = await graph.data(request);
      if (graph.tag.length) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      const found = [];
      const fit = await viewer(page, "zoom");
      for (let step = 0; step < 24; step += 1) {
        const zoom = await viewer(page, "zoom");
        if (zoom > 2 * Math.sqrt(STEP)) break;
        const wrong = await wrongNow(page, `the overview zoomed in, zoom ${zoom.toFixed(3)}`);
        if (wrong.length) found.push({ zoom: Number(zoom.toFixed(3)), wrong });
        await page.getByRole("button", { name: "Zoom in", exact: true }).click();
        await twoFrames(page);
      }
      expect(fit).toBeGreaterThan(0);
      expect(found).toEqual([]);
    });

    test("with a node selected, every drawn arrowhead is entered straight, whole and clear, at the fit and up close", async ({
      page,
      request,
    }) => {
      const data = await graph.data(request);
      if (graph.tag.length) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page, `?focus=${encodeURIComponent(busiestSource(data))}&depth=1`);
      await expect.poll(async () => (await viewer(page, "lineLooks")).some((look) => look.walk)).toBe(true);
      // An overview for a project whose top level does not fit the canvas is deferred (ruling 11):
      // where the fit is held at the smallest zoom, its heads are read up close only.
      const clamped = (await viewer(page, "level")).fitZoom <= MIN_ZOOM + 1e-9;
      const atFit = clamped ? [] : await wrongNow(page, "a selection at the fit");
      await openEveryBox(page);
      const found = { atFit, upClose: {} };
      for (const zoom of [0.545, 1]) {
        const reached = await zoomNear(page, zoom);
        found.upClose[zoom] = await wrongNow(page, `a selection, every box open, zoom ${reached.toFixed(3)}`);
      }
      expect(found).toEqual({ atFit: [], upClose: { 0.545: [], 1: [] } });
    });
  });
}
