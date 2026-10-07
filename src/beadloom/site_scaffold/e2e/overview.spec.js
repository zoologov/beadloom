// The overview reads at a glance: its own routes between the boxes, counts on pills, titles that fit, calm until asked.
//
// An earlier overview drew each line between two boxes along the medoid of its
// edges' routes, where ELK had run them at full detail: on this portal's graph 12
// pairs of arrowheads lay on each other, lines ran 0.8 px apart, 13 of 34 lines
// ran under a title, a count was a label the next line painted over, and a title
// too wide for its box was drawn across the lines above it. The overview now
// routes its lines itself, between the boxes that never move, on tracks a few
// pixels apart, with a straight run into each box and one arrowhead where lines
// share their last run; a count is a pill drawn over every line; a title shrinks
// to fit its box and otherwise stands above it on a plate no line runs under; and
// the lines are light until the pointer rests on a box, which brings that box's
// lines forward and fades the rest.
//
// What the cases cannot see. They read the state the viewer drew, through its
// test handle, and measure it with their own geometry (`support/overview.js`);
// they compare no pixels, so a pill drawn in the wrong colour passes. On the
// adopter-sized graph the whole-graph fit is clamped at the smallest zoom and does
// not fit the canvas, its boxes about 35 by 10 px and every title on a plate
// larger than its box; the owner deferred an overview for such a project (ruling
// 11), so titles, and lines kept from under them, are held on this portal's graph
// only. There a plate can close every way into a box, and the router runs a line
// under it rather than leave the line unrouted.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { canvasBackground, contrastRatio } from "./support/look.js";
import { drawnEdgesOf, levelOf, treeOf } from "./support/map.js";
import {
  arrivalsOf,
  boxOnScreen,
  headsUnderLines,
  narrowestGap,
  overlappingHeads,
  rectsOverlap,
  segmentInRect,
  segmentsOf,
  segmentsOutside,
  sharedArrivals,
} from "./support/overview.js";
import { withTwoMoreEdges } from "./support/perturbedGraph.js";
import { edgesThroughBoxes } from "./support/routeMetrics.js";
import { requireShape } from "./support/shape.js";
import { openThemeModules } from "./support/themeModules.js";
import { architectureData, openArchitecture, viewer, withAncestors } from "./support/viewer.js";

/** The share of the lines that carry more than one edge that have a pill: a short or crowded line may have none. */
const MOST_PILLS = 0.75;
/** How many lines a case hovers to read their counts in the note, those whose pill found no place first. */
const HOVERED_DROPPED = 2;
/** Lines that run beside each other keep at least this far apart at the fit, in pixels. */
const GAP_PX = 5;
/** The sizes a title is tried at on screen, in pixels, the largest first. */
const TITLE_PX = [14, 12.5, 11, 10];
/** A straight run into a box holds an arrowhead and a rounded corner, in pixels. */
const STRAIGHT_RUN_PX = 12;
/** An arrowhead's length on screen, in pixels. */
const HEAD_PX = 6;
/** How far a route's end may lie from its box's border, in layout units. */
const ON_BORDER = 0.5;

/** The graphs the overview is read on: this portal's and an adopter-sized one. */
const GRAPHS = [
  {
    name: "this portal's architecture graph",
    tag: [],
    open: async (page, request) => {
      const data = await architectureData(request);
      await openArchitecture(page);
      return data;
    },
  },
  {
    name: "an adopter-sized architecture graph",
    tag: [ADOPTER_SIZED],
    open: async (page, request) => {
      const data = adopterSizedGraph(await architectureData(request));
      await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      return data;
    },
  },
];

/**
 * Room around the pointer, in pixels, that no other line may enter for a line to
 * be hovered there: Cytoscape takes an edge within 8 px of the pointer, and half
 * a line more. A node is taken only inside its shape, and a title not at all.
 */
const HOVER_CLEAR_PX = 12;
const HOVER_CLEAR_OF_NODES_PX = 4;
/** How many points of a line a case tries the pointer on before it gives the line up. */
const HOVER_TRIES = 6;

/**
 * Points of `look`'s route on the canvas, in pixels, inside the canvas `size`,
 * at least `HOVER_CLEAR_PX` from every one of `segments` (other lines') and
 * `HOVER_CLEAR_OF_NODES_PX` from `rects` (nodes and titles): at most
 * `HOVER_TRIES`, spread along the line.
 */
function clearPointsOn(look, segments, rects, view, size) {
  const points = look.points.map((p) => ({ x: p.x * view.zoom + view.pan.x, y: p.y * view.zoom + view.pan.y }));
  const near = (p, a, b) => {
    const [dx, dy] = [b.x - a.x, b.y - a.y];
    const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1)));
    return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy) < HOVER_CLEAR_PX;
  };
  const found = [];
  for (let k = 1; k < points.length; k += 1) {
    const [a, b] = [points[k - 1], points[k]];
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    // Every point of the line, its ends kept clear by the room from nodes; a straight line is drawn
    // as two segments, so a margin from each segment's ends would leave a short one no point.
    for (let s = 0; s <= length; s += 2) {
      const p = { x: a.x + ((b.x - a.x) * s) / length, y: a.y + ((b.y - a.y) * s) / length };
      if (p.x < HOVER_CLEAR_PX || p.y < HOVER_CLEAR_PX || p.x > size.width - HOVER_CLEAR_PX || p.y > size.height - HOVER_CLEAR_PX) continue;
      if (segments.some((seg) => near(p, seg.a, seg.b))) continue;
      const room = HOVER_CLEAR_OF_NODES_PX;
      if (rects.some((r) => p.x > r.x1 - room && p.x < r.x2 + room && p.y > r.y1 - room && p.y < r.y2 + room)) continue;
      found.push(p);
    }
  }
  const every = Math.max(1, Math.floor(found.length / HOVER_TRIES));
  return found.filter((_, i) => i % every === 0).slice(0, HOVER_TRIES);
}

/**
 * How long the straight run is that ends at the first of `points`, in pixels at
 * `unit` layout units each, through every point on one line with it: `{ run,
 * cornered }`, `cornered` false when the whole line is straight.
 */
function straightRunInto(points, unit) {
  const way = (p, q) => ({ x: Math.sign(Math.round(q.x - p.x)), y: Math.sign(Math.round(q.y - p.y)) });
  const first = way(points[0], points[1]);
  let k = 1;
  while (k + 1 < points.length && JSON.stringify(way(points[k], points[k + 1])) === JSON.stringify(first)) k += 1;
  return { run: Math.hypot(points[k].x - points[0].x, points[k].y - points[0].y) / unit, cornered: k + 1 < points.length };
}

/** The viewer's smallest zoom (the navigation's `minZoom`): a fit held at it does not fit the canvas. */
const MIN_ZOOM = 0.02;

