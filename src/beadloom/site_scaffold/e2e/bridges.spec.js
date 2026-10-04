// A highlighted edge hops over every edge it crosses, so a reader can follow it through a busy area.
//
// Where routes cross, a line being followed is lost among the others. The
// highlighted edges — every edge along a hovered line, and every edge of a
// selection's walk — now carry a bridge, a half circle, at every crossing with
// another drawn edge; nothing else does, since bridges on every crossing read as
// texture. Edges of one bundle cross each other where they fan out, and no
// bridge is drawn there: a bundle is one line to the reader.
//
// Where the bridges belong is checked against `support/bridges.js`, which tests
// every pair of drawn segments with no index, from the routes the handle reports
// as drawn (`edgeRoutes`). The cases that read every edge open every box first:
// at the whole-graph fit the viewer draws a map (`map.spec.js`).

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { bundleSiblings, compareBridges, expectedBridges } from "./support/bridges.js";
import { neighbourhood } from "./support/graph.js";
import { drag } from "./support/pointer.js";
import { distanceToPolyline } from "./support/routeMetrics.js";
import { CYTOSCAPE_FALLBACK_COLOUR, architectureData, openArchitecture, openEveryBox, parentMap, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

/** The most zoom steps a case takes to bring the view to about full size. */
const ZOOM_STEPS = 30;
/** How far a crossing may lie from a box's border and still not count as inside or outside it, in layout units. */
const BORDER = 1;
/** The radius a hop takes once the view is at full size or closer, in pixels, and the most it ever takes there. */
const HOP_PX = 5;
const WIDEST_HOP_PX = 10;
/** How long drawing the bridges may take per frame, on average, in ms: a few, so no frame is lost to them. */
const FRAME_BUDGET_MS = 3;
/** How long finding and colouring a hub's bridges may take once, in ms, on an adopter-sized graph. */
const REFRESH_BUDGET_MS = 150;
/** The most drags a case takes to bring a point to the centre. */
const CENTRING_DRAGS = 12;
/** How many frames a measured pan lasts. */
const PAN_FRAMES = 60;
/** How far, in pixels on screen, a hovered point lies from any other edge and any node. */
const CLEARANCE_PX = 12;
/** The window, in layout units, the busiest place of bridges is counted over: about a canvas at full size. */
const WINDOW = { width: 1000, height: 500 };

/** The graphs bridges are read on: this portal's and an adopter-sized one. */
const GRAPHS = [
  {
    name: "this portal's architecture graph",
    tag: [],
    data: (request) => architectureData(request),
  },
  {
    name: "an adopter-sized architecture graph",
    tag: [ADOPTER_SIZED],
    data: async (request) => adopterSizedGraph(await architectureData(request)),
    slow: true,
  },
];

/** Serve `data` as the architecture data file, and open the architecture page with `query`. */
async function openWith(page, data, query = "") {
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page, query);
}

/** The ids that hold no other node. */
const leavesOf = (parents) => {
  const holders = new Set(Object.values(parents).filter(Boolean));
  return new Set(Object.keys(parents).filter((id) => !holders.has(id)));
};

/** The routed edges drawn now, `[{ id, key, source, target, aggregated, points }]`. */
async function drawnRoutes(page) {
  return (await viewer(page, "edgeRoutes")).filter((r) => r.routed);
}

/** The leaf with the most edges drawn at full detail. */
async function busiestLeaf(page, data) {
  await openWith(page, data);
  await openEveryBox(page);
  const leaves = leavesOf(parentMap(data));
  const degree = new Map();
  for (const r of await drawnRoutes(page)) {
    for (const id of [r.source, r.target]) if (leaves.has(id)) degree.set(id, (degree.get(id) || 0) + 1);
  }
  const [busiest] = [...degree].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0] || [null];
  requireShape(Boolean(busiest), "no node has a drawn edge");
  return busiest;
}

/**
 * The edges the walk `keys` highlights among the routed edges drawn now: an edge
 * of the data file when the walk took it, an aggregated edge when it carries one
 * the walk took.
 */
