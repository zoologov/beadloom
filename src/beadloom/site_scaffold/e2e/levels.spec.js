// Levels: a box opens when its nodes are readable, an open box keeps its outward edges at the box, a selection is framed readably.
//
// In an earlier viewer a box opened once it was 600 px wide on screen, where
// its nodes were about 55 by 12 px and their wiring fused; an open box drew
// every edge out of it as itself, about a hundred lines from small nodes to
// closed boxes; a selection made at the fit stayed at the fit, its boxes opened
// with nodes 2 px tall, and an edge from a node to the box that holds it was
// drawn by Cytoscape as a curve straight across the box, whatever its route.
//
// The owner's rulings now: a box opens when its nodes are readable, about 24 px
// tall (12); an open box shows its nodes and the edges among them and keeps its
// outward edges aggregated at the box, a node's own edges to the outside drawn
// when it is hovered or selected (9), and a node inside an open box carries a
// "+N" mark for those (14); selecting a node zooms to its neighbourhood (7); an
// edge from a node to its own box stays drawn (13), routed like every other.
//
// What the cases cannot see. They read the state the viewer drew through its
// test handle and compare it with the rule restated here (`support/map.js`,
// `support/levels.js`); they compare no pixels.

import { test, expect } from "@playwright/test";
import { drawnEdgesOf, levelOf, outwardOf, smallestChildOf, treeOf } from "./support/map.js";
import {
  CLOSE_SHARE,
  FIT_FLOOR,
  READABLE_PX,
  againstReadability,
  centreOn,
  readableZoomOf,
  settled,
  twoFrames,
  unroutedLines,
  zoomInUntil,
  zoomIntoBox,
} from "./support/levels.js";
import { degreesOf } from "./support/map.js";
import { boxOnScreen, rectsOverlap, segmentInRect, segmentsOf } from "./support/overview.js";
import { drag } from "./support/pointer.js";
import { layerScopesOf } from "./support/layers.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, openEveryBox, viewer, withAncestors } from "./support/viewer.js";

/** A node with this many drawn edges is a hub. */
const HUB_DEGREE = 20;
/** The most zoom steps a case takes before it gives up. */
const ZOOM_STEPS = 30;
/** How far a route's end may lie from a box's border, in layout units. */
const ON_BORDER = 0.5;

const sorted = (ids) => [...ids].sort();

/**
 * The top-level box holding the most nodes, the one a reader is likeliest to open; the case is skipped without one.
 * A box holding a scoped rule's layer boxes is not one: it holds layer boxes rather than nodes and opens only where
 * they are readable, also when tapped, which `layer-boxes.spec.js` holds (`layerScopesOf`).
 */
function largestTopBox(data, tree) {
  const inside = (box) => data.nodes.filter((n) => withAncestors([n.id], tree.parents).has(box)).length;
  const scopes = layerScopesOf(data);
  const box = [...tree.topBoxes].filter((id) => !scopes.has(id)).sort((a, b) => inside(b) - inside(a) || (a < b ? -1 : 1))[0];
  requireShape(Boolean(box), "no box at the top of the containment tree");
  return box;
}

/** The edges the filters show at rest: every drawn edge of the file (no filter is set). */
const shownEdges = (data) => drawnEdgesOf(data);

/** Whether `point` lies on the border of `box`. */
const onBorder = (point, box) =>
  Math.min(Math.abs(point.x - box.x1), Math.abs(point.x - box.x2), Math.abs(point.y - box.y1), Math.abs(point.y - box.y2)) <= ON_BORDER;