/**
 * The lines the overview's router found no route for, by the id of their
 * aggregated edge, and whether the whole-graph fit is held at the smallest zoom.
 * Every line is routed where the top level fits the canvas; where it does not —
 * the overview the owner deferred (ruling 11) — a small box wedged among others
 * can have no way out that keeps off every other line's arrowhead, and its line
 * is drawn along its medoid. Such lines are reported, and left out of what the
 * cases hold of the router's lines.
 */
async function unroutedLines(page) {
  const clamped = (await viewer(page, "level")).fitZoom <= MIN_ZOOM + 1e-9;
  const failed = new Set((await viewer(page, "overviewPlan")).failed);
  const ids = (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn && failed.has(e.ends.join("\n"))).map((e) => e.id);
  if (ids.length) test.info().annotations.push({ type: "measured", description: `${ids.length} line(s) with no route, drawn along their medoid: ${ids.join(", ")}` });
  return { clamped, ids: new Set(ids) };
}

/** Wait until the page has drawn two more frames. */
const twoFrames = (page) => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));

/** The view the handle reports: the zoom and the pan that put the graph on screen. */
async function viewOf(page) {
  return { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
}

/** Every drawn node's box on screen, by id. */
async function nodeRects(page, view) {
  return Object.fromEntries(Object.entries(await viewer(page, "nodeBoxes")).map(([id, box]) => [id, boxOnScreen(box, view)]));
}

/** The drawn aggregated edges by the name of their pair, "a|b". */
async function drawnAggregates(page) {
  return Object.fromEntries((await viewer(page, "aggregatedEdges")).filter((e) => e.drawn).map((e) => [e.ends.join("|"), e]));
}

/** The nodes at the top of the containment tree: under the box that holds everything, or the roots when none does. */
const topLevelOf = (tree) => Object.keys(tree.parents).filter((id) => id !== tree.wrapper && tree.parents[id] === tree.wrapper).sort();
const centreOf = (r) => ({ x: (r.x1 + r.x2) / 2, y: (r.y1 + r.y2) / 2 });
/** Whether rectangle `r` lies within `box`, half a unit either way. */
const within = (r, box) => r.x1 >= box.x1 - 0.5 && r.x2 <= box.x2 + 0.5 && r.y1 >= box.y1 - 0.5 && r.y2 <= box.y2 + 0.5;

/** `points` without a point in the middle of a straight run: Cytoscape draws a line with no corner through its midpoint. */
function cornersOf(points) {
  const out = [];
  for (const p of points) {
    out.push(p);
    while (out.length >= 3) {
      const [a, b, c] = out.slice(-3);
      if (Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-6) break;
      out.splice(out.length - 2, 1);
    }
  }
  return out;
}

/**
 * What moved of line `line` (`aggregatedEdges`) since it was drawn as `before`,
 * in words: nothing may, but an end at a node of `grown`, drawn larger than its
 * layout, along the line's last run, and onto that node's border in `boxes`.
 */
function movedBeyondItsLastRuns(name, before, line, grown, boxes) {
  const [p, q] = [cornersOf(before.points), cornersOf(line.points)];
  if (p.length !== q.length) return [`${name} has ${q.length} corners and ends, ${p.length} before`];
  const same = (u, v) => Math.abs(u.x - v.x) < 1e-6 && Math.abs(u.y - v.y) < 1e-6;
  const wrong = [];
  for (let k = 1; k < p.length - 1; k += 1) if (!same(p[k], q[k])) wrong.push(`${name} moved its corner ${k}`);
  for (const [k, next, end] of [[0, 1, line.ends[0]], [p.length - 1, p.length - 2, line.ends[1]]]) {
    if (same(p[k], q[k])) continue;
    const along = Math.abs(q[next].x - q[k].x) < 1e-6 ? Math.abs(q[k].x - p[k].x) < 1e-6 : Math.abs(q[k].y - p[k].y) < 1e-6;
    const r = boxes[end];
    const onBorder =
      within({ x1: q[k].x, y1: q[k].y, x2: q[k].x, y2: q[k].y }, r) &&
      Math.min(Math.abs(q[k].x - r.x1), Math.abs(q[k].x - r.x2), Math.abs(q[k].y - r.y1), Math.abs(q[k].y - r.y2)) <= ON_BORDER;
    if (!grown.includes(end) || !along || !onBorder) wrong.push(`${name}'s end at ${end} moved off its last run or off its border`);
  }
  return wrong;
}

for (const graph of GRAPHS) {
  test.describe(`on ${graph.name}`, { tag: graph.tag }, () => {
    test("at the whole-graph fit every line between two top-level ends is routed square from the border of one to the border of the other, through no box", async ({
      page,
      request,
    }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      requireShape(tree.topBoxes.length > 1, "fewer than two boxes at the top of the containment tree");
      const lines = Object.values(await drawnAggregates(page));
      requireShape(lines.length > 0, "no line between two top-level ends");
      const boxes = await viewer(page, "nodeBoxes");
      const unrouted = await unroutedLines(page);
      if (!unrouted.clamped) expect([...unrouted.ids]).toEqual([]);

      const onBorder = (point, box) =>
        point.x >= box.x1 - ON_BORDER && point.x <= box.x2 + ON_BORDER && point.y >= box.y1 - ON_BORDER && point.y <= box.y2 + ON_BORDER &&
        Math.min(Math.abs(point.x - box.x1), Math.abs(point.x - box.x2), Math.abs(point.y - box.y1), Math.abs(point.y - box.y2)) <= ON_BORDER;
      const square = (points) => points.slice(1).every((p, i) => Math.abs(p.x - points[i].x) < ON_BORDER || Math.abs(p.y - points[i].y) < ON_BORDER);
      const off = lines.filter((e) => !square(e.points) || !onBorder(e.points[0], boxes[e.ends[0]]) || !onBorder(e.points[e.points.length - 1], boxes[e.ends[1]]));
      expect(off.map((e) => e.id)).toEqual([]);
      const through = edgesThroughBoxes(lines.map((e) => ({ id: e.id, source: e.ends[0], target: e.ends[1], points: e.points })), boxes, tree.parents);
      expect(through).toEqual([]);
    });

    test("at the whole-graph fit no two arrowheads overlap, no line crosses an arrowhead, lines that share their last run into a box end in one arrowhead, and each stands on a straight run long enough for itself and a corner", async ({
      page,
      request,
    }) => {
      await graph.open(page, request);
      const view = await viewOf(page);
      const unrouted = await unroutedLines(page);
      const looks = (await viewer(page, "lineLooks")).filter((look) => !unrouted.ids.has(look.id));
      requireShape(looks.some((look) => look.aggregated), "no line between two top-level ends");
      const arrivals = arrivalsOf(looks, view);

      expect(overlappingHeads(arrivals)).toEqual([]);
      expect(headsUnderLines(arrivals, segmentsOf(looks, view))).toEqual([]);
      const groups = sharedArrivals(arrivals);
      // One head per shared last run, and a line with a head there never shares it with one without.
      expect(groups.filter((group) => group.filter((a) => a.arrives && a.drawn).length !== (group.some((a) => a.arrives) ? 1 : 0)).map((g) => g.map((a) => a.id).join(" + "))).toEqual([]);
      expect(groups.filter((group) => group.some((a) => a.arrives) && group.some((a) => !a.arrives)).map((g) => g.map((a) => a.id).join(" + "))).toEqual([]);

      // The straight run into each end edges arrive at, in the pixels of the scale the overview is
      // planned at: a head and a corner long, or a head long on a line with no corner at all.
      const { unit } = await viewer(page, "overviewPlan");
      const short = looks
        .filter((look) => look.aggregated)
        .flatMap((look) => [
          ...(look.forward > 0 ? [{ id: `${look.id}:target`, ...straightRunInto([...look.points].reverse(), unit) }] : []),
          ...(look.backward > 0 ? [{ id: `${look.id}:source`, ...straightRunInto(look.points, unit) }] : []),
        ])
        .filter(({ run, cornered }) => run < (cornered ? STRAIGHT_RUN_PX : HEAD_PX) - 1e-6)
        .map(({ id, run }) => `${id}: ${run.toFixed(1)} px`);
      expect(short).toEqual([]);
    });

    test(`at the whole-graph fit lines that run beside each other keep at least ${GAP_PX} px apart`, async ({ page, request }) => {
      await graph.open(page, request);
      const unrouted = await unroutedLines(page);
      const looks = (await viewer(page, "lineLooks")).filter((look) => !unrouted.ids.has(look.id));
      requireShape(looks.filter((look) => look.aggregated).length > 1, "fewer than two lines between top-level ends");

      const gap = narrowestGap(looks, await viewOf(page));
      test.info().annotations.push({ type: "measured", description: `narrowest gap ${gap.minimum.toFixed(2)} px (${gap.closest})` });
      expect(gap.minimum, gap.closest).toBeGreaterThanOrEqual(GAP_PX);
    });

    test("at the whole-graph fit every count above one is on a pill that covers no box, no title, no arrowhead and no other pill, and a line that carries one edge has none", async ({
      page,
      request,
    }) => {
      await graph.open(page, request);
      const view = await viewOf(page);
      const lines = Object.values(await drawnAggregates(page));
      requireShape(lines.some((e) => e.weight > 1), "no line between top-level ends carries more than one edge");
      const { pills, dropped } = await viewer(page, "pills");

      const counted = lines.filter((e) => e.weight > 1).map((e) => e.id).sort();
      expect([...pills.map((p) => p.id), ...dropped].sort()).toEqual(counted);
      const byId = Object.fromEntries(lines.map((e) => [e.id, e]));
      expect(pills.filter((p) => p.text !== byId[p.id].label).map((p) => p.id)).toEqual([]);
      test.info().annotations.push({ type: "measured", description: `${pills.length} pills, ${dropped.length} without a free place` });
      // A line too short for a pill, or crowded by its neighbours' pills, has none; most lines have one.
      expect(pills.length).toBeGreaterThanOrEqual(Math.ceil(MOST_PILLS * counted.length));

      const covered = [];
      // A pill lies inside an open box, the one that holds everything at least, and on no other node.
      const open = new Set(await viewer(page, "openBoxes"));
      const rects = Object.entries(await nodeRects(page, view)).filter(([id]) => !open.has(id));
      for (const pill of pills) {
        for (const [id, box] of rects) if (rectsOverlap(pill, box)) covered.push(`${pill.id} over ${id}`);
        for (const title of await viewer(page, "titles")) if (rectsOverlap(pill, title)) covered.push(`${pill.id} over the title of ${title.id}`);
        for (const other of pills) if (other !== pill && rectsOverlap(pill, other)) covered.push(`${pill.id} over ${other.id}`);
        for (const head of arrivalsOf(await viewer(page, "lineLooks"), view).filter((a) => a.drawn)) {
          if (head.triangle.some((p) => p.x > pill.x1 && p.x < pill.x2 && p.y > pill.y1 && p.y < pill.y2)) covered.push(`${pill.id} over the head of ${head.id}`);
        }
      }
      expect(covered).toEqual([]);
      // Pills are drawn above every line, the followed ones included.
      expect(await viewer(page, "overlayLayers")).toEqual(["followed", "pills"]);

      // A count shows while the pointer is on its line, in the note: a line without a pill is tried
      // first, then the others, at points clear of everything else; one at least is read.
      await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
      await twoFrames(page);
      const canvas = await page.getByTestId("graph-canvas").boundingBox();
      const shown = await viewOf(page);
      const allLooks = await viewer(page, "lineLooks");
      const everyTitle = await viewer(page, "titles");
      const clearOf = [...rects.map(([, r]) => r), ...everyTitle];
      const hovered = [];
      for (const id of [...dropped, ...lines.map((e) => e.id).filter((id) => !dropped.includes(id))]) {
        if (hovered.length >= HOVERED_DROPPED) break;
        const look = allLooks.find((l) => l.id === id);
        // The pointer on the line, at the first point where Cytoscape reports this line and no other.
        let onIt = false;
        for (const point of clearPointsOn(look, segmentsOf(allLooks.filter((l) => l.id !== id), shown), clearOf, shown, canvas)) {
          await page.mouse.move(canvas.x + point.x, canvas.y + point.y);
          await twoFrames(page);
          onIt = JSON.stringify(await viewer(page, "hoveredEdges")) === JSON.stringify([id]);
          if (onIt) break;
        }
        if (!onIt) continue;
        for (const count of [byId[id].forwardKeys.length, byId[id].backwardKeys.length].filter(Boolean)) {
          await expect(page.getByTestId("aggregated-edge-note"), id).toContainText(`${count} edge`);
        }
        hovered.push(id);
        await page.mouse.move(canvas.x + 2, canvas.y + 2);
      }
      test.info().annotations.push({
        type: "measured",
        description: `the count read on hover for ${hovered.length} line(s), ${hovered.filter((id) => dropped.includes(id)).length} of the ${dropped.length} without a pill`,
      });
      expect(hovered.length).toBeGreaterThan(0);
    });

    test("the overview's routes are planned once: a zoom and a box opening move no line between two closed boxes, and a line into a node drawn larger than its layout at most runs on along its last run", async ({
      page,
      request,
    }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      const before = await drawnAggregates(page);
      requireShape(Object.keys(before).length > 1, "fewer than two lines between top-level ends");
      const { grown } = await viewer(page, "overviewPlan");
      // The same zoom draws every line where it was; a box opened lets a node drawn larger than its
      // layout, that an edge of the file is now drawn into, take its laid-out size, and a line into it
      // runs on along its last run to that box's border.
      const moved = async (after) => {
        const boxes = await viewer(page, "nodeBoxes");
        return Object.entries(after)
          .filter(([name]) => before[name])
          .flatMap(([name, line]) => movedBeyondItsLastRuns(name, before[name], line, grown, boxes));
      };

      await page.getByRole("button", { name: "Zoom in", exact: true }).click();
      await page.getByRole("button", { name: "Zoom out", exact: true }).click();
      await twoFrames(page);
      const again = await drawnAggregates(page);
      expect(Object.keys(again).filter((name) => before[name] && JSON.stringify(again[name].points) !== JSON.stringify(before[name].points))).toEqual([]);

      // The box with the most lines opened: every line between two other boxes keeps its route.
      const lines = Object.values(before);
      const busiest = tree.topBoxes.map((id) => [id, lines.filter((e) => e.ends.includes(id)).length]).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0][0];
      await page.evaluate((id) => window.__beadloomViewer.revealNodes([id]), busiest);
      await expect.poll(async () => (await viewer(page, "openBoxes")).includes(busiest)).toBe(true);
      const others = Object.fromEntries(Object.entries(await drawnAggregates(page)).filter(([, e]) => !e.ends.some((end) => withAncestors([end], tree.parents).has(busiest))));
      requireShape(Object.keys(others).length > 0, "every line between top-level ends touches the busiest box");
      expect(await moved(others)).toEqual([]);
    });
  });
}

