// The overview reads like a map: top-level boxes and one aggregated edge per pair, more as the reader zooms in.
//
// In an earlier version the whole-graph view drew every node and every edge at
// once: on a graph of 130 nodes, 453 edges at a scale where none could be told
// apart, and on an adopter-sized graph a frame took over 160 ms without a GPU.
// The overview now draws the boxes at the top, and each edge with an end inside a
// closed box is carried by one aggregated edge per pair of drawn ends, its count
// split by direction. A box opens where the reader zooms in, and a selection opens
// the boxes it needs. Every level is a view of the one layout: no box moves.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { landscapeData, openLandscape } from "./support/landscape.js";
import { edgesThroughBoxes } from "./support/routeMetrics.js";
import {
  AGGREGATE_BUDGET,
  budgetLeftOut,
  degreesOf,
  drawnEdgesOf,
  levelOf,
  treeOf,
} from "./support/map.js";
import { neighbourhood, impact } from "./support/graph.js";
import { architectureData, openArchitecture, viewer, withAncestors } from "./support/viewer.js";
import { drag } from "./support/pointer.js";
import { LACKING, requireShape } from "./support/shape.js";
import { openThemeModules } from "./support/themeModules.js";

/** A box opens at this larger side on screen, in pixels, and closes below 0.8 of it. */
const OPEN_SIDE_PX = 600;
const CLOSE_SIDE_PX = 0.8 * OPEN_SIDE_PX;
/** ... and only once the view is zoomed in this far past the whole-graph fit. */
const FIT_FLOOR = 1.3;
/** How far a drawn box may lie from where it is drawn at full detail, in layout units. */
const DISPLACEMENT = 1e-6;
/** How far a point of an aggregated route may lie from a member's route, in layout units. */
const TOLERANCE = 0.5;
/** A node with this many drawn edges is a hub: selected alone, it opens only its own boxes. */
const HUB_DEGREE = 20;
/** The screen size a map mark keeps, in pixels, within one zoom step of the restyle. */
const STEP = 1.25;
/** A count's size on its pill, in pixels: drawn over the canvas, it is that size at every zoom. */
const COUNT_PILL_PX = 10.5;
/** The one weight every line is drawn at, in pixels on screen (`look.spec.js`). */
const LINE_PX = 1.35;
/** The sizes a closed box's title is tried at, in pixels on screen. */
const BOX_TITLE_PX = [14, 12.5, 11, 10];
/** The most zoom steps a case takes before it gives up. */
const ZOOM_STEPS = 30;
/** How far inside the canvas's edges a point the pointer aims at lies, in pixels. */
const MARGIN_PX = 20;

const sorted = (ids) => [...ids].sort();

/** The graphs a level is read on: this portal's and an adopter-sized one. */
const GRAPHS = [
  {
    name: "this portal's architecture graph",
    tag: [],
    open: async (page, request, query = "") => {
      const data = await architectureData(request);
      await openArchitecture(page, query);
      return data;
    },
  },
  {
    name: "an adopter-sized architecture graph",
    tag: [ADOPTER_SIZED],
    open: async (page, request, query = "") => {
      const data = adopterSizedGraph(await architectureData(request));
      await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page, query);
      return data;
    },
  },
];

/** Every node id in the file, which `revealNodes` turns into full detail. */
const everyNode = (data) => data.nodes.map((n) => n.id);

/** Draw the nodes in `ids` as themselves, opening every box that holds one (the handle's one action). */
function reveal(page, ids) {
  return page.evaluate((list) => window.__beadloomViewer.revealNodes(list), ids);
}

/** The aggregated edges the viewer holds, by the name of their pair, "a|b". */
async function aggregatedByPair(page) {
  return Object.fromEntries((await viewer(page, "aggregatedEdges")).map((e) => [e.ends.join("|"), e]));
}

/** The keys an aggregated edge of the viewer carries each way: `{ forward, backward }`, sorted. */
const carried = (edge) => ({ forward: sorted(edge.forwardKeys), backward: sorted(edge.backwardKeys) });