test("a box opens when its nodes are readable, about 24 px tall, and closes below 0.9 of that, as the view zooms in and out", async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  requireShape(tree.topBoxes.length > 0, "no box at the top of the containment tree");
  await openArchitecture(page);
  const { boxes } = await viewer(page, "elkGeometry");
  const smallest = smallestChildOf(tree, boxes);
  const target = largestTopBox(data, tree);
  await centreOn(page, target);

  const broken = [];
  const check = async (step) => {
    await expect.poll(async () => againstReadability(await viewer(page, "level"), tree, boxes, smallest)).toEqual([]).catch(async () => {
      broken.push(`${step}: ${againstReadability(await viewer(page, "level"), tree, boxes, smallest).join("; ")}`);
    });
  };
  let opened = false;
  for (let step = 0; step < ZOOM_STEPS && !opened; step += 1) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
    await check(`zoom in ${step + 1}`);
    opened = (await viewer(page, "openBoxes")).includes(target);
  }
  expect(opened).toBe(true);
  // Opened at the first step its nodes were readable; one step out they are 0.8 of that, and it stays open.
  const opening = smallest.get(target) * (await viewer(page, "zoom"));
  await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await twoFrames(page);
  await check("one step out");
  const out = smallest.get(target) * (await viewer(page, "zoom"));
  // Still readable at the share it closes below, and past the floor over the fit: still open.
  const { fitZoom } = await viewer(page, "level");
  if (out >= READABLE_PX * CLOSE_SHARE && (await viewer(page, "zoom")) >= FIT_FLOOR * fitZoom) expect(await viewer(page, "openBoxes")).toContain(target);
  test.info().annotations.push({ type: "measured", description: `${target} opened with its smallest node ${opening.toFixed(1)} px tall; one step out ${out.toFixed(1)} px` });
  expect(broken).toEqual([]);
});

test("with a box opened by zooming in, an edge is drawn between the two children of the lowest box that holds its ends, and none drawn as itself leaves an open box", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const target = largestTopBox(data, tree);
  requireShape(Boolean(target), "no box at the top of the containment tree");
  await zoomIntoBox(page, target);

  const open = new Set(await viewer(page, "openBoxes"));
  const expected = levelOf(tree, open, shownEdges(data));
  const drawnKeys = (await viewer(page, "edgeLooks")).map((look) => look.key).sort();
  expect(drawnKeys).toEqual(expected.originals);
  const drawn = Object.fromEntries((await viewer(page, "aggregatedEdges")).map((e) => [e.ends.join("|"), e]));
  expect(sorted(Object.keys(drawn))).toEqual(sorted(expected.pairs.keys()));
  const wrong = [...expected.pairs].filter(
    ([name, pair]) => JSON.stringify({ forward: sorted(drawn[name].forwardKeys), backward: sorted(drawn[name].backwardKeys) }) !== JSON.stringify({ forward: pair.forward, backward: pair.backward })
  );
  expect(wrong.map(([name]) => name)).toEqual([]);
});

test("opening a box moves no line between two top-level ends and changes none of their counts", async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const target = largestTopBox(data, tree);
  await centreOn(page, target);
  const top = (e) => e.ends.every((id) => tree.parents[id] === tree.wrapper);
  const lines = async () => Object.fromEntries((await viewer(page, "aggregatedEdges")).filter((e) => e.drawn && top(e)).map((e) => [e.ends.join("|"), e]));
  // Compared at the step before the box opens and the step it opens at; an end drawn larger than its layout changes with every step.
  let before = await lines();
  const opened = await zoomInUntil(page, async () => {
    if ((await viewer(page, "openBoxes")).includes(target)) return true;
    before = await lines();
    return false;
  });
  expect(opened).toBe(true);
  const after = await lines();
  const grown = new Set((await viewer(page, "overviewPlan")).grown);
  expect(sorted(Object.keys(after))).toEqual(sorted(Object.keys(before)));
  const moved = Object.keys(after).filter((name) => {
    const [a, b] = [before[name], after[name]];
    if (JSON.stringify([a.forwardKeys, a.backwardKeys]) !== JSON.stringify([b.forwardKeys, b.backwardKeys])) return true;
    if (a.ends.some((id) => grown.has(id))) return false;
    return JSON.stringify(a.points) !== JSON.stringify(b.points);
  });
  expect(moved).toEqual([]);
});

test('a node inside an open box carries a "+N" mark for its outward edges not drawn at rest, and no other node carries one', async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const target = largestTopBox(data, tree);
  await zoomIntoBox(page, target);

  const open = new Set(await viewer(page, "openBoxes"));
  const edges = shownEdges(data);
  const expected = outwardOf(tree, open, edges, levelOf(tree, open, edges));
  const visible = new Set(await viewer(page, "visibleIds"));
  const marks = await viewer(page, "outwardMarks");
  const counts = Object.fromEntries(Object.entries(marks).map(([id, mark]) => [id, mark.count]));
  const wanted = Object.fromEntries([...expected].filter(([id]) => visible.has(id)).map(([id, keys]) => [id, keys.length]));
  requireShape(Object.keys(wanted).length > 0, "no node inside an open box has an edge to the outside");
  expect(counts).toEqual(wanted);
  // Each mark says its count, and those inside the canvas are drawn.
  expect(Object.entries(marks).filter(([, mark]) => mark.text !== `+${mark.count}`).map(([id]) => id)).toEqual([]);
  expect(Object.values(marks).some((mark) => mark.shown)).toBe(true);
});

