// The design's readings, measured a second time: each case reads one number the design bounds, reports it, and holds it.
//
// The viewer's design states its goals as numbers: no two arrowheads overlap at
// the overview, lines that run beside each other keep a gap, no line runs under a
// title or through a box, one line weight, an arrowhead whole on a straight run as
// long as itself, a box that opens only when its nodes are about 24 px tall, an
// open box that keeps its outward edges at the box and says how many with "+N",
// counts on pills nothing covers, titles inside their boxes, and an activity line
// whose box reflects its parts. The other specs hold each rule with their own
// oracles; these cases measure the same goals with geometry of their own
// (`support/metrics.js`), so a mistake in one oracle does not hide a defect from
// both, and each case records what it measured on the run's report
// (`measured` annotations), the reading a reviewer compares with the goal.
//
// The cases whose reading the layout decides — the titles at the fit, a box
// opened at the fit — run on this portal's graph and again on the same graph
// with two edges more (`support/perturbedGraph.js`), laid out another way. There
// a title's size is held as the map draws every mark, within a step of its scale:
// on this portal the fit lands where the floor holds at the size itself.
//
// What the cases cannot see. They read the state the viewer drew through its test
// handle and compare no pixels. Arrowheads are the triangles Cytoscape's source
// says it draws. On the adopter-sized graph the whole-graph fit is held at the
// smallest zoom and does not fit the canvas (the owner deferred an overview for
// such a project), so its titles and pills are not held there, and a line the
// overview's router found no route for there is reported and left out.

import { test, expect } from "@playwright/test";
import { ADOPTER_SIZED, adopterSizedGraph } from "./support/adopterGraph.js";
import { drawnEdgesOf, treeOf } from "./support/map.js";
import { centreOn, settled, twoFrames, zoomIntoBox } from "./support/levels.js";
import { AA_TEXT, canvasBackground, contrastRatio, over } from "./support/look.js";
import {
  arrivalGroups,
  arrowLength,
  drawnHeads,
  lineEnters,
  narrowestRunGap,
  overlappingTriangles,
  rectToScreen,
  rectsShare,
  shrink,
  spread,
  triangleOverlap,
} from "./support/metrics.js";
import { withTwoMoreEdges } from "./support/perturbedGraph.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, openEveryBox, viewer, withAncestors } from "./support/viewer.js";
import { layerBoxesOf } from "./support/layers.js";

/** The one weight every line is drawn at, in pixels on screen. */
const LINE_PX = 1.35;
/** The step the marks are restyled at as the zoom changes: a size on screen stays within half of it. */
const SCALE_STEP = 1.25;
/** An arrowhead of the overview's own lines, in pixels on screen. */
const HEAD_PX = 6;
/** The smallest an arrowhead is drawn, where its run holds no larger one, in pixels on screen. */
const SMALLEST_HEAD_PX = 3;
/** The radius a corner is rounded at on screen, where both its runs leave room for it, in pixels. */
const CORNER_PX = 6;
/** Lines that run beside each other keep at least this far apart at the fit, in pixels. */
const GAP_PX = 5;
/** On this portal's own graph the overview's narrowest gap is at least this, in pixels: the design's goal for it. */
const OWN_GAP_PX = 7;
/** A node is readable at this height on screen, in pixels: a box opens once its nodes are. */
const READABLE_PX = 24;
/** An open box may stay open down to this share of `READABLE_PX`, and no further. */
const STAY_OPEN_SHARE = 0.8;
/** The smallest title on screen, in pixels. */
const SMALLEST_TITLE_PX = 10;
/** Two arrowheads that reach into each other by less than this, in pixels, touch rather than overlap. */
const HEAD_SLACK_PX = 0.25;
/** How far a line may enter a box or a title it does not end at, in pixels: under a pixel is the stroke's own antialiasing. */
const RECT_SLACK_PX = 1;
/** The viewer's smallest zoom: a fit held at it does not fit the canvas. */
const MIN_ZOOM = 0.02;
/** The most zoom steps a case takes from the fit. */
const ZOOM_STEPS = 30;

/** The graphs the overview is measured on: this portal's and an adopter-sized one. */
const GRAPHS = [
  { name: "this portal's architecture graph", own: true, tag: [], data: (served) => served },
  { name: "an adopter-sized architecture graph", own: false, tag: [ADOPTER_SIZED], data: (served) => adopterSizedGraph(served) },
];

const half = Math.sqrt(SCALE_STEP);
/** Whether `px` is `wanted` within half a scale step either way. */
const withinAStep = (px, wanted) => px >= wanted / half - 1e-6 && px <= wanted * half + 1e-6;

/** Record a reading on the case's report. */
function measured(description) {
  test.info().annotations.push({ type: "measured", description });
}

/** Open the architecture page over `data`, served in place of the portal's own file. */
async function openOver(page, data) {
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await twoFrames(page);
}