for (const graph of GRAPHS) {
  test.describe(`on ${graph.name}`, { tag: graph.tag }, () => {
    test("at the whole-graph fit only the top-level boxes are drawn, and one aggregated edge per pair carries every edge between them", async ({
      page,
      request,
    }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      requireShape(tree.topBoxes.length > 1, "fewer than two boxes at the top of the containment tree");
      const expected = levelOf(tree, new Set(), drawnEdgesOf(data));

      expect(await viewer(page, "openBoxes")).toEqual(tree.wrapper ? [tree.wrapper] : []);
      expect(await viewer(page, "visibleIds")).toEqual(sorted(expected.nodes));
      const looks = await viewer(page, "edgeLooks");
      expect(looks.map((look) => look.key)).toEqual(expected.originals);
      const drawn = await aggregatedByPair(page);
      expect(sorted(Object.keys(drawn))).toEqual(sorted(expected.pairs.keys()));
      const wrong = [...expected.pairs].filter(
        ([name, pair]) => JSON.stringify(carried(drawn[name])) !== JSON.stringify({ forward: pair.forward, backward: pair.backward })
      );
      expect(wrong.map(([name]) => name)).toEqual([]);
    });

    test("at the whole-graph fit at most 100 edges are drawn, every one between two nodes at the top", async ({
      page,
      request,
    }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      requireShape(tree.topBoxes.length > 1, "fewer than two boxes at the top of the containment tree");

      const drawn = await viewer(page, "edgeRoutes");
      // The nodes at the top: under the one root that holds everything, or the roots when none does.
      const top = new Set(Object.keys(tree.parents).filter((id) => id !== tree.wrapper && tree.parents[id] === tree.wrapper));
      expect(drawn.length).toBeGreaterThan(0);
      expect(drawn.length).toBeLessThanOrEqual(AGGREGATE_BUDGET);
      expect(drawn.filter((r) => !top.has(r.source) || !top.has(r.target)).map((r) => r.id)).toEqual([]);
    });

    test("an aggregated edge has an arrowhead at each end its edges arrive at, its counts in its label, and a square route from the border of one of its boxes to the other's through no other box", async ({
      page,
      request,
    }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      const edges = (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn);
      requireShape(edges.length > 0, "no edge between two boxes at the top of the containment tree");
      const { boxes } = await viewer(page, "elkGeometry");

      // An end its edges arrive at draws a head, unless it shares its last run with a line that draws it.
      const dropped = new Set((await viewer(page, "droppedHeads")).map((d) => `${d.id}:${d.end}`));
      const headAt = (e, end, arrow) => arrow !== "none" || dropped.has(`${e.id}:${end}`);
      const arrows = edges.filter(
        (e) => headAt(e, "target", e.targetArrow) !== e.forwardKeys.length > 0 || headAt(e, "source", e.sourceArrow) !== e.backwardKeys.length > 0
      );
      expect(arrows.map((e) => e.id)).toEqual([]);
      const counts = (e) => [e.forwardKeys.length, e.backwardKeys.length].filter(Boolean);
      expect(edges.filter((e) => e.label !== counts(e).join(" + ")).map((e) => e.id)).toEqual([]);

      // Every aggregated edge between two boxes neither of which holds the other is routed: from the
      // border of one to the border of the other, at right angles. At the overview its route is the
      // overview's own, routed afresh between the boxes (`overview.spec.js`), not one of its edges'.
      const holds = (outer, inner) => withAncestors([inner], tree.parents).has(outer);
      const between = edges.filter((e) => !holds(e.ends[0], e.ends[1]) && !holds(e.ends[1], e.ends[0]));
      expect(between.length).toBeGreaterThan(0);
      expect(between.filter((e) => !e.routed).map((e) => e.id)).toEqual([]);
      const onBorder = (point, box) =>
        Math.min(Math.abs(point.x - box.x1), Math.abs(point.x - box.x2), Math.abs(point.y - box.y1), Math.abs(point.y - box.y2)) <= TOLERANCE;
      const off = between.filter((e) => {
        const [first, last] = [e.points[0], e.points[e.points.length - 1]];
        const square = e.points.slice(1).every((p, i) => Math.abs(p.x - e.points[i].x) < TOLERANCE || Math.abs(p.y - e.points[i].y) < TOLERANCE);
        return !square || !onBorder(first, boxes[e.ends[0]]) || !onBorder(last, boxes[e.ends[1]]);
      });
      expect(off.map((e) => e.id)).toEqual([]);
      const drawnBoxes = Object.fromEntries((await viewer(page, "visibleIds")).map((id) => [id, boxes[id]]));
      const through = edgesThroughBoxes(
        between.map((e) => ({ id: e.id, source: e.ends[0], target: e.ends[1], points: e.points })),
        drawnBoxes,
        tree.parents
      );
      expect(through).toEqual([]);
    });

    test("no box moves between levels, whatever order they are opened and closed in", async ({ page, request }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      const deepest = Math.max(...[...tree.boxes].map((id) => tree.depth(id)));
      requireShape(deepest >= 1, "no box sits inside another");
      await reveal(page, everyNode(data));
      const reference = await viewer(page, "nodeBoxes");
      // Level n has every box down to depth n open, a revealed box being drawn open; level 0 is the overview.
      const levels = Array.from({ length: deepest + 1 }, (_, index) => index);
      const orders = [levels, [...levels].reverse(), [levels[levels.length - 1], ...levels.slice(0, -1)]];

      let largest = 0;
      for (const order of orders) {
        for (const level of order) {
          await reveal(page, [...tree.boxes].filter((id) => tree.depth(id) === level));
          const drawn = await viewer(page, "nodeBoxes");
          for (const [id, box] of Object.entries(drawn)) {
            for (const side of ["x1", "y1", "x2", "y2"]) largest = Math.max(largest, Math.abs(box[side] - reference[id][side]));
          }
        }
      }
      expect(largest).toBeLessThanOrEqual(DISPLACEMENT);
    });
  });
}