async function walkedNow(page, keys) {
  const carried = new Map((await viewer(page, "aggregatedEdges")).filter((a) => a.drawn).map((a) => [a.id, [...a.forwardKeys, ...a.backwardKeys]]));
  const routes = await drawnRoutes(page);
  const walked = (r) => (r.aggregated ? (carried.get(r.id) || []).some((key) => keys.has(key)) : keys.has(r.key));
  return { routes, highlighted: new Set(routes.filter(walked).map((r) => r.id)) };
}

/** The difference between the bridges drawn now and the ones the rule asks for, with the walk `keys` highlighted. */
async function bridgesAgainstWalk(page, keys) {
  const { routes, highlighted } = await walkedNow(page, keys);
  const siblings = bundleSiblings(await viewer(page, "bundles"));
  const reported = await viewer(page, "bridges");
  return { reported, highlighted, ...compareBridges(reported, expectedBridges(routes, highlighted, siblings)) };
}

/**
 * Bring the view to about full size around `point`, in graph coordinates: the
 * panel closed, the point brought to the centre at every zoom step, since a step
 * zooms about the centre.
 */
async function zoomToFullSizeAt(page, point) {
  await page.getByRole("button", { name: "Panel" }).click();
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await nextFrames(page);
  for (let step = 0; step < ZOOM_STEPS && (await viewer(page, "zoom")) < 1; step += 1) {
    await centreOn(page, point);
    await page.getByRole("button", { name: "Zoom in" }).click();
  }
  await centreOn(page, point);
}

/** Wait until the page has drawn two more frames. */
function nextFrames(page) {
  return page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
}

/** Where a point in graph coordinates is on the page now. */
async function onPage(page, point) {
  const zoom = await viewer(page, "zoom");
  const pan = await viewer(page, "pan");
  const rect = await page.getByTestId("graph-canvas").boundingBox();
  return { x: rect.x + point.x * zoom + pan.x, y: rect.y + point.y * zoom + pan.y };
}

/** Pan the view, a third of the canvas at a time, until `point` (graph coordinates) is at the canvas's centre. */
async function centreOn(page, point) {
  const rect = await page.getByTestId("graph-canvas").boundingBox();
  const centre = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
  for (let step = 0; step < CENTRING_DRAGS; step += 1) {
    const at = await onPage(page, point);
    const [dx, dy] = [centre.x - at.x, centre.y - at.y];
    if (Math.abs(dx) < 2 && Math.abs(dy) < 2) break;
    const clamp = (value, limit) => Math.max(-limit, Math.min(limit, value));
    await drag(page, centre, clamp(dx, rect.width / 3), clamp(dy, rect.height / 3));
  }
  // The pointer leaves the canvas, so no edge stays hovered and highlighted.
  await page.mouse.move(2, 2);
  await nextFrames(page);
}

/** The crossing with the most others in a `WINDOW` around it. */
function busiestPlace(crossings) {
  const near = (c) => crossings.filter((o) => Math.abs(o.x - c.x) < WINDOW.width / 2 && Math.abs(o.y - c.y) < WINDOW.height / 2).length;
  return crossings.map((c) => ({ c, n: near(c) })).sort((a, b) => b.n - a.n)[0].c;
}

/** The canvas's background colour, as `rgb(r,g,b)`. */
async function canvasBackground(page) {
  const colour = await page.getByTestId("graph-canvas").evaluate((element) => getComputedStyle(element).backgroundColor);
  return colour.replace(/\s+/g, "");
}

const channels = (colour) => (String(colour).match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number);

/** How far two colours lie apart: the largest difference of a channel. */
const colourDistance = (a, b) => Math.max(...channels(a).map((value, i) => Math.abs(value - channels(b)[i])));

/**
 * The colour of a gradient line `look` (`edgeLooks`) at `point`, drawn from
 * `start` to `end`: the stops' colours mixed at the point's projection on that
 * line, as a canvas mixes a linear gradient.
 */
function gradientColourAt(look, start, end, point) {
  const positions = look.stopPositions.map((value) => parseFloat(value) / 100);
  const [dx, dy] = [end.x - start.x, end.y - start.y];
  const t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy);
  const stops = look.stops.map(channels);
  let i = 1;
  while (i < stops.length - 1 && t > positions[i]) i += 1;
  const share = Math.max(0, Math.min(1, (t - positions[i - 1]) / (positions[i] - positions[i - 1])));
  return `rgb(${stops[i].map((value, k) => Math.round(stops[i - 1][k] + share * (value - stops[i - 1][k]))).join(",")})`;
}
/** How far a colour a bridge is drawn in may lie from the line's own there, per channel: rounding. */
const COLOUR_ROUNDING = 2;

