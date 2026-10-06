// Edges are drawn along the routes ELK computed, around every box, and boxes at ELK's size.
//
// A node's fans are then bundled from those routes (`bundles.spec.js`), so an
// edge is drawn along its route as the viewer computed it from ELK's.
//
// In an earlier version the viewer placed the nodes where ELK put them and threw
// ELK's routes away: Cytoscape drew each edge as a curve from centre to centre,
// so on a graph of 130 nodes 232 of 453 edges passed through a box they did not
// connect and 22 were more than half shared with another. A compound box was
// sized by Cytoscape around its children, smaller than ELK's, and when a filter
// hid every child it shrank to a node's size where it stood. And the canvas's
// shape was part of what ELK was given, so a node page, whose canvas is shorter,
// had the same graph laid out again.
//
// The cases on the architecture graph read it at full detail, every box open: at
// the whole-graph fit the viewer draws a map of closed boxes (`map.spec.js`). The
// theme case reads the map as drawn at the fit.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { landscapeData, openLandscape } from "./support/landscape.js";
import {
  deviation,
  distanceToPolyline,
  edgesThroughBoxes,
  polylineOf,
  sharing,
} from "./support/routeMetrics.js";
import {
  architectureData,
  openArchitecture,
  openEveryBox,
  parentMap,
  viewer,
  viewerAfter,
  withAncestors,
} from "./support/viewer.js";
import { LACKING, requireShape } from "./support/shape.js";

/** How far a drawn route, a box side or a label may lie from ELK's, in layout units. */
const ROUTE_TOLERANCE = 0.5;
/** The most of its middle an edge may share, on average, with edges it has no common end with. */
const MEAN_SHARED = 0.03;

/** What a case about routes needs: an edge between two nodes, neither of which holds the other. */
const BETWEEN_TWO_BOXES = "no drawn edge between two nodes neither of which holds the other";

/** The architecture page's path, under any base. */
const ARCHITECTURE_PAGE = /\/architecture\.html$/;
const pathOf = (page) => new URL(page.url()).pathname;

/** Whether `id` is `other` or one of its containers. */
function holds(id, other, parents) {
  for (let cursor = other; cursor; cursor = parents[cursor]) if (cursor === id) return true;
  return false;
}

/** The drawn edges that are loops: from a node to itself or to a box that holds it. */
const loopsOf = (routes, parents) =>
  routes
    .filter((r) => holds(r.source, r.target, parents) || holds(r.target, r.source, parents))
    .map((r) => r.id)
    .sort();

/** How far two drawings may place one node apart, in layout units: the rounding of a sum, a millionth of a pixel at zoom 1. */
const CENTRE_ROUNDING = 1e-6;

/** The ids of the boxes in `ids` whose drawn sides lie further than the tolerance from ELK's. */
function misdrawnBoxes(ids, drawn, elk) {
  return ids.filter((id) =>
    ["x1", "y1", "x2", "y2"].some((side) => Math.abs(drawn[id][side] - elk[id][side]) > ROUTE_TOLERANCE)
  );
}

/** The pages a graph is drawn on, each with how to open it and the containment it draws. */
const DRAWINGS = [
  {
    name: "this portal's architecture graph",
    tag: [],
    open: async (page, request) => {
      const data = await architectureData(request);
      await openArchitecture(page);
      await openEveryBox(page);
      return parentMap(data);
    },
  },
  {
    name: "an adopter-sized architecture graph",
    tag: [ADOPTER_SIZED],
    open: async (page, request) => {
      const data = adopterSizedGraph(await architectureData(request));
      await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      await openEveryBox(page);
      return parentMap(data);
    },
  },
  {
    name: "the landscape",
    tag: [],
    open: async (page, request) => {
      const data = await landscapeData(request);
      requireShape(data.edges.length > 0, LACKING.landscape);
      await openLandscape(page);
      return {};
    },
  },
];

