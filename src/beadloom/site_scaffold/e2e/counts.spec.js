// One count per node and per line: the "+N" a node carries, the edges a hover draws and the edges a click draws agree, at every zoom.
//
// In the viewer before this rule, a reader zoomed into a box saw "+4" on a node,
// pointed at it and saw three lines, clicked it and saw four: the click opened
// the boxes its neighbours sit in and drew each edge to its node, the hover drew
// one line to each closed box, and the line carrying two edges said so only on a
// pill the reader had to find. Selected and zoomed out until the node folded into
// its box, the line to another box said the 27 edges the two boxes exchange, not
// the one edge of the node. A click on a box walked the box's own few edges, all
// into it, and none of the edges leaving its parts.
//
// The rule (owner, 2026-10-06): the "+N" on a node names exactly its edges the
// level does not draw as lines of its own, and pointing at it or clicking it
// draws exactly those N edges, on the same lines, each line of the map saying how
// many it carries, one included; while a node is selected every line of its walk
// says the selected node's count; a click on a box frames the whole box open, its
// contents at full strength, and its lines to the outside as a hover shows them.
//
// The expected edges come from the data file (`support/map.js`,
// `support/counts.js`); the cases read what was drawn through the test handle and
// compare no pixels. The reader's way is followed: every node is reached by a
// click on the card of a node next to it, so each is read at the zoom a
// selection frames it at, and pointed at with the pointer there.

import { test, expect } from "@playwright/test";
import { drawnEdgesOf, treeOf } from "./support/map.js";
import { settled, twoFrames } from "./support/levels.js";
import {
  boxSummaryOf,
  drawnLines,
  edgesOfNode,
  holdersOf,
  isWithin,
  linesCarrying,
  outwardKeysOf,
  wrongNumbers,
  wrongWalkNumbers,
} from "./support/counts.js";
import { requireShape } from "./support/shape.js";
import { architectureData, openArchitecture, viewer } from "./support/viewer.js";

/** How many cases the nodes are read in, each a share of the top-level boxes, so they run side by side. */
const PARTS = 4;
/** How far inside the canvas, past the panel, a box framed whole keeps from every edge, in pixels. */
const FRAME_MARGIN_PX = 10;
/** The most "Zoom out" presses a case takes to fold a selected node into its box. */
const FOLD_STEPS = 8;
/** How long a part may take: every node of a large portal is clicked, pointed at and zoomed out from. */
const PART_MS = 300_000;

/** Record a reading on the case's report. */
function measured(description) {
  test.info().annotations.push({ type: "measured", description });
}

/** The nodes read by part `part`: the subtrees of every PARTS-th node at the top, in id order. */
function partOf(data, tree, part) {
  const top = Object.keys(tree.parents).filter((id) => id !== tree.wrapper && (tree.parents[id] || null) === tree.wrapper).sort();
  const mine = new Set(top.filter((_, k) => k % PARTS === part));
  return data.nodes.map((n) => n.id).filter((id) => id !== tree.wrapper && [...mine].some((box) => isWithin(tree, id, box))).sort();
}

/** Each node's neighbours by the drawn edges, either way. */
function neighboursOf(edges) {
  const out = new Map();
  for (const { src, dst } of edges) {
    for (const [a, b] of [[src, dst], [dst, src]]) out.set(a, [...(out.get(a) || []), b]);
  }
  return out;
}

/** The shortest walk over `neighbours` from `from` to the nearest node in `wanted`, the nodes after `from`; null when none is reachable. */
function pathTo(neighbours, from, wanted) {
  const previous = new Map([[from, null]]);
  const queue = [from];
  while (queue.length) {
    const id = queue.shift();
    if (wanted.has(id) && id !== from) {
      const path = [];
      for (let cursor = id; cursor !== from; cursor = previous.get(cursor)) path.unshift(cursor);
      return path;
    }
    for (const next of [...(neighbours.get(id) || [])].sort()) {
      if (previous.has(next)) continue;
      previous.set(next, id);
      queue.push(next);
    }
  }
  return null;
}

/**
 * Where the pointer reaches node `id` on the page, the canvas scrolled into
 * view: its middle, or for a box the band its title is drawn in, which none of
 * its nodes covers; null when it is not drawn.
 */