/** Every crossing reported, flat: `[{ edge, x, y, crossed, colour, crossedColour, under }]`. */
const crossingsOf = (reported) => reported.flatMap(({ edge, crossings }) => crossings.map((crossing) => ({ edge, ...crossing })));

for (const graph of GRAPHS) {
  for (const colorScheme of ["light", "dark"]) {
    test.describe(`on ${graph.name}, in the ${colorScheme} theme`, { tag: graph.tag }, () => {
      test.use({ colorScheme });

      test("with a node's neighbourhood selected, every crossing of a highlighted edge carries a bridge in its colour, and nothing else does", async ({
        page,
        request,
      }) => {
        if (graph.slow) test.setTimeout(180_000);
        const data = await graph.data(request);
        const busiest = await busiestLeaf(page, data);
        await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
        await openEveryBox(page);
        expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(colorScheme === "dark");

        const keys = new Set(neighbourhood(data, busiest, 1, "both").edges);
        const { reported, highlighted, edges, missing, stray } = await bridgesAgainstWalk(page, keys);
        expect(highlighted.size).toBeGreaterThan(0);
        expect(edges).toEqual([]);
        expect(missing).toEqual([]);
        expect(stray).toEqual([]);
        const crossings = crossingsOf(reported);
        requireShape(crossings.length > 0, "no highlighted edge crosses another drawn edge");

        // Each line keeps its own colour at the crossing, and the hop is drawn over what lies under it.
        const background = await canvasBackground(page);
        const looks = new Map((await viewer(page, "edgeLooks")).map((look) => [look.key, look]));
        const routes = new Map((await drawnRoutes(page)).map((r) => [r.id, r]));
        const fills = new Map(
          (await viewer(page, "colours")).filter((c) => c.property === "background-color").map((c) => [c.element, c.value])
        );
        const boxes = Object.entries(await viewer(page, "nodeBoxes"));
        const fallback = crossings.filter((c) => [c.colour, c.crossedColour, c.under].includes(CYTOSCAPE_FALLBACK_COLOUR));
        expect(fallback).toEqual([]);
        const colourAt = (id, point) => {
          const route = routes.get(id);
          const look = looks.get(route.key);
          return look ? gradientColourAt(look, route.points[0], route.points[route.points.length - 1], point) : null;
        };
        const offTheLine = crossings.filter((c) => {
          const [own, crossed] = [colourAt(c.edge, c), colourAt(c.crossed, c)];
          return (own && colourDistance(c.colour, own) > COLOUR_ROUNDING) || (crossed && colourDistance(c.crossedColour, crossed) > COLOUR_ROUNDING);
        });
        expect(offTheLine).toEqual([]);
        // Under a crossing lies the background, tinted by every box around it: no
        // channel beyond the background's and those boxes' fills.
        const wrong = crossings.filter((c) => {
          const near = (b) => Math.min(Math.abs(c.x - b.x1), Math.abs(c.x - b.x2), Math.abs(c.y - b.y1), Math.abs(c.y - b.y2)) < BORDER;
          const around = boxes.filter(([, b]) => c.x > b.x1 && c.x < b.x2 && c.y > b.y1 && c.y < b.y2);
          if (around.some(([, b]) => near(b))) return false;
          if (!around.length) return c.under !== background;
          const tones = [background, ...around.map(([id]) => fills.get(id))];
          const lo = [0, 1, 2].map((i) => Math.min(...tones.map((t) => channels(t)[i])) - 1);
          const hi = [0, 1, 2].map((i) => Math.max(...tones.map((t) => channels(t)[i])) + 1);
          return c.under === background || channels(c.under).some((v, i) => v < lo[i] || v > hi[i]);
        });
        expect(wrong).toEqual([]);
      });
    });
  }

  test(`on ${graph.name}, with nothing highlighted no bridge is drawn, at the overview or at full detail`, { tag: graph.tag }, async ({ page, request }) => {
    if (graph.slow) test.setTimeout(180_000);
    const data = await graph.data(request);
    const busiest = await busiestLeaf(page, data);
    await openWith(page, data);
    expect(await viewer(page, "bridges")).toEqual([]);
    await openEveryBox(page);
    await nextFrames(page);
    expect(await viewer(page, "bridges")).toEqual([]);

    await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
    await openEveryBox(page);
    await expect.poll(async () => (await viewer(page, "bridges")).length).toBeGreaterThan(0);
    await page.getByTestId("graph-canvas").focus();
    await page.keyboard.press("Escape");
    await expect.poll(() => viewer(page, "selection")).toBeNull();
    await expect.poll(() => viewer(page, "bridges")).toEqual([]);
    await nextFrames(page);
    const { frames } = await viewer(page, "bridgeFrames");
    expect(frames[frames.length - 1].drawn).toBe(0);
  });

  test(`on ${graph.name}, drawing the bridges of a hub's neighbourhood costs a few milliseconds a frame`, { tag: graph.tag }, async ({ page, request }) => {
    if (graph.slow) test.setTimeout(180_000);
    const data = await graph.data(request);
    const busiest = await busiestLeaf(page, data);
    await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
    await openEveryBox(page);
    const crossings = crossingsOf(await viewer(page, "bridges"));
    requireShape(crossings.length > 0, "no highlighted edge crosses another drawn edge");
    await zoomToFullSizeAt(page, busiestPlace(crossings));
    const start = await page.evaluate(() => performance.now());
    const canvas = await page.getByTestId("graph-canvas").boundingBox();
    const centre = { x: canvas.x + canvas.width / 2, y: canvas.y + canvas.height / 2 };
    await page.mouse.move(centre.x, centre.y);
    await page.mouse.down();
    for (let step = 1; step <= PAN_FRAMES; step += 1) {
      const swing = Math.sin((step / PAN_FRAMES) * 2 * Math.PI);
      await page.mouse.move(centre.x + 200 * swing, centre.y + 120 * swing);
      await nextFrames(page);
    }
    await page.mouse.up();
    const { findMs, paintMs, frames } = await viewer(page, "bridgeFrames");
    const measured = frames.filter((frame) => frame.at >= start && frame.drawn > 0);
    expect(measured.length).toBeGreaterThan(PAN_FRAMES / 2);
    const mean = measured.reduce((sum, frame) => sum + frame.ms, 0) / measured.length;
    expect(mean).toBeLessThanOrEqual(FRAME_BUDGET_MS);
    expect(findMs + paintMs).toBeLessThanOrEqual(REFRESH_BUDGET_MS);
  });
}