test("hovering a node inside an open box draws its own outward edges on top, one line to each closed box; the pointer gone, they are not drawn", async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  const target = largestTopBox(data, tree);
  await zoomIntoBox(page, target);

  const marks = await viewer(page, "outwardMarks");
  const boxes = await viewer(page, "boxes");
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const reachable = (id) => {
    const b = boxes[id];
    const [x, y] = [(b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2];
    return b && x > canvas.x + 40 && x < canvas.x + canvas.width - 40 && y > canvas.y + 40 && y < canvas.y + canvas.height - 40 && !tree.boxes.has(id);
  };
  const [node] = Object.entries(marks).filter(([id]) => reachable(id)).sort((a, b) => b[1].count - a[1].count || (a[0] < b[0] ? -1 : 1))[0] || [];
  requireShape(Boolean(node), "no node with outward edges inside the canvas");
  const open = new Set(await viewer(page, "openBoxes"));
  const edges = shownEdges(data);
  const outward = outwardOf(tree, open, edges, levelOf(tree, open, edges)).get(node);
  const rest = new Set((await viewer(page, "edgeLooks")).map((look) => look.key));
  expect(outward.filter((key) => rest.has(key))).toEqual([]);

  const b = boxes[node];
  await page.mouse.move((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2);
  await expect.poll(async () => (await viewer(page, "ownLines")).length + (await viewer(page, "edgeLooks")).filter((l) => outward.includes(l.key)).length).toBeGreaterThan(0);
  const own = await viewer(page, "ownLines");
  const itself = (await viewer(page, "lineLooks")).filter((look) => look.key && outward.includes(look.key));
  const carried = sorted([...itself.map((look) => look.key), ...own.flatMap((line) => [...line.forwardKeys, ...line.backwardKeys])]);
  expect(carried).toEqual(outward);
  // On top: every one is followed, and a line of the box that carries them is not followed with them.
  const followed = new Set((await viewer(page, "followed")).edges.map((e) => e.id));
  expect([...itself.map((look) => look.id), ...own.map((line) => line.id)].filter((id) => !followed.has(id))).toEqual([]);
  const pairs = (await viewer(page, "aggregatedEdges")).filter((e) => e.drawn && e.ends.includes(target));
  expect(pairs.filter((e) => followed.has(e.id)).map((e) => e.id)).toEqual([]);
  // One line to each drawn end it reaches, from the node's border to that end's border.
  const drawn = await viewer(page, "nodeBoxes");
  expect(own.filter((line) => !line.ends.includes(node)).map((line) => line.id)).toEqual([]);
  const ends = own.map((line) => line.ends.find((id) => id !== node));
  expect(ends.length).toBe(new Set(ends).size);
  const off = own.filter((line) => {
    const [first, last] = [line.points[0], line.points[line.points.length - 1]];
    const [from, to] = line.ends[0] === node ? [first, last] : [last, first];
    return !onBorder(from, drawn[node]) || !onBorder(to, drawn[line.ends.find((id) => id !== node)]);
  });
  expect(off.map((line) => line.id)).toEqual([]);

  await page.mouse.move(2, 2);
  await expect.poll(async () => (await viewer(page, "ownLines")).length).toBe(0);
  expect((await viewer(page, "edgeLooks")).filter((look) => outward.includes(look.key)).map((look) => look.key)).toEqual([]);
});

/** Every node drawn inside an open box shorter on screen than a box closes at: what is drawn and cannot be read. */
async function unreadableNodes(page, tree) {
  const zoom = await viewer(page, "zoom");
  const boxes = await viewer(page, "nodeBoxes");
  const visible = await viewer(page, "visibleIds");
  return visible
    .filter((id) => tree.parents[id] && tree.parents[id] !== tree.wrapper && !tree.boxes.has(id))
    .filter((id) => (boxes[id].y2 - boxes[id].y1) * zoom < READABLE_PX * CLOSE_SHARE - 1e-6)
    .map((id) => `${id} ${((boxes[id].y2 - boxes[id].y1) * zoom).toFixed(1)} px`);
}

/** What a reader sees of the selected node `id` once the view has settled: whether it is drawn, its height on screen, and whether its centre is on the canvas. */
async function selectedSeen(page, id) {
  const zoom = await viewer(page, "zoom");
  const box = (await viewer(page, "nodeBoxes"))[id];
  const page_ = (await viewer(page, "boxes"))[id];
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const panel = await page.getByTestId("viewer-panel").boundingBox();
  const right = panel && panel.x < canvas.x + canvas.width ? panel.x : canvas.x + canvas.width;
  const centre = page_ ? { x: (page_.x1 + page_.x2) / 2, y: (page_.y1 + page_.y2) / 2 } : null;
  return {
    drawn: (await viewer(page, "visibleIds")).includes(id),
    tall: box ? (box.y2 - box.y1) * zoom >= READABLE_PX - 1e-6 : false,
    inCanvas: Boolean(centre) && centre.x > canvas.x && centre.x < right && centre.y > canvas.y && centre.y < canvas.y + canvas.height,
  };
}

test("selecting a node frames its neighbourhood at a zoom where it is drawn as itself and readable, and draws nothing unreadable: by the URL and a hub by the URL; a tap on a box frames the box whole", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const degree = degreesOf(data);
  const leaves = data.nodes.filter((n) => !tree.boxes.has(n.id) && tree.depth(n.id) >= 2);
  const quiet = leaves.filter((n) => (degree.get(n.id) || 0) > 0 && (degree.get(n.id) || 0) < HUB_DEGREE).sort((a, b) => tree.depth(b.id) - tree.depth(a.id) || (a.id < b.id ? -1 : 1))[0];
  const hub = [...degree].filter(([id, d]) => d >= HUB_DEGREE && !tree.boxes.has(id) && tree.parents[id] && tree.parents[id] !== tree.wrapper).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0]?.[0];
  requireShape(Boolean(quiet) && Boolean(hub), "no node two levels down with a few edges, or no hub inside a box");

  const found = {};
  for (const [name, id] of [["by the URL", quiet.id], ["a hub by the URL", hub]]) {
    await openArchitecture(page, `?focus=${encodeURIComponent(id)}`);
    await settled(page);
    found[name] = { ...(await selectedSeen(page, id)), unreadable: await unreadableNodes(page, tree), zoom: await viewer(page, "zoom") };
  }
  // A tap on a top-level box at the overview selects it: the view frames the whole box, open, even where
  // its nodes are drawn smaller than a reader reads (owner, 2026-10-06): the box is what was asked for.
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await twoFrames(page);
  const target = largestTopBox(data, tree);
  const b = (await viewer(page, "boxes"))[target];
  await page.mouse.click((b.x1 + b.x2) / 2, b.y1 + Math.min(12, (b.y2 - b.y1) / 4));
  await expect.poll(() => viewer(page, "selection")).toBe(target);
  await settled(page);
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const whole = (await viewer(page, "boxes"))[target];
  found["a tap on a box"] = {
    ...(await selectedSeen(page, target)),
    unreadable: [],
    whole: whole.x1 >= canvas.x && whole.x2 <= canvas.x + canvas.width && whole.y1 >= canvas.y && whole.y2 <= canvas.y + canvas.height && (await viewer(page, "openBoxes")).includes(target),
    zoom: await viewer(page, "zoom"),
  };
  const readable = { drawn: true, tall: true, inCanvas: true, unreadable: [] };
  const { boxes } = await viewer(page, "elkGeometry");
  test.info().annotations.push({ type: "measured", description: JSON.stringify(Object.fromEntries(Object.entries(found).map(([k, v]) => [k, v.zoom]))) });
  expect(Object.fromEntries(Object.entries(found).map(([k, v]) => [k, { drawn: v.drawn, tall: k === "a tap on a box" ? v.whole : v.tall, inCanvas: v.inCanvas, unreadable: v.unreadable }]))).toEqual({
    "by the URL": readable,
    "a hub by the URL": readable,
    "a tap on a box": readable,
  });
  // The leaf is framed at least at the zoom where every box holding it is readable.
  expect(found["by the URL"].zoom).toBeGreaterThanOrEqual(readableZoomOf(quiet.id, tree, boxes) - 1e-6);
});