for (const drawing of DRAWINGS) {
  test.describe(`on ${drawing.name}`, { tag: drawing.tag }, () => {
    // The route is ELK's with a node's fans bundled (`bundles.spec.js` checks
    // the bundling against ELK's routes); this case checks it is drawn as computed.
    // A loop, from a node into a box that holds it, is drawn along ELK's route too: Cytoscape once drew it
    // as a curve straight across the box (`levels.spec.js`), and it keeps ELK's route, unbundled.
    test("every edge is drawn along its route with its label on it, an edge into its own box along ELK's", async ({
      page,
      request,
    }) => {
      const parents = await drawing.open(page, request);
      const { routes: computed } = await viewer(page, "bundles");
      const { routes: elk } = (await viewer(page, "elkGeometry")) || { routes: {} };
      // The edges of the file: a line of the map's is routed by the map (`map.spec.js`, `overview.spec.js`).
      const drawn = (await viewer(page, "edgeRoutes")).filter((r) => !r.aggregated);
      requireShape(drawn.some((r) => !r.loop), BETWEEN_TWO_BOXES);

      const loops = loopsOf(drawn, parents);
      expect(drawn.filter((r) => r.loop).map((r) => r.id).sort()).toEqual(loops);
      expect(drawn.filter((r) => !r.routed).map((r) => r.id).sort()).toEqual([]);
      const routed = drawn.filter((r) => r.routed);
      const offRoute = routed
        .map((r) => ({ id: r.id, by: deviation(r.points, r.loop ? polylineOf(elk[r.id].sections) : computed[r.id]) }))
        .filter((r) => r.by > ROUTE_TOLERANCE);
      expect(offRoute).toEqual([]);
      const labelsOff = routed.filter((r) => distanceToPolyline(r.label, r.points) > ROUTE_TOLERANCE);
      expect(labelsOff.map((r) => r.id)).toEqual([]);
    });

    test("no routed edge passes through a box it does not connect, and none is more than half shared", async ({
      page,
      request,
    }) => {
      const parents = await drawing.open(page, request);
      const { boxes } = await viewer(page, "elkGeometry");
      // Every edge but a loop, which Cytoscape draws inside the box it leaves.
      const between = (await viewer(page, "edgeRoutes")).filter((r) => !r.loop);
      requireShape(between.length > 0, BETWEEN_TWO_BOXES);

      expect(edgesThroughBoxes(between, boxes, parents)).toEqual([]);
      expect(sharing(between).indistinct).toEqual([]);
    });

    // Edges that leave or reach one node share their trunk by design; an edge
    // counts as shared only beside an edge with no common end (`routeMetrics.js`).
    test("on average an edge shares at most 3% of its middle with edges it has no common end with", async ({
      page,
      request,
    }) => {
      await drawing.open(page, request);
      const between = (await viewer(page, "edgeRoutes")).filter((r) => !r.loop);
      requireShape(between.length > 0, BETWEEN_TWO_BOXES);

      expect(sharing(between).meanShared).toBeLessThanOrEqual(MEAN_SHARED);
    });
  });
}

test("every box is drawn as ELK sized it, also when a filter hides every child of a box it shows", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const parents = parentMap(data);
  const holders = new Set(Object.values(parents).filter(Boolean));
  // A kind that keeps a box on the canvas and hides all of its children: the box
  // then holds nothing Cytoscape could size it by.
  const emptiedBoxes = (kind) => {
    const shown = withAncestors(data.nodes.filter((n) => n.kind === kind).map((n) => n.id), parents);
    return [...holders].filter((box) => shown.has(box) && !data.nodes.some((n) => parents[n.id] === box && shown.has(n.id)));
  };
  const kinds = [...new Set(data.nodes.map((n) => n.kind))].sort();
  const kind = kinds.sort((a, b) => emptiedBoxes(b).length - emptiedBoxes(a).length)[0];
  requireShape(holders.size > 0 && emptiedBoxes(kind).length > 0, "no kind filter shows a box without any of its children");

  await openArchitecture(page);
  await openEveryBox(page);
  const { boxes: elk } = await viewer(page, "elkGeometry");
  expect(misdrawnBoxes(Object.keys(elk), await viewer(page, "nodeBoxes"), elk)).toEqual([]);

  await page.getByLabel("Kind", { exact: true }).selectOption(kind);
  await expect.poll(async () => (await viewer(page, "visibleIds")).length).toBeLessThan(data.nodes.length);
  const shown = await viewer(page, "visibleIds");
  expect(misdrawnBoxes(shown, await viewer(page, "nodeBoxes"), elk)).toEqual([]);
});

test("the routes stay when the theme changes", async ({ page }) => {
  await openArchitecture(page);
  const light = await viewer(page, "edgeRoutes");
  const colours = await viewer(page, "colours");
  requireShape(light.some((r) => !r.loop), BETWEEN_TWO_BOXES);

  await page.getByRole("switch", { name: /dark theme/i }).first().click();
  await page.waitForFunction(() => document.documentElement.classList.contains("dark"));
  await expect.poll(async () => JSON.stringify(await viewer(page, "colours"))).not.toBe(JSON.stringify(colours));

  const dark = await viewer(page, "edgeRoutes");
  expect(dark.filter((r) => !r.loop && !r.routed).map((r) => r.id)).toEqual([]);
  expect(dark).toEqual(light);
});

test("the page, full screen and a node page share one layout, whatever the canvas's shape", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const node = data.nodes.find((n) => n.url);
  requireShape(Boolean(node), "no node has a page of its own");
  await openArchitecture(page, `?focus=${encodeURIComponent(node.id)}`);
  expect((await viewer(page, "layoutRun")).source).toBe("worker");
  const geometry = await viewer(page, "elkGeometry");
  const positions = await viewer(page, "positions");

  // Full screen gives the canvas the screen's shape; the node page opened from it
  // draws the graph on a canvas shorter than the architecture page's.
  await page.getByRole("button", { name: /full screen/i }).click();
  await viewerAfter(page, () => page.getByRole("link", { name: "Open the node's page →" }).click());
  expect(pathOf(page)).not.toMatch(ARCHITECTURE_PAGE);

  expect((await viewer(page, "layoutRun")).source).toBe("cache");
  expect(await viewer(page, "elkGeometry")).toEqual(geometry);
  // The same places, but for the last bits of a box's centre where the box is drawn larger around a
  // node the overview draws larger than its layout: each canvas's shape gives the overview its own
  // scale, and Cytoscape centres the larger box by another sum.
  const now = await viewer(page, "positions");
  expect(Object.keys(now).sort()).toEqual(Object.keys(positions).sort());
  const apart = Object.keys(positions).filter((id) => Math.abs(now[id].x - positions[id].x) > CENTRE_ROUNDING || Math.abs(now[id].y - positions[id].y) > CENTRE_ROUNDING);
  expect(apart).toEqual([]);
});
