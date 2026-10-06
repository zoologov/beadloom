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
// Every head drawn wrong fails the case, whatever is in its way. An earlier case
// only noted a head the drawing left no room for — a line that bends, crosses or
// runs beside it nearer than even the smallest head needs — and what a loop did
// wrong: Cytoscape drew a line from a node to a box that holds it as a curve
// across the box. The levels now draw a line between
// nodes only where they are readable, keep an open box's outward edges at the
// box, and route a loop like any other line; a line that leaves a node beside
// where a head arrives starts behind its base, and of two heads side by side on
// one border, too near for both at the zoom drawn, one gives way. The cases read the states the
// viewer draws: every box open as a reader's zoom opens it, from the lowest zoom
// a box stays open at, and a selection, its node's own edges on top. A followed
// line is drawn over every line that is not, and meets their heads by design.
//
// The cases run on this portal's graph, on the same graph with two edges more
// (`support/perturbedGraph.js`), which ELK lays out another way, and on an
// adopter-sized one: a rule that held on one layout of a graph once failed on
// the next when two edges were added, so each is read on two.
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
import { CLOSE_SHARE, READABLE_PX } from "./support/levels.js";
import { withTwoMoreEdges } from "./support/perturbedGraph.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, openEveryBox, viewer } from "./support/viewer.js";

/** An arrowhead's full length on screen, in pixels. */
const HEAD_PX = 6;
/** The smallest length the viewer draws an arrowhead at, in pixels, where its run has no room for the full one. */
const SMALLEST_HEAD_PX = 3;
/** The zoom step of the buttons, and the step the viewer restyles its marks at. */
const STEP = 1.25;
/** The viewer's smallest zoom (the navigation's `minZoom`): a fit held at it does not fit the canvas. */
const MIN_ZOOM = 0.02;
/** The zooms every head is read at with every box open, besides the lowest at which a box stays open (`closingZoomOf`). */
const ZOOMS = [0.545, 0.8, 1, 1.5, 2];

/**
 * The lowest zoom at which the viewer draws a node inside an open box: where its
 * smallest node stands at the share of the readable height an open box closes
 * below (`support/levels.js`). Below it every box is closed and no line between
 * nodes is drawn, so no head of one is read there.
 */
function closingZoomOf(boxes, data) {
  const parents = new Set(data.nodes.map((n) => n.parent).filter((parent, i) => parent && parent !== data.nodes[i].id));
  const leaves = data.nodes.filter((n) => !parents.has(n.id) && boxes[n.id]).map((n) => boxes[n.id].y2 - boxes[n.id].y1);
  return (CLOSE_SHARE * READABLE_PX) / Math.min(...leaves);
}
const SIZES = { head: HEAD_PX, smallest: SMALLEST_HEAD_PX, step: STEP };

const twoFrames = (page) => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));

/** Press the zoom buttons until the view is within half a step of `target`, or when `atLeast`, within a step above it. */
async function zoomNear(page, target, { atLeast = false } = {}) {
  for (let press = 0; press < 40; press += 1) {
    const zoom = await viewer(page, "zoom");
    const steps = Math.log(target / zoom) / Math.log(STEP);
    if (atLeast ? zoom >= target && steps > -1 : Math.abs(steps) <= 0.5 + 1e-6) break;
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
 * Every head now that is wrong, whatever is in its way: drawn wrong by the
 * viewer, left no room by the drawing — a line that bends, crosses or runs
 * beside it too near for even the smallest head — or wrong because of a loop.
 * Each is named with what is wrong, and with which of the three it is.
 */
async function wrongNow(page) {
  const heads = await headsNow(page);
  requireShape(heads.length > 0, "no drawn line ends in an arrowhead");
  return [...wrongHeads(heads), ...roomlessHeads(heads).map((text) => `no room: ${text}`), ...loopHeads(heads).map((text) => `loop: ${text}`)];
}

/** The node that depends on the most others. */
function busiestSource(data) {
  const counts = new Map();
  for (const edge of data.edges.filter((e) => e.kind === "depends_on")) counts.set(edge.src, (counts.get(edge.src) || 0) + 1);
  const [busiest] = [...counts].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0] || [];
  requireShape(Boolean(busiest), "no node depends on another");
  return busiest;
}

/** The served file with two edges more, laid out another way (`support/perturbedGraph.js`); the case is skipped without one. */
function perturbed(data) {
  const more = withTwoMoreEdges(data);
  requireShape(Boolean(more), "no two leaves in two other top-level boxes than a third leaf's");
  return more.data;
}

/** The graphs the heads are read on: the served one, as the browser gets it, and two made from it, served in its place. */
const GRAPHS = [
  { name: "this portal's architecture graph", served: true, tag: [], data: async (request) => architectureData(request) },
  {
    name: "this portal's architecture graph with two edges more",
    served: false,
    tag: [],
    data: async (request) => perturbed(await architectureData(request)),
  },
  {
    name: "an adopter-sized architecture graph",
    served: false,
    tag: [ADOPTER_SIZED],
    data: async (request) => adopterSizedGraph(await architectureData(request)),
  },
];

for (const graph of GRAPHS) {
  test.describe(graph.name, { tag: graph.tag }, () => {
    test("with every box open, every arrowhead is entered straight, is whole and keeps clear of other lines, at every zoom from the lowest a box stays open at to 2", async ({
      page,
      request,
    }) => {
      const data = await graph.data(request);
      if (!graph.served) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      await openEveryBox(page, { edges: false });
      const closing = closingZoomOf((await viewer(page, "elkGeometry")).boxes, data);
      const zooms = [Number(closing.toFixed(3)), ...ZOOMS.filter((zoom) => zoom > closing)];
      const found = {};
      for (const zoom of zooms) {
        const reached = await zoomNear(page, zoom, { atLeast: zoom === zooms[0] });
        found[zoom] = { zoom: Number(reached.toFixed(3)), wrong: await wrongNow(page) };
      }
      expect(found).toEqual(Object.fromEntries(zooms.map((zoom) => [zoom, { zoom: found[zoom].zoom, wrong: [] }])));
    });

    test("as the overview is zoomed into, every drawn arrowhead is entered straight, whole and clear", async ({ page, request }) => {
      const data = await graph.data(request);
      if (!graph.served) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      const found = [];
      const fit = await viewer(page, "zoom");
      for (let step = 0; step < 24; step += 1) {
        const zoom = await viewer(page, "zoom");
        if (zoom > 2 * Math.sqrt(STEP)) break;
        const wrong = await wrongNow(page);
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
      if (!graph.served) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page, `?focus=${encodeURIComponent(busiestSource(data))}&depth=1`);
      await expect.poll(async () => (await viewer(page, "lineLooks")).some((look) => look.walk)).toBe(true);
      // An overview for a project whose top level does not fit the canvas is deferred (ruling 11):
      // where the fit is held at the smallest zoom, its heads are read up close only.
      const clamped = (await viewer(page, "level")).fitZoom <= MIN_ZOOM + 1e-9;
      const atFit = clamped ? [] : await wrongNow(page);
      await openEveryBox(page, { edges: false });
      const found = { atFit, upClose: {} };
      for (const zoom of [0.545, 1]) {
        await zoomNear(page, zoom);
        found.upClose[zoom] = await wrongNow(page);
      }
      expect(found).toEqual({ atFit: [], upClose: { 0.545: [], 1: [] } });
    });
  });
}
