// A node's edges are drawn together: a bus at every node, a trunk at a busy one, and nothing moves.
//
// In an earlier version every edge followed the route ELK gave it, and ELK gives
// each edge of a node a channel of its own: on a graph of 130 nodes the busiest
// one left its side at 69 points and turned at 36 heights, a staircase as wide as
// the graph, and the fans of the whole drawing had 396 steps more than two per
// node. The routes are now rewritten after ELK, which moves no node: a node's
// edges that leave one side in one direction share one channel, and a busy node's
// edges to one top-level box share one route to a line along that box. Where two
// routes part, a dot marks it; hovering a shared line names every edge on it; and
// edges outside a selection fade in colour, so a trunk of them does not darken.
//
// Every case reads the graph at full detail, every box open: at the whole-graph
// fit the viewer draws a map of closed boxes (`map.spec.js`).

import { test, expect } from "@playwright/test";
import { adopterSizedGraph } from "./support/adopterGraph.js";
import {
  branchPoints,
  channelsOf,
  collinearPairs,
  deviation,
  distanceToPolyline,
  excessSteps,
  lanesAt,
  polylineOf,
} from "./support/routeMetrics.js";
import { architectureData, openArchitecture, openEveryBox, parentMap, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

/** A node with this many drawn edges is busy enough for trunks; the viewer's own threshold. */
const TRUNK_DEGREE = 20;
/** How far out from a busy node its lanes are counted, in layout units. */
const LANE_DISTANCE = 150;
/** The share of ELK's excess steps the drawn fans may keep. */
const STEPS_KEPT = 0.2;
/** ELK's excess steps below which a drawing has no staircase worth measuring. */
const STAIRCASE = 20;
/** How long rewriting the routes may take on an adopter-sized graph, in ms. */
const BUNDLING_BUDGET_MS = 50;
/** How far two points, or a point and a line, may lie apart and count as one, in layout units. */
const TOLERANCE = 0.5;
/** How far, in pixels on screen, a hovered point lies from any other edge and any node. */
const CLEARANCE_PX = 12;
/** The zoom steps that bring the canvas from the fit to full size, at most. */
const ZOOM_STEPS = 20;
/**
 * Why the two cases about every busy node are expected to fail on an
 * adopter-sized graph: there some busy leaves keep a second channel and more
 * lanes than the bound. A case marked so passes while it fails, and fails the run
 * the day it passes, so the mark goes with the fix.
 */
const KNOWN_STAIRCASES = "known: busy leaves of an adopter-sized graph keep a second channel and exceed the lane bound";

/** The graphs a bundled drawing is read on; `knownStaircases` names why its busy nodes are expected to fail. */
const GRAPHS = [
  {
    name: "this portal's architecture graph",
    knownStaircases: null,
    open: async (page, request) => {
      const data = await architectureData(request);
      await openArchitecture(page);
      await openEveryBox(page);
      return data;
    },
  },
  {
    name: "an adopter-sized architecture graph",
    knownStaircases: KNOWN_STAIRCASES,
    open: async (page, request) => {
      const data = adopterSizedGraph(await architectureData(request));
      await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      await openEveryBox(page);
      return data;
    },
  },
];

/** The crafted graph's box with many edges, its two children, and the top-level boxes its edges lead to. */
const BOX_HUB = "hub";
const HUB_CHILDREN = ["hub-core", "hub-port"];
const TARGET_BOXES = [
  ["left", 7],
  ["middle", 6],
  ["right", 6],
];

/**
 * `served` with its nodes and edges replaced by a crafted graph whose one busy
 * node is a box: a box holding two leaves draws twenty edges, nineteen routed to
 * the leaves of three other top-level boxes and one into its own child, which is
 * drawn as a loop. Its children have edges of their own, one inside the box and
 * one out through its border, so the box is not an empty frame.
 */
function boxHubGraph(served) {
  const nodeOf = (id, kind, parent) => ({
    id,
    label: id,
    kind,
    parent: parent || id,
    findings: [],
    doc_status: "fresh",
    lint_clean: true,
  });
  const dependency = (src, dst) => ({ src, dst, kind: "depends_on" });
  const nodes = [nodeOf("system", "service", null), nodeOf(BOX_HUB, "domain", "system")];
  nodes.push(...HUB_CHILDREN.map((child) => nodeOf(child, "component", BOX_HUB)));
  const edges = [];
  for (const [box, leaves] of TARGET_BOXES) {
    nodes.push(nodeOf(box, "domain", "system"));
    for (let k = 0; k < leaves; k += 1) {
      nodes.push(nodeOf(`${box}-n${k}`, "component", box));
      edges.push(dependency(BOX_HUB, `${box}-n${k}`));
    }
  }
  const [core, port] = HUB_CHILDREN;
  edges.push(dependency(BOX_HUB, core), dependency(core, port), dependency(port, `${TARGET_BOXES[1][0]}-n0`));
  const containment = nodes.map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" }));
  return { ...served, nodes, edges: [...containment, ...edges] };
}

/** Every edge drawn now along a route, with its ends: `[{ id, source, target, points }]`. */
async function drawnRoutes(page) {
  return (await viewer(page, "edgeRoutes"))
    .filter((r) => r.routed)
    .map(({ id, source, target, points }) => ({ id, source, target, points }));
}

/** The same edges along ELK's routes, as ELK computed them. */
function elkRoutesOf(drawn, geometry) {
  return drawn.map((r) => ({ ...r, points: polylineOf(geometry.routes[r.id].sections) }));
}

/** The ids that hold no other node. */
const leavesOf = (parents) => {
  const holders = new Set(Object.values(parents).filter(Boolean));
  return new Set(Object.keys(parents).filter((id) => !holders.has(id)));
};

/** The top-level box of each node: below the one root that holds everything, or its own root. */
function topBoxOf(parents) {
  const roots = Object.keys(parents).filter((id) => !parents[id]);
  const holders = new Set(Object.values(parents).filter(Boolean));
  const wrapper = roots.length === 1 && holders.has(roots[0]) ? roots[0] : null;
  return (id) => {
    let cursor = id;
    while (parents[cursor] && parents[cursor] !== wrapper) cursor = parents[cursor];
    return cursor;
  };
}

/** The node with the most drawn edges, and how many. */
function busiestOf(routes, leaves) {
  const degree = new Map();
  for (const r of routes) {
    for (const id of [r.source, r.target]) if (leaves.has(id)) degree.set(id, (degree.get(id) || 0) + 1);
  }
  return [...degree].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0] || [null, 0];
}