test("over the budget the weakest aggregated edges are counted on their boxes, and hovering or selecting a box draws all of its edges", { tag: ADOPTER_SIZED }, async ({
  page,
  request,
}) => {
  const data = await GRAPHS[1].open(page, request);
  const tree = treeOf(data);
  const expected = levelOf(tree, new Set(), drawnEdgesOf(data));
  const weighed = [...expected.pairs.values()].map((p) => ({ ends: p.ends, weight: p.forward.length + p.backward.length }));
  requireShape(weighed.length > AGGREGATE_BUDGET, `no more than ${AGGREGATE_BUDGET} pairs of boxes at the top`);
  const leftOut = budgetLeftOut(weighed);

  const edges = await viewer(page, "aggregatedEdges");
  const shown = edges.filter((e) => e.drawn);
  expect(shown.length).toBe(AGGREGATE_BUDGET);
  expect(edges.filter((e) => e.drawn === leftOut.has(e.ends.join("|"))).map((e) => e.id)).toEqual([]);
  const hiddenAt = new Map();
  for (const e of edges.filter((x) => !x.drawn)) for (const end of e.ends) hiddenAt.set(end, (hiddenAt.get(end) || 0) + 1);
  const marks = await viewer(page, "hiddenEdgeCounts");
  expect(Object.fromEntries(Object.entries(marks).map(([id, m]) => [id, m.count]))).toEqual(Object.fromEntries(hiddenAt));
  expect(Object.entries(marks).filter(([, m]) => !m.label.endsWith(`+${m.count}`)).map(([id]) => id)).toEqual([]);

  // The box on screen with the most hidden edges, hovered: all of them drawn; the pointer gone: hidden again.
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const drawnBoxes = await viewer(page, "boxes");
  const centreOf = (id) => ({ x: (drawnBoxes[id].x1 + drawnBoxes[id].x2) / 2, y: (drawnBoxes[id].y1 + drawnBoxes[id].y2) / 2 });
  const onScreen = (id) => {
    const { x, y } = centreOf(id);
    return x > canvas.x + MARGIN_PX && x < canvas.x + canvas.width - MARGIN_PX && y > canvas.y + MARGIN_PX && y < canvas.y + canvas.height - MARGIN_PX;
  };
  const box = [...hiddenAt].filter(([id]) => onScreen(id)).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0];
  expect(box, "a box with hidden edges inside the canvas").toBeTruthy();
  const ofBox = (list) => list.filter((e) => e.ends.includes(box));
  await page.mouse.move(centreOf(box).x, centreOf(box).y);
  await expect.poll(async () => ofBox(await viewer(page, "aggregatedEdges")).every((e) => e.drawn)).toBe(true);
  await page.mouse.move(2, 2);
  await expect.poll(async () => ofBox(await viewer(page, "aggregatedEdges")).filter((e) => !e.drawn).length).toBe(hiddenAt.get(box));

  // Selected, the box is drawn open, and its edges are those of everything in it: all drawn.
  await page.goto(`architecture.html?focus=${encodeURIComponent(box)}`);
  await page.waitForFunction(() => window.__beadloomViewer?.ready() === true);
  const inside = (id) => withAncestors([id], tree.parents).has(box);
  await expect
    .poll(async () => {
      const mine = (await viewer(page, "aggregatedEdges")).filter((e) => e.ends.some(inside));
      return mine.length > 0 && mine.every((e) => e.drawn);
    })
    .toBe(true);
});