/**
 * A point on the page, on an edge that crosses another drawn edge, with no other
 * edge and no leaf near enough to take the pointer; null when none is in view.
 */
async function hoverablePointWithCrossings(page, routes) {
  const siblings = bundleSiblings(await viewer(page, "bundles"));
  const zoom = await viewer(page, "zoom");
  const clearance = CLEARANCE_PX / zoom;
  const leaves = await page.evaluate(() => {
    const handle = window.__beadloomViewer;
    const boxes = handle.boxes();
    return Object.entries(handle.nodeBoxes()).filter(([id]) => !boxes[id]?.isParent).map(([, box]) => box);
  });
  const rect = await page.getByTestId("graph-canvas").boundingBox();
  const viewport = page.viewportSize();
  const { extent } = await viewer(page, "level");
  for (const route of routes) {
    if (!expectedBridges(routes, new Set([route.id]), siblings)[route.id].length) continue;
    for (let i = 1; i < route.points.length; i += 1) {
      const [a, b] = [route.points[i - 1], route.points[i]];
      const candidate = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      if (candidate.x < extent.x1 || candidate.x > extent.x2 || candidate.y < extent.y1 || candidate.y > extent.y2) continue;
      const crowded = routes.some((r) => r.id !== route.id && distanceToPolyline(candidate, r.points) < clearance);
      const onNode = leaves.some((n) => candidate.x > n.x1 - clearance && candidate.x < n.x2 + clearance && candidate.y > n.y1 - clearance && candidate.y < n.y2 + clearance);
      if (crowded || onNode) continue;
      const at = await onPage(page, candidate);
      const onScreen =
        at.x > rect.x + CLEARANCE_PX && at.x < Math.min(rect.x + rect.width, viewport.width) - CLEARANCE_PX &&
        at.y > rect.y + CLEARANCE_PX && at.y < Math.min(rect.y + rect.height, viewport.height) - CLEARANCE_PX;
      if (onScreen) return at;
    }
  }
  return null;
}