/** This portal's graph with two edges more: the same graph, laid out another way (`support/perturbedGraph.js`). */
const PERTURBED = {
  name: "this portal's architecture graph with two edges more",
  tag: [],
  open: async (page, request) => {
    const more = withTwoMoreEdges(await architectureData(request));
    requireShape(Boolean(more), "no two leaves in two other top-level boxes than a third leaf's");
    await page.route("**/architecture.data.json", (route) => route.fulfill({ json: more.data }));
    await openArchitecture(page);
    return more.data;
  },
};

// The box that holds everything is drawn with a visible frame, so a line that
// leaves it to reach a sibling box and comes back in reads as leaving the
// project. Before, the router's tracks reached six pitches past the outermost
// boxes, and on this portal a line ran round the outside of the frame on its
// right. A pair the router cannot route inside the frame is named, with a count,
// by the case on unrouted lines above; it is never routed outside.
for (const graph of [...GRAPHS, PERTURBED]) {
  test(`at the whole-graph fit every line runs inside the frame of the box that holds everything, on ${graph.name}`, { tag: graph.tag }, async ({
    page,
    request,
  }) => {
    const tree = treeOf(await graph.open(page, request));
    requireShape(Boolean(tree.wrapper), "no box that holds every node");
    const view = await viewOf(page);
    const frame = (await viewer(page, "nodeBoxes"))[tree.wrapper];
    const frameWidth = (await viewer(page, "nodeLooks")).find((look) => look.id === tree.wrapper).borderWidth * view.zoom;
    const looks = await viewer(page, "lineLooks");
    requireShape(looks.length > 0, "no line drawn at the whole-graph fit");
    const { failed } = await viewer(page, "overviewPlan");

    const outside = segmentsOutside(looks, frame, view, frameWidth);
    test.info().annotations.push({
      type: "measured",
      description: `${outside.length} of ${looks.reduce((sum, look) => sum + look.points.length - 1, 0)} segments of ${looks.length} lines outside the frame; ${failed.length} pair(s) with no route inside it`,
    });
    expect(outside).toEqual([]);
  });
}

