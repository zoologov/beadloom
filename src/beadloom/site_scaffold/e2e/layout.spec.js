// The layout: ELK runs in a Web Worker, its geometry is in the graph's coordinates, and it is reused.
//
// In an earlier version ELK ran on the page's main thread through `cytoscape-elk`,
// which used a nested elkjs of its own and handed the canvas node positions only.
// Laying out an adopter-sized graph held the page for over two seconds, during which
// no control of the toolbar answered, and ELK's edge routes were thrown away.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import {
  architectureData,
  openArchitecture,
  openEveryBox,
  viewer,
  viewerAfter,
  waitForViewer,
} from "./support/viewer.js";
import { requireShape } from "./support/shape.js";
import { ENVIRONMENT, boundHere } from "./support/environment.js";

/** How far a drawn position may lie from ELK's, in layout units. */
const POSITION_TOLERANCE = 0.5;
/** How far a route's end may lie outside the box of the node it ends on, in layout units. */
const END_TOLERANCE = 1;
/**
 * The longest one task may hold the page's main thread while the graph is laid
 * out, per environment (`support/environment.js`). ELK takes 2 to 3 s over the
 * adopter-sized graph on an Apple M1 Max, and on the main thread it held the page
 * that long in one task; it runs in a worker now, and what is left is the
 * viewer's own work before and after it.
 *
 * On a GitHub-hosted Ubuntu runner the longest task took 2,427 ms on the
 * adopter-sized graph built from a portal that declares no layers, in one task
 * that drew the layout, measured the whole graph's fit and planned the overview.
 * The same viewer took 608 to 615 ms in that task on an Apple M-series machine
 * (headless Chromium, no GPU, the case alone) and 2,478 to 2,495 ms with the
 * page's processor slowed four times: the runner runs this work about four times
 * slower. The build server's bound stays 2,000 ms; the local one is that bound
 * over the runner's factor, 500 ms, so a task the runner would hold too long is
 * seen on the machine the change is made on.
 */
const LONGEST_TASK_MS = { local: 500, ci: 2000 };

/** The architecture page's path, under any base. */
const ARCHITECTURE_PAGE = /\/architecture\.html$/;

const pathOf = (page) => new URL(page.url()).pathname;
const centreOf = (box) => ({ x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 });
const within = (point, box, slack) =>
  point.x >= box.x1 - slack &&
  point.x <= box.x2 + slack &&
  point.y >= box.y1 - slack &&
  point.y <= box.y2 + slack;

test("each node is drawn where ELK placed it, and every box and route is in the graph's coordinates", async ({
  page,
}) => {
  await openArchitecture(page);
  await openEveryBox(page);
  const { boxes, routes } = await viewer(page, "elkGeometry");
  const drawn = await viewer(page, "boxes");
  const positions = await viewer(page, "positions");
  expect(Object.keys(boxes).sort()).toEqual(Object.keys(positions).sort());

  const misplaced = Object.keys(positions)
    .filter((id) => !drawn[id].isParent)
    .filter((id) => {
      const centre = centreOf(boxes[id]);
      return (
        Math.abs(positions[id].x - centre.x) > POSITION_TOLERANCE ||
        Math.abs(positions[id].y - centre.y) > POSITION_TOLERANCE
      );
    });
  expect(misplaced).toEqual([]);

  // A child's box lies inside its container's: both are in the graph's coordinates, not the parent's.
  const outsideContainer = Object.entries(drawn)
    .filter(([, box]) => box.parent)
    .filter(([id, box]) => {
      const { x1, y1, x2, y2 } = boxes[id];
      const container = boxes[box.parent];
      return !within({ x: x1, y: y1 }, container, END_TOLERANCE) || !within({ x: x2, y: y2 }, container, END_TOLERANCE);
    })
    .map(([id]) => id);
  expect(outsideContainer).toEqual([]);

  const edgeCount = (await viewer(page, "edgeLooks")).length;
  requireShape(edgeCount > 0, "no drawn edge between two nodes of the graph");
  expect(Object.keys(routes)).toHaveLength(edgeCount);
  const detached = Object.entries(routes)
    .filter(([, route]) => {
      const points = route.sections.flat();
      return (
        route.sections.length === 0 ||
        !within(points[0], boxes[route.source], END_TOLERANCE) ||
        !within(points[points.length - 1], boxes[route.target], END_TOLERANCE)
      );
    })
    .map(([id]) => id);
  expect(detached).toEqual([]);
});