test("hovering an edge bridges it where it crosses others, and moving off it takes the bridges away", async ({ page, request }) => {
  const data = await architectureData(request);
  const busiest = await busiestLeaf(page, data);
  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
  await openEveryBox(page);
  const selected = crossingsOf(await viewer(page, "bridges"));
  requireShape(selected.length > 0, "no highlighted edge crosses another drawn edge");
  const busiestCrossing = busiestPlace(selected);
  // Hover with no selection, so the bridges are the hovered line's alone.
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("Escape");
  await expect.poll(() => viewer(page, "bridges")).toEqual([]);
  await zoomToFullSizeAt(page, busiestCrossing);
  const routes = await drawnRoutes(page);
  const point = await hoverablePointWithCrossings(page, routes);
  requireShape(Boolean(point), "no edge in view that crosses another has a point clear of other edges and nodes");
  await page.mouse.move(point.x, point.y);
  await expect.poll(async () => (await viewer(page, "hoveredEdges")).length).toBeGreaterThan(0);

  const hovered = new Set(await viewer(page, "hoveredEdges"));
  const lit = new Set(routes.filter((r) => hovered.has(r.id)).map((r) => r.id));
  const reported = await viewer(page, "bridges");
  const expected = expectedBridges(routes, lit, bundleSiblings(await viewer(page, "bundles")));
  requireShape(Object.values(expected).some((crossings) => crossings.length > 0), "the hovered line crosses no other drawn edge");
  const { edges, missing, stray } = compareBridges(reported, expected);
  expect(reported.map((entry) => entry.edge).sort()).toEqual([...lit].sort());
  expect(edges).toEqual([]);
  expect(missing).toEqual([]);
  expect(stray).toEqual([]);

  await page.mouse.move(2, 2);
  await expect.poll(() => viewer(page, "hoveredEdges")).toEqual([]);
  await expect.poll(() => viewer(page, "bridges")).toEqual([]);
});

test("no bridge joins two edges of one bundle, though bundled edges cross each other where they fan out", async ({ page, request }) => {
  const data = await architectureData(request);
  const busiest = await busiestLeaf(page, data);
  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
  await openEveryBox(page);
  const { routes, highlighted } = await walkedNow(page, new Set(neighbourhood(data, busiest, 1, "both").edges));
  const siblings = bundleSiblings(await viewer(page, "bundles"));
  const everyCrossing = crossingsOf(Object.entries(expectedBridges(routes, highlighted, null)).map(([edge, crossings]) => ({ edge, crossings })));
  const withinBundles = everyCrossing.filter((c) => siblings.get(c.edge)?.has(c.crossed));
  requireShape(withinBundles.length > 0, "no two edges of one bundle cross");

  const reported = crossingsOf(await viewer(page, "bridges"));
  expect(reported.length).toBeGreaterThan(0);
  expect(reported.filter((c) => siblings.get(c.edge)?.has(c.crossed))).toEqual([]);
  expect(reported.filter((c) => c.edge === c.crossed)).toEqual([]);
});