test("every closed box and every top-level node at the fit is titled readably: at 14, 12.5, 11 or 10 px inside it, or beside it on a plate with a border that nothing covers and no line runs under", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const view = await viewOf(page);
  const top = Object.keys(tree.parents).filter((id) => id !== tree.wrapper && tree.parents[id] === tree.wrapper);
  const titles = await viewer(page, "titles");
  // Every closed box takes the map's title; a top-level node that is not a box keeps its own label
  // where that reads larger, and then reads at no less than the smallest size a title is tried at.
  const closed = (await viewer(page, "level")).collapsed.map((b) => b.id);
  expect(closed.filter((id) => !titles.some((t) => t.id === id))).toEqual([]);
  const own = (await viewer(page, "nodeLooks")).filter((look) => top.includes(look.id) && !titles.some((t) => t.id === look.id));
  expect(own.filter((look) => look.fontSize * view.zoom < Math.min(...TITLE_PX) - 1e-6).map((look) => look.id)).toEqual([]);
  requireShape(titles.length > 0, "no closed box or top-level node takes the map's title at the fit");

  // A title is fitted at the scale the overview was planned at, and keeps that size in the graph's
  // units when the view is further out: where the fit lands one step coarser than the plan's own
  // (the fit counts the lines and the panel too), a title is drawn that much smaller.
  const step = Math.sqrt(1.25);
  const { unit } = await viewer(page, "overviewPlan");
  const shrink = Math.min(1, unit / (await viewer(page, "level")).scale);
  const wrong = titles.filter((t) => {
    const wanted = t.sizePx * shrink;
    return !TITLE_PX.includes(t.sizePx) || t.fontSize < wanted / step - 1e-6 || t.fontSize > wanted * step + 1e-6;
  });
  expect(wrong.map((t) => `${t.id}: ${t.sizePx} px drawn at ${t.fontSize.toFixed(2)}`)).toEqual([]);
  const rects = await nodeRects(page, view);
  const inside = (r, box) => r.x1 >= box.x1 - 0.5 && r.x2 <= box.x2 + 0.5 && r.y1 >= box.y1 - 0.5 && r.y2 <= box.y2 + 0.5;
  expect(titles.filter((t) => t.inside && !inside(t, rects[t.id])).map((t) => t.id)).toEqual([]);
  // A title outside its box stands on an opaque plate with a border on one side of the box, clear of it.
  const besideBox = (t, box) => t.y2 <= box.y1 + 0.5 || t.y1 >= box.y2 - 0.5 || t.x2 <= box.x1 + 0.5 || t.x1 >= box.x2 - 0.5;
  expect(titles.filter((t) => !t.inside && (t.plate.opacity < 1 || !(t.plate.borderWidth > 0) || !besideBox(t, rects[t.id]))).map((t) => t.id)).toEqual([]);
  // Nothing covers a title: no other node, no other title.
  const covered = titles.flatMap((t) => [
    ...Object.entries(rects).filter(([id]) => id !== t.id && id !== tree.wrapper && rectsOverlap(t, rects[id])).map(([id]) => `${t.id} under ${id}`),
    ...titles.filter((o) => o !== t && rectsOverlap(t, o)).map((o) => `${t.id} under the title of ${o.id}`),
  ]);
  expect(covered).toEqual([]);
  const segments = segmentsOf(await viewer(page, "lineLooks"), view);
  const underTitles = titles.filter((t) => !t.inside).flatMap((t) => segments.filter((s) => segmentInRect(s.a, s.b, t, 1)).map((s) => `${s.id} under ${t.id}`));
  expect(underTitles).toEqual([]);
});