/** The view the handle reports: the zoom and pan that put the graph on screen. */
async function viewOf(page) {
  return { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
}

/**
 * The lines drawn at the overview that the router planned, and those it found no
 * route for where the fit is held at the smallest zoom: `{ looks, unrouted }`.
 */
async function plannedLines(page) {
  const clamped = (await viewer(page, "level")).fitZoom <= MIN_ZOOM + 1e-9;
  const failed = new Set((await viewer(page, "overviewPlan")).failed);
  const unrouted = new Set(
    (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn && clamped && failed.has(e.ends.join("\n"))).map((e) => e.id)
  );
  const looks = (await viewer(page, "lineLooks")).filter((look) => !unrouted.has(look.id));
  if (unrouted.size) measured(`${unrouted.size} line(s) with no route at a fit held at the smallest zoom, left out: ${[...unrouted].join(", ")}`);
  return { looks, unrouted };
}

/** Each drawn node's box on screen, by id. */
async function screenBoxes(page, view) {
  return Object.fromEntries(Object.entries(await viewer(page, "nodeBoxes")).map(([id, box]) => [id, rectToScreen(box, view)]));
}

/**
 * The layouts a rule the layout decides is read on: the served file's, and the
 * one ELK makes of it with two edges more (`support/perturbedGraph.js`), served
 * in its place. A rule read on one layout holds by that layout's luck.
 */
const LAYOUTS = [
  { name: "", served: true, data: (request) => architectureData(request) },
  {
    name: ", with two edges more",
    served: false,
    data: async (request) => {
      const more = withTwoMoreEdges(await architectureData(request));
      requireShape(Boolean(more), "no two leaves in two other top-level boxes than a third leaf's");
      return more.data;
    },
  },
];

/**
 * The least size on screen a title of the smallest size may be drawn at at the
 * fit, as the map draws its marks: one size on screen within half of the step
 * its scale is restyled at, a power of 1.25 near 1 / zoom, and laid out at the
 * scale of the overview's plan, so one step smaller where the fit, which
 * measures the routes as well, lands a step coarser. On the served layout the
 * design's goal holds the floor at the size itself.
 */
async function smallestTitleOnScreen(page) {
  const shrink = Math.min(1, (await viewer(page, "overviewPlan")).unit / (await viewer(page, "level")).scale);
  return (SMALLEST_TITLE_PX * shrink) / half;
}

/** Open the architecture page over `layout`'s `data`: the served file as it is, or `data` served in its place. */
async function openLayout(page, layout, data) {
  if (!layout.served) await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
}

/** The top-level box holding the most nodes; the case is skipped without one. */
function largestTopBox(data, tree) {
  const held = (box) => data.nodes.filter((n) => n.id !== box && withAncestors([n.id], tree.parents).has(box)).length;
  const box = [...tree.topBoxes].sort((a, b) => held(b) - held(a) || (a < b ? -1 : 1))[0];
  requireShape(Boolean(box), "no box at the top of the containment tree");
  return box;
}

/** Each box's smallest child's height in layout units, from ELK's boxes: what decides when it opens. */
function smallestChildren(tree, boxes) {
  const smallest = new Map();
  for (const [id, parent] of Object.entries(tree.parents)) {
    if (parent && boxes[id]) smallest.set(parent, Math.min(smallest.get(parent) ?? Infinity, boxes[id].y2 - boxes[id].y1));
  }
  return smallest;
}

/** Press a toolbar zoom button once and wait two frames. */
async function press(page, name) {
  await page.getByRole("button", { name, exact: true }).click();
  await twoFrames(page);
}

/** Press "Zoom in" until the zoom is at least `zoom`. */
async function zoomTo(page, zoom) {
  for (let step = 0; step < ZOOM_STEPS && (await viewer(page, "zoom")) < zoom; step += 1) await press(page, "Zoom in");
  expect(await viewer(page, "zoom"), `the view zoomed in to ${zoom}`).toBeGreaterThanOrEqual(zoom);
}

/** Open every box at the zoom drawn now, as a reader's zoom opens them, edges kept at rest. */
async function openEveryBoxAtRest(page) {
  await page.evaluate(() => {
    const handle = window.__beadloomViewer;
    handle.revealNodes(Object.keys(handle.positions()), { edges: false });
  });
  await twoFrames(page);
}

for (const graph of GRAPHS) {
  test.describe(`on ${graph.name}, at the whole-graph fit`, { tag: graph.tag }, () => {
    test("no two arrowheads overlap, measured as triangles", async ({ page, request }) => {
      await openOver(page, graph.data(await architectureData(request)));
      const { looks } = await plannedLines(page);
      const heads = drawnHeads(looks, await viewOf(page));
      const overlaps = overlappingTriangles(heads, HEAD_SLACK_PX);
      measured(`${overlaps.length} overlapping pair(s) of ${heads.length} arrowheads`);

      expect(overlaps).toEqual([]);
    });

    test("lines that end at one point from one direction draw one arrowhead there, and every arrival has one", async ({ page, request }) => {
      await openOver(page, graph.data(await architectureData(request)));
      const { looks } = await plannedLines(page);
      const groups = arrivalGroups(looks, await viewOf(page));
      const shared = groups.filter((g) => g.ids.length > 1);
      const wrong = groups.filter((g) => g.heads !== 1).map((g) => `${g.ids.join(" + ")}: ${g.heads} heads`);
      measured(`${groups.length} arrival point(s), ${shared.length} shared by two lines or more, ${wrong.length} not drawing exactly one head`);

      expect(wrong).toEqual([]);
    });

    test(`two lines that run beside each other keep at least ${graph.own ? OWN_GAP_PX : GAP_PX} px apart`, async ({ page, request }) => {
      await openOver(page, graph.data(await architectureData(request)));
      const { looks } = await plannedLines(page);
      const { gap, between, pairs } = narrowestRunGap(looks, await viewOf(page));
      measured(`narrowest gap ${gap.toFixed(2)} px over ${pairs} pair(s) of runs beside each other: ${between}`);

      expect(gap).toBeGreaterThanOrEqual(graph.own ? OWN_GAP_PX : GAP_PX);
    });

    test("no line runs through a box it does not end at", async ({ page, request }) => {
      const data = graph.data(await architectureData(request));
      await openOver(page, data);
      const tree = treeOf(data);
      const view = await viewOf(page);
      const boxes = await screenBoxes(page, view);
      const ends = new Map((await viewer(page, "edgeRoutes")).map((route) => [route.id, [route.source, route.target]]));
      const { looks } = await plannedLines(page);
      const through = [];
      for (const look of looks) {
        // A line runs inside the boxes that hold its ends; it ends on its own ends' borders.
        const holding = withAncestors(ends.get(look.id) || [], tree.parents);
        for (const [id, rect] of Object.entries(boxes)) {
          if (!holding.has(id) && lineEnters(look, shrink(rect, RECT_SLACK_PX), view)) through.push(`${look.id} through ${id}`);
        }
      }
      measured(`${through.length} line(s) through a box, of ${looks.length} lines and ${Object.keys(boxes).length} boxes`);

      expect(through).toEqual([]);
    });

    test("every line is drawn at one weight on screen", async ({ page, request }) => {
      await openOver(page, graph.data(await architectureData(request)));
      const zoom = await viewer(page, "zoom");
      const widths = (await viewer(page, "lineLooks")).map((look) => look.width * zoom);
      measured(`${widths.length} line(s), widths on screen ${spread(widths)} px`);

      expect(widths.filter((px) => !withinAStep(px, LINE_PX))).toEqual([]);
    });

    test(`every arrowhead of the overview's own lines is ${HEAD_PX} px on screen, and every arrowhead stands on a straight run at least as long as itself`, async ({ page, request }) => {
      await openOver(page, graph.data(await architectureData(request)));
      const { looks } = await plannedLines(page);
      const heads = drawnHeads(looks, await viewOf(page));
      const own = new Set(looks.filter((look) => look.aggregated).map((look) => look.id));
      // At a fit held at the smallest zoom a box can be a few pixels tall, and a head shrinks to its room: reported, not held.
      const clamped = (await viewer(page, "level")).fitZoom <= MIN_ZOOM + 1e-9;
      const offSize = heads.filter((h) => own.has(h.id) && !withinAStep(h.length, HEAD_PX)).map((h) => `${h.id}:${h.end} ${h.length.toFixed(2)} px`);
      if (clamped && offSize.length) measured(`at a fit held at the smallest zoom, ${offSize.length} head(s) of the overview's own lines drawn smaller: ${offSize.join(", ")}`);
      const off = clamped ? [] : offSize;
      const short = heads.filter((h) => h.run < h.length - 0.01).map((h) => `${h.id}:${h.end} run ${h.run.toFixed(2)} < head ${h.length.toFixed(2)}`);
      measured(`${heads.length} arrowhead(s), ${heads.filter((h) => own.has(h.id)).length} on the overview's own lines; sizes ${spread(heads.map((h) => h.length))} px, straight runs ${spread(heads.map((h) => h.run))} px, ${short.length} shorter than their head`);

      expect({ off, short }).toEqual({ off: [], short: [] });
    });
  });
}

test.describe("on this portal's architecture graph", () => {
  test("at the whole-graph fit no line runs under a title, a plate's included", async ({ page }) => {
    await openArchitecture(page);
    const view = await viewOf(page);
    const titles = [...(await viewer(page, "titles")), ...(await viewer(page, "boxTitles"))];
    const looks = await viewer(page, "lineLooks");
    const under = [];
    for (const title of titles) {
      for (const look of looks) if (lineEnters(look, shrink(title, RECT_SLACK_PX), view)) under.push(`${look.id} under ${title.id}'s title`);
    }
    measured(`${under.length} line(s) under a title, of ${looks.length} lines and ${titles.length} titles`);

    expect(under).toEqual([]);
  });

  test("at the whole-graph fit every count above one is on a pill that covers no box, title, arrowhead or other pill, and a line carrying one edge has none", async ({ page, request }) => {
    const { wrapper } = treeOf(await architectureData(request));
    await openArchitecture(page);
    const view = await viewOf(page);
    const { pills, dropped } = await viewer(page, "pills");
    const boxes = await screenBoxes(page, view);
    const titles = await viewer(page, "titles");
    const looks = await viewer(page, "lineLooks");
    const counted = new Map(looks.filter((look) => look.aggregated).map((look) => [look.id, look.forward + look.backward]));
    const headRects = drawnHeads(looks, view).map((h) => ({
      id: `${h.id}:${h.end}`,
      x1: Math.min(...h.triangle.map((p) => p.x)),
      y1: Math.min(...h.triangle.map((p) => p.y)),
      x2: Math.max(...h.triangle.map((p) => p.x)),
      y2: Math.max(...h.triangle.map((p) => p.y)),
    }));
    const covers = [];
    for (const [k, pill] of pills.entries()) {
      for (const [id, rect] of Object.entries(boxes)) if (rectsShare(pill, rect, RECT_SLACK_PX)) covers.push(`${pill.id} on box ${id}`);
      for (const title of titles) if (rectsShare(pill, title, RECT_SLACK_PX)) covers.push(`${pill.id} on ${title.id}'s title`);
      for (const head of headRects) if (rectsShare(pill, head, RECT_SLACK_PX)) covers.push(`${pill.id} on head ${head.id}`);
      for (const other of pills.slice(k + 1)) if (rectsShare(pill, other, 0)) covers.push(`${pill.id} on pill ${other.id}`);
    }
    // A box that holds everything is drawn behind every line, and a pill may sit over it.
    const real = covers.filter((cover) => !cover.endsWith(`on box ${wrapper}`));
    const single = pills.filter((pill) => counted.get(pill.id) === 1).map((pill) => pill.id);
    const many = [...counted.values()].filter((count) => count > 1).length;
    measured(`${pills.length} pill(s) for ${many} line(s) carrying more than one edge, ${dropped.length} dropped for want of a place; ${real.length} covering; ${single.length} on a line of one edge; layers ${JSON.stringify(await viewer(page, "overlayLayers"))}`);

    expect({ covers: real, single }).toEqual({ covers: [], single: [] });
  });

  for (const layout of LAYOUTS) {
    test(`at the whole-graph fit every closed box and top-level node is titled at 10 px ${layout.served ? "or more" : "within a step of the map's scale"}, inside its box${layout.name}`, async ({ page, request }) => {
      const data = await layout.data(request);
      const tree = treeOf(data);
      await openLayout(page, layout, data);
      const view = await viewOf(page);
      const floor = layout.served ? SMALLEST_TITLE_PX : await smallestTitleOnScreen(page);
      const boxes = await screenBoxes(page, view);
      const titles = await viewer(page, "titles");
      const zoom = await viewer(page, "zoom");
      const nodeLooks = new Map((await viewer(page, "nodeLooks")).map((look) => [look.id, look]));
      const top = Object.keys(tree.parents).filter((id) => id !== tree.wrapper && (tree.parents[id] === tree.wrapper || (!tree.wrapper && !tree.parents[id])));
      const byId = new Map(titles.map((title) => [title.id, title]));
      const wrong = [];
      for (const id of top) {
        const title = byId.get(id);
        // A top-level leaf whose own label reads larger than a title would keeps its label, centred in it.
        const label = nodeLooks.get(id);
        if (!title && !(label && !label.isParent && label.labelValign === "center" && label.fontSize * zoom >= floor - 0.01)) wrong.push(`${id}: no title`);
        else if (!title) continue;
        else if (title.fontSize < floor - 0.01) wrong.push(`${id}: ${title.fontSize.toFixed(2)} px`);
        else if (!title.inside || !(title.x1 >= boxes[id].x1 - 0.5 && title.x2 <= boxes[id].x2 + 0.5 && title.y1 >= boxes[id].y1 - 0.5 && title.y2 <= boxes[id].y2 + 0.5))
          wrong.push(`${id}: outside its box${title.inside ? "" : " on a plate"}`);
      }
      const project = (await viewer(page, "boxTitles")).find((title) => title.id === tree.wrapper);
      measured(`${top.length} top-level node(s); titles ${spread(top.filter((id) => byId.has(id)).map((id) => byId.get(id).fontSize))} px; ${wrong.length} wrong; the project box's title ${project ? `${project.fontSize.toFixed(2)} px${project.plate ? " on a plate" : ""}` : "not drawn"}`);

      expect(wrong).toEqual([]);
    });

    test(`opening a box at the whole-graph fit moves no line between top-level ends and no pill, and draws no line of the file out of the box${layout.name}`, async ({ page, request }) => {
      const data = await layout.data(request);
      const tree = treeOf(data);
      const box = largestTopBox(data, tree);
      await openLayout(page, layout, data);
      const top = new Set(tree.topBoxes.concat(Object.keys(tree.parents).filter((id) => tree.parents[id] === tree.wrapper)));
      const lines = async () =>
        Object.fromEntries(
          (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn && e.ends.every((end) => top.has(end))).map((e) => [e.ends.join("|"), JSON.stringify([e.points, e.label])])
        );
      const pills = async () => Object.fromEntries((await viewer(page, "pills")).pills.map((p) => [`${p.id}`, JSON.stringify([p.text, p.x1.toFixed(2), p.y1.toFixed(2)])]));
      const [linesBefore, pillsBefore, idsBefore] = [await lines(), await pills(), await viewer(page, "aggregatedEdges")];
      const pairIds = Object.fromEntries(idsBefore.filter((e) => e.drawn).map((e) => [e.id, e.ends.join("|")]));

      await page.evaluate((id) => window.__beadloomViewer.revealNodes([id], { edges: false }), box);
      await expect.poll(() => viewer(page, "openBoxes")).toContain(box);
      await twoFrames(page);
      const [linesAfter, pillsAfterRaw] = [await lines(), await pills()];
      const moved = Object.keys(linesBefore).filter((pair) => linesAfter[pair] !== linesBefore[pair]);
      // A pill is named by its line's id; a line keeps its pair, so a pill is compared by its pair.
      const byPair = (raw, ids) => Object.fromEntries(Object.entries(raw).map(([id, v]) => [ids[id] ?? id, v]));
      const pairIdsAfter = Object.fromEntries((await viewer(page, "aggregatedEdges")).filter((e) => e.drawn).map((e) => [e.id, e.ends.join("|")]));
      const [pillsA, pillsB] = [byPair(pillsBefore, pairIds), byPair(pillsAfterRaw, pairIdsAfter)];
      const pillsMoved = Object.keys(pillsA).filter((pair) => pair in linesBefore && pillsB[pair] !== pillsA[pair]);
      const inBox = (id) => withAncestors([id], tree.parents).has(box);
      const ancestor = (a, b) => withAncestors([b], tree.parents).has(a);
      const outward = (await viewer(page, "edgeRoutes")).filter(
        (route) => !route.aggregated && inBox(route.source) !== inBox(route.target) && !ancestor(route.source, route.target) && !ancestor(route.target, route.source)
      );
      measured(`opened ${box}: ${Object.keys(linesBefore).length} top-level line(s), ${moved.length} moved; ${Object.keys(pillsA).length} pill(s), ${pillsMoved.length} moved; ${outward.length} line(s) of the file out of the box at rest`);

      expect({ moved, pillsMoved, outward: outward.map((route) => route.key) }).toEqual({ moved: [], pillsMoved: [], outward: [] });
    });
  }

  test('a node in a box opened by zooming carries "+N" for exactly its edges out of the box, and hovering it draws exactly those', async ({ page, request }) => {
    const data = await architectureData(request);
    const tree = treeOf(data);
    const box = largestTopBox(data, tree);
    const edges = drawnEdgesOf(data);
    const holds = (outer, id) => withAncestors([id], tree.parents).has(outer);
    // Out of the box: the other end is not in it, and is not a box that holds the node (a loop, drawn at rest).
    const outOf = (id) => edges.filter((e) => (e.src === id && !holds(box, e.dst) && !holds(e.dst, id)) || (e.dst === id && !holds(box, e.src) && !holds(e.src, id))).map((e) => e.key).sort();
    const children = Object.keys(tree.parents).filter((id) => tree.parents[id] === box && !tree.boxes.has(id));
    await openArchitecture(page);
    await zoomIntoBox(page, box);
    const marks = await viewer(page, "outwardMarks");
    const wrong = [];
    for (const id of children) {
      const wanted = outOf(id).length;
      const mark = marks[id];
      if ((mark?.count ?? 0) !== wanted || (wanted > 0 && mark.text !== `+${wanted}`)) wrong.push(`${id}: "+N" says ${mark ? `${mark.count} ("${mark.text}")` : "nothing"}, ${wanted} out of the box`);
    }
    // The pointer reaches a node whose middle is well inside the canvas.
    const canvas = await page.getByTestId("graph-canvas").boundingBox();
    const pageBoxes = await viewer(page, "boxes");
    const reachable = (id) => {
      const [x, y] = [(pageBoxes[id].x1 + pageBoxes[id].x2) / 2, (pageBoxes[id].y1 + pageBoxes[id].y2) / 2];
      return x > canvas.x + 40 && x < canvas.x + canvas.width - 40 && y > canvas.y + 40 && y < canvas.y + canvas.height - 40;
    };
    const busiest = children.filter((id) => pageBoxes[id] && reachable(id)).sort((a, b) => outOf(b).length - outOf(a).length || (a < b ? -1 : 1))[0];
    requireShape(Boolean(busiest) && outOf(busiest).length > 0, "no node in view in the largest top-level box has an edge out of it");
    // The pointer comes from elsewhere: a move to where it already rests is no move.
    await page.mouse.move(2, 2);
    const b = pageBoxes[busiest];
    await page.mouse.move((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2);
    // Its edges into a box drawn open are drawn as themselves; the rest on its own lines.
    const drawnOut = async () => {
      const asThemselves = (await viewer(page, "lineLooks")).filter((look) => look.key && outOf(busiest).includes(look.key)).map((look) => look.key);
      const carried = (await viewer(page, "ownLines")).flatMap((line) => [...line.forwardKeys, ...line.backwardKeys]);
      return [...new Set([...asThemselves, ...carried])].sort();
    };
    await expect.poll(async () => (await drawnOut()).length).toBeGreaterThan(0);
    const own = await drawnOut();
    await page.mouse.move(2, 2);
    await expect.poll(async () => (await drawnOut()).length).toBe(0);
    measured(`${children.length} node(s) in ${box}, ${wrong.length} with a wrong "+N"; hovering ${busiest} draws ${own.length} of its ${outOf(busiest).length} edges out of the box, and none once the pointer leaves`);

    expect({ wrong, own }).toEqual({ wrong: [], own: outOf(busiest) });
  });

  test(`a box opens only once its nodes are ${READABLE_PX} px tall, and stays open only above ${STAY_OPEN_SHARE} of that, zooming in and out`, async ({ page, request }) => {
    const data = await architectureData(request);
    const tree = treeOf(data);
    const box = largestTopBox(data, tree);
    await openArchitecture(page);
    const smallest = smallestChildren(tree, (await viewer(page, "elkGeometry")).boxes);
    await centreOn(page, box);
    const fit = (await viewer(page, "level")).fitZoom;
    const openedAt = {};
    const tooSmall = [];
    let wasOpen = new Set();
    const read = async () => {
      const level = await viewer(page, "level");
      const open = new Set(level.open.filter((id) => id !== tree.wrapper));
      for (const id of open) {
        const px = smallest.get(id) * level.zoom;
        if (!wasOpen.has(id)) openedAt[id] = px;
        if (px < READABLE_PX * STAY_OPEN_SHARE - 0.01) tooSmall.push(`${id} open at ${px.toFixed(1)} px`);
      }
      wasOpen = open;
      return level.zoom;
    };
    await read();
    for (let step = 0; step < ZOOM_STEPS && (await read()) < 2; step += 1) await press(page, "Zoom in");
    for (let step = 0; step < ZOOM_STEPS && (await read()) > fit * 1.01; step += 1) await press(page, "Zoom out");
    const early = Object.entries(openedAt).filter(([, px]) => px < READABLE_PX - 0.01).map(([id, px]) => `${id} opened at ${px.toFixed(1)} px`);
    measured(`${Object.keys(openedAt).length} box(es) opened; their nodes' height on screen when opening ${spread(Object.values(openedAt))} px; ${tooSmall.length} reading(s) of an open box below ${(READABLE_PX * STAY_OPEN_SHARE).toFixed(1)} px`);

    expect(Object.keys(openedAt)).toContain(box);
    expect({ early, tooSmall }).toEqual({ early: [], tooSmall: [] });
  });

  test("with every box open, every arrowhead stands on a straight run at least as long as itself and is 3 to 6 px, at the zoom the nodes are readable at, at zoom 1 and at zoom 2", async ({ page, request }) => {
    const data = await architectureData(request);
    const tree = treeOf(data);
    await openArchitecture(page);
    const smallest = smallestChildren(tree, (await viewer(page, "elkGeometry")).boxes);
    // The zoom at which the smallest node of every box is readable: where every box is open to a reader.
    const heights = [...smallest].filter(([id]) => id !== tree.wrapper).map(([, height]) => READABLE_PX / height);
    const results = {};
    for (const zoom of [...(heights.length ? [Math.max(...heights)] : []), 1, 2]) {
      await zoomTo(page, zoom);
      await openEveryBoxAtRest(page);
      const view = await viewOf(page);
      const heads = drawnHeads(await viewer(page, "lineLooks"), view);
      const short = heads.filter((h) => h.run < h.length - 0.01).map((h) => `${h.id}:${h.end} ${h.run.toFixed(2)} < ${h.length.toFixed(2)}`);
      const off = heads.filter((h) => h.length < SMALLEST_HEAD_PX / half - 1e-6 || h.length > HEAD_PX * half + 1e-6).map((h) => `${h.id}:${h.end} ${h.length.toFixed(2)} px`);
      const smaller = heads.filter((h) => !withinAStep(h.length, HEAD_PX)).length;
      measured(`zoom ${view.zoom.toFixed(3)}: ${heads.length} arrowhead(s), sizes ${spread(heads.map((h) => h.length))} px (${smaller} drawn smaller than ${HEAD_PX} px for want of room), ${short.length} on a run shorter than themselves`);
      results[view.zoom.toFixed(3)] = { short, off };
    }

    for (const [zoom, { short, off }] of Object.entries(results)) expect({ zoom, short, off }).toEqual({ zoom, short: [], off: [] });
  });

  test("with every box open at zoom 1, every corner with room for it is rounded at one radius on screen", async ({ page }) => {
    await openArchitecture(page);
    await zoomTo(page, 1 / half);
    await openEveryBoxAtRest(page);
    const view = await viewOf(page);
    const wrong = [];
    let corners = 0;
    let roomless = 0;
    for (const look of await viewer(page, "lineLooks")) {
      if (!look.cornerRadii.length) continue;
      const points = look.points.map((p) => ({ x: p.x * view.zoom, y: p.y * view.zoom }));
      for (let k = 1; k < points.length - 1; k += 1) {
        const [a, b, c] = [points[k - 1], points[k], points[k + 1]];
        if (Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) < 1e-6) continue;
        corners += 1;
        const radius = (look.cornerRadii.length === 1 ? look.cornerRadii[0] : look.cornerRadii[k - 1]) * view.zoom;
        // A corner next to an arrowhead leaves a head and half a head of its run straight.
        const head = arrowLength(look) * view.zoom * 1.5;
        const [before, after] = [Math.hypot(b.x - a.x, b.y - a.y), Math.hypot(c.x - b.x, c.y - b.y)];
        // Edges arrive at a line's target, and at a line of the map's source when it carries edges back.
        const atSource = k === 1 && (look.sourceArrow !== "none" || (look.aggregated && look.backward > 0));
        const atTarget = k === points.length - 2 && (!look.aggregated || look.forward > 0);
        const room = Math.min(atSource ? before - head : before / 2, atTarget ? after - head : after / 2);
        if (room < CORNER_PX / half) roomless += 1;
        else if (!withinAStep(radius, CORNER_PX)) wrong.push(`${look.id} corner ${k}: ${radius.toFixed(2)} px`);
      }
    }
    measured(`zoom ${view.zoom.toFixed(3)}: ${corners} corner(s), ${roomless} with no room for a ${CORNER_PX} px radius, ${wrong.length} with room drawn at another radius`);

    expect(wrong).toEqual([]);
  });

  test("a hovered line is drawn on top of every line it crosses, from a layer over the canvas, and no bridge or junction dot exists", async ({ page }) => {
    await openArchitecture(page);
    await openEveryBox(page);
    await zoomTo(page, 1 / half);
    await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
    await twoFrames(page);
    const found = await viewer(page, "edgeMidpoint");
    requireShape(Boolean(found), "no drawn edge has a middle clear of other edges and nodes");
    await page.mouse.move(found[1].x, found[1].y);
    await expect.poll(async () => (await viewer(page, "followed")).edges.length).toBeGreaterThan(0);
    const followed = await viewer(page, "followed");
    const view = await viewOf(page);
    const looks = await viewer(page, "lineLooks");
    const ids = new Set(followed.edges.map((edge) => edge.id));
    // The lines the followed ones cross, on screen: each is drawn under them.
    const followedLooks = looks.filter((look) => ids.has(look.id));
    const crossed = looks.filter(
      (look) => !ids.has(look.id) && followedLooks.some((f) => f.points.slice(1).some((p, k) => lineEnters(look, { x1: Math.min(p.x, f.points[k].x) * view.zoom + view.pan.x - 0.5, y1: Math.min(p.y, f.points[k].y) * view.zoom + view.pan.y - 0.5, x2: Math.max(p.x, f.points[k].x) * view.zoom + view.pan.x + 0.5, y2: Math.max(p.y, f.points[k].y) * view.zoom + view.pan.y + 0.5 }, view)))
    ).length;
    const layers = await viewer(page, "overlayLayers");
    const handle = await page.evaluate(() => ["bridges", "bridgeFrames", "junctions"].filter((name) => name in window.__beadloomViewer));
    const stacking = await page.evaluate(() => {
      const container = document.querySelector("[data-testid='graph-canvas']");
      const layer = container.querySelector("canvas[data-layer='followed']");
      return Number(getComputedStyle(layer).zIndex) > Number(getComputedStyle(container.firstElementChild).zIndex);
    });
    measured(`${followed.edges.length} line(s) followed over ${crossed} line(s) they cross; passes ${followed.passes.map((p) => p.name).join(" > ")}; layers ${layers.join(", ")}`);

    expect({ above: stacking, casingsFirst: followed.passes[0]?.name, layers, handle }).toEqual({ above: true, casingsFirst: "casings", layers: ["followed", "pills"], handle: [] });
  });

  test("selecting a node from the URL frames it: drawn as itself, readable, in the canvas", async ({ page, request }) => {
    const data = await architectureData(request);
    const tree = treeOf(data);
    const leaf = data.nodes.filter((n) => !tree.boxes.has(n.id) && tree.depth(n.id) >= 2).map((n) => n.id).sort()[0];
    requireShape(Boolean(leaf), "no node two levels below the top of the containment tree");
    await openArchitecture(page);
    const fit = await viewer(page, "zoom");
    await openArchitecture(page, `?focus=${encodeURIComponent(leaf)}`);
    await expect.poll(async () => (await viewer(page, "ready")) && (await viewer(page, "visibleIds")).includes(leaf)).toBe(true);
    await settled(page);
    const zoom = await viewer(page, "zoom");
    const nodeBox = (await viewer(page, "nodeBoxes"))[leaf];
    const height = (nodeBox.y2 - nodeBox.y1) * zoom;
    const canvas = await page.getByTestId("graph-canvas").boundingBox();
    const b = (await viewer(page, "boxes"))[leaf];
    const inCanvas = b.x1 >= canvas.x && b.x2 <= canvas.x + canvas.width && b.y1 >= canvas.y && b.y2 <= canvas.y + canvas.height;
    measured(`${leaf}: zoom ${fit.toFixed(3)} at the fit, ${zoom.toFixed(3)} selected; drawn ${height.toFixed(1)} px tall; in the canvas: ${inCanvas}`);

    // A graph whose fit already draws the node readably needs no zoom: what is held is what the reader sees.
    expect({ drawn: (await viewer(page, "visibleIds")).includes(leaf), readable: height >= READABLE_PX * STAY_OPEN_SHARE, inCanvas }).toEqual({ drawn: true, readable: true, inCanvas: true });
  });

  // A box a layer rule draws is titled as every closed box is (owner, 2026-10-08):
  // inside it at 10 px or more, wherever a reader's gesture draws it. Read on the
  // two ways a reader reaches the scope's layers: a tap on the scope at the fit,
  // which frames it whole, and zooming into the scope, then two steps further each.
  test("every box a layer rule draws is titled at 10 px or more, inside its box, as a tap on its scope or a zoom into it draws it", async ({ page, request }) => {
    const data = await architectureData(request);
    const layerBoxes = layerBoxesOf(data);
    requireShape(layerBoxes.length > 0, "no layer rule scoped to a box inside the project's frame, as a frontend service's rule is");
    const scope = layerBoxes[0].scope;
    const ids = layerBoxes.filter((box) => box.scope === scope).map((box) => box.id);
    const wrong = [];
    const sizes = [];
    let read = 0;
    const readTitles = async (gesture) => {
      const view = await viewOf(page);
      const boxes = await screenBoxes(page, view);
      const byId = new Map((await viewer(page, "titles")).map((title) => [title.id, title]));
      // A closed box is titled by the map; an open one at its layout's size, as every open box is.
      const closed = new Set((await viewer(page, "level")).collapsed.map((box) => box.id));
      for (const id of ids.filter((boxId) => boxes[boxId] && closed.has(boxId))) {
        read += 1;
        const title = byId.get(id);
        const box = boxes[id];
        if (!title) wrong.push(`${gesture} at ${view.zoom.toFixed(3)}: ${id} has no title`);
        // At 10 px or more within a step of the map's scale: a mark keeps one size on screen between steps only.
        else if (title.fontSize < SMALLEST_TITLE_PX / half - 0.01) wrong.push(`${gesture} at ${view.zoom.toFixed(3)}: ${id} ${title.fontSize.toFixed(2)} px`);
        else if (!title.inside || !(title.x1 >= box.x1 - 0.5 && title.x2 <= box.x2 + 0.5 && title.y1 >= box.y1 - 0.5 && title.y2 <= box.y2 + 0.5)) {
          wrong.push(`${gesture} at ${view.zoom.toFixed(3)}: ${id} outside its box${title.inside ? "" : " on a plate"}`);
        }
        if (title) sizes.push(title.fontSize);
      }
    };
    const onwards = async (gesture) => {
      for (let step = 0; step < ZOOM_STEPS && !(await viewer(page, "openBoxes")).includes(scope); step += 1) {
        await readTitles(gesture);
        await press(page, "Zoom in");
        await settled(page);
      }
      for (let step = 0; step <= 2; step += 1) {
        await readTitles(gesture);
        await press(page, "Zoom in");
        await settled(page);
      }
    };

    await page.emulateMedia({ reducedMotion: "reduce" });
    await openArchitecture(page);
    await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
    await twoFrames(page);
    const at = (await viewer(page, "boxes"))[scope];
    await page.mouse.click((at.x1 + at.x2) / 2, at.y1 + Math.min(12, (at.y2 - at.y1) / 4));
    await expect.poll(() => viewer(page, "selection")).toBe(scope);
    await settled(page);
    await onwards("a tap");
    await openArchitecture(page);
    await zoomIntoBox(page, scope);
    await settled(page);
    await onwards("a zoom");
    measured(`${ids.length} layer box(es) of ${scope}; ${read} title reading(s), ${spread(sizes)} px; ${wrong.length} wrong`);

    expect(read).toBeGreaterThan(0);
    expect(wrong).toEqual([]);
  });

  test("a box's activity reflects its parts: it has changed at least as many lines as its busiest part, and a part changed in 30 days leaves it changed", async ({ request }) => {
    const data = await architectureData(request);
    const tree = treeOf(data);
    const activity = new Map(data.nodes.filter((n) => n.activity).map((n) => [n.id, n.activity]));
    const quietLevels = new Set(["quiet", "dormant"]);
    const parts = (box) => data.nodes.filter((n) => n.id !== box && withAncestors([n.id], tree.parents).has(box) && activity.has(n.id)).map((n) => n.id);
    const boxes = [...tree.boxes].filter((box) => activity.has(box) && parts(box).length);
    requireShape(boxes.length > 0, "no box whose activity and whose parts' activity the data file holds");
    const wrong = [];
    for (const box of boxes) {
      const own = activity.get(box);
      const busiest = Math.max(...parts(box).map((id) => activity.get(id).lines_30d ?? 0));
      if ((own.lines_30d ?? 0) < busiest) wrong.push(`${box}: ${own.lines_30d} lines, a part changed ${busiest}`);
      if (quietLevels.has(own.level) && parts(box).some((id) => !quietLevels.has(activity.get(id).level))) wrong.push(`${box}: ${own.level} with a part changed in 30 days`);
    }
    const levels = {};
    for (const a of activity.values()) levels[a.level] = (levels[a.level] || 0) + 1;
    measured(`${activity.size} node(s) with activity, levels ${JSON.stringify(levels)} (${Object.keys(levels).length} populated); ${boxes.length} box(es) read, ${wrong.length} not reflecting their parts`);

    expect(wrong).toEqual([]);
  });
});

for (const colorScheme of ["light", "dark"]) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("no drawn colour is a fallback, and every title and label reads at WCAG AA at the overview and with every box open", async ({ page }) => {
      await openArchitecture(page);
      const background = await canvasBackground(page);
      const readings = [];
      const read = async (state) => {
        const looks = await viewer(page, "nodeLooks");
        const byId = new Map(looks.map((look) => [look.id, look]));
        const plated = new Set((await viewer(page, "titles")).filter((title) => !title.inside).map((title) => title.id));
        // What a title is drawn on: its node's fill over what holds the node, the canvas at the top;
        // a title on a plate outside its box is drawn on what holds the box.
        const ground = (id) => (byId.has(id) ? over(byId.get(id).fill, ground(byId.get(id).parent), byId.get(id).fillOpacity) : background);
        const ratios = looks.map((look) => contrastRatio(look.labelColour, plated.has(look.id) ? ground(look.parent) : ground(look.id)));
        const fallback = (await viewer(page, "colours")).filter((c) => /var\(/.test(c.value) || c.value.replace(/\s+/g, "") === "rgb(153,153,153)");
        readings.push({ state, low: ratios.filter((ratio) => ratio < AA_TEXT).length, fallback: fallback.length });
        measured(`${state}: ${looks.length} node(s), contrast ${spread(ratios)}, ${fallback.length} fallback colour(s)`);
      };
      await read("overview");
      await openEveryBoxAtRest(page);
      await read("every box open");

      expect(readings).toEqual([
        { state: "overview", low: 0, fallback: 0 },
        { state: "every box open", low: 0, fallback: 0 },
      ]);
    });
  });
}

test("the triangle reading tells two arrowheads that reach into each other from two that stand apart", () => {
  // Two 6 px heads into one point from facing sides overlap; side by side 7 px apart, they do not.
  const head = (tip, way) => {
    const base = { x: tip.x - way.x * 6, y: tip.y - way.y * 6 };
    return [tip, { x: base.x - way.y * 3, y: base.y + way.x * 3 }, { x: base.x + way.y * 3, y: base.y - way.x * 3 }];
  };
  const facing = triangleOverlap(head({ x: 10, y: 0 }, { x: 1, y: 0 }), head({ x: 8, y: 0 }, { x: -1, y: 0 }));
  const apart = triangleOverlap(head({ x: 10, y: 0 }, { x: 1, y: 0 }), head({ x: 10, y: 7 }, { x: 1, y: 0 }));

  expect({ facing: facing > HEAD_SLACK_PX, apart: apart > HEAD_SLACK_PX }).toEqual({ facing: true, apart: false });
});
