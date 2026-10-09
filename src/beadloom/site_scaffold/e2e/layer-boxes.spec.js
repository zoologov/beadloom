// A rule scoped to a box draws its layers as boxes inside that box.
//
// The owner's ruling of 2026-10-08: layers as drawn boxes. A
// Feature-Sliced frontend is a service whose slices sit in six layers; before,
// the viewer drew the first layer rule only, so this portal's twenty site slices
// were drawn side by side in their service's box, in the tone of the service's
// layer, with no red line where `lint` judged them. Now a rule whose scope is a box inside the project's frame draws
// one box per layer inside its scope, derived from the rule and not a node of the
// graph: each holds the scope's own parts in that layer, is drawn in the layer's
// tone and titled by its name, opens once its parts are readable like any box,
// and the lines between layers end on it. A rule scoped to the frame itself draws
// its layers as lanes, as it always did, so a project of one rule is drawn as
// before. Every expected answer is read from the data file
// (`support/layers.js`), never from the viewer.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, openEveryBox, parentMap, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";
import { edgeKey } from "./support/graph.js";
import { drawnParentMap, layerBoxesOf, layerOfNode, layersOfData, withoutLayerRules } from "./support/layers.js";
import { canvasBackground, channelDistance, legendSamples } from "./support/look.js";
import { drawnEdgesOf, levelOf, smallestChildOf, treeOf } from "./support/map.js";
import { CLOSE_SHARE, READABLE_PX, againstReadability, settled, twoFrames, zoomIntoBox } from "./support/levels.js";
import { rectsOverlap, segmentInRect } from "./support/overview.js";

const LACKING_SCOPED_RULE =
  "no layer rule is scoped to a box inside the project's frame; a frontend service's slices tagged by their own layer rule are";

/** The data file and the boxes its scoped rules draw, the case skipped where there are none. */
async function scopedData(request) {
  const data = await architectureData(request);
  const boxes = layerBoxesOf(data);
  requireShape(boxes.length > 0, LACKING_SCOPED_RULE);
  return { data, boxes };
}

/** A box on screen, `{ x1, y1, x2, y2 }`, of a box in graph coordinates at the view `level` reports. */
function onScreen(box, { zoom, pan }) {
  return { x1: box.x1 * zoom + pan.x, y1: box.y1 * zoom + pan.y, x2: box.x2 * zoom + pan.x, y2: box.y2 * zoom + pan.y };
}

test("a rule scoped to a box draws one box per layer inside it, each holding the scope's own parts in that layer, titled and toned by the layer", async ({
  page,
  request,
}) => {
  const { data, boxes } = await scopedData(request);
  await openArchitecture(page);
  await openEveryBox(page, { edges: false });

  const drawn = await viewer(page, "boxes");
  const looks = new Map((await viewer(page, "nodeLooks")).map((look) => [look.id, look]));
  const titles = new Map((await viewer(page, "boxTitles")).map((title) => [title.id, title.text]));
  const samples = await legendSamples(page);
  const layers = layersOfData(data);
  const off = [];
  for (const box of boxes) {
    const layer = layers.find((l) => l.rule === box.rule && l.rank === box.rank);
    if (!drawn[box.id]) {
      off.push(`${box.id}: not drawn`);
      continue;
    }
    if (drawn[box.id].parent !== box.scope) off.push(`${box.id}: in ${drawn[box.id].parent}, not in ${box.scope}`);
    const held = Object.entries(drawn).filter(([, b]) => b.parent === box.id).map(([id]) => id).sort();
    if (JSON.stringify(held) !== JSON.stringify(box.members)) off.push(`${box.id}: holds ${held.join(", ")}, not ${box.members.join(", ")}`);
    if (titles.get(box.id) !== box.name) off.push(`${box.id}: titled "${titles.get(box.id)}", not "${box.name}"`);
    const tone = samples.get(layer.label)?.tone;
    if (!tone || channelDistance(looks.get(box.id)?.borderColour, tone) > 0) off.push(`${box.id}: border ${looks.get(box.id)?.borderColour}, its layer's ${tone}`);
  }
  // Nothing the scope holds directly is in a layer of its rule: each such part is in its layer's box.
  const scopes = new Set(boxes.map((box) => box.scope));
  const ruled = new Set(boxes.map((box) => box.rule));
  for (const node of data.nodes) {
    const layer = layerOfNode(node, data, layers);
    if (scopes.has(node.parent) && layer && ruled.has(layer.rule) && !String(drawn[node.id]?.parent).startsWith("layer:")) {
      off.push(`${node.id}: in ${drawn[node.id]?.parent}, outside its layer's box`);
    }
  }
  expect(off).toEqual([]);
});