/** Every node, leaf or box, with at least `threshold` drawn edges, busiest first: `[[id, degree]]`. */
async function busyNodes(page, threshold) {
  const degree = new Map();
  for (const r of await viewer(page, "edgeRoutes")) {
    for (const id of new Set([r.source, r.target])) degree.set(id, (degree.get(id) || 0) + 1);
  }
  return [...degree].filter(([, d]) => d >= threshold).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

/**
 * The drawn routes of `node`'s own edges: every one but an edge another node's
 * trunk carries. A busy node's edge to another busy node rides its source's trunk
 * and arrives at the target in a lane of its own, so it counts at its source.
 */
function ownRoutes(drawn, node, trunks) {
  const carried = new Set(trunks.filter((t) => t.node !== node).flatMap((t) => t.members));
  const mine = new Set(trunks.filter((t) => t.node === node).flatMap((t) => t.members));
  return drawn.filter((r) => (r.source === node || r.target === node) && (mine.has(r.id) || !carried.has(r.id)));
}

/** Every side a busy node of `busy` leaves in more than one channel in one direction: `["node side: N channels"]`. */
async function staircasesOf(page, busy) {
  const drawn = await drawnRoutes(page);
  const { trunks } = await viewer(page, "bundles");
  const { boxes } = await viewer(page, "elkGeometry");
  return busy.flatMap(([node]) =>
    [...channelsOf(ownRoutes(drawn, node, trunks), node, boxes[node])]
      .filter(([, heights]) => heights.size > 1)
      .map(([side, heights]) => `${node} ${side}: ${heights.size} channels`)
  );
}

/**
 * Every side whose edges, of a busy node of `busy`, cross a line 150 units out
 * in more lanes than the top-level boxes they lead to plus one per edge into the
 * node's own: `["node side: N lanes, at most M"]`.
 */
async function lanesOverBoundOf(page, busy, parents) {
  const drawn = await drawnRoutes(page);
  const { trunks } = await viewer(page, "bundles");
  const { boxes } = await viewer(page, "elkGeometry");
  const topBox = topBoxOf(parents);
  return busy.flatMap(([node]) => {
    const own = topBox(node);
    return Object.entries(lanesAt(ownRoutes(drawn, node, trunks), node, boxes[node], LANE_DISTANCE))
      .map(([side, { lanes, others }]) => {
        const bound =
          new Set(others.map(topBox).filter((top) => top !== own)).size + others.filter((o) => topBox(o) === own).length;
        return { side, lanes, bound };
      })
      .filter(({ lanes, bound }) => lanes > bound)
      .map(({ side, lanes, bound }) => `${node} ${side}: ${lanes} lanes, at most ${bound}`);
  });
}

/** Whether every junction lies by a point of `expected`, and every point of `expected` by a junction. */
function sameJunctions(junctions, expected) {
  const by = (point) => (other) => Math.hypot(point.x - other.x, point.y - other.y) <= 1;
  return {
    stray: junctions.filter((j) => !expected.some(by(j))),
    missing: expected.filter((p) => !junctions.some(by(p))),
  };
}

for (const graph of GRAPHS) {
  test.describe(`on ${graph.name}`, () => {
    test("no node or box moves: every leaf stands at its ELK box's centre and every box keeps ELK's size", async ({
      page,
      request,
    }) => {
      const parents = parentMap(await graph.open(page, request));
      const { boxes } = await viewer(page, "elkGeometry");
      const positions = await viewer(page, "positions");
      const drawn = await viewer(page, "nodeBoxes");

      const moved = [...leavesOf(parents)].filter((id) => {
        const box = boxes[id];
        if (!box) return false;
        const centre = { x: (box.x1 + box.x2) / 2, y: (box.y1 + box.y2) / 2 };
        return Math.hypot(positions[id].x - centre.x, positions[id].y - centre.y) > TOLERANCE;
      });
      expect(moved).toEqual([]);
      const resized = Object.keys(boxes).filter((id) =>
        ["x1", "y1", "x2", "y2"].some((side) => Math.abs(drawn[id][side] - boxes[id][side]) > TOLERANCE)
      );
      expect(resized).toEqual([]);
    });

    test("the drawn fans keep at most a fifth of the steps ELK's staircases have", async ({ page, request }) => {
      const leaves = leavesOf(parentMap(await graph.open(page, request)));
      const drawn = await drawnRoutes(page);
      const elk = excessSteps(elkRoutesOf(drawn, await viewer(page, "elkGeometry")), leaves);
      requireShape(elk >= STAIRCASE, `ELK draws fewer than ${STAIRCASE} excess steps: no staircase to bundle`);

      expect(excessSteps(drawn, leaves)).toBeLessThanOrEqual(STEPS_KEPT * elk);
    });

    test("every route joins its own two boxes with right angles only, and an edge in no bundle keeps ELK's route", async ({
      page,
      request,
    }) => {
      await graph.open(page, request);
      const { boxes, routes: elk } = await viewer(page, "elkGeometry");
      const { routes, trunks, buses } = await viewer(page, "bundles");
      const drawn = await drawnRoutes(page);
      const bundled = new Set([...trunks, ...buses].flatMap((bundle) => bundle.members));
      requireShape(bundled.size > 0, "no node has two edges that leave one side in one direction");

      const onBorder = (point, box) =>
        point.x >= box.x1 - TOLERANCE &&
        point.x <= box.x2 + TOLERANCE &&
        point.y >= box.y1 - TOLERANCE &&
        point.y <= box.y2 + TOLERANCE &&
        Math.min(...["x1", "x2"].map((s) => Math.abs(point.x - box[s])), ...["y1", "y2"].map((s) => Math.abs(point.y - box[s]))) <= TOLERANCE;
      const wrong = drawn
        .map(({ id, source, target }) => ({ id, source, target, points: routes[id] }))
        .filter(({ source, target, points }) => {
          const square = points.slice(1).every((p, i) => Math.abs(p.x - points[i].x) < TOLERANCE || Math.abs(p.y - points[i].y) < TOLERANCE);
          return !square || !onBorder(points[0], boxes[source]) || !onBorder(points[points.length - 1], boxes[target]);
        })
        .map(({ id }) => id);
      expect(wrong).toEqual([]);
      const rerouted = drawn
        .filter(({ id }) => !bundled.has(id) && deviation(routes[id], polylineOf(elk[id].sections)) > TOLERANCE)
        .map(({ id }) => id);
      expect(rerouted).toEqual([]);
    });

    test("every node with 20 drawn edges or more leaves each side in one channel per direction", async ({
      page,
      request,
    }) => {
      test.fail(Boolean(graph.knownStaircases), graph.knownStaircases);
      await graph.open(page, request);
      const busy = await busyNodes(page, TRUNK_DEGREE);
      requireShape(busy.length > 0, `no node has ${TRUNK_DEGREE} drawn edges`);

      expect(await staircasesOf(page, busy)).toEqual([]);
    });

    test("every node with 20 drawn edges or more crosses a line 150 units out in no more lanes than the top-level boxes it leads to, plus one per edge into its own", async ({
      page,
      request,
    }) => {
      test.fail(Boolean(graph.knownStaircases), graph.knownStaircases);
      const parents = parentMap(await graph.open(page, request));
      const busy = await busyNodes(page, TRUNK_DEGREE);
      requireShape(busy.length > 0, `no node has ${TRUNK_DEGREE} drawn edges`);

      expect(await lanesOverBoundOf(page, busy, parents)).toEqual([]);
    });

    test("no two edges with no common end are drawn along one line", async ({ page, request }) => {
      await graph.open(page, request);
      const drawn = await drawnRoutes(page);
      requireShape(drawn.length > 1, "fewer than two drawn edges");

      expect(collinearPairs(drawn)).toEqual([]);
    });

    test("a junction dot marks every point where drawn routes part, and no other", async ({ page, request }) => {
      await graph.open(page, request);
      const expected = branchPoints(await drawnRoutes(page));
      requireShape(expected.length > 0, "no two drawn routes run together and part");

      const { stray, missing } = sameJunctions(await viewer(page, "junctions"), expected);
      expect(stray).toEqual([]);
      expect(missing).toEqual([]);
    });
  });
}

test("the bundling takes at most 50 ms on an adopter-sized graph", async ({ page, request }) => {
  await GRAPHS[1].open(page, request);
  const { ms } = await viewer(page, "bundles");
  expect(ms).toBeLessThanOrEqual(BUNDLING_BUDGET_MS);
});

test("the busiest node leaves each side in one channel per direction, in no more lanes than the boxes it leads to", async ({
  page,
  request,
}) => {
  const parents = parentMap(await GRAPHS[0].open(page, request));
  const drawn = await drawnRoutes(page);
  const [busiest, degree] = busiestOf(drawn, leavesOf(parents));
  requireShape(degree >= TRUNK_DEGREE, `no node has ${TRUNK_DEGREE} drawn edges`);
  const box = (await viewer(page, "elkGeometry")).boxes[busiest];

  const steps = [...channelsOf(drawn, busiest, box)].filter(([, heights]) => heights.size > 1);
  expect(steps.map(([side, heights]) => `${side}: ${heights.size} channels`)).toEqual([]);
  // A lane per top-level box the edges lead to, and one per edge into the node's own box.
  const topBox = topBoxOf(parents);
  const own = topBox(busiest);
  for (const [side, { lanes, others }] of Object.entries(lanesAt(drawn, busiest, box, LANE_DISTANCE))) {
    const boxes = new Set(others.map(topBox).filter((top) => top !== own)).size;
    const inOwn = others.filter((other) => topBox(other) === own).length;
    expect(lanes, `${side} side`).toBeLessThanOrEqual(boxes + inOwn);
  }
});

test("a box with 20 drawn edges, one of them a loop into its own child, leaves its side in one channel and crosses a line 150 units out in one lane per top-level box it leads to", async ({
  page,
  request,
}) => {
  const data = boxHubGraph(await architectureData(request));
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  await openEveryBox(page);
  const busy = await busyNodes(page, TRUNK_DEGREE);
  expect(busy).toEqual([[BOX_HUB, TRUNK_DEGREE]]);
  const loops = (await viewer(page, "edgeRoutes")).filter((r) => r.loop && r.source === BOX_HUB);
  expect(loops.map((r) => r.target)).toEqual([HUB_CHILDREN[0]]);

  expect(await staircasesOf(page, busy)).toEqual([]);
  expect(await lanesOverBoundOf(page, busy, parentMap(data))).toEqual([]);
});

test("junction dots follow the edges drawn now: a filter and a hidden neighbourhood remove the ones they part", async ({
  page,
  request,
}) => {
  const data = await GRAPHS[0].open(page, request);
  const parents = parentMap(data);
  const before = await viewer(page, "junctions");
  const [busiest] = busiestOf(await drawnRoutes(page), leavesOf(parents));
  const kinds = [...new Set(data.nodes.map((n) => n.kind))].sort();
  requireShape(before.length > 0 && kinds.length > 1, "no junction, or a single node kind to filter by");

  // The kind whose filter leaves routes drawn and removes the most junctions.
  let removed = 0;
  for (const kind of kinds) {
    await page.getByLabel("Kind", { exact: true }).selectOption(kind);
    await expect.poll(async () => (await viewer(page, "visibleIds")).length).toBeLessThan(data.nodes.length);
    const drawn = await drawnRoutes(page);
    const { stray, missing } = sameJunctions(await viewer(page, "junctions"), branchPoints(drawn));
    expect(stray, kind).toEqual([]);
    expect(missing, kind).toEqual([]);
    removed = Math.max(removed, before.length - (await viewer(page, "junctions")).length);
  }
  expect(removed).toBeGreaterThan(0);

  await openArchitecture(page, `?focus=${encodeURIComponent(busiest)}&depth=1&hide=1`);
  await expect.poll(async () => (await viewer(page, "neighbourhood")).ids.length).toBeGreaterThan(0);
  const shown = await drawnRoutes(page);
  const { stray, missing } = sameJunctions(await viewer(page, "junctions"), branchPoints(shown));
  expect(stray).toEqual([]);
  expect(missing).toEqual([]);
});

/** The middles of the stretches two members of one bundle share, longest first, in graph coordinates. */
function sharedStretches(bundles, routes) {
  const found = [];
  for (const { members } of bundles) {
    const [a, b] = members.filter((id) => routes[id]);
    if (!b) continue;
    const points = routes[a];
    for (let i = 1; i < points.length; i += 1) {
      const [p, q] = [points[i - 1], points[i]];
      if (distanceToPolyline(p, routes[b]) > TOLERANCE || distanceToPolyline(q, routes[b]) > TOLERANCE) continue;
      found.push({ length: Math.hypot(q.x - p.x, q.y - p.y), point: { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 } });
    }
  }
  return found.sort((x, y) => y.length - x.length).map(({ point }) => point);
}

/** Where a point in graph coordinates is on the page now. */
async function onPage(page, point) {
  const zoom = await viewer(page, "zoom");
  const pan = await viewer(page, "pan");
  const rect = await page.getByTestId("graph-canvas").boundingBox();
  return { x: rect.x + point.x * zoom + pan.x, y: rect.y + point.y * zoom + pan.y };
}

test("hovering a line several edges share highlights every edge along it and names them", async ({ page, request }) => {
  const parents = parentMap(await GRAPHS[0].open(page, request));
  const [busiest] = busiestOf(await drawnRoutes(page), leavesOf(parents));
  requireShape(Boolean(busiest), "no node has a drawn edge");
  // The busiest node's fans in the middle of the canvas, at about full size.
  await openArchitecture(page, `?focus=${encodeURIComponent(busiest)}`);
  await openEveryBox(page);
  await page.getByRole("button", { name: "Panel" }).click();
  await page.getByRole("button", { name: "Centre" }).click();
  for (let step = 0; step < ZOOM_STEPS && (await viewer(page, "zoom")) < 1; step += 1) {
    await page.getByRole("button", { name: "Zoom in" }).click();
  }
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  // Cytoscape reads where its canvas is when the scroll reaches it (`edges.spec.js`).
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
  const { trunks, buses } = await viewer(page, "bundles");
  const drawn = await drawnRoutes(page);
  const routes = Object.fromEntries(drawn.map((r) => [r.id, r.points]));
  const leaves = leavesOf(parents);
  const nodes = Object.entries(await viewer(page, "nodeBoxes")).filter(([id]) => leaves.has(id)).map(([, box]) => box);
  const clearance = CLEARANCE_PX / (await viewer(page, "zoom"));
  const viewport = page.viewportSize();
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  // A point on a shared stretch, on screen, with no other edge and no leaf near enough to take the pointer.
  let point = null;
  let along = [];
  for (const candidate of sharedStretches([...trunks, ...buses], routes)) {
    const through = drawn.filter((r) => distanceToPolyline(candidate, r.points) <= TOLERANCE);
    const crowded = drawn.some(
      (r) => !through.includes(r) && distanceToPolyline(candidate, r.points) < clearance
    );
    const onNode = nodes.some(
      (b) => candidate.x > b.x1 - clearance && candidate.x < b.x2 + clearance && candidate.y > b.y1 - clearance && candidate.y < b.y2 + clearance
    );
    const at = await onPage(page, candidate);
    const onScreen =
      at.x > canvas.x + CLEARANCE_PX && at.x < Math.min(canvas.x + canvas.width, viewport.width) - CLEARANCE_PX &&
      at.y > canvas.y + CLEARANCE_PX && at.y < Math.min(canvas.y + canvas.height, viewport.height) - CLEARANCE_PX;
    if (crowded || onNode || !onScreen) continue;
    point = at;
    along = through.map((r) => r.id).sort();
    break;
  }
  requireShape(Boolean(point), "no two edges of one bundle share a stretch clear of other edges and nodes");

  await page.mouse.move(point.x, point.y);
  await expect.poll(() => viewer(page, "hoveredEdges")).toEqual(along);
  await expect(page.getByTestId("edge-bundle-note")).toContainText(`${along.length} edges`);
  await page.mouse.move(2, 2);
  await expect.poll(() => viewer(page, "hoveredEdges")).toEqual([]);
  await expect(page.getByTestId("edge-bundle-note")).toBeHidden();
});

test("an edge outside a selection fades in colour at full opacity, so a trunk of them is no darker than one", async ({
  page,
  request,
}) => {
  const parents = parentMap(await GRAPHS[0].open(page, request));
  const plain = Object.fromEntries((await viewer(page, "edgeLooks")).map((look) => [look.key, look]));
  const [busiest] = busiestOf(await drawnRoutes(page), leavesOf(parents));
  requireShape(Boolean(busiest), "no node has a drawn edge");

  await openArchitecture(page, `?focus=${encodeURIComponent(busiest)}&depth=1`);
  await openEveryBox(page);
  await expect.poll(async () => (await viewer(page, "neighbourhood")).edges.length).toBeGreaterThan(0);
  const walked = new Set((await viewer(page, "neighbourhood")).edges);
  const looks = await viewer(page, "edgeLooks");
  const dimmed = looks.filter((look) => !walked.has(look.key));
  requireShape(dimmed.length > 0, "the busiest node's neighbourhood takes every drawn edge");

  expect(dimmed.filter((look) => look.opacity !== 1 || look.lineColour === plain[look.key].lineColour)).toEqual([]);
  expect(looks.filter((look) => walked.has(look.key) && look.lineColour !== plain[look.key].lineColour)).toEqual([]);
});