test("a graph drawn again is not laid out again", async ({ page, request }) => {
  const data = await architectureData(request);
  const node = data.nodes.find((n) => n.url);
  requireShape(Boolean(node), "no node has a page of its own");
  await openArchitecture(page, `?focus=${encodeURIComponent(node.id)}`);
  const first = await viewer(page, "layoutRun");
  const positions = await viewer(page, "positions");
  expect(first.source).toBe("worker");

  // To the node's page and back, inside the single-page app: the module that holds the layouts stays.
  // Each step waits for the next page's own viewer: one read before the node page is
  // drawn reads the architecture page's, and the node page's can then answer for the
  // way back, on a canvas of another shape.
  await viewerAfter(page, () => page.getByRole("link", { name: "Open the node's page →" }).click());
  expect(pathOf(page)).not.toMatch(ARCHITECTURE_PAGE);
  await viewerAfter(page, () => page.goBack());
  expect(pathOf(page)).toMatch(ARCHITECTURE_PAGE);

  expect((await viewer(page, "layoutRun")).source).toBe("cache");
  expect(await viewer(page, "positions")).toEqual(positions);
});

/** A font family whose glyphs are as wide as each other, unlike the portal's own. */
const OTHER_FONT = '"Courier New", Courier, monospace';

/**
 * Draw every later page of `page` in `OTHER_FONT`: the portal's web fonts are not
 * served, and the theme's font variable names the other family. A build server
 * renders text with fonts of its own, and this is the same difference made on
 * purpose.
 */
async function drawInAnotherFont(page) {
  await page.route(/\.woff2?(\?.*)?$/, (route) => route.abort());
  await page.addInitScript((family) => {
    const style = document.createElement("style");
    style.textContent = `:root { --vp-font-family-base: ${family} !important; }`;
    document.addEventListener("DOMContentLoaded", () => document.head.appendChild(style));
  }, OTHER_FONT);
}

/**
 * The layout of the graph drawn now, at full detail, and how wide the page's font
 * sets text: `{ source, geometry, positions, routes, labels }`, `source` where
 * the layout came from and `labels` the width of every node's id set in the font
 * the page draws text in, as the browser renders it.
 */
async function layoutAndLabels(page) {
  await openArchitecture(page);
  await openEveryBox(page);
  const labels = await page.evaluate((ids) => {
    const context = document.createElement("canvas").getContext("2d");
    context.font = `600 12px ${getComputedStyle(document.body).fontFamily}`;
    return ids.map((id) => context.measureText(id).width);
  }, Object.keys(await viewer(page, "positions")));
  const routes = Object.fromEntries((await viewer(page, "edgeRoutes")).map((r) => [r.id, r.points]));
  const { source } = await viewer(page, "layoutRun");
  return { source, geometry: await viewer(page, "elkGeometry"), positions: await viewer(page, "positions"), routes, labels };
}

test("the layout does not depend on the fonts text is rendered in: in another font every box, position and route is the same", async ({
  page,
}) => {
  const ours = await layoutAndLabels(page);
  await drawInAnotherFont(page);
  const other = await layoutAndLabels(page);
  // Both were laid out, and the other font sets text at other widths, or the comparison shows nothing.
  expect([ours.source, other.source]).toEqual(["worker", "worker"]);
  expect(other.labels).not.toEqual(ours.labels);

  const differing = (a, b) => Object.keys({ ...a, ...b }).filter((id) => JSON.stringify(a[id]) !== JSON.stringify(b[id]));
  expect(differing(other.geometry.boxes, ours.geometry.boxes)).toEqual([]);
  expect(differing(other.geometry.routes, ours.geometry.routes)).toEqual([]);
  expect(differing(other.positions, ours.positions)).toEqual([]);
  expect(differing(other.routes, ours.routes)).toEqual([]);
});