test("the scope opens onto its layers, closed, each title inside its box with no line under it, and a layer box opens once its parts are readable", async ({
  page,
  request,
}) => {
  const { data, boxes } = await scopedData(request);
  const scope = boxes[0].scope;
  const ofScope = boxes.filter((box) => box.scope === scope);
  await openArchitecture(page);
  await zoomIntoBox(page, scope);
  await settled(page);

  const level = await viewer(page, "level");
  const view = { zoom: level.zoom, pan: await viewer(page, "pan") };
  const collapsed = new Set(level.collapsed.map((box) => box.id));
  expect(ofScope.filter((box) => !collapsed.has(box.id)).map((box) => box.id)).toEqual([]);

  const nodeBoxes = await viewer(page, "nodeBoxes");
  const titles = new Map((await viewer(page, "titles")).map((title) => [title.id, title]));
  const lines = (await viewer(page, "lineLooks")).filter((look) => look.points?.length > 1);
  const off = [];
  for (const box of ofScope) {
    const title = titles.get(box.id);
    if (!title) {
      off.push(`${box.id}: no title`);
      continue;
    }
    if (title.text !== box.name) off.push(`${box.id}: titled "${title.text}"`);
    const rect = onScreen(nodeBoxes[box.id], view);
    if (!title.inside || title.x1 < rect.x1 - 0.5 || title.x2 > rect.x2 + 0.5 || title.y1 < rect.y1 - 0.5 || title.y2 > rect.y2 + 0.5) {
      off.push(`${box.id}: title [${title.x1.toFixed(1)}, ${title.y1.toFixed(1)}, ${title.x2.toFixed(1)}, ${title.y2.toFixed(1)}] outside its box [${rect.x1.toFixed(1)}, ${rect.y1.toFixed(1)}, ${rect.x2.toFixed(1)}, ${rect.y2.toFixed(1)}]`);
    }
    for (const line of lines) {
      const points = line.points.map((p) => ({ x: p.x * view.zoom + view.pan.x, y: p.y * view.zoom + view.pan.y }));
      if (points.slice(1).some((p, i) => segmentInRect(points[i], p, title))) off.push(`${line.id} runs under the title of ${box.id}`);
    }
  }
  expect(off).toEqual([]);

  // Zoomed further into the layer with the most parts, it opens by the rule every box opens by.
  const widest = [...ofScope].sort((a, b) => b.members.length - a.members.length)[0];
  await zoomIntoBox(page, widest.id);
  await settled(page);
  const tree = treeOf(data);
  const geometry = await viewer(page, "elkGeometry");
  expect(againstReadability(await viewer(page, "level"), tree, geometry.boxes, smallestChildOf(tree, geometry.boxes))).toEqual([]);
});

test("with the scope open, the lines between its layers are drawn between their boxes, each carrying the edges between them", async ({
  page,
  request,
}) => {
  const { data, boxes } = await scopedData(request);
  const scope = boxes[0].scope;
  await openArchitecture(page);
  await zoomIntoBox(page, scope);
  await settled(page);

  const tree = treeOf(data);
  const level = await viewer(page, "level");
  const ids = new Set(boxes.filter((box) => box.scope === scope).map((box) => box.id));
  const wanted = [...levelOf(tree, new Set(level.open), drawnEdgesOf(data)).pairs.values()]
    .filter(({ ends }) => ends.every((end) => ids.has(end)))
    .map(({ ends, forward, backward }) => `${ends.join(" | ")}: ${forward.length} + ${backward.length}`)
    .sort();
  const drawn = (await viewer(page, "aggregatedEdges"))
    .filter(({ ends }) => ends.every((end) => ids.has(end)))
    .map(({ ends, forwardKeys, backwardKeys }) => `${ends.join(" | ")}: ${forwardKeys.length} + ${backwardKeys.length}`)
    .sort();
  expect(wanted.length).toBeGreaterThan(0);
  expect(drawn).toEqual(wanted);
});