/** Within this of each other, two zooms are one. */
const SAME_ZOOM = 1e-9;

/** The zooms the view is drawn at over the next `count` frames, each once, to six places. */
const zoomsOverFrames = (page, count) =>
  page.evaluate(
    (frames) =>
      new Promise((done) => {
        const out = [];
        const tick = () => {
          out.push(window.__beadloomViewer.zoom().toFixed(6));
          if (out.length < frames) requestAnimationFrame(tick);
          else done([...new Set(out)]);
        };
        requestAnimationFrame(tick);
      }),
    count
  );

// The move is judged by the viewer's own count of the frames it drew the move
// over (`move` on the handle), not by sampling the zoom from outside: the case
// can start reading only once the click has returned, and on a slow machine the
// 350 ms move is over by then. Measured with the CPU throttled 6x, the case run
// alone, in the viewer of 8.0.0 and of the next version: the 30 frames read after
// the click saw one zoom in 5 runs of 5, as a CI runner had seen once.
test("with reduced motion a selection's frame is reached at once; otherwise the view moves there over several frames", async ({ page, request }) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const target = largestTopBox(data, tree);
  const found = {};
  for (const motion of ["reduce", "no-preference"]) {
    await page.emulateMedia({ reducedMotion: motion });
    await openArchitecture(page);
    await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
    await twoFrames(page);
    const b = (await viewer(page, "boxes"))[target];
    const start = await viewer(page, "zoom");
    await page.mouse.click((b.x1 + b.x2) / 2, b.y1 + Math.min(12, (b.y2 - b.y1) / 4));
    // Reduced, nothing is left to move once the click has returned: every frame read shows one zoom.
    const seen = motion === "reduce" ? await zoomsOverFrames(page, 30) : null;
    await expect.poll(async () => (await viewer(page, "move"))?.done ?? false).toBe(true);
    const move = await viewer(page, "move");
    const zoom = await viewer(page, "zoom");
    found[motion] = {
      animated: move.animated,
      frames: move.frames,
      fromWhereItWas: Math.abs(move.from - start) < SAME_ZOOM,
      reached: Math.abs(move.to - start) > SAME_ZOOM && Math.abs(zoom - move.to) < SAME_ZOOM,
      ...(seen ? { oneZoomSeen: seen.length === 1 && seen[0] === move.to.toFixed(6) } : {}),
    };
  }
  test.info().annotations.push({ type: "measured", description: JSON.stringify(found) });
  // Reduced: the frame is reached in one frame of the viewer's.
  expect(found.reduce).toEqual({ animated: false, frames: 1, fromWhereItWas: true, reached: true, oneZoomSeen: true });
  // Otherwise: the view moves there over several.
  expect(found["no-preference"]).toMatchObject({ animated: true, fromWhereItWas: true, reached: true });
  expect(found["no-preference"].frames).toBeGreaterThan(1);
});