test("zoomed out from the fit, no line runs under a title: a title keeps to the room the routes left it", async ({ page }) => {
  await openArchitecture(page);
  requireShape((await viewer(page, "titles")).length > 0, "no closed box or top-level node is titled at the fit");
  for (let step = 0; step < ZOOM_OUT_STEPS; step += 1) await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await twoFrames(page);

  const titles = await viewer(page, "titles");
  const segments = segmentsOf(await viewer(page, "lineLooks"), await viewOf(page));
  const under = titles.filter((t) => !t.inside).flatMap((t) => segments.filter((s) => segmentInRect(s.a, s.b, t, 1)).map((s) => `${s.id} under ${t.id}`));
  expect(under).toEqual([]);
});

test("at the fit, and zoomed out from it, the title of the box that holds everything reads at a title's size, inside it or on a plate above it that no node covers and no line runs under", async ({
  page,
  request,
}) => {
  const tree = treeOf(await architectureData(request));
  requireShape(Boolean(tree.wrapper), "no box that holds every node");
  await openArchitecture(page);
  const wrong = [];
  const look = async (state) => {
    const view = await viewOf(page);
    const title = (await viewer(page, "boxTitles")).find((t) => t.id === tree.wrapper);
    if (!title) return wrong.push(`${state}: no title drawn`);
    // Fitted at the scale the overview was planned at, as every title is, so one step coarser where the fit lands past it.
    const shrink = Math.min(1, (await viewer(page, "overviewPlan")).unit / (await viewer(page, "level")).scale);
    if (title.fontSize < (Math.min(...TITLE_PX) * shrink) / Math.sqrt(1.25) - 1e-6) wrong.push(`${state}: drawn at ${title.fontSize.toFixed(2)} px`);
    const rects = await nodeRects(page, view);
    wrong.push(...Object.keys(rects).filter((id) => id !== tree.wrapper && rectsOverlap(title, rects[id])).map((id) => `${state}: under ${id}`));
    const segments = segmentsOf(await viewer(page, "lineLooks"), view);
    wrong.push(...[...new Set(segments.filter((s) => segmentInRect(s.a, s.b, title, 1)).map((s) => s.id))].map((id) => `${state}: ${id} under it`));
    test.info().annotations.push({ type: "measured", description: `${state}: ${tree.wrapper}'s title ${title.fontSize.toFixed(1)} px${title.plate ? " on a plate" : ""}` });
  };
  await look("at the fit");
  for (let step = 0; step < ZOOM_OUT_STEPS; step += 1) await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await twoFrames(page);
  await look(`${ZOOM_OUT_STEPS} steps out`);
  expect(wrong).toEqual([]);
});

/** The room a title keeps from its box's edges, in pixels on screen; a line of a title is this share of its size tall. */
const TITLE_INSET_PX = 6;
const TITLE_LINE_HEIGHT = 1.25;
/** What a status mark takes at each end of a title's line, at most, in pixels: the mark and its inset from the corner. */
const MARK_ROOM_PX = 7 + 4;
/** A plate's padding and border around its title, in pixels at the size the plate was laid out at. */
const PLATE_FRAME_PX = 3 + 1;
/** The least room a box drawn larger than its layout keeps from every other box, in pixels. */
const NEIGHBOUR_GAP_PX = 3;


test("at the fit every top-level node is a box with its title inside: one too small for its title is drawn larger, centred on its laid-out box and clear of every other box, and a title stands on a plate only where even the smallest box for it would come within a few pixels of another", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const view = await viewOf(page);
  const top = topLevelOf(tree);
  const drawn = await nodeRects(page, view);
  const { boxes: elk } = await viewer(page, "elkGeometry");
  const laid = Object.fromEntries(top.filter((id) => elk[id]).map((id) => [id, boxOnScreen(elk[id], view)]));
  const titles = Object.fromEntries((await viewer(page, "titles")).map((t) => [t.id, t]));
  requireShape(top.some((id) => titles[id]), "no top-level node takes the map's title at the fit");
  const marked = new Set((await viewer(page, "nodeLooks")).filter((look) => look.status).map((look) => look.id));

  // A box drawn larger than its layout holds its laid-out box and shares its centre: no node moves.
  const off = Object.keys(laid).filter((id) => {
    const [a, b] = [centreOf(laid[id]), centreOf(drawn[id])];
    return !within(laid[id], drawn[id]) || Math.hypot(a.x - b.x, a.y - b.y) > 0.5;
  });
  expect(off).toEqual([]);
  // No two top-level boxes overlap, and none covers another's title.
  const overlapping = top.flatMap((id, k) => top.slice(k + 1).filter((other) => rectsOverlap(drawn[id], drawn[other], 0.5)).map((other) => `${id} and ${other}`));
  expect(overlapping).toEqual([]);
  const covered = Object.values(titles).flatMap((t) => top.filter((id) => id !== t.id && rectsOverlap(t, drawn[id], 0.5)).map((id) => `the title of ${t.id} under ${id}`));
  expect(covered).toEqual([]);

  // The smallest box that holds a title on a plate inside it at the smallest size, centred where its
  // node is: its text, its inset from the box's edges, and the room of a status mark at each end.
  const smallestBoxOf = (id) => {
    const t = titles[id];
    const frame = PLATE_FRAME_PX * (t.fontSize / t.sizePx);
    const text = (t.x2 - t.x1 - 2 * frame) * (Math.min(...TITLE_PX) / t.fontSize);
    const width = text + 2 * (marked.has(id) ? MARK_ROOM_PX : TITLE_INSET_PX);
    const height = String(t.text).split("\n").length * TITLE_LINE_HEIGHT * Math.min(...TITLE_PX) + TITLE_INSET_PX;
    const { x, y } = centreOf(drawn[id]);
    return { x1: x - width / 2, y1: y - height / 2, x2: x + width / 2, y2: y + height / 2 };
  };
  const crowded = (id) => {
    const r = smallestBoxOf(id);
    const reach = { x1: r.x1 - NEIGHBOUR_GAP_PX, y1: r.y1 - NEIGHBOUR_GAP_PX, x2: r.x2 + NEIGHBOUR_GAP_PX, y2: r.y2 + NEIGHBOUR_GAP_PX };
    return top.some((other) => other !== id && rectsOverlap(reach, drawn[other]));
  };
  const outside = top.filter((id) => titles[id] && !(titles[id].inside && within(titles[id], drawn[id])));
  test.info().annotations.push({
    type: "measured",
    description: `${top.filter((id) => titles[id]).length - outside.length} of ${top.filter((id) => titles[id]).length} top-level titles inside their box; on a plate: ${outside.join(", ") || "none"}`,
  });
  expect(outside.filter((id) => !crowded(id))).toEqual([]);
  // The plan names the plates it stood titles on, and they are the ones drawn.
  expect((await viewer(page, "overviewPlan")).plates).toEqual(outside);
});

/** How many toolbar steps a case zooms in, at most, for a box drawn larger than its layout to meet it. */
const MEETING_STEPS = 16;