test("the bridges are found again after a level switch, a filter and a hidden neighbourhood", async ({ page, request }) => {
  const data = await architectureData(request);
  const busiest = await busiestLeaf(page, data);
  const keys = new Set(neighbourhood(data, busiest, 1, "both").edges);
  const agrees = async (when) => {
    const { reported, edges, missing, stray } = await bridgesAgainstWalk(page, keys);
    expect(edges, when).toEqual([]);
    expect(missing, when).toEqual([]);
    expect(stray, when).toEqual([]);
    return crossingsOf(reported);
  };

  // The overview: the hub's own boxes open, its edges to the rest aggregated.
  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
  const overview = await agrees("at the overview");
  requireShape(
    (await drawnRoutes(page)).some((r) => r.aggregated) && overview.length > 0,
    "no aggregated edge drawn, or no bridge, around the busiest node at the overview"
  );

  await openEveryBox(page);
  const full = await agrees("at full detail");
  // Each step must change the bridges, or it shows nothing about finding them again.
  requireShape(full.length !== overview.length, "the same bridges at the overview and at full detail");

  const kind = data.nodes.find((node) => node.id === busiest).kind;
  await page.getByLabel("Kind", { exact: true }).selectOption(kind);
  await expect.poll(async () => (await viewer(page, "visibleIds")).length).toBeLessThan(data.nodes.length);
  const filtered = await agrees(`with only kind ${kind} shown`);
  requireShape(filtered.length < full.length, `no bridge over an edge the kind filter ${kind} hides`);

  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}&hide=1`);
  await openEveryBox(page);
  const hidden = await agrees("with the rest hidden");
  requireShape(hidden.length < full.length, "no bridge over an edge outside the neighbourhood");
});

test("the bridges move with pan and zoom, and none is drawn where a hop would be too small to see", async ({ page, request }) => {
  const data = await architectureData(request);
  const busiest = await busiestLeaf(page, data);
  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
  await openEveryBox(page);
  await page.getByRole("button", { name: "Fit" }).click();
  await nextFrames(page);
  const all = crossingsOf(await viewer(page, "bridges"));
  requireShape(all.length > 0, "no highlighted edge crosses another drawn edge");
  const lastDrawn = async () => {
    await nextFrames(page);
    const { frames } = await viewer(page, "bridgeFrames");
    return frames[frames.length - 1].drawn;
  };
  expect(await lastDrawn()).toBe(0);

  // At full size every hop is HOP_PX or more; the ones in view are drawn, and no other.
  const inView = async () => {
    const zoom = await viewer(page, "zoom");
    const { extent } = await viewer(page, "level");
    const within = (grow) => all.filter((c) => c.x > extent.x1 - grow && c.x < extent.x2 + grow && c.y > extent.y1 - grow && c.y < extent.y2 + grow).length;
    return { inner: within(-HOP_PX / zoom), outer: within(WIDEST_HOP_PX / zoom), extent };
  };
  await zoomToFullSizeAt(page, busiestPlace(all));
  const here = await inView();
  requireShape(here.inner > 0, "no bridge in view at full size around the busiest node");
  let drawn = await lastDrawn();
  expect(drawn).toBeGreaterThanOrEqual(here.inner);
  expect(drawn).toBeLessThanOrEqual(here.outer);

  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  await drag(page, { x: canvas.x + canvas.width / 2, y: canvas.y + canvas.height / 2 }, -canvas.width / 3, -canvas.height / 3);
  await page.mouse.move(2, 2);
  const there = await inView();
  expect(there.extent).not.toEqual(here.extent);
  drawn = await lastDrawn();
  expect(drawn).toBeGreaterThanOrEqual(there.inner);
  expect(drawn).toBeLessThanOrEqual(there.outer);
});

/** The mean of a colour's channels: light under a light theme, dark under a dark one. */
const brightness = (colour) => channels(colour).reduce((sum, value) => sum + value, 0) / 3;
const MIDDLE = 128;

test("switching the theme repaints the bridges in the new theme's colours", async ({ page, request }) => {
  const data = await architectureData(request);
  const busiest = await busiestLeaf(page, data);
  await openWith(page, data, `?focus=${encodeURIComponent(busiest)}`);
  await openEveryBox(page);
  const place = (c) => `${c.edge}|${c.crossed}|${c.x.toFixed(1)},${c.y.toFixed(1)}`;
  const light = crossingsOf(await viewer(page, "bridges"));
  requireShape(light.length > 0, "no highlighted edge crosses another drawn edge");
  expect(light.filter((c) => brightness(c.under) < MIDDLE)).toEqual([]);

  await page.getByRole("switch", { name: /dark theme/i }).first().click();
  await page.waitForFunction(() => document.documentElement.classList.contains("dark"));
  await expect.poll(async () => crossingsOf(await viewer(page, "bridges")).filter((c) => brightness(c.under) >= MIDDLE).length).toBe(0);
  const dark = crossingsOf(await viewer(page, "bridges"));
  expect(dark.map(place)).toEqual(light.map(place));
  expect(dark.filter((c) => [c.colour, c.crossedColour, c.under].includes(CYTOSCAPE_FALLBACK_COLOUR))).toEqual([]);
  const unchanged = dark.filter((c, i) => c.under === light[i].under || c.crossedColour === light[i].crossedColour);
  expect(unchanged).toEqual([]);
});