/**
 * Record, from the page's first script on, every task that holds the main thread
 * over 50 ms (the Long Tasks API reports no shorter one) and when the layout's
 * status is removed. Installed before the page loads, it cannot miss a task that
 * starts before a case could look.
 */
function recordLayoutTasks() {
  const probe = { tasks: [], hidden: null };
  window.__layoutProbe = probe;
  probe.observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) probe.tasks.push({ start: entry.startTime, end: entry.startTime + entry.duration });
  });
  probe.observer.observe({ type: "longtask", buffered: true });
  let shown = false;
  new MutationObserver(() => {
    const present = Boolean(document.querySelector("[data-testid='layout-status']"));
    if (present) shown = true;
    else if (shown && probe.hidden === null) probe.hidden = performance.now();
  }).observe(document, { childList: true, subtree: true });
}

/**
 * The tasks over 50 ms that ran, any part of them, from the moment the data file
 * arrived until the layout's status was removed, and that window. The window
 * opens at the data file rather than at the status, because the task that starts
 * the layout ends as the status is shown, and a hold in it would fall outside.
 */
function layoutTasks(page) {
  return page.evaluate(() => {
    const probe = window.__layoutProbe;
    for (const entry of probe.observer.takeRecords()) probe.tasks.push({ start: entry.startTime, end: entry.startTime + entry.duration });
    const data = performance.getEntriesByType("resource").find((entry) => new URL(entry.name).pathname.endsWith("/architecture.data.json"));
    const opened = data ? data.responseEnd : null;
    const during = probe.tasks.filter((task) => task.end >= opened && task.start <= probe.hidden);
    return { opened, hidden: probe.hidden, durations: during.map((task) => task.end - task.start) };
  });
}

test("the toolbar answers while an adopter-sized graph is laid out", { tag: ADOPTER_SIZED }, async ({ page, request }) => {
  const data = adopterSizedGraph(await architectureData(request));
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await page.addInitScript(recordLayoutTasks);
  await page.goto("architecture.html");

  const status = page.getByTestId("layout-status");
  await expect(status).toBeVisible({ timeout: 45_000 });
  const panel = page.getByRole("button", { name: "Panel", exact: true });
  const before = await panel.getAttribute("aria-expanded");
  // The button's answer is recorded with whether the layout was still running when it came.
  await panel.evaluate((button) => {
    new MutationObserver(() => {
      window.__answeredWhileLayingOut = Boolean(document.querySelector("[data-testid='layout-status']"));
    }).observe(button, { attributes: true, attributeFilter: ["aria-expanded"] });
  });
  await panel.click();

  await expect.poll(() => page.evaluate(() => window.__answeredWhileLayingOut)).toBe(true);
  expect(await panel.getAttribute("aria-expanded")).not.toBe(before);
  await waitForViewer(page);
  await expect(status).toBeHidden();

  // Every task that held the main thread from the data file's arrival until the graph was placed.
  const { opened, hidden, durations } = await layoutTasks(page);
  expect(opened, "the data file's arrival was timed").not.toBeNull();
  expect(hidden, "the layout's status was removed").not.toBeNull();
  const longest = Math.max(0, ...durations);
  const bound = boundHere(LONGEST_TASK_MS);
  test.info().annotations.push({
    type: "measured",
    description: `${ENVIRONMENT}: longest main-thread task while laying out ${longest.toFixed(0)} ms (bound ${bound} ms) over ${(hidden - opened).toFixed(0)} ms, ${durations.length} tasks over 50 ms`,
  });
  expect(longest).toBeLessThan(bound);

  await openEveryBox(page);
  expect(await viewer(page, "visibleIds")).toHaveLength(data.nodes.length);
});