async function centreOf(page, id) {
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  const box = (await viewer(page, "boxes"))[id];
  if (!box) return null;
  return { x: (box.x1 + box.x2) / 2, y: box.isParent ? box.y1 + Math.min(12, (box.y2 - box.y1) / 4) : (box.y1 + box.y2) / 2 };
}

/** Select `id` by a click on the selected node's card, where it is one of the node's edges' other ends. */
async function selectFromCard(page, id) {
  await page.locator(`[data-card-field="edges"] [data-edge-target="${id.replace(/"/g, '\\"')}"]`).first().click();
  await expect.poll(() => viewer(page, "selection")).toBe(id);
  await settled(page);
}

/** Point at `id` from away from it, and wait for what the pointer draws; true when it reached the node. */
async function pointAt(page, id) {
  const centre = await centreOf(page, id);
  if (!centre) return false;
  await page.mouse.move(2, 2);
  await twoFrames(page);
  await page.mouse.move(centre.x, centre.y);
  await expect.poll(async () => (await viewer(page, "lineLooks")).some((look) => look.front) || (await viewer(page, "ownLines")).length > 0, { timeout: 2000 }).toBe(true).catch(() => {});
  await twoFrames(page);
  return true;
}

/**
 * Read node `id` the reader's way, from the moment it is selected: what its
 * selection draws, its "+N" with nothing selected, what pointing at it draws,
 * and, selected again and zoomed out until it folds into its box, what the
 * lines of its walk say. `wrong` collects every disagreement.
 */
async function readNode(page, { tree, edges }, id, wrong) {
  const outward = outwardKeysOf(tree, edges, id);
  const own = edgesOfNode(tree, edges, id);
  // Selected: the lines of the node carry its outward edges, each line saying how many.
  await page.mouse.move(2, 2);
  await twoFrames(page);
  const selectedLines = await drawnLines(page);
  const click = linesCarrying(selectedLines, id, outward);
  for (const text of wrongWalkNumbers(selectedLines, own)) wrong.push(`${id} selected: ${text}`);
  // Nothing selected, the same view: the mark, and what the pointer on the node draws.
  await page.getByRole("button", { name: "Close the card" }).click();
  await expect.poll(() => viewer(page, "selection")).toBe(null);
  await settled(page);
  const openNow = new Set(await viewer(page, "openBoxes"));
  const mark = (await viewer(page, "outwardMarks"))[id]?.count ?? 0;
  const isOpen = openNow.has(id);
  let hover = null;
  if (!isOpen && (await pointAt(page, id))) hover = linesCarrying(await drawnLines(page), id, outward);
  const n = outward.length;
  if (!isOpen && mark !== n) wrong.push(`${id}: "+${mark}", ${n} outward edges`);
  if (click.keys.join() !== outward.join() || click.twice.length) wrong.push(`${id} selected draws ${click.keys.length} of its ${n} outward edges${click.twice.length ? `, ${click.twice.length} twice` : ""}`);
  if (hover && (hover.keys.join() !== outward.join() || hover.twice.length)) wrong.push(`${id} pointed at draws ${hover.keys.length} of its ${n} outward edges${hover.twice.length ? `, ${hover.twice.length} twice` : ""}`);
  if (hover && JSON.stringify(sortedRecord(hover.lines)) !== JSON.stringify(sortedRecord(click.lines))) wrong.push(`${id}: a hover draws ${JSON.stringify(hover.lines)}, a click ${JSON.stringify(click.lines)}`);
  for (const text of [...wrongNumbers(click), ...(hover ? wrongNumbers(hover) : [])]) wrong.push(`${id}: ${text}`);
  // Selected again, zoomed out until it folds into its box: the walk's lines say its count.
  const centre = await centreOf(page, id);
  await page.mouse.move(2, 2);
  if (centre) await page.mouse.click(centre.x, centre.y);
  await expect.poll(() => viewer(page, "selection")).toBe(id);
  await settled(page);
  // A node at the top folds into nothing, and its lines at the fit are what the overview draws.
  if (!holdersOf(tree, id).some((box) => box !== tree.wrapper)) return { mark, n, hoverLines: hover ? Object.keys(hover.lines).length : null, clickLines: Object.keys(click.lines).length, walkLines: null };
  for (let step = 0; step < FOLD_STEPS && (await viewer(page, "visibleIds")).includes(id); step += 1) {
    await page.getByRole("button", { name: "Zoom out", exact: true }).click();
    await settled(page);
  }
  const folded = await drawnLines(page);
  for (const text of wrongWalkNumbers(folded, own)) wrong.push(`${id} selected, zoomed out to ${(await viewer(page, "zoom")).toFixed(3)}: ${text}`);
  return { mark, n, hoverLines: hover ? Object.keys(hover.lines).length : null, clickLines: Object.keys(click.lines).length, walkLines: folded.filter((line) => line.walk).length, crowded: folded.filter((line) => line.walk && line.crowded).length };
}

