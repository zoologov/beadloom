// The viewer stays as fast as it was: a frame at the whole-graph fit and at zoom 1, the first drawing, planning the overview, bundling, a zoom step and a hover.
//
// Before the overview drew a map, the whole-graph fit drew every node and every
// edge. Measured without a GPU on an Apple M1 Max (headless Chromium, the room
// these cases run in by default), with the view panned by script frame by frame,
// a frame at the fit took 31 ms on this portal's graph and 121 ms on the
// adopter-sized one, 43 ms at zoom 1 on the adopter-sized one, and the
// adopter-sized graph was first drawn 6.3 s after the page was opened. These cases hold the viewer to bounds stated per environment
// (`support/environment.js`), so a change that makes it slower is reported by the
// suite and not by a reader.
//
// They measure time, so the configuration runs them in a project of their own,
// one case at a time, after every other case has finished
// (`playwright.config.js`): timed beside other browsers, a case would measure
// them as well. When another case fails, these are not run.
//
// What they cannot see: a frame is timed by the browser's animation frames, which
// come at most 60 times a second, so a cost that stays inside one frame (16.7 ms)
// does not show. What keeps that cost low is what the overview draws, and
// `map.spec.js` holds it: the top-level nodes only, and at most 100 edges.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { ENVIRONMENT, GESTURE_MS, boundHere } from "./support/environment.js";
import { treeOf } from "./support/map.js";
import { centreOn } from "./support/levels.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, viewer, waitForViewer } from "./support/viewer.js";

/**
 * The longest a frame may take on average while the reader pans, at the fit and
 * at zoom 1, in ms. Locally (Apple M1 Max, no GPU) this viewer draws in every
 * 60 Hz frame, 16.7 ms apart, on both graphs, and its drawing takes 1.7 to 2.9 ms
 * of the frame; the bound is a frame and a half. A build server is slower and
 * unmeasured: its bound is two frames, which a drawing five times slower than the
 * local one still meets.
 */
const FRAME_MS = { local: 25, ci: 33.4 };
/**
 * The longest the adopter-sized graph may take to be first drawn, from opening
 * the page until the viewer is ready, in ms. Locally: 15% over the 6,271 ms the
 * viewer before the map took (median of five, Apple M1 Max, no GPU); this one
 * took 5,645. A build server is unmeasured: its bound catches a first drawing
 * that takes twice as long as the local one, not one 15% slower.
 */
const FIRST_DRAWING_MS = { local: 7200, ci: 15000 };
/**
 * The longest the overview's routes may take to plan, at the first drawing, in
 * ms, on this portal's graph and on an adopter-sized one. Measured on an Apple
 * M1 Max, no GPU, the median of three openings, on the portal these cases were
 * written on: 16 ms on its graph and 121 ms on its adopter-sized one; and 223 ms
 * on the slowest adopter-sized graph measured, built from another portal's
 * layers, which holds a box no route reaches. A build server is unmeasured: its
 * bound catches a plan four times slower than the local one.
 */
const PLAN_MS = { own: { local: 50, ci: 200 }, adopter: { local: 250, ci: 1000 } };

/**
 * How long rewriting the routes may take on an adopter-sized graph, in ms, per
 * environment (`support/environment.js`). Locally (Apple M1 Max, headless
 * Chromium, no GPU) it took 36 to 39 ms; the bound is 50. On a GitHub-hosted
 * Ubuntu runner (two Playwright workers, no GPU) it took 186.8 ms, and the same
 * code took 157 to 161 ms here with the page's processor slowed four times and
 * 196 to 205 ms slowed five times, so the runner runs it about 4.7 times slower;
 * its bound is 400, about twice what it measured there. Either bound still
 * catches the bundling without its indexes, which took 100 to 230 ms locally
 * (`shared/geometry/spatialIndex.js`). The case once ran beside the other browser cases and
 * took 43 ms there, once 50.3 with six other browsers at work: it is timed here,
 * alone, the median of `OPENINGS` openings.
 */
const BUNDLING_MS = { local: 50, ci: 400 };

/** How many pointer moves a pan makes, one per animation frame. */
const PAN_MOVES = 150;
/** How many frames pass between two readings of the drawings, well within the 240 the handle keeps. */
const COLLECT_EVERY = 30;
/** How far a pan moves the view from where it starts, in pixels, back and forth. */
const PAN_REACH_PX = 120;
/** How many drawings at the start of a pan are not counted: the pointer is pressed in them. */
const WARM_DRAWINGS = 3;
/** How many times the adopter-sized graph is opened for its first drawing; the median is held. */
const OPENINGS = 3;
/** One step of the toolbar's zoom buttons; zoom 1 is reached within half a step of it. */
const ZOOM_STEP = 1.25;
/** The most zoom steps a case takes from the fit before it gives up. */
const ZOOM_STEPS = 30;

