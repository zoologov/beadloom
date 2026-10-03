// The layout: ELK runs in a Web Worker, its geometry is in the graph's coordinates, and it is reused.
//
// In an earlier version ELK ran on the page's main thread through `cytoscape-elk`,
// which used a nested elkjs of its own and handed the canvas node positions only.
// Laying out an adopter-sized graph held the page for over two seconds, during which
// no control of the toolbar answered, and ELK's edge routes were thrown away.

import { test, expect } from "@playwright/test";
import { adopterSizedGraph } from "./support/adopterGraph.js";
import {
  architectureData,
  openArchitecture,
  viewer,
  viewerAfter,
  waitForViewer,
} from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

/** How far a drawn position may lie from ELK's, in layout units. */
const POSITION_TOLERANCE = 0.5;
/** How far a route's end may lie outside the box of the node it ends on, in layout units. */
const END_TOLERANCE = 1;
/** How often the main thread is sampled while the graph is laid out. */
const PROBE_INTERVAL_MS = 10;
/**
 * The longest the main thread may be held at a time while the graph is laid out. ELK
 * takes 2 to 3 seconds over this graph, and on the main thread it held the page that
 * long in one task; in the worker the longest hold measured 120 to 450 ms.
 */
const LONGEST_HOLD_MS = 1000;

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

test("the toolbar answers while an adopter-sized graph is laid out", async ({ page, request }) => {
  const data = adopterSizedGraph(await architectureData(request));
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await page.goto("architecture.html");

  const status = page.getByTestId("layout-status");
  await expect(status).toBeVisible({ timeout: 45_000 });
  // How long the page's main thread was held at a time, sampled until the layout is placed.
  await page.evaluate((every) => {
    window.__layoutGaps = [];
    let last = performance.now();
    const probe = setInterval(() => {
      const now = performance.now();
      window.__layoutGaps.push(now - last);
      last = now;
      if (!document.querySelector("[data-testid='layout-status']")) clearInterval(probe);
    }, every);
  }, PROBE_INTERVAL_MS);
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
  expect(await viewer(page, "visibleIds")).toHaveLength(data.nodes.length);
  const gaps = await page.evaluate(() => window.__layoutGaps);
  expect(gaps.length).toBeGreaterThan(0);
  expect(Math.max(...gaps)).toBeLessThan(LONGEST_HOLD_MS);
});

test("a layout that cannot run is reported rather than left laying out", async ({ page }) => {
  await page.route("**/elk.worker*.js", (route) => route.abort());
  await page.goto("architecture.html");

  await expect(page.getByRole("alert")).toContainText("could not be laid out", { timeout: 45_000 });
  await expect(page.getByTestId("layout-status")).toBeHidden();
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