test("every line drawn is routed square, a loop from a node to its own box included: at the fit, zoomed into a box, a node hovered and selected, and every box open", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  const loops = drawnEdgesOf(data).filter((e) => withAncestors([e.src], tree.parents).has(e.dst) || withAncestors([e.dst], tree.parents).has(e.src));
  requireShape(loops.length > 0, "no edge from a node to a box that holds it");
  const found = {};
  await openArchitecture(page);
  found.fit = unroutedLines(await viewer(page, "lineLooks"));
  const target = largestTopBox(data, tree);
  await zoomIntoBox(page, target);
  found.open = unroutedLines(await viewer(page, "lineLooks"));
  const marks = await viewer(page, "outwardMarks");
  const [node] = Object.keys(marks).sort((a, b) => marks[b].count - marks[a].count || (a < b ? -1 : 1));
  if (node) {
    const b = (await viewer(page, "boxes"))[node];
    await page.mouse.move((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2);
    await twoFrames(page);
    found.hovered = unroutedLines(await viewer(page, "lineLooks"));
    await page.mouse.move(2, 2);
  }
  const loopNode = loops[0].src;
  await openArchitecture(page, `?focus=${encodeURIComponent(withAncestors([loops[0].src], tree.parents).has(loops[0].dst) ? loops[0].src : loops[0].dst)}`);
  await settled(page);
  found.selected = unroutedLines(await viewer(page, "lineLooks"));
  await openEveryBox(page);
  await twoFrames(page);
  found.everyBox = unroutedLines(await viewer(page, "lineLooks"));
  const drawnLoops = (await viewer(page, "edgeLooks")).filter((look) => loops.some((e) => e.key === look.key));
  expect(drawnLoops.length, `the loops, ${loopNode}'s among them, are drawn with every box open`).toBe(loops.length);
  expect(found).toEqual({ fit: [], open: [], ...(node ? { hovered: [] } : {}), selected: [], everyBox: [] });
});

