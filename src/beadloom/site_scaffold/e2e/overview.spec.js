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
import { ENVIRONMENT, boundHere } from "./support/environment.js";
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
  sharedArrivals,
} from "./support/overview.js";
import { edgesThroughBoxes } from "./support/routeMetrics.js";
import { requireShape } from "./support/shape.js";
import { openThemeModules } from "./support/themeModules.js";
import { architectureData, openArchitecture, viewer, withAncestors } from "./support/viewer.js";

/** The share of the lines that carry more than one edge that have a pill: a short or crowded line may have none. */
const MOST_PILLS = 0.75;
/** How many lines whose pill found no place a case hovers, to read their counts in the note. */
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
/** The longest planning the overview may take, in ms, per graph and environment. */
const PLAN_BUDGET_MS = {
  own: { local: 50, ci: 200 },
  adopter: { local: 250, ci: 1000 },
};

/** The graphs the overview is read on: this portal's and an adopter-sized one. */
const GRAPHS = [
  {
    name: "this portal's architecture graph",
    key: "own",
    tag: [],
    open: async (page, request) => {
      const data = await architectureData(request);
      await openArchitecture(page);
      return data;
    },
  },
  {
    name: "an adopter-sized architecture graph",
    key: "adopter",
    tag: [ADOPTER_SIZED],
    open: async (page, request) => {
      const data = adopterSizedGraph(await architectureData(request));
      await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
      await openArchitecture(page);
      return data;
    },
  },
];

/** Room around the pointer, in pixels, that no other line, node or title may enter for a line to be hovered there. */
const HOVER_CLEAR_PX = 6;

/**
 * A point of `look`'s route on the canvas, in pixels, inside the canvas `size`
 * and at least `HOVER_CLEAR_PX` from every one of `segments` (other lines') and
 * `rects` (nodes and titles), or null when the line has none.
 */
function clearPointOn(look, segments, rects, view, size) {
  const points = look.points.map((p) => ({ x: p.x * view.zoom + view.pan.x, y: p.y * view.zoom + view.pan.y }));
  const near = (p, a, b) => {
    const [dx, dy] = [b.x - a.x, b.y - a.y];
    const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1)));
    return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy) < HOVER_CLEAR_PX;
  };
  for (let k = 1; k < points.length; k += 1) {
    const [a, b] = [points[k - 1], points[k]];
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    for (let s = HOVER_CLEAR_PX; s < length - HOVER_CLEAR_PX; s += 2) {
      const p = { x: a.x + ((b.x - a.x) * s) / length, y: a.y + ((b.y - a.y) * s) / length };
      if (p.x < HOVER_CLEAR_PX || p.y < HOVER_CLEAR_PX || p.x > size.width - HOVER_CLEAR_PX || p.y > size.height - HOVER_CLEAR_PX) continue;
      if (segments.some((seg) => near(p, seg.a, seg.b))) continue;
      if (rects.some((r) => p.x > r.x1 - HOVER_CLEAR_PX && p.x < r.x2 + HOVER_CLEAR_PX && p.y > r.y1 - HOVER_CLEAR_PX && p.y < r.y2 + HOVER_CLEAR_PX)) continue;
      return p;
    }
  }
  return null;
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
      const plan = await viewer(page, "overviewPlan");
      expect(plan.failed).toEqual([]);

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
      const looks = await viewer(page, "lineLooks");
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
      const looks = await viewer(page, "lineLooks");
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

      // A count with no pill shows while the pointer is on its line, at a point clear of everything else.
      await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
      await twoFrames(page);
      const canvas = await page.getByTestId("graph-canvas").boundingBox();
      const shown = await viewOf(page);
      const allLooks = await viewer(page, "lineLooks");
      const everyTitle = await viewer(page, "titles");
      const clearOf = [...rects.map(([, r]) => r), ...everyTitle];
      const hovered = [];
      for (const id of dropped) {
        if (hovered.length >= HOVERED_DROPPED) break;
        const look = allLooks.find((l) => l.id === id);
        const point = clearPointOn(look, segmentsOf(allLooks.filter((l) => l.id !== id), shown), clearOf, shown, canvas);
        if (!point) continue;
        await page.mouse.move(canvas.x + point.x, canvas.y + point.y);
        for (const count of [byId[id].forwardKeys.length, byId[id].backwardKeys.length].filter(Boolean)) {
          await expect(page.getByTestId("aggregated-edge-note"), id).toContainText(`${count} edge`);
        }
        hovered.push(id);
        await page.mouse.move(canvas.x + 2, canvas.y + 2);
      }
      test.info().annotations.push({ type: "measured", description: `the count read on hover for ${hovered.length} of ${dropped.length} lines without a pill` });
    });

    test("the overview's routes are planned once: a zoom and a box opening move no line between two closed boxes", async ({ page, request }) => {
      const data = await graph.open(page, request);
      const tree = treeOf(data);
      const before = await drawnAggregates(page);
      requireShape(Object.keys(before).length > 1, "fewer than two lines between top-level ends");
      const moved = (after) =>
        Object.entries(after)
          .filter(([name]) => before[name])
          .filter(([name, e]) => JSON.stringify(e.points) !== JSON.stringify(before[name].points))
          .map(([name]) => name);

      await page.getByRole("button", { name: "Zoom in", exact: true }).click();
      await page.getByRole("button", { name: "Zoom out", exact: true }).click();
      await twoFrames(page);
      expect(moved(await drawnAggregates(page))).toEqual([]);

      // The box with the most lines opened: every line between two other boxes keeps its route.
      const lines = Object.values(before);
      const busiest = tree.topBoxes.map((id) => [id, lines.filter((e) => e.ends.includes(id)).length]).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0][0];
      await page.evaluate((id) => window.__beadloomViewer.revealNodes([id]), busiest);
      await expect.poll(async () => (await viewer(page, "openBoxes")).includes(busiest)).toBe(true);
      const others = Object.fromEntries(Object.entries(await drawnAggregates(page)).filter(([, e]) => !e.ends.some((end) => withAncestors([end], tree.parents).has(busiest))));
      requireShape(Object.keys(others).length > 0, "every line between top-level ends touches the busiest box");
      expect(moved(others)).toEqual([]);
    });

    test("planning the overview takes no longer than the bound for this environment", async ({ page, request }) => {
      const bound = boundHere(PLAN_BUDGET_MS[graph.key]);
      await graph.open(page, request);
      const { ms } = await viewer(page, "overviewPlan");
      test.info().annotations.push({ type: "measured", description: `${ENVIRONMENT}: overview planned in ${ms.toFixed(1)} ms (bound ${bound} ms)` });
      expect(ms).toBeLessThanOrEqual(bound);
    });
  });
}

test("every closed box and every top-level node at the fit is titled at 14, 12.5, 11 or 10 px inside it, or beside it on a plate with a border that nothing covers and no line runs under", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const view = await viewOf(page);
  const top = Object.keys(tree.parents).filter((id) => id !== tree.wrapper && tree.parents[id] === tree.wrapper);
  const titles = await viewer(page, "titles");
  expect(titles.map((t) => t.id).sort()).toEqual([...top].sort());

  const step = Math.sqrt(1.25);
  const wrong = titles.filter((t) => !TITLE_PX.includes(t.sizePx) || t.fontSize < t.sizePx / step - 1e-6 || t.fontSize > t.sizePx * step + 1e-6);
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