/** How many points across the canvas, each way, the pointer is rested on. */
const GRID = [12, 8];

test("wherever the pointer rests at the overview, it draws the left-out edges of one box at most, the one it rests on", { tag: ADOPTER_SIZED }, async ({
  page,
  request,
}) => {
  const data = await GRAPHS[1].open(page, request);
  const tree = treeOf(data);
  requireShape(levelOf(tree, new Set(), drawnEdgesOf(data)).pairs.size > AGGREGATE_BUDGET, `no more than ${AGGREGATE_BUDGET} pairs of boxes at the top`);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const counted = async () => Object.keys(await viewer(page, "hiddenEdgeCounts"));
  const atRest = await counted();
  expect(atRest.length).toBeGreaterThan(1);

  // The pointer rests on every point of a grid over the canvas: on boxes, on edges, on the
  // box that holds everything. Each box whose left-out edges are drawn loses its count.
  const lifted = [];
  for (let i = 1; i < GRID[0]; i += 1) {
    for (let j = 1; j < GRID[1]; j += 1) {
      const [x, y] = [canvas.x + (canvas.width * i) / GRID[0], canvas.y + (canvas.height * j) / GRID[1]];
      await page.mouse.move(x, y);
      await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
      const now = new Set(await counted());
      const uncounted = atRest.filter((id) => !now.has(id));
      if (uncounted.length > 1) lifted.push(`${uncounted.length} boxes with the pointer at ${x.toFixed(0)},${y.toFixed(0)}`);
    }
  }
  expect(lifted).toEqual([]);
});

/** The names of the pairs the map's budget leaves out of `pairs`, `[{ name, weight }]`, sorted. */
async function leftOutByBudget(page, pairs, budget = AGGREGATE_BUDGET) {
  return page.evaluate(
    async ({ list, most }) => {
      const { budgetOf } = await import("/widgets/graph-viewer/lib/levels.js");
      return [...budgetOf(list, most)].sort();
    },
    { list: pairs, most: budget }
  );
}

/** `count` pairs of weight `weight`, named `prefix-000` onwards. */
const pairsOf = (prefix, count, weight) =>
  Array.from({ length: count }, (_, k) => ({ name: `${prefix}-${String(k).padStart(3, "0")}`, weight }));

test("101 pairs that each carry one edge: the budget draws 100 of them and leaves out one, the same one whatever the order", async ({
  page,
}) => {
  await openThemeModules(page);
  const pairs = pairsOf("pair", AGGREGATE_BUDGET + 1, 1);

  expect(await leftOutByBudget(page, pairs)).toEqual(["pair-100"]);
  expect(await leftOutByBudget(page, [...pairs].reverse())).toEqual(["pair-100"]);
});