for (let part = 0; part < PARTS; part += 1) {
  test(`every node, part ${part + 1} of ${PARTS}: its "+N", what pointing at it draws and what clicking it draws are the same edges on the same lines, and selected it says its own count on every line of its walk, framed and zoomed out`, async ({ page, request }) => {
    test.setTimeout(PART_MS);
    await page.emulateMedia({ reducedMotion: "reduce" });
    const data = await architectureData(request);
    const tree = treeOf(data);
    const edges = drawnEdgesOf(data);
    const neighbours = neighboursOf(edges);
    const subjects = partOf(data, tree, part);
    requireShape(subjects.length > 0, `no node under the ${PARTS}-part split of the top level for part ${part + 1}`);
    const todo = new Set(subjects);
    const wrong = [];
    const readings = {};
    let current = null;
    while (todo.size) {
      const path = current ? pathTo(neighbours, current, todo) : null;
      if (!path) {
        current = [...todo][0];
        await openArchitecture(page, `?focus=${encodeURIComponent(current)}`);
        await settled(page);
      } else {
        for (const hop of path) await selectFromCard(page, hop);
        current = path[path.length - 1];
      }
      todo.delete(current);
      readings[current] = await readNode(page, { tree, edges }, current, wrong);
    }
    const marked = Object.values(readings).filter((r) => r.n > 0).length;
    const crowded = Object.values(readings).reduce((sum, r) => sum + (r.crowded || 0), 0);
    measured(`${subjects.length} node(s) read, ${marked} with an outward edge; "+N" ${JSON.stringify(Object.fromEntries(Object.entries(readings).filter(([, r]) => r.n > 0).map(([id, r]) => [id, `+${r.mark} of ${r.n}, ${r.hoverLines ?? "-"} line(s) pointed at, ${r.clickLines} clicked`])))}; ${crowded} pill(s) of a walk zoomed out standing where they cover something, for want of a free place; ${wrong.length} disagreement(s)`);

    expect(wrong).toEqual([]);
  });
}