test("zoomed in from the fit, a node drawn larger than its layout keeps its centre and, while the level stays, about its size on screen and its title inside, until its laid-out box is as large; its lines keep their routes, a last run into it only longer along itself and ending on its border", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const top = topLevelOf(tree);
  const { boxes: elk } = await viewer(page, "elkGeometry");
  const larger = (boxes) => top.filter((id) => elk[id] && boxes[id] && ["x1", "y1", "x2", "y2"].some((side) => Math.abs(boxes[id][side] - elk[id][side]) > ON_BORDER));
  const grown = larger(await viewer(page, "nodeBoxes"));
  requireShape(grown.length > 0, "no top-level node is drawn larger than its layout at the fit");
  const atFit = await drawnAggregates(page);
  const sizeOnScreen = (box, zoom) => ({ width: (box.x2 - box.x1) * zoom, height: (box.y2 - box.y1) * zoom });
  /** What a step is compared with: the zoom, the boxes open, and each node's size on screen, its title's text and whether an edge of the file is drawn into it. */
  const stateAt = async () => {
    const zoom = await viewer(page, "zoom");
    const boxes = await viewer(page, "nodeBoxes");
    const titles = Object.fromEntries((await viewer(page, "titles")).map((t) => [t.id, t]));
    const ownLines = (await viewer(page, "edgeRoutes")).filter((r) => !r.aggregated);
    const nodes = Object.fromEntries(
      grown.filter((id) => boxes[id]).map((id) => [id, { size: sizeOnScreen(boxes[id], zoom), text: titles[id]?.text ?? null, own: ownLines.some((r) => r.source === id || r.target === id) }])
    );
    return { zoom, boxes, titles, open: JSON.stringify(await viewer(page, "openBoxes")), nodes };
  };

  const wrong = [];
  const resized = [];
  let last = await stateAt();
  let still = grown;
  for (let step = 1; step <= MEETING_STEPS && still.length; step += 1) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
    const now = await stateAt();
    const view = await viewOf(page);
    for (const id of grown.filter((id) => now.nodes[id])) {
      const box = now.boxes[id];
      const [a, b] = [centreOf(box), centreOf(elk[id])];
      if (!within(elk[id], box) || Math.hypot(a.x - b.x, a.y - b.y) > ON_BORDER) wrong.push(`step ${step}: ${id} does not hold its laid-out box around its centre`);
      // An edge of the file drawn as itself into it ends on its laid-out border: the node is drawn at that size.
      if (now.nodes[id].own) {
        if (larger(now.boxes).includes(id)) wrong.push(`step ${step}: ${id} is drawn larger than its layout with an edge drawn as itself into it`);
        continue;
      }
      const title = now.titles[id];
      if (title && !(title.inside && within(title, boxOnScreen(box, view)))) wrong.push(`step ${step}: ${id}'s title is outside its box`);
      // While the level stays — the same boxes open, the same title, no edge drawn into it — on screen
      // it neither shrinks nor grows faster than the zoom: no step reads as a move. A level that changes
      // can give its title a line or take one, or draw an edge into it, and its box follows.
      const before = last.nodes[id];
      const size = now.nodes[id].size;
      if (!before || before.own || before.text !== now.nodes[id].text || last.open !== now.open) {
        if (before && ["width", "height"].some((side) => Math.abs(size[side] - before.size[side] * (now.zoom / last.zoom)) > 0.5)) resized.push(`step ${step}: ${id}`);
        continue;
      }
      for (const side of ["width", "height"]) {
        if (size[side] < before.size[side] - 0.5 || size[side] > before.size[side] * (now.zoom / last.zoom) + 0.5) wrong.push(`step ${step}: ${id}'s ${side} ${before.size[side].toFixed(1)} -> ${size[side].toFixed(1)} px`);
      }
    }
    // A line between two top-level ends keeps its route; only an end at a node drawn larger than its
    // layout may move, along its last run, and it ends on that node's border.
    for (const [name, line] of Object.entries(await drawnAggregates(page))) {
      if (atFit[name]) wrong.push(...movedBeyondItsLastRuns(name, atFit[name], line, grown, now.boxes).map((what) => `step ${step}: ${what}`));
    }
    still = larger(now.boxes);
    last = now;
  }
  test.info().annotations.push({
    type: "measured",
    description: `${grown.join(", ")} drawn larger at the fit; ${still.length ? `still larger after ${MEETING_STEPS} steps: ${still.join(", ")}` : "every one met its laid-out box"}; resized where the level changed: ${resized.join(", ") || "none"}`,
  });
  expect(wrong).toEqual([]);
  expect(still).toEqual([]);
});

test("calm by default: hovering a box draws its lines and pills in front and fades every other line and pill; the pointer gone, all are back at rest", async ({
  page,
}) => {
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await twoFrames(page);
  const lines = Object.values(await drawnAggregates(page));
  const counts = new Map();
  for (const e of lines) for (const end of e.ends) counts.set(end, (counts.get(end) || 0) + 1);
  const [box] = [...counts].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0] || [];
  requireShape(Boolean(box) && lines.some((e) => !e.ends.includes(box)), "no top-level box with lines beside lines of others");
  const rest = Object.fromEntries((await viewer(page, "lineLooks")).map((look) => [look.id, look]));
  expect(Object.values(rest).filter((look) => look.front || look.behind).map((look) => look.id)).toEqual([]);

  const r = (await viewer(page, "boxes"))[box];
  await page.mouse.move((r.x1 + r.x2) / 2, (r.y1 + r.y2) / 2);
  const own = lines.filter((e) => e.ends.includes(box)).map((e) => e.id).sort();
  await expect.poll(async () => (await viewer(page, "followed")).edges.map((e) => e.id).sort()).toEqual(own);
  const looks = await viewer(page, "lineLooks");
  expect(looks.filter((look) => own.includes(look.id) !== look.front).map((look) => look.id)).toEqual([]);
  expect(looks.filter((look) => !own.includes(look.id) && !look.behind).map((look) => look.id)).toEqual([]);
  const background = await canvasBackground(page);
  const brighter = looks.filter((look) => look.behind && contrastRatio(look.colour, background) >= contrastRatio(rest[look.id].colour, background));
  expect(brighter.map((look) => look.id)).toEqual([]);
  const { pills } = await viewer(page, "pills");
  expect(pills.filter((p) => own.includes(p.id) === p.faded).map((p) => p.id)).toEqual([]);

  await page.mouse.move(2, 2);
  await expect.poll(async () => (await viewer(page, "followed")).edges).toEqual([]);
  expect((await viewer(page, "lineLooks")).filter((look) => look.front || look.behind).map((look) => look.id)).toEqual([]);
  expect((await viewer(page, "pills")).pills.filter((p) => p.faded).map((p) => p.id)).toEqual([]);
});