test("over the budget the strongest pairs are drawn, and a tie at the cut fills the budget rather than emptying it", async ({
  page,
}) => {
  await openThemeModules(page);
  const strong = pairsOf("strong", 99, 5);
  const weak = pairsOf("weak", 300, 1);
  // 99 strong pairs and the first weak one by name fill the budget; the other 299 are left out.
  expect(await leftOutByBudget(page, [...weak, ...strong])).toEqual(weak.slice(1).map((p) => p.name));

  // 90 of weight 3 and 20 of weight 2: every heavy pair and the first 10 of weight 2.
  const heavy = pairsOf("heavy", 90, 3);
  const middle = pairsOf("middle", 20, 2);
  expect(await leftOutByBudget(page, [...middle, ...heavy])).toEqual(middle.slice(10).map((p) => p.name));

  // Within the budget nothing is left out.
  expect(await leftOutByBudget(page, pairsOf("few", AGGREGATE_BUDGET, 1))).toEqual([]);
});

/**
 * `served` with its nodes and edges replaced by `boxes` top-level boxes of one
 * node each and one edge between the nodes of each of the first `pairs` pairs of
 * boxes: every aggregated edge at the overview carries one edge.
 */
function evenlyWeakGraph(served, boxes, pairs) {
  const node = (id, parent) => ({ id, label: id, kind: parent ? "component" : "domain", parent: parent || id, findings: [], doc_status: "fresh", lint_clean: true });
  const nodes = [];
  for (let b = 0; b < boxes; b += 1) nodes.push(node(`box${b}`), node(`box${b}-n`, `box${b}`));
  const edges = [];
  for (let a = 0; a < boxes && edges.length < pairs; a += 1) {
    for (let b = a + 1; b < boxes && edges.length < pairs; b += 1) edges.push({ src: `box${a}-n`, dst: `box${b}-n`, kind: "depends_on" });
  }
  return { ...served, nodes, edges: [...nodes.map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" })), ...edges] };
}

test("at the overview 101 pairs of boxes joined by one edge each draw 100 aggregated edges and count the one left out on its two boxes", async ({
  page,
  request,
}) => {
  const data = evenlyWeakGraph(await architectureData(request), 15, AGGREGATE_BUDGET + 1);
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);

  const edges = await viewer(page, "aggregatedEdges");
  expect(edges).toHaveLength(AGGREGATE_BUDGET + 1);
  const left = edges.filter((e) => !e.drawn);
  expect(left).toHaveLength(1);
  const counts = await viewer(page, "hiddenEdgeCounts");
  expect(Object.fromEntries(Object.entries(counts).map(([id, m]) => [id, m.count]))).toEqual(
    Object.fromEntries(left[0].ends.map((end) => [end, 1]))
  );
});

/** Whether the box `box` is in view, by the viewer's extent. */
const inView = (box, extent) => box.x2 > extent.x1 && box.x1 < extent.x2 && box.y2 > extent.y1 && box.y1 < extent.y2;

/** The top-level boxes that break the rule at the view `level` reports: open when they should not be, or closed when they should be open. */
function againstTheRule(level, boxes, topBoxes) {
  const past = level.zoom >= FIT_FLOOR * level.fitZoom;
  const open = new Set(level.open);
  return topBoxes.filter((id) => {
    const b = boxes[id];
    const side = Math.max(b.x2 - b.x1, b.y2 - b.y1) * level.zoom;
    const seen = past && inView(b, level.extent);
    if (seen && side >= OPEN_SIDE_PX && !open.has(id)) return true;
    return open.has(id) && !(seen && side >= CLOSE_SIDE_PX);
  });
}

test("zooming into a box opens it and draws its children, and zooming out closes it again", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  requireShape(tree.topBoxes.length > 0, "no box at the top of the containment tree");
  await openArchitecture(page);
  const { boxes } = await viewer(page, "elkGeometry");
  const level = await viewer(page, "level");
  expect(level.fitZoom).toBeCloseTo(await viewer(page, "zoom"), 6);
  // The largest top-level box, aimed at with the pointer.
  const target = [...tree.topBoxes].sort((a, b) => {
    const area = (id) => (boxes[id].x2 - boxes[id].x1) * (boxes[id].y2 - boxes[id].y1);
    return area(b) - area(a) || a.localeCompare(b);
  })[0];
  const children = data.nodes.filter((n) => tree.parents[n.id] === target).map((n) => n.id);
  const canvas = page.getByTestId("graph-canvas");
  await canvas.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  // The box dragged to the middle of the canvas, where the zoom buttons zoom.
  const area = await canvas.boundingBox();
  const b = (await viewer(page, "boxes"))[target];
  const from = { x: (b.x1 + b.x2) / 2, y: (b.y1 + b.y2) / 2 };
  const [dx, dy] = [area.x + area.width / 2 - from.x, area.y + area.height / 2 - from.y];
  // A press that does not move is a tap, which would select the box: drag only when it is off the middle.
  if (Math.hypot(dx, dy) > MARGIN_PX) await drag(page, from, dx, dy);
  const step = async (name) => {
    await page.getByRole("button", { name, exact: true }).click();
    await expect.poll(async () => againstTheRule(await viewer(page, "level"), boxes, tree.topBoxes)).toEqual([]);
  };

  let opened = false;
  for (let taken = 0; taken < ZOOM_STEPS && !opened; taken += 1) {
    await step("Zoom in");
    opened = (await viewer(page, "openBoxes")).includes(target);
  }
  expect(opened).toBe(true);
  const shown = new Set(await viewer(page, "visibleIds"));
  expect(children.filter((id) => !shown.has(id))).toEqual([]);
  // When it opened at the first step that made it 600 px, it is under 750; one step out it is
  // under 600 and over 480, and stays open: it closes only below 0.8 of the size it opens at.
  // When it opened at the step that passed the floor instead, one step out is under the floor.
  await step("Zoom out");
  const zoom = await viewer(page, "zoom");
  const side = Math.max(boxes[target].x2 - boxes[target].x1, boxes[target].y2 - boxes[target].y1) * zoom;
  if (zoom >= FIT_FLOOR * level.fitZoom) {
    expect(side).toBeGreaterThanOrEqual(CLOSE_SIDE_PX);
    expect(side).toBeLessThan(OPEN_SIDE_PX);
    expect(await viewer(page, "openBoxes")).toContain(target);
  } else {
    expect(await viewer(page, "openBoxes")).not.toContain(target);
  }

  for (let taken = 0; taken < ZOOM_STEPS && (await viewer(page, "zoom")) > level.fitZoom * 1.05; taken += 1) {
    await step("Zoom out");
  }
  expect(await viewer(page, "openBoxes")).toEqual(tree.wrapper ? [tree.wrapper] : []);
});