test("an edge the scoped rule finds against is drawn red, between the layer boxes and as itself", async ({
  page,
  request,
}) => {
  const { data, boxes } = await scopedData(request);
  // One finding introduced on purpose: the lowest layer's part depends on the highest layer's,
  // against the rule's order, so lint finds against it and the data file marks it a violation.
  const ofRule = boxes.filter((box) => box.rule === boxes[0].rule).sort((a, b) => a.rank - b.rank);
  const [upper, lower] = [ofRule[0], ofRule[ofRule.length - 1]];
  requireShape(upper.rank < lower.rank, "a scoped layer rule with parts in two of its layers");
  const finding = { src: lower.members[0], dst: upper.members[0], kind: "depends_on", violation: true };
  const served = { ...data, edges: [...data.edges, finding] };
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: served }));
  await openArchitecture(page);
  await zoomIntoBox(page, upper.scope);
  await settled(page);

  const pair = [upper.id, lower.id].sort().join(" ");
  const carrying = (await viewer(page, "aggregatedEdges")).filter((line) => line.drawn && [...line.ends].sort().join(" ") === pair);
  const styles = new Map((await viewer(page, "lineLooks")).map((look) => [look.id, look.styleKey]));
  expect(carrying.map((line) => styles.get(line.id))).toEqual(["violation"]);

  await openEveryBox(page);
  const own = (await viewer(page, "lineLooks")).filter((look) => !look.aggregated && look.key === edgeKey(finding));
  expect(own.map((look) => look.styleKey)).toEqual(["violation"]);
});

// A layer box's title obeys the rule every box's title does (owner, 2026-10-08):
// sized by its box at 14, 12.5, 11 or 10 px, a plate only as the exception, and
// never over another title or a box. Below the size its parts are readable at, a
// layer box is not drawn at all, as the nodes of a closed box are not. Before, a
// tap on the scope at the fit framed it whole and forced it open at any zoom, so
// its six layer boxes were drawn 12 to 22 px tall with their titles on plates
// over each other's boxes and titles (this portal: five overlaps at zoom 0.128).
// A tap still frames the scope whole; it opens onto its layer boxes where they
// are readable, as a reader's zoom opens any box.

/** The smallest size a box's title is drawn at, in pixels. */
const SMALLEST_TITLE_PX = 10;
/**
 * The least it may read on screen: within half of the step the map restyles its
 * marks at (1.25), since a mark keeps one size on screen only between steps.
 */
const SMALLEST_ON_SCREEN_PX = SMALLEST_TITLE_PX / Math.sqrt(1.25);
/** How far two rectangles may share before they overlap, in pixels: a stroke's antialiasing. */
const TOUCH_PX = 0.5;
/** The most zoom steps the case takes in from the frame. */
const ZOOM_STEPS = 24;
/** The zoom steps the case takes past the one the scope opens at. */
const PAST_OPENING = 3;

/**
 * What is wrong with the titles the map draws now, a closed box's or a top-level
 * node's: one over another, or over a box that neither is its own nor holds it,
 * and a layer box of `layerBoxIds` drawn closed without its title inside it at
 * `SMALLEST_TITLE_PX` or more, within a step of the map's scale
 * (`SMALLEST_ON_SCREEN_PX`). An open box's title is drawn at its layout's size,
 * as every open box's is, and is not read here. `parents` is the containment
 * drawn (`drawnParentMap`).
 */
async function titlesWrong(page, layerBoxIds, parents) {
  const view = { zoom: await viewer(page, "zoom"), pan: await viewer(page, "pan") };
  const titles = await viewer(page, "titles");
  const nodeBoxes = await viewer(page, "nodeBoxes");
  const closed = new Set((await viewer(page, "level")).collapsed.map((box) => box.id));
  const holds = (outer, id) => {
    for (let cursor = parents[id]; cursor; cursor = parents[cursor]) if (cursor === outer) return true;
    return false;
  };
  const wrong = [];
  for (const [index, title] of titles.entries()) {
    for (const other of titles.slice(index + 1)) if (rectsOverlap(title, other, TOUCH_PX)) wrong.push(`${title.id}'s title over ${other.id}'s`);
    for (const [id, box] of Object.entries(nodeBoxes)) {
      if (id === title.id || holds(id, title.id) || holds(title.id, id)) continue;
      if (rectsOverlap(title, onScreen(box, view), TOUCH_PX)) wrong.push(`${title.id}'s title over ${id}`);
    }
  }
  for (const id of layerBoxIds.filter((boxId) => nodeBoxes[boxId] && closed.has(boxId))) {
    const title = titles.find((t) => t.id === id);
    const rect = onScreen(nodeBoxes[id], view);
    if (!title) wrong.push(`${id}: drawn with no title`);
    else if (!title.inside || title.fontSize < SMALLEST_ON_SCREEN_PX - 0.01 || title.x1 < rect.x1 - 0.5 || title.x2 > rect.x2 + 0.5 || title.y1 < rect.y1 - 0.5 || title.y2 > rect.y2 + 0.5) {
      wrong.push(`${id}: titled at ${title.fontSize.toFixed(1)} px${title.inside ? "" : " on a plate"}, in a box ${(rect.x2 - rect.x1).toFixed(1)} x ${(rect.y2 - rect.y1).toFixed(1)} px`);
    }
  }
  return wrong;
}