/** How many zoom steps a case takes at most before it gives up. */
const ZOOM_STEPS = 6;
/** How far out from the fit a case zooms, in steps of the toolbar's zoom (1.25 each): to about two thirds. */
const ZOOM_OUT_STEPS = 2;

test("a closed box large enough to say it says how many edges come in and how many go out, inside it and clear of its title", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  // Zoomed in until a box is large enough, or as far as the steps allow.
  const saying = async () => Object.values(await viewer(page, "boxTallies")).some((t) => t.shown);
  for (let step = 0; step < ZOOM_STEPS && !(await saying()); step += 1) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
  }
  const expected = levelOf(tree, new Set(), drawnEdgesOf(data));
  const tally = new Map();
  for (const pair of expected.pairs.values()) {
    const [a, b] = pair.ends;
    const add = (id, incoming, outgoing) => {
      const now = tally.get(id) || { incoming: 0, outgoing: 0 };
      tally.set(id, { incoming: now.incoming + incoming, outgoing: now.outgoing + outgoing });
    };
    add(a, pair.backward.length, pair.forward.length);
    add(b, pair.forward.length, pair.backward.length);
  }
  const shown = await viewer(page, "boxTallies");
  const closed = (await viewer(page, "level")).collapsed.map((b) => b.id);
  expect(Object.keys(shown).sort()).toEqual(closed.filter((id) => tally.has(id)).sort());
  expect(Object.entries(shown).filter(([id, t]) => t.incoming !== tally.get(id).incoming || t.outgoing !== tally.get(id).outgoing).map(([id]) => id)).toEqual([]);
  const said = Object.entries(shown).filter(([, t]) => t.shown);
  requireShape(said.length > 0, `no closed box is large enough to say its edges within ${ZOOM_STEPS} zoom steps of the fit`);

  const rects = await nodeRects(page, await viewOf(page));
  const titles = Object.fromEntries((await viewer(page, "titles")).map((t) => [t.id, t]));
  const wrong = said.filter(([id, t]) => {
    const box = rects[id];
    const within = t.x1 >= box.x1 && t.x2 <= box.x2 && t.y1 >= box.y1 && t.y2 <= box.y2;
    return t.text !== `in ${t.incoming} · out ${t.outgoing}` || !within || rectsOverlap(t, titles[id]);
  });
  expect(wrong.map(([id]) => id)).toEqual([]);
});

/** Plan `input` with the shipped router, in the page. */
function plan(page, input) {
  return page.evaluate(async (given) => {
    const { planOverview } = await import("/widgets/graph-viewer/lib/overviewRoutes.js");
    const { paths, failed } = planOverview(given);
    return { paths: Object.fromEntries(paths), failed };
  }, input);
}

const box = (id, x1, y1, x2, y2) => ({ id, x1, y1, x2, y2 });
const lengthOf = (a, b) => Math.hypot(b.x - a.x, b.y - a.y);

test("a planned line leaves one box and reaches the other on their borders, with a straight run into each long enough for an arrowhead and a corner", async ({
  page,
}) => {
  await openThemeModules(page);
  // Two boxes offset both ways, so the line has to bend.
  const input = {
    unit: 1,
    boxes: [box("a", 0, 0, 60, 30), box("b", 200, 150, 260, 180)],
    pairs: [{ name: "a\nb", a: "a", b: "b", forward: 3, backward: 1 }],
  };
  const { paths, failed } = await plan(page, input);
  expect(failed).toEqual([]);
  const path = paths["a\nb"];
  const onBorderOf = (p, b) => (p.x === b.x1 || p.x === b.x2 || p.y === b.y1 || p.y === b.y2) && p.x >= b.x1 && p.x <= b.x2 && p.y >= b.y1 && p.y <= b.y2;
  expect(onBorderOf(path[0], input.boxes[0])).toBe(true);
  expect(onBorderOf(path[path.length - 1], input.boxes[1])).toBe(true);
  expect(path.length).toBeGreaterThan(2);
  expect(lengthOf(path[0], path[1])).toBeGreaterThanOrEqual(STRAIGHT_RUN_PX);
  expect(lengthOf(path[path.length - 2], path[path.length - 1])).toBeGreaterThanOrEqual(STRAIGHT_RUN_PX);
});

test("a title plate is routed around and no line ends on it: the line ends on its box's border", async ({ page }) => {
  await openThemeModules(page);
  // b's title stands on a plate to its left, right across the straight way from a, level with it.
  const plate = { x1: 110, y1: 100, x2: 196, y2: 130 };
  const input = {
    unit: 1,
    boxes: [box("a", 0, 100, 40, 130), box("b", 200, 100, 240, 130)],
    plates: [plate],
    pairs: [{ name: "a\nb", a: "a", b: "b", forward: 1, backward: 0 }],
  };
  const { paths, failed } = await plan(page, input);
  expect(failed).toEqual([]);
  const path = paths["a\nb"];
  const under = path.slice(1).filter((p, k) => segmentInRect(path[k], p, plate, 0.01));
  expect(under).toEqual([]);
  const end = path[path.length - 1];
  const b = input.boxes[1];
  expect(end.x >= b.x1 && end.x <= b.x2 && end.y >= b.y1 && end.y <= b.y2).toBe(true);
});

test("a box drawn larger than its laid-out box is routed around, and a line into it runs straight through the room it adds and ends on the laid-out border", async ({
  page,
}) => {
  await openThemeModules(page);
  // b is laid out 10 by 4 and drawn 60 by 24 around it, to hold its title; a stands to its left, c above it.
  const core = { x1: 225, y1: 110, x2: 235, y2: 114 };
  const drawnB = { x1: 200, y1: 100, x2: 260, y2: 124 };
  const input = {
    unit: 1,
    boxes: [box("a", 0, 100, 40, 130), { ...box("b", drawnB.x1, drawnB.y1, drawnB.x2, drawnB.y2), core }, box("c", 140, 0, 180, 30)],
    pairs: [
      { name: "a\nb", a: "a", b: "b", forward: 1, backward: 0 },
      { name: "b\nc", a: "b", b: "c", forward: 1, backward: 1 },
    ],
  };
  const { paths, failed } = await plan(page, input);
  expect(failed).toEqual([]);
  const wrong = [];
  for (const [name, path] of Object.entries(paths)) {
    // The line from its end at b: on the laid-out border, then straight out across the drawn box.
    const fromB = name.endsWith("\nb") ? [...path].reverse() : path;
    const [end, next] = [fromB[0], fromB[1]];
    const onCore = end.x >= core.x1 && end.x <= core.x2 && end.y >= core.y1 && end.y <= core.y2 && [end.x - core.x1, core.x2 - end.x, end.y - core.y1, core.y2 - end.y].some((d) => Math.abs(d) < 1e-6);
    if (!onCore) wrong.push(`${name} ends at (${end.x}, ${end.y}), not on b's laid-out border`);
    const straightOut = (Math.abs(next.x - end.x) < 1e-6 && (end.y === core.y1 ? next.y <= drawnB.y1 : next.y >= drawnB.y2)) || (Math.abs(next.y - end.y) < 1e-6 && (end.x === core.x1 ? next.x <= drawnB.x1 : next.x >= drawnB.x2));
    if (!straightOut) wrong.push(`${name}'s last run into b does not run straight across the drawn box`);
    if (fromB.slice(2).some((p, k) => segmentInRect(fromB[k + 1], p, drawnB, 0.01))) wrong.push(`${name} runs through the drawn box`);
  }
  expect(wrong).toEqual([]);
});