test("a selection opens the boxes that hold it, at any zoom; a hub selected alone does not open its neighbours' boxes", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const degree = degreesOf(data);
  const deep = data.nodes
    .filter((n) => tree.depth(n.id) >= 2 && (degree.get(n.id) || 0) < HUB_DEGREE && !tree.boxes.has(n.id))
    .sort((a, b) => tree.depth(b.id) - tree.depth(a.id) || a.id.localeCompare(b.id))[0];
  requireShape(deep, "no node that is not a hub sits two levels below the top");

  // A node that is not a hub opens its own boxes and its neighbours'.
  await openArchitecture(page, `?focus=${encodeURIComponent(deep.id)}`);
  const walk = neighbourhood(data, deep.id, 1, "both").ids;
  await expect
    .poll(async () => {
      const visible = new Set(await viewer(page, "visibleIds"));
      return walk.filter((id) => !visible.has(id));
    })
    .toEqual([]);
  const openNow = new Set(await viewer(page, "openBoxes"));
  const holding = [...withAncestors(walk, tree.parents)].filter((id) => tree.boxes.has(id) && !walk.includes(id));
  expect(holding.filter((id) => !openNow.has(id))).toEqual([]);

  // A hub, selected alone, opens its own boxes; its edges into the others stay aggregated, and marked.
  const hub = [...degree].filter(([, d]) => d >= HUB_DEGREE).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0];
  requireShape(hub, `no node has ${HUB_DEGREE} drawn edges`);
  await openArchitecture(page, `?focus=${encodeURIComponent(hub)}`);
  const own = [...withAncestors([hub], tree.parents)].filter((id) => id !== hub);
  const open = await viewer(page, "openBoxes");
  expect(own.filter((id) => !open.includes(id))).toEqual([]);
  const others = tree.topBoxes.filter((id) => !own.includes(id));
  const neighbours = neighbourhood(data, hub, 1, "both").ids.filter((id) => id !== hub);
  const reached = others.filter((box) => neighbours.some((id) => withAncestors([id], tree.parents).has(box) && id !== box));
  requireShape(reached.length > 0, "the busiest hub has no neighbour in a box of its own");
  expect(reached.filter((box) => open.includes(box))).toEqual([]);
  const marked = (await viewer(page, "aggregatedEdges")).filter((e) => e.ends.includes(hub) && e.walk).flatMap((e) => e.ends);
  expect(reached.filter((box) => !marked.includes(box))).toEqual([]);

  // Asked for more — two steps, or impact — the walk opens every box it reaches.
  for (const [query, ids] of [
    ["&depth=2", neighbourhood(data, hub, 2, "both").ids],
    ["&view=impact", [...impact(data, hub).distances.keys()]],
  ]) {
    await openArchitecture(page, `?focus=${encodeURIComponent(hub)}${query}`);
    const visible = new Set(await viewer(page, "visibleIds"));
    expect(ids.filter((id) => !visible.has(id)), query).toEqual([]);
  }
});