test("a layout that cannot run is reported, nothing unplaced is drawn, and the controls that act on the graph are off", async ({
  page,
}) => {
  await page.route("**/elk.worker*.js", (route) => route.abort());
  await page.goto("architecture.html");

  const alert = page.getByRole("alert");
  await expect(alert).toContainText("could not be laid out", { timeout: 45_000 });
  // The alert says what failed: the layout's worker, which could not be loaded.
  await expect(alert).toContainText("the layout worker stopped: it could not be loaded");
  await expect(page.getByTestId("layout-status")).toBeHidden();
  // No node was placed, so the canvas is not shown: every node would stand at one point.
  await expect(page.getByTestId("graph-canvas")).toBeHidden();
  // Nothing to zoom, filter or walk; the panel and full screen act on the viewer, not the graph.
  const live = await page
    .getByRole("toolbar", { name: "Graph viewer tools" })
    .locator("button, select, input")
    .evaluateAll((controls) => controls.filter((c) => !c.matches(":disabled")).map((c) => c.getAttribute("aria-label") || c.textContent.trim()));
  expect(live.sort()).toEqual(["Full screen", "Panel"]);
});

/**
 * A graph whose node ids are the ids the viewer gives things of its own: `root`,
 * the name ELK's root graph had, and `e0:a->b`, the id Cytoscape's edge from `a`
 * to `b` had as the file's first edge, in the one id space Cytoscape keeps for
 * nodes and edges. Each colliding node is a box or a leaf with routed edges.
 */
function graphNamedLikeTheViewersIds(served) {
  const node = (id, parent) => ({
    id,
    label: id,
    kind: parent ? "component" : "domain",
    parent: parent || id,
    findings: [],
    doc_status: "fresh",
    lint_clean: true,
  });
  const nodes = [
    node("root"),
    node("a", "root"),
    node("b", "root"),
    node("other"),
    node("e0:a->b", "other"),
    node("c", "other"),
  ];
  const drawn = [
    ["a", "b"],
    ["e0:a->b", "a"],
    ["c", "root"],
    ["e0:a->b", "c"],
    ["b", "e0:a->b"],
  ].map(([src, dst]) => ({ src, dst, kind: "depends_on" }));
  const containment = nodes.map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" }));
  return { ...served, nodes, edges: [...drawn, ...containment] };
}

test("a node named like an id the viewer gives its own things gets its box and its routes", async ({
  page,
  request,
}) => {
  const data = graphNamedLikeTheViewersIds(await architectureData(request));
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  await openEveryBox(page);
  const ids = data.nodes.map((n) => n.id).sort();
  const drawnEdges = data.edges.filter((e) => e.kind !== "part_of");

  const { boxes, routes } = await viewer(page, "elkGeometry");
  expect(Object.keys(boxes).sort()).toEqual(ids);
  expect(Object.keys(await viewer(page, "positions")).sort()).toEqual(ids);
  expect((await viewer(page, "edgeLooks")).map((e) => e.key)).toEqual(
    drawnEdges.map((e) => `${e.kind}:${e.src}->${e.dst}`).sort()
  );

  expect(Object.keys(routes)).toHaveLength(drawnEdges.length);
  const detached = Object.entries(routes)
    .filter(([, route]) => {
      const points = route.sections.flat();
      return (
        points.length === 0 ||
        !boxes[route.source] ||
        !boxes[route.target] ||
        !within(points[0], boxes[route.source], END_TOLERANCE) ||
        !within(points[points.length - 1], boxes[route.target], END_TOLERANCE)
      );
    })
    .map(([, route]) => `${route.source}->${route.target}`);
  expect(detached).toEqual([]);
  const drawn = await viewer(page, "edgeRoutes");
  expect(drawn.filter((r) => !r.loop && !r.routed).map((r) => `${r.source}->${r.target}`)).toEqual([]);
});