/** The graphs a frame is timed on: this portal's and an adopter-sized one. */
const GRAPHS = [
  { name: "this portal's architecture graph", key: "own", tag: [], data: (served) => served },
  { name: "an adopter-sized architecture graph", key: "adopter", tag: [ADOPTER_SIZED], data: (served) => adopterSizedGraph(served) },
];

const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const mean = (values) => values.reduce((sum, value) => sum + value, 0) / values.length;

/** Open the architecture page over `data`. */
async function openOver(page, data) {
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
}

/**
 * Pan by dragging the canvas from its centre back and forth, one pointer move per
 * animation frame, and return how long passed between every two frames in which
 * the canvas was drawn, in ms.
 *
 * The moves are dispatched from the page, one in each frame, so every frame has
 * a move to draw: a pointer driven from outside the page delivers moves at its
 * own rate, and the frames between two moves would be timed with nothing to draw.
 * The frames the canvas was drawn in are timed rather than every frame, because
 * the canvas skips frames when a drawing takes long, and a reader sees drawings.
 * A frame was drawn in when the canvas reported a drawing (`frames`: the layer
 * over the canvas is drawn at its every drawing) between its start and the next frame's.
 */
async function panIntervals(page) {
  const { starts, drawings } = await page.evaluate(
    async ({ moves, reach, every }) => {
      const area = document.querySelector("[data-testid='graph-canvas']").getBoundingClientRect();
      const centre = { x: area.left + area.width / 2, y: area.top + area.height / 2 };
      const target = document.elementFromPoint(centre.x, centre.y);
      const fire = (type, x, y) =>
        target.dispatchEvent(
          new MouseEvent(type, { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y, button: 0, buttons: type === "mouseup" ? 0 : 1 })
        );
      const frameStarts = [];
      // The handle keeps the last drawings only, so they are collected as the pan goes.
      const drawn = new Set();
      const collect = () => window.__beadloomViewer.frames().frames.forEach((frame) => drawn.add(frame.at));
      // The pointer comes to rest on the canvas before it is pressed, as a reader's does.
      const nextFrames = () => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
      fire("mousemove", centre.x, centre.y);
      await nextFrames();
      fire("mousedown", centre.x, centre.y);
      await new Promise((done) => {
        const tick = (now) => {
          frameStarts.push(now);
          if (frameStarts.length % every === 0) collect();
          const phase = (frameStarts.length / moves) * 2 * Math.PI;
          if (frameStarts.length > moves) return done();
          fire("mousemove", centre.x + reach * Math.sin(phase), centre.y + (reach / 2) * Math.sin(2 * phase));
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
      fire("mouseup", centre.x, centre.y);
      collect();
      return { starts: frameStarts, drawings: [...drawn] };
    },
    { moves: PAN_MOVES, reach: PAN_REACH_PX, every: COLLECT_EVERY }
  );
  const drawnIn = starts.slice(0, -1).filter((start, index) => drawings.some((at) => at >= start && at < starts[index + 1]));
  return drawnIn.slice(1).map((start, index) => start - drawnIn[index]);
}

/** The intervals of a pan past its first drawings, of which there must be some. */
async function drawnWhilePanning(page) {
  const intervals = (await panIntervals(page)).slice(WARM_DRAWINGS);
  expect(intervals.length, "drawings of the canvas while it panned").toBeGreaterThan(0);
  return intervals;
}

/** Press "Zoom in" until the view is within half a zoom step of 1. */
async function zoomToOne(page) {
  const zoomIn = page.getByRole("button", { name: "Zoom in", exact: true });
  for (let step = 0; step < ZOOM_STEPS && (await viewer(page, "zoom")) < 1 / Math.sqrt(ZOOM_STEP); step += 1) {
    await zoomIn.click();
  }
  expect(await viewer(page, "zoom"), "the view zoomed in to about 1").toBeGreaterThanOrEqual(1 / Math.sqrt(ZOOM_STEP));
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
}

/** Record a measurement on the case, so the report says what was measured against what. */
function report(what, measured, bound) {
  test.info().annotations.push({ type: "measured", description: `${ENVIRONMENT}: ${what} ${measured.toFixed(1)} ms (bound ${bound} ms)` });
}

for (const graph of GRAPHS) {
  test(`on ${graph.name} a frame takes no longer than the bound for this environment, at the whole-graph fit and at zoom 1`, { tag: graph.tag }, async ({
    page,
    request,
  }) => {
    const bound = boundHere(FRAME_MS);
    await openOver(page, graph.data(await architectureData(request)));
    await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();

    const atFit = mean(await drawnWhilePanning(page));
    report("mean time between two drawings while panning at the fit", atFit, bound);
    await zoomToOne(page);
    const atOne = mean(await drawnWhilePanning(page));
    report(`mean time between two drawings while panning at zoom ${(await viewer(page, "zoom")).toFixed(2)}`, atOne, bound);

    expect(atFit, "a frame at the whole-graph fit, in ms").toBeLessThanOrEqual(bound);
    expect(atOne, "a frame at zoom 1, in ms").toBeLessThanOrEqual(bound);
  });
}

for (const graph of GRAPHS) {
  test(`on ${graph.name} the overview's routes are planned within the bound for this environment`, { tag: graph.tag }, async ({ page, request }) => {
    const bound = boundHere(PLAN_MS[graph.key]);
    const data = graph.data(await architectureData(request));
    // Each opening plans afresh, as a reader's first drawing does; the median is held.
    const plans = [];
    for (let opening = 0; opening < OPENINGS; opening += 1) {
      await openOver(page, data);
      plans.push((await viewer(page, "overviewPlan")).ms);
    }
    const planned = median(plans);
    report(`planning the overview, the median of ${plans.map((ms) => ms.toFixed(0)).join(", ")}:`, planned, bound);

    expect(planned, "planning the overview, in ms").toBeLessThanOrEqual(bound);
  });
}

test("the bundling of an adopter-sized graph takes no longer than the bound for this environment", { tag: ADOPTER_SIZED }, async ({ page, request }) => {
  const bound = boundHere(BUNDLING_MS);
  const data = adopterSizedGraph(await architectureData(request));
  // Each opening lays the graph out and bundles it afresh; the median is held.
  const runs = [];
  for (let opening = 0; opening < OPENINGS; opening += 1) {
    await openOver(page, data);
    runs.push((await viewer(page, "bundles")).ms);
  }
  const bundled = median(runs);
  report(`bundling, the median of ${runs.map((ms) => ms.toFixed(1)).join(", ")}:`, bundled, bound);

  expect(bundled, "bundling the adopter-sized graph, in ms").toBeLessThanOrEqual(bound);
});

test("the adopter-sized graph is first drawn within the bound for this environment", { tag: ADOPTER_SIZED }, async ({ browser, request }, testInfo) => {
  test.setTimeout(OPENINGS * 60_000);
  const bound = boundHere(FIRST_DRAWING_MS);
  const data = adopterSizedGraph(await architectureData(request));
  const { baseURL, viewport } = testInfo.project.use;

  const drawings = [];
  for (let opening = 0; opening < OPENINGS; opening += 1) {
    // A browser context of its own each time: nothing an earlier opening loaded or laid out is reused.
    const context = await browser.newContext({ baseURL, viewport });
    // When the viewer first reports it is ready, read on every animation frame from the page's start.
    await context.addInitScript(() => {
      const poll = () => {
        if (window.__beadloomViewer?.ready?.()) window.__firstDrawn = performance.now();
        else requestAnimationFrame(poll);
      };
      requestAnimationFrame(poll);
    });
    const page = await context.newPage();
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
    await page.goto("architecture.html");
    await waitForViewer(page);
    await page.waitForFunction(() => typeof window.__firstDrawn === "number");
    drawings.push(await page.evaluate(() => window.__firstDrawn));
    await context.close();
  }
  const first = median(drawings);
  report(`first drawing, the median of ${drawings.map((ms) => ms.toFixed(0)).join(", ")}:`, first, bound);

  expect(first, "the first drawing of the adopter-sized graph, in ms").toBeLessThanOrEqual(bound);
});

/** How many nodes in view a hover is timed on, at most, per opening. */
const HOVERED_NODES = 6;
/** How far inside the canvas's edges a node the pointer rests on lies, in pixels. */
const HOVER_MARGIN_PX = 40;

/**
 * The top-level box nearest the middle of the canvas at the fit, which a zoom
 * towards the middle keeps in view until it opens; the case is skipped without one.
 */
async function middleTopBox(page, data) {
  const { topBoxes } = treeOf(data);
  requireShape(topBoxes.length > 0, "no box at the top of the containment tree");
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const rects = await viewer(page, "boxes");
  const [cx, cy] = [canvas.x + canvas.width / 2, canvas.y + canvas.height / 2];
  const distance = (id) => Math.hypot((rects[id].x1 + rects[id].x2) / 2 - cx, (rects[id].y1 + rects[id].y2) / 2 - cy);
  return [...topBoxes].filter((id) => rects[id]).sort((a, b) => distance(a) - distance(b) || (a < b ? -1 : 1))[0];
}

/**
 * Press "Zoom in" from the page itself, and return how long passed until the
 * viewer held still again and two more frames were drawn, in ms, with whether
 * the box `box` is open then.
 */
function zoomStep(page, box) {
  return page.evaluate(async (id) => {
    const handle = window.__beadloomViewer;
    const frame = () => new Promise((done) => requestAnimationFrame(done));
    const start = performance.now();
    document.querySelector("button[aria-label='Zoom in']").click();
    await frame();
    while (!handle.ready()) await frame();
    await frame();
    await frame();
    return { ms: performance.now() - start, open: handle.openBoxes().includes(id) };
  }, box);
}

/** Rest the pointer on the middle of `rect` from the page itself, and return how long passed until two frames were drawn, in ms. */
function hoverAt(page, rect) {
  return page.evaluate(async ([x, y]) => {
    const target = document.elementFromPoint(x, y);
    const start = performance.now();
    target.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y }));
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    return performance.now() - start;
  }, [(rect.x1 + rect.x2) / 2, (rect.y1 + rect.y2) / 2]);
}