test("the search box opens the boxes that hold what it finds", async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const target = data.nodes
    .filter((n) => tree.depth(n.id) >= 2)
    .sort((a, b) => a.id.localeCompare(b.id))[0];
  requireShape(target, "no node sits two levels below the top");
  const matches = data.nodes.filter((n) => [n.id, n.label].some((t) => String(t || "").toLowerCase().includes(target.id.toLowerCase())));

  await openArchitecture(page);
  await page.getByRole("searchbox", { name: "Search nodes" }).fill(target.id);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(sorted(withAncestors(matches.map((n) => n.id), tree.parents)));
});

test("a filter composes with the level: a closed box holding a kept node stays closed, and its aggregated edges carry only kept edges", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const kinds = [...new Set(data.nodes.map((n) => n.kind))].sort();
  // The kind kept inside the most top-level boxes, so the overview still has pairs.
  const keptIn = (kind) =>
    new Set(data.nodes.filter((n) => n.kind === kind).flatMap((n) => [...withAncestors([n.id], tree.parents)])).size;
  const kind = kinds.sort((a, b) => keptIn(b) - keptIn(a) || a.localeCompare(b))[0];
  const kept = withAncestors(data.nodes.filter((n) => n.kind === kind).map((n) => n.id), tree.parents);
  const edges = drawnEdgesOf(data).filter((e) => kept.has(e.src) && kept.has(e.dst));
  const expected = levelOf(tree, new Set(), edges);
  requireShape(expected.pairs.size > 0 && kept.size < data.nodes.length, "no kind keeps an edge between two boxes and leaves a node out");

  await openArchitecture(page);
  await page.getByLabel("Kind", { exact: true }).selectOption(kind);

  await expect.poll(() => viewer(page, "visibleIds")).toEqual(sorted([...expected.nodes].filter((id) => kept.has(id))));
  const drawn = await aggregatedByPair(page);
  expect(sorted(Object.keys(drawn))).toEqual(sorted(expected.pairs.keys()));
  const wrong = [...expected.pairs].filter(
    ([name, pair]) => JSON.stringify(carried(drawn[name])) !== JSON.stringify({ forward: pair.forward, backward: pair.backward })
  );
  expect(wrong.map(([name]) => name)).toEqual([]);
});