test("a click on every top-level box frames the whole box open, leaves its contents at full strength, draws its lines to the outside as pointing at it does and dims the rest, and its card says what it holds and where its edges go", async ({ page, request }) => {
  test.setTimeout(PART_MS);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const data = await architectureData(request);
  const tree = treeOf(data);
  const edges = drawnEdgesOf(data);
  const top = Object.keys(tree.parents).filter((id) => id !== tree.wrapper && (tree.parents[id] || null) === tree.wrapper);
  const boxes = tree.topBoxes.filter((id) => id !== tree.wrapper).sort();
  requireShape(boxes.length > 0, "no box at the top of the containment tree");
  const wrong = [];
  const read = {};
  for (const box of boxes) {
    await openArchitecture(page);
    await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
    await twoFrames(page);
    const at = (await viewer(page, "boxes"))[box];
    const point = { x: (at.x1 + at.x2) / 2, y: at.y1 + Math.min(12, (at.y2 - at.y1) / 4) };
    await page.mouse.move(2, 2);
    await twoFrames(page);
    await page.mouse.move(point.x, point.y);
    await expect.poll(async () => (await viewer(page, "lineLooks")).some((look) => look.front), { timeout: 2000 }).toBe(true).catch(() => {});
    // A line onto a box that holds this one is a loop, no line to a neighbour.
    const toNeighbour = (line) => line.ends.includes(box) && !holdersOf(tree, box).includes(line.ends.find((end) => end !== box));
    const pointed = (await drawnLines(page)).filter((line) => line.front && toNeighbour(line));
    // What a line says; a pill with no room on its line is left out, its count in the note over the line.
    const hovered = Object.fromEntries(pointed.map((line) => [line.ends.find((end) => end !== box), line.map ? line.label : "1"]));
    const unplaced = pointed.filter((line) => line.map && line.pill === null).length;
    await page.mouse.click(point.x, point.y);
    await expect.poll(() => viewer(page, "selection")).toBe(box);
    await settled(page);
    await page.mouse.move(2, 2);
    await twoFrames(page);
    // (1) Open, and framed whole: inside the canvas the panel leaves, with a margin.
    const canvas = await page.getByTestId("graph-canvas").boundingBox();
    const panel = await page.getByTestId("viewer-panel").boundingBox();
    const right = panel && panel.x < canvas.x + canvas.width ? panel.x : canvas.x + canvas.width;
    const drawn = (await viewer(page, "boxes"))[box];
    const margins = [drawn.x1 - canvas.x, right - drawn.x2, drawn.y1 - canvas.y, canvas.y + canvas.height - drawn.y2];
    if (!(await viewer(page, "openBoxes")).includes(box)) wrong.push(`${box}: not open`);
    if (Math.min(...margins) < FRAME_MARGIN_PX) wrong.push(`${box}: framed with margins ${margins.map((m) => m.toFixed(0)).join("/")} px`);
    // (2) Nothing inside dimmed, no line between two of its parts dimmed.
    const dimmed = new Set(await viewer(page, "dimmedIds"));
    const inside = [...dimmed].filter((id) => id !== box && isWithin(tree, id, box));
    if (inside.length) wrong.push(`${box}: ${inside.length} node(s) inside dimmed: ${inside.slice(0, 5).join(", ")}`);
    const lines = await drawnLines(page);
    const innerDimmed = lines.filter((line) => line.dimmed && line.ends.every((end) => isWithin(tree, end, box)));
    if (innerDimmed.length) wrong.push(`${box}: ${innerDimmed.length} line(s) inside dimmed`);
    // (3) Its lines to the outside as pointing at it drew them, saying the same; their other ends at full strength, every other top-level node dimmed.
    const walkLines = lines.filter((line) => line.walk && toNeighbour(line));
    const walked = Object.fromEntries(walkLines.map((line) => [line.ends.find((end) => end !== box), line.map ? line.label : "1"]));
    if (JSON.stringify(sortedRecord(walked)) !== JSON.stringify(sortedRecord(hovered))) wrong.push(`${box}: pointed at ${JSON.stringify(hovered)}, clicked ${JSON.stringify(walked)}`);
    const neighbours = new Set(Object.keys(walked));
    for (const id of top) {
      if (id === box) continue;
      const isDimmed = dimmed.has(id);
      if (neighbours.has(id) && isDimmed) wrong.push(`${box}: its neighbour ${id} dimmed`);
      if (!neighbours.has(id) && !isDimmed && (await viewer(page, "visibleIds")).includes(id)) wrong.push(`${box}: ${id}, no neighbour, not dimmed`);
    }
    // (4) The card: how many nodes it holds, and how many edges go out to and come in from each neighbour.
    const summary = boxSummaryOf(tree, edges, box);
    const card = page.locator('[data-card-field="contents"]');
    const said = (await card.count())
      ? await card.evaluate((element) => ({
          inside: Number(element.querySelector("[data-contents-inside]")?.dataset.contentsInside),
          out: Object.fromEntries([...element.querySelectorAll("[data-contents-out]")].map((e) => [e.dataset.contentsOut, Number(e.dataset.count)])),
          in: Object.fromEntries([...element.querySelectorAll("[data-contents-in]")].map((e) => [e.dataset.contentsIn, Number(e.dataset.count)])),
        }))
      : null;
    if (JSON.stringify(said) !== JSON.stringify({ inside: summary.inside, out: sortedRecord(summary.out), in: sortedRecord(summary.in) })) wrong.push(`${box}: the card says ${JSON.stringify(said)}, the data file ${JSON.stringify(summary)}`);
    read[box] = { zoom: Number((await viewer(page, "zoom")).toFixed(3)), lines: Object.keys(walked).length, margin: Math.round(Math.min(...margins)), pillsWithoutRoom: { pointed: unplaced, clicked: walkLines.filter((line) => line.map && line.pill === null).length } };
  }
  measured(`${boxes.length} top-level box(es) clicked: ${JSON.stringify(read)}; ${wrong.length} disagreement(s)`);

  expect(wrong).toEqual([]);
});

/** `record` with its keys in code-unit order, as the card lists them. */
function sortedRecord(record) {
  return Object.fromEntries(Object.entries(record).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}