test("zooming in from the fit, a top-level node drawn larger than its layout never gets smaller on screen: no level draws it at its laid-out size while larger reads", async ({
  page,
}) => {
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  const grown = (await viewer(page, "overviewPlan")).grown;
  requireShape(grown.length > 0, "no top-level node is drawn larger than its layout at the fit");
  const shrunk = [];
  const last = {};
  for (let step = 0; step < 16; step += 1) {
    const zoom = await viewer(page, "zoom");
    const boxes = await viewer(page, "nodeBoxes");
    for (const id of grown) {
      const size = { width: (boxes[id].x2 - boxes[id].x1) * zoom, height: (boxes[id].y2 - boxes[id].y1) * zoom };
      for (const side of ["width", "height"]) {
        if (last[id] && size[side] < last[id][side] - 0.5) shrunk.push(`${id}'s ${side} at zoom ${zoom.toFixed(3)}: ${last[id][side].toFixed(1)} -> ${size[side].toFixed(1)} px`);
      }
      last[id] = size;
    }
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
  }
  expect(shrunk).toEqual([]);
});

/** How many toolbar steps past the zoom where every box's nodes are readable the title cases look again. */
const STEPS_PAST_READABLE = 4;

/**
 * What covers the title of an open box on the canvas now: `{ covered, read, over }`.
 * `covered` lists `"state: …"`, each a drawn node other than the box and the
 * boxes holding it whose shape reaches into the title, a line that runs through
 * a title not drawn again over the lines on top, or a count's pill over it;
 * `read` counts the titles read, so a case can tell none covered from none
 * drawn, and `over` names the boxes whose title the layer of followed lines
 * draws again over them.
 */