test("a frame is an outer wall: every line runs inside it, clear of it, and a pair with no way inside is named, not routed outside", async ({ page }) => {
  await openThemeModules(page);
  // a and b stand against the frame's left and right walls; c stands between them, from the top wall down.
  const frame = { x1: 0, y1: 0, x2: 300, y2: 200 };
  const sides = [box("a", 2, 80, 40, 120), box("b", 260, 80, 298, 120)];
  const pairs = [{ name: "a\nb", a: "a", b: "b", forward: 1, backward: 0 }];
  const wrong = [];
  for (const bottom of [150, 198]) {
    const input = { unit: 1, frame, boxes: [...sides, box("c", 60, 2, 240, bottom)], pairs };
    const { paths, failed } = await plan(page, input);
    // Half a pitch, the room every box keeps from a line, is kept from the frame too.
    const room = 4;
    const outside = Object.values(paths).flatMap((path) => path.filter((p) => p.x < frame.x1 + room || p.x > frame.x2 - room || p.y < frame.y1 + room || p.y > frame.y2 - room));
    if (outside.length) wrong.push(`c down to ${bottom}: ${outside.length} point(s) within ${room} px of the frame or past it`);
    const expected = bottom < frame.y2 - 2 * room ? [] : ["a\nb"];
    if (JSON.stringify(failed) !== JSON.stringify(expected)) wrong.push(`c down to ${bottom}: failed ${JSON.stringify(failed)}, wanted ${JSON.stringify(expected)}`);
  }
  expect(wrong).toEqual([]);
});

test("a straight line with an arrowhead at each end is at least two arrowheads long, however near its two boxes stand", async ({ page }) => {
  await openThemeModules(page);
  const short = [];
  for (let gap = 4; gap <= 16; gap += 1) {
    const input = { unit: 1, boxes: [box("a", 0, 0, 60, 30), box("b", 0, 30 + gap, 60, 60 + gap)], pairs: [{ name: "a\nb", a: "a", b: "b", forward: 2, backward: 1 }] };
    const { paths, failed } = await plan(page, input);
    expect(failed, `boxes ${gap} px apart`).toEqual([]);
    const path = paths["a\nb"];
    const run = straightRunInto(path, 1);
    if (!run.cornered && run.run < 2 * HEAD_PX) short.push(`boxes ${gap} px apart: a straight line ${run.run.toFixed(1)} px long`);
  }
  expect(short).toEqual([]);
});

/**
 * A layout of 30 small boxes in a jittered grid and 45 lines between them, made
 * from `seed`: boxes 3 to 42 px wide and 3 to 16 px tall, so many are too small
 * for a track of their own and get one forced through their middles.
 */
function smallBoxesLayout(seed) {
  let state = seed >>> 0;
  const random = () => (state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 4294967296;
  const boxes = [];
  for (let row = 0; row < 5; row += 1) {
    for (let column = 0; column < 6; column += 1) {
      const [w, h] = [3 + Math.floor(random() * 40), 3 + Math.floor(random() * 14)];
      const [x, y] = [column * 70 + Math.floor(random() * 20), row * 50 + Math.floor(random() * 15)];
      boxes.push(box(`b${row}${column}`, x, y, x + w, y + h));
    }
  }
  const pairs = [];
  const seen = new Set();
  while (pairs.length < 45) {
    const [a, b] = [boxes[Math.floor(random() * boxes.length)].id, boxes[Math.floor(random() * boxes.length)].id].sort();
    if (a === b || seen.has(`${a}\n${b}`)) continue;
    seen.add(`${a}\n${b}`);
    const forward = random() < 0.7 ? 1 : 0;
    const backward = random() < 0.5 ? 1 : 0;
    pairs.push({ name: `${a}\n${b}`, a, b, forward: forward || (backward ? 0 : 1), backward });
  }
  return { unit: 1, boxes, pairs };
}

/** A seed whose layout has three tracks within a lane of each other, where a rule that looked only at the next track let two lines run 4 px apart. */
const CROWDED_TRACKS_SEED = 3;

test(`where several tracks lie within a lane of each other, they carry one line between them: no two lines run closer than ${GAP_PX} px`, async ({
  page,
}) => {
  await openThemeModules(page);
  const { paths } = await plan(page, smallBoxesLayout(CROWDED_TRACKS_SEED));
  const gap = narrowestGap(Object.entries(paths).map(([id, points]) => ({ id, points })), { zoom: 1, pan: { x: 0, y: 0 } });
  expect(gap.minimum, gap.closest).toBeGreaterThanOrEqual(GAP_PX);
});

test("lines that reach a crowded box share their last run only with lines that agree on having an arrowhead there", async ({
  page,
}) => {
  await openThemeModules(page);
  // Sixteen boxes on a ring around a small one with a few ports a side: lines must share them.
  const centre = box("hub", 0, 0, 30, 30);
  const ring = Array.from({ length: 16 }, (_, k) => {
    const angle = (2 * Math.PI * k) / 16;
    const [x, y] = [15 + 140 * Math.cos(angle), 15 + 140 * Math.sin(angle)];
    return box(`r${String(k).padStart(2, "0")}`, x - 6, y - 6, x + 6, y + 6);
  });
  // Every other line carries its edges into the hub; the rest carry them out of it.
  const pairs = ring.map((r, k) => ({ name: `hub\n${r.id}`, a: "hub", b: r.id, forward: k % 2 ? 1 : 0, backward: k % 2 ? 0 : 1 }));
  const { paths, failed } = await plan(page, { unit: 1, boxes: [centre, ...ring], pairs });
  expect(failed).toEqual([]);

  // Each line's end at the hub, and whether its edges arrive there.
  const ends = Object.entries(paths).map(([name, path]) => ({ name, at: path[0], arrives: pairs.find((p) => p.name === name).backward > 0 }));
  const byPoint = new Map();
  for (const end of ends) {
    const key = `${end.at.x.toFixed(3)},${end.at.y.toFixed(3)}`;
    byPoint.set(key, [...(byPoint.get(key) || []), end]);
  }
  const shared = [...byPoint.values()].filter((group) => group.length > 1);
  expect(shared.length).toBeGreaterThan(0);
  expect(shared.filter((group) => new Set(group.map((end) => end.arrives)).size > 1).map((g) => g.map((e) => e.name).join(" + "))).toEqual([]);
});