/**
 * Open `data` and press "Zoom in" towards the top-level box nearest the middle
 * until it opens: `{ box, steps }`, how long each step took, in ms.
 */
async function zoomIntoBoxTimed(page, data) {
  await openOver(page, data);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  const box = await middleTopBox(page, data);
  await centreOn(page, box);
  const steps = [];
  for (let step = 0; step < ZOOM_STEPS; step += 1) {
    const { ms, open } = await zoomStep(page, box);
    steps.push(ms);
    if (open) return { box, steps };
  }
  throw new Error(`${box} did not open in ${ZOOM_STEPS} zoom steps`);
}

for (const graph of GRAPHS) {
  test(`on ${graph.name} a zoom step towards a box is drawn within the bound for this environment`, { tag: graph.tag }, async ({ page, request }) => {
    test.setTimeout(OPENINGS * 60_000);
    const bound = boundHere(GESTURE_MS.zoomStep[graph.key]);
    const data = graph.data(await architectureData(request));
    const steps = [];
    let box = null;
    for (let opening = 0; opening < OPENINGS; opening += 1) {
      const run = await zoomIntoBoxTimed(page, data);
      box = run.box;
      steps.push(...run.steps);
    }
    const step = median(steps);
    report(`a zoom step until ${box} opens, the median of ${steps.length} (the longest ${Math.max(...steps).toFixed(0)}):`, step, bound);

    expect(step, "a zoom step, in ms").toBeLessThanOrEqual(bound);
  });

  test(`on ${graph.name} the pointer resting on a node inside an open box is drawn within the bound for this environment`, { tag: graph.tag }, async ({ page, request }) => {
    test.setTimeout(OPENINGS * 60_000);
    const bound = boundHere(GESTURE_MS.hover[graph.key]);
    const data = graph.data(await architectureData(request));
    const hovers = [];
    for (let opening = 0; opening < OPENINGS; opening += 1) {
      await zoomIntoBoxTimed(page, data);
      // The nodes in view with edges out of the box, which a hover draws.
      const marks = await viewer(page, "outwardMarks");
      const rects = await viewer(page, "boxes");
      const canvas = await page.getByTestId("graph-canvas").boundingBox();
      const inView = (r) =>
        (r.x1 + r.x2) / 2 > canvas.x + HOVER_MARGIN_PX && (r.x1 + r.x2) / 2 < canvas.x + canvas.width - HOVER_MARGIN_PX &&
        (r.y1 + r.y2) / 2 > canvas.y + HOVER_MARGIN_PX && (r.y1 + r.y2) / 2 < canvas.y + canvas.height - HOVER_MARGIN_PX;
      const nodes = Object.keys(marks).filter((id) => rects[id] && inView(rects[id])).sort().slice(0, HOVERED_NODES);
      requireShape(nodes.length > 0, "no node in view inside the top-level box zoomed into has an edge out of it");
      for (const id of nodes) {
        await page.mouse.move(2, 2);
        await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
        hovers.push(await hoverAt(page, rects[id]));
      }
    }
    const hover = median(hovers);
    report(`the pointer resting on a node with edges out of its box, the median of ${hovers.length} (the longest ${Math.max(...hovers).toFixed(0)}):`, hover, bound);

    expect(hover, "a hover, in ms").toBeLessThanOrEqual(bound);
  });
}