test("a tap on the scope at the fit frames it whole and draws its layer boxes only once they are readable; zooming in from there and out again, no title is over another title or a box, and each layer box is titled inside it at 10 px or more", async ({
  page,
  request,
}) => {
  const { data, boxes } = await scopedData(request);
  const scope = boxes[0].scope;
  const ids = boxes.filter((box) => box.scope === scope).map((box) => box.id);
  const parents = drawnParentMap(data);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openArchitecture(page);
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  await twoFrames(page);
  const at = (await viewer(page, "boxes"))[scope];
  await page.mouse.click((at.x1 + at.x2) / 2, at.y1 + Math.min(12, (at.y2 - at.y1) / 4));
  await expect.poll(() => viewer(page, "selection")).toBe(scope);
  await settled(page);

  // Framed whole: inside the canvas the panel leaves.
  const canvas = await page.getByTestId("graph-canvas").boundingBox();
  const panel = await page.getByTestId("viewer-panel").boundingBox();
  const right = panel && panel.x < canvas.x + canvas.width ? panel.x : canvas.x + canvas.width;
  const framed = (await viewer(page, "boxes"))[scope];
  expect([framed.x1 >= canvas.x, framed.x2 <= right, framed.y1 >= canvas.y, framed.y2 <= canvas.y + canvas.height]).toEqual([true, true, true, true]);

  const tree = treeOf(data);
  const smallest = smallestChildOf(tree, (await viewer(page, "elkGeometry")).boxes);
  const wrong = [];
  const readings = [];
  /** Read the view now: whether the scope is open as its layer boxes' height says, and every title. */
  const read = async (way) => {
    const level = await viewer(page, "level");
    const open = level.open.includes(scope);
    const tall = smallest.get(scope) * level.zoom;
    // Zooming in, the scope opens once they are readable; zooming out, it closes below a share of that.
    const least = way === "in" ? READABLE_PX : READABLE_PX * CLOSE_SHARE;
    readings.push(`${way} ${level.zoom.toFixed(3)} ${open ? "open" : "closed"} ${tall.toFixed(1)} px`);
    if (open !== tall >= least - 1e-6) wrong.push(`zoom ${level.zoom.toFixed(3)} ${way}: the scope ${open ? "open" : "closed"} with its layer boxes ${tall.toFixed(1)} px tall`);
    for (const finding of await titlesWrong(page, ids, parents)) wrong.push(`zoom ${level.zoom.toFixed(3)} ${way}: ${finding}`);
    return open;
  };
  const press = async (name) => {
    await page.getByRole("button", { name, exact: true }).click();
    await settled(page);
  };
  let past = -1;
  for (let step = 0; step <= ZOOM_STEPS && past < PAST_OPENING; step += 1) {
    if (await read("in")) past += 1;
    await press("Zoom in");
  }
  for (let step = 0; step <= ZOOM_STEPS && (await read("out")); step += 1) await press("Zoom out");
  test.info().annotations.push({ type: "measured", description: readings.join("; ") });
  expect(past, "the scope opened onto its layer boxes as the view zoomed in").toBeGreaterThanOrEqual(0);
  expect(wrong).toEqual([]);
});

test("a data file without every rule's keys draws no layer box: its layers are the first rule's lanes, as before", async ({
  page,
  request,
}) => {
  const { data } = await scopedData(request);
  const served = withoutLayerRules(data);
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: served }));
  await openArchitecture(page);
  await openEveryBox(page, { edges: false });

  const drawn = Object.keys(await viewer(page, "boxes"));
  expect(drawn.filter((id) => !served.nodes.some((node) => node.id === id))).toEqual([]);
  const legend = await page.locator("[data-legend-layer]").evaluateAll((items) => items.map((item) => item.dataset.legendLayer));
  expect(legend).toEqual([...served.layers].sort((a, b) => a.rank - b.rank).map((layer) => layer.name));
  // The parents a file without rules gives are the file's own.
  expect(Object.keys(parentMap(served)).sort()).toEqual(served.nodes.map((node) => node.id).sort());
  expect(await canvasBackground(page)).toBeTruthy();
});