async function coveredTitles(page, tree, state) {
  const view = { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
  const titles = await viewer(page, "boxTitles");
  const shown = new Set(await viewer(page, "visibleIds"));
  const boxes = Object.entries(await viewer(page, "nodeBoxes")).filter(([id]) => shown.has(id));
  const segments = segmentsOf(await viewer(page, "lineLooks"), view);
  const { pills } = await viewer(page, "pills");
  const over = (await viewer(page, "followed")).passes.find((pass) => pass.name === "titles")?.boxes || [];
  const covered = titles.flatMap((title) => {
    const own = withAncestors([title.id], tree.parents);
    const across = over.includes(title.id) ? [] : [...new Set(segments.filter((s) => segmentInRect(s.a, s.b, title)).map((s) => s.id))];
    return [
      ...boxes.filter(([id, box]) => !own.has(id) && rectsOverlap(title, boxOnScreen(box, view))).map(([id]) => `${state}: the title of ${title.id} under ${id}`),
      ...across.map((id) => `${state}: ${id} across the title of ${title.id}`),
      ...pills.filter((pill) => rectsOverlap(title, pill)).map((pill) => `${state}: the pill of ${pill.id} over the title of ${title.id}`),
    ];
  });
  return { covered, read: titles.length, over };
}

/** The most the title case drags the view by at once, in pixels, so the pointer stays on the page. */
const DRAG_STEP_PX = 250;
/** How near the canvas's middle a node is brought, in pixels. */
const NEAR_MIDDLE_PX = 20;

/** Drag the view, from the canvas's middle, until node `id` is there: it may start off the canvas, where no drag can start. */
async function bringToMiddle(page, id) {
  const canvas = page.getByTestId("graph-canvas");
  await canvas.scrollIntoViewIfNeeded();
  const area = await canvas.boundingBox();
  const middle = { x: area.x + area.width / 2, y: area.y + area.height / 2 };
  const clamp = (d) => Math.max(-DRAG_STEP_PX, Math.min(DRAG_STEP_PX, d));
  for (let step = 0; step < ZOOM_STEPS; step += 1) {
    const b = (await viewer(page, "boxes"))[id];
    const [dx, dy] = [middle.x - (b.x1 + b.x2) / 2, middle.y - (b.y1 + b.y2) / 2];
    if (Math.hypot(dx, dy) <= NEAR_MIDDLE_PX) return;
    await drag(page, middle, clamp(dx), clamp(dy));
    await twoFrames(page);
  }
}

/** Open every box, with its edges drawn as themselves or not, and zoom in until every box's nodes are readable. */
async function everyBoxReadable(page, tree, { edges }) {
  await openEveryBox(page, { edges });
  const { boxes } = await viewer(page, "elkGeometry");
  const readable = Math.max(...[...smallestChildOf(tree, boxes).values()].map((height) => READABLE_PX / height));
  await zoomInUntil(page, async () => (await viewer(page, "zoom")) >= readable);
  await settled(page);
}

test("no open box's title is covered by a node or crossed by a line: in a box opened by zooming into it, and with every box open at the zoom its nodes are readable at and further in", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  requireShape(tree.boxes.size > 0, "no box in the containment tree");
  await openArchitecture(page);
  const covered = [];
  let read = 0;
  const look = async (state) => {
    const found = await coveredTitles(page, tree, state);
    covered.push(...found.covered);
    read += found.read;
  };
  await look("at the fit");
  if (tree.topBoxes.length) {
    const target = largestTopBox(data, tree);
    await zoomIntoBox(page, target);
    await look(`${target} opened by zooming in`);
  }

  await openArchitecture(page);
  await everyBoxReadable(page, tree, { edges: false });
  await look(`every box open at zoom ${(await viewer(page, "zoom")).toFixed(3)}`);
  for (let step = 0; step < STEPS_PAST_READABLE; step += 1) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await twoFrames(page);
  }
  await settled(page);
  await look(`every box open at zoom ${(await viewer(page, "zoom")).toFixed(3)}`);
  test.info().annotations.push({ type: "measured", description: `${read} open-box titles read over four states; ${covered.length} covered` });
  expect(read).toBeGreaterThan(0);
  expect(covered).toEqual([]);
});

test("a line drawn on top through an open box's title, as a hovered node's line into the first row of another box can run, runs under it: the title is drawn again over the lines on top", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const tree = treeOf(data);
  await openArchitecture(page);
  // Every edge drawn as itself: the lines a node's pointer can bring on top, and which of them runs through a title.
  await everyBoxReadable(page, tree, { edges: true });
  const view = { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
  const titles = await viewer(page, "boxTitles");
  const through = (await viewer(page, "edgeRoutes"))
    .filter((look) => look.key && !look.loop && !tree.boxes.has(look.source))
    .map((look) => ({ look, title: titles.find((t) => segmentsOf([look], view).some((s) => segmentInRect(s.a, s.b, t))) }))
    .filter(({ title }) => title)
    .sort((a, b) => (a.look.key < b.look.key ? -1 : 1))[0];
  requireShape(Boolean(through), "no edge between two open boxes whose line runs through the title of one of them");
  const { look, title } = through;

  await everyBoxReadable(page, tree, { edges: false });
  await bringToMiddle(page, look.source);
  const b = (await viewer(page, "boxes"))[look.source];
  // From off the node, so the pointer arrives on it after the drag that centred it.
  await page.mouse.move(2, 2);
  await page.mouse.move((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2, { steps: 4 });
  await expect.poll(async () => (await viewer(page, "followed")).edges.length).toBeGreaterThan(0);
  const found = await coveredTitles(page, tree, `the pointer on ${look.source}`);
  test.info().annotations.push({ type: "measured", description: `${look.key} runs through the title of ${title.id}; drawn again over the lines on top: ${found.over.join(", ") || "none"}` });
  expect(found.covered).toEqual([]);
  expect(found.over).toContain(title.id);
});