test("an edge onto the box that holds everything is not drawn at the overview, and is drawn at full detail", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const onto = drawnEdgesOf(data).filter(
    (e) => tree.wrapper && (e.dst === tree.wrapper || e.src === tree.wrapper) && tree.depth(e.dst === tree.wrapper ? e.src : e.dst) >= 2
  );
  requireShape(onto.length > 0, "no edge onto the box that holds everything from inside another box");

  await openArchitecture(page);
  expect((await viewer(page, "aggregatedEdges")).filter((e) => e.ends.includes(tree.wrapper))).toEqual([]);
  expect((await viewer(page, "edgeLooks")).filter((look) => onto.some((e) => e.key === look.key))).toEqual([]);

  await reveal(page, everyNode(data));
  const keys = new Set((await viewer(page, "edgeLooks")).map((look) => look.key));
  expect(onto.filter((e) => !keys.has(e.key)).map((e) => e.key)).toEqual([]);
});

test("the map's marks keep their size on screen as the view zooms", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(treeOf(data).topBoxes.length > 1, "fewer than two boxes at the top of the containment tree");
  await openArchitecture(page);

  const within = (pixels, wanted) => pixels >= wanted / STEP - 1e-6 && pixels <= wanted * STEP + 1e-6;
  const readings = [];
  for (let step = 0; step < 4; step += 1) {
    const zoom = await viewer(page, "zoom");
    const edges = (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn);
    const { pills } = await viewer(page, "pills");
    const titles = await viewer(page, "titles");
    readings.push({ zoom, edges, pills, titles });
    await page.getByRole("button", { name: "Zoom out", exact: true }).click();
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  }
  for (const { zoom, edges, pills, titles } of readings) {
    expect(edges.length + titles.length).toBeGreaterThan(0);
    // One weight whatever the count an aggregated edge carries: the count is on its pill.
    expect(edges.filter((e) => !within(e.width * zoom, LINE_PX)).map((e) => `${e.id} at zoom ${zoom}`)).toEqual([]);
    expect(pills.filter((p) => p.fontSize !== COUNT_PILL_PX).map((p) => p.id)).toEqual([]);
    // A title keeps the size it was fitted at, one of the few it is tried at.
    expect(titles.filter((t) => !BOX_TITLE_PX.includes(t.sizePx) || !within(t.fontSize, t.sizePx)).map((t) => `${t.id} at zoom ${zoom}`)).toEqual([]);
  }
});

test("a box too small for its title shows the title outside it", async ({ page, request }) => {
  const served = await architectureData(request);
  const node = (id, parent) => ({ id, label: id, kind: parent ? "component" : "domain", parent: parent || id, findings: [], doc_status: "fresh", lint_clean: true });
  const small = "a-box-whose-title-is-far-longer-than-the-one-node-it-holds";
  // A box of six nodes in a chain, which ELK stacks, and a box of one node with a long title.
  const nodes = [node(small), node("s1", small), node("big")];
  for (let k = 0; k < 6; k += 1) nodes.push(node(`b${k}`, "big"));
  const chain = nodes.filter((n) => n.parent === "big").slice(1).map((n, k) => ({ src: `b${k}`, dst: n.id, kind: "depends_on" }));
  const data = {
    ...served,
    nodes,
    edges: [
      ...nodes.map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" })),
      ...chain,
      { src: "s1", dst: "b0", kind: "depends_on" },
    ],
  };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);

  const titles = Object.fromEntries((await viewer(page, "level")).collapsed.map((b) => [b.id, b.outside]));
  expect(titles).toEqual({ [small]: true, big: false });
});

test("the landscape has no boxes, so no levels: every service is drawn", async ({ page, request }) => {
  const data = await landscapeData(request);
  requireShape(data.nodes.length > 0, LACKING.landscapeService);
  await openLandscape(page);

  expect(await viewer(page, "openBoxes")).toEqual([]);
  expect((await viewer(page, "level")).collapsed).toEqual([]);
  expect(await viewer(page, "aggregatedEdges")).toEqual([]);
  expect(await viewer(page, "visibleIds")).toEqual(sorted(data.nodes.map((n) => n.id)));
});
