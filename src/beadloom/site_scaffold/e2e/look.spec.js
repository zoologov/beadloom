// The viewer's base look: one thin line weight, whole arrowheads, no bridges and no dots, a followed line on top.
//
// An earlier viewer was structurally right and looked unfinished: a line of the
// overview grew to about 7 px with its count, an arrowhead on a thick line was
// about twice the line's width and broke over the bend before its box, bridges
// erased notches out of the lines they hopped, a junction dot sat beside the
// rounded stroke it marked, and a line faded towards its source. Now every line
// has one thin weight at every zoom, arrowheads have one size on screen with one
// head where lines share their last run, there are no bridges and no dots,
// corners are rounded at one size on screen, and a followed line is drawn on top
// of everything with a casing. A status is a mark in a node's corner rather than
// a wider border, so a finding no longer moves every node of the layout.
//
// What the cases cannot see. A line's sizes are restyled when the zoom crosses a
// step of 1.25, so a size on screen is held within half a step of its own. ELK
// ends a line 10 layout units after its last bend where the line arrives from the
// layer above (on a portal of 436 routes, a quarter of them; the shortest 6). A
// head now keeps a straight run of its own and half a head more: the last bend
// moves back where nothing is in the way, and a head whose run has no room for
// its full size is drawn smaller, down to a smallest size. How a line enters its
// head at every zoom is `heads.spec.js`'s; the head case here holds the sizes.

import { test, expect } from "@playwright/test";
import {
  AA_TEXT,
  NON_TEXT,
  canvasBackground,
  contrastRatio,
  cornerRooms,
  drawnColours,
  endsInCorners,
  finalRunGroups,
  hasTargetHead,
  headLength,
  over,
  roundedAt,
  straightFinalRun,
  withinAStep,
} from "./support/look.js";
import { architectureData, openArchitecture, openEveryBox, serveEveryEdgeKind, viewer, waitForViewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";
import { treeOf } from "./support/map.js";

/** The one weight every line is drawn at, in pixels on screen. */
const LINE_PX = 1.35;
/** The one length every arrowhead is drawn at, in pixels on screen, where its run has room for it. */
const HEAD_PX = 6;
/** The smallest length an arrowhead is drawn at, in pixels on screen, where its run has no room for more (`heads.spec.js`). */
const SMALLEST_HEAD_PX = 3;
/** The width the border of the box that holds everything is drawn at, in pixels on screen, at every zoom. */
const PROJECT_BORDER_PX = 1;
/**
 * How far the tint of the box that holds everything stands from the canvas, at
 * least, as a contrast ratio. It read as the canvas at 1.02 (light) and 1.05
 * (dark); a node's tint stands at about 1.24 to 1.4, and the frame is to stay
 * fainter than any node it holds.
 */
const PROJECT_TINT_CONTRAST = 1.08;
/** The radius every rounded corner is drawn at, in pixels on screen, where its runs leave room for it. */
const CORNER_PX = 6;
/**
 * The radius every node's and every box's corners are drawn at, in pixels on
 * screen: a card's at zoom 1, Cytoscape's own for a rounded rectangle, the look
 * the owner asked the boxes to share (2026-10-07). A shape smaller than four
 * times that takes a quarter of its shorter side, Cytoscape's own clamp.
 */
const NODE_CORNER_PX = 8;
/** How much less round a box's corners may be drawn at the overview, in pixels, where a line's end holds them (`overview.spec.js`). */
const CORNER_SLACK_PX = 1;
/** How many zoom steps the corner cases take out from the fit. */
const OUT_STEPS = 2;
/**
 * How far a measured length may lie below the one it is compared with and be the
 * same, in layout units: a route's numbers are handed to Cytoscape at six
 * decimals and its corners come back recomputed.
 */
const ROUNDING = 0.01;

/** Wait until the page has drawn two more frames. */
const twoFrames = (page) => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));

async function zoomIn(page, steps) {
  for (let step = 0; step < steps; step += 1) await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await twoFrames(page);
}

/** Press "Zoom in" until the view is within half a zoom step of 1. */
async function zoomToOne(page) {
  for (let step = 0; step < 30 && (await viewer(page, "zoom")) < 1 / Math.sqrt(1.25); step += 1) {
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  }
  await twoFrames(page);
}

/** Press "Zoom out" `steps` times. */
async function zoomOut(page, steps) {
  for (let step = 0; step < steps; step += 1) await page.getByRole("button", { name: "Zoom out", exact: true }).click();
  await twoFrames(page);
}

/**
 * The drawn nodes and boxes whose corners are not the nodes' radius on screen
 * (`roundedAt`), named with what they measure; `held` takes the ids of those held
 * smaller by a line's end near a corner.
 */
async function offCorners(page, state, held = new Set()) {
  const zoom = await viewer(page, "zoom");
  const looks = await viewer(page, "nodeLooks");
  requireShape(looks.length > 0, `no node drawn ${state}`);
  const rooms = cornerRooms(await viewer(page, "lineLooks"), looks, await viewer(page, "nodeBoxes"), zoom);
  for (const look of looks) if (look.cornerRadius * zoom < NODE_CORNER_PX / Math.sqrt(1.25) - 0.01 && (rooms.get(look.id) ?? Infinity) < NODE_CORNER_PX) held.add(look.id);
  return looks
    .filter((look) => !roundedAt(look, zoom, NODE_CORNER_PX, rooms.get(look.id)))
    .map((look) => `${state} ${look.id}: ${look.shape}, ${(look.cornerRadius * zoom).toFixed(2)} px (a quarter of its shorter side ${((Math.min(look.width, look.height) / 4) * zoom).toFixed(2)} px, a line's end leaves ${(rooms.get(look.id) ?? Infinity).toFixed(2)} px)`);
}

/** The ends of the drawn lines that meet a node's border inside a rounded corner (`endsInCorners`), named with the state. */
async function endsInCornersNow(page, state) {
  const zoom = await viewer(page, "zoom");
  const found = endsInCorners(await viewer(page, "lineLooks"), await viewer(page, "nodeLooks"), await viewer(page, "nodeBoxes"), zoom);
  return found.map((finding) => `${state}: ${finding}`);
}

/** The drawn lines whose width on screen is not the one weight, named with what they measure. */
async function offWeight(page) {
  const zoom = await viewer(page, "zoom");
  return (await viewer(page, "lineLooks"))
    .filter((look) => !withinAStep(look.width * zoom, LINE_PX))
    .map((look) => `${look.id} ${look.styleKey}: ${(look.width * zoom).toFixed(2)} px`);
}

/**
 * The drawn arrowheads whose length on screen is not between the smallest and
 * the one size, named with what they measure; with `full`, a line of the map's
 * (whose route keeps a run long enough for a whole head) not at the one size.
 */
async function offHead(page, { full = false } = {}) {
  const zoom = await viewer(page, "zoom");
  const half = Math.sqrt(1.25);
  const off = (look, px) =>
    full && look.aggregated ? !withinAStep(px, HEAD_PX) : px < SMALLEST_HEAD_PX / half - 1e-6 || px > HEAD_PX * half + 1e-6;
  return (await viewer(page, "lineLooks"))
    .filter((look) => look.targetArrow !== "none" || look.sourceArrow !== "none")
    .filter((look) => off(look, headLength(look) * zoom))
    .map((look) => `${look.id}: ${(headLength(look) * zoom).toFixed(2)} px`);
}

/** The node that depends on the most others: a selection of it walks edges and leaves others outside. */
function busiestSource(data) {
  const counts = new Map();
  for (const edge of data.edges.filter((e) => e.kind === "depends_on")) counts.set(edge.src, (counts.get(edge.src) || 0) + 1);
  const [busiest] = [...counts].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0] || [];
  requireShape(Boolean(busiest), "no node depends on another");
  return busiest;
}

/** Rest the pointer on the middle of an edge clear of other edges and nodes (`edgeMidpoint`). */
async function hoverAnEdge(page) {
  await page.getByTestId("graph-canvas").scrollIntoViewIfNeeded();
  // Cytoscape reads where its canvas is when the scroll reaches it (`edges.spec.js`).
  await twoFrames(page);
  const found = await viewer(page, "edgeMidpoint");
  requireShape(Boolean(found), "no drawn edge has a middle clear of other edges and nodes");
  await page.mouse.move(found[1].x, found[1].y);
  await expect.poll(async () => (await viewer(page, "hoveredEdges")).length).toBeGreaterThan(0);
}

test("every drawn line has one weight on screen: at the overview, zoomed in, at full detail, followed and outside a selection", async ({
  page,
  request,
}) => {
  const data = await serveEveryEdgeKind(page, request);
  await openArchitecture(page);
  expect(await offWeight(page)).toEqual([]);
  await zoomIn(page, 3);
  expect(await offWeight(page)).toEqual([]);

  await openEveryBox(page);
  await zoomToOne(page);
  const kinds = new Set((await viewer(page, "lineLooks")).map((look) => look.styleKey));
  expect([...kinds].sort()).toEqual(["consumes", "depends_on", "produces", "uses", "violation"]);
  expect(await offWeight(page)).toEqual([]);

  const busy = busiestSource(data);
  await openArchitecture(page, `?focus=${encodeURIComponent(busy)}&depth=1`);
  await openEveryBox(page);
  await expect.poll(async () => (await viewer(page, "lineLooks")).filter((look) => look.walk).length).toBeGreaterThan(0);
  expect(await offWeight(page)).toEqual([]);
  const dimmed = (await viewer(page, "lineLooks")).filter((look) => look.dimmed).length;
  requireShape(dimmed > 0, "the busiest node's neighbourhood takes every drawn edge");
});

test("every arrowhead of the overview's own lines has one size on screen, and no arrowhead is ever larger, nor smaller than the smallest", async ({
  page,
  request,
}) => {
  await serveEveryEdgeKind(page, request);
  await openArchitecture(page);
  expect(await offHead(page, { full: true })).toEqual([]);
  await zoomIn(page, 3);
  expect(await offHead(page)).toEqual([]);
  await openEveryBox(page);
  expect(await offHead(page)).toEqual([]);
  await zoomToOne(page);
  expect(await offHead(page)).toEqual([]);
});

test("at full size every arrowhead sits on a straight run at least as long as itself", async ({ page }) => {
  await openArchitecture(page);
  await openEveryBox(page);
  await zoomToOne(page);
  const looks = (await viewer(page, "lineLooks")).filter((look) => hasTargetHead(look) && look.cornerRadii.length);
  requireShape(looks.length > 0, "no routed line ends in an arrowhead");

  const broken = looks
    .map((look) => ({ id: look.id, straight: straightFinalRun(look), head: headLength(look) }))
    .filter(({ straight, head }) => straight !== null && straight < head - ROUNDING)
    .map(({ id, straight, head }) => `${id}: a run of ${straight.toFixed(2)} under a head of ${head.toFixed(2)}`);
  expect(broken).toEqual([]);
});

test("lines that share their last run into a node end in one arrowhead, and a line that arrives on its own keeps its own", async ({
  page,
}) => {
  await openArchitecture(page);
  // Every box open as a reader's zoom opens it: the lines of the map's at the boxes, the edges inside them.
  await openEveryBox(page, { edges: false });
  // Each end edges arrive at, as a line ending there: an edge's target, and each end of a line of the map's
  // that its count says edges arrive at.
  const arrivals = (await viewer(page, "lineLooks"))
    .filter((look) => look.cornerRadii.length)
    .flatMap((look) => {
      const ends = [];
      if (!look.aggregated || look.forward > 0) ends.push({ ...look, head: look.targetArrow, sourceEnd: false });
      if (look.aggregated && look.backward > 0) ends.push({ ...look, points: [...look.points].reverse(), head: look.sourceArrow, sourceEnd: true });
      return ends;
    });
  const groups = finalRunGroups(arrivals);
  requireShape(groups.some((group) => group.length > 1), "no two drawn lines share their last run");

  // Of two heads side by side on one border, too near for both at the scale drawn, one gives way to the
  // other (`heads.spec.js`): its line arrives on its own, with no head.
  const gaveWay = new Set((await viewer(page, "droppedHeads")).map((d) => `${d.id}:${d.end}`));
  const heads = (group) => group.filter((end) => end.head !== "none").length;
  const alone = (group) => group.length === 1 && gaveWay.has(`${group[0].id}:${group[0].sourceEnd ? "source" : "target"}`);
  expect(groups.filter((group) => heads(group) !== 1 && !alone(group)).map((group) => group.map((look) => look.id).join(" + "))).toEqual([]);
});

test("every routed line turns its corners at one radius on screen, so a branch leaves its trunk in a rounded merge", async ({
  page,
}) => {
  await openArchitecture(page);
  const radiusPx = async () => {
    const zoom = await viewer(page, "zoom");
    // The first corner of a line with an arrowhead only at its target is never shortened for a head.
    return (await viewer(page, "lineLooks"))
      .filter((look) => look.cornerRadii.length && look.sourceArrow === "none" && look.points.length > 3)
      .map((look) => ({ id: look.id, px: look.cornerRadii[0] * zoom }));
  };
  for (const zoomSteps of [0, 3]) {
    await zoomIn(page, zoomSteps);
    const off = (await radiusPx()).filter(({ px }) => !withinAStep(px, CORNER_PX));
    expect(off.map(({ id, px }) => `${id}: ${px.toFixed(2)} px`)).toEqual([]);
  }
  await openEveryBox(page);
  await zoomToOne(page);
  const radii = await radiusPx();
  requireShape(radii.length > 0, "no routed line turns more than once");
  expect(radii.filter(({ px }) => !withinAStep(px, CORNER_PX)).map(({ id }) => id)).toEqual([]);
});

// The owner, after the look at 5bcb6881: the overview's boxes were drawn square
// while every node had rounded corners. A box's corners were Cytoscape's own,
// 8 layout units, which at this portal's whole-graph fit is half a pixel.
test("at full detail every line meets a node or a box on the straight part of a side, clear of its rounded corners", async ({ page }) => {
  await openArchitecture(page);
  await openEveryBox(page);
  await waitForViewer(page);
  const found = await endsInCornersNow(page, "every box open at the fit");
  await zoomToOne(page);
  await waitForViewer(page);
  found.push(...(await endsInCornersNow(page, "every box open at zoom 1")));
  await zoomIn(page, 2);
  await waitForViewer(page);
  found.push(...(await endsInCornersNow(page, "every box open, two steps past zoom 1")));
  expect(found).toEqual([]);
});

test("no bridge and no junction dot is drawn: the layers over the canvas draw the followed lines and the map's counts, above Cytoscape's", async ({
  page,
}) => {
  await openArchitecture(page);
  await openEveryBox(page);
  expect(await viewer(page, "overlayLayers")).toEqual(["followed", "pills"]);
  const handle = await page.evaluate(() => ["bridges", "bridgeFrames", "junctions"].filter((name) => name in window.__beadloomViewer));
  expect(handle).toEqual([]);
  const stacking = await page.evaluate(() => {
    const container = document.querySelector("[data-testid='graph-canvas']");
    const layer = container.querySelector("canvas[data-layer='followed']");
    const cytoscape = container.firstElementChild;
    return {
      after: Boolean(cytoscape.compareDocumentPosition(layer) & Node.DOCUMENT_POSITION_FOLLOWING),
      above: Number(getComputedStyle(layer).zIndex) > Number(getComputedStyle(cytoscape).zIndex),
    };
  });
  expect(stacking).toEqual({ after: true, above: true });
});

test("a hovered line is drawn on top in its full colour, over a casing in the canvas's colour, and its label shows only while it is hovered", async ({
  page,
}) => {
  await openArchitecture(page);
  await openEveryBox(page);
  await zoomToOne(page);
  expect((await viewer(page, "followed")).edges).toEqual([]);
  await hoverAnEdge(page);

  const followed = await viewer(page, "followed");
  const along = await viewer(page, "hoveredEdges");
  expect(followed.edges.map((edge) => edge.id).sort()).toEqual(along);
  const background = await canvasBackground(page);
  const rest = Object.fromEntries((await viewer(page, "lineLooks")).map((look) => [look.id, look]));
  // At rest a line is drawn lighter than its full colour, but for one that reports a problem;
  // followed, it is drawn in the full one.
  const strength = (edge) => contrastRatio(edge.colour, background) - contrastRatio(rest[edge.id].colour, background);
  for (const edge of followed.edges) {
    expect(edge.casing, edge.id).toBe(background.replace(/\s+/g, ""));
    expect(strength(edge), edge.id).toBeGreaterThanOrEqual(0);
  }
  expect(followed.edges.some((edge) => strength(edge) > 0)).toBe(true);
  // Every casing is drawn before any line, so the lines of one bundle cut no slit into each other;
  // a title a line runs through is drawn again over the lines (`levels.spec.js`), and the label last.
  expect(followed.passes.map((pass) => pass.name)).toEqual(["casings", "lines", "heads", "titles", "labels"]);
  const labels = followed.passes.find((pass) => pass.name === "labels");
  // The pointer is over one edge, though not always the one whose middle it aimed at (`edges.spec.js`).
  expect(labels.edges).toHaveLength(1);
  expect(along).toContain(labels.edges[0]);
  expect(await viewer(page, "shownEdgeLabels")).toEqual(labels.edges);

  await page.mouse.move(2, 2);
  await expect.poll(async () => (await viewer(page, "followed")).edges).toEqual([]);
  expect(await viewer(page, "shownEdgeLabels")).toEqual([]);
});

test("a selection's walk is drawn on top with casings, and a selected line shows no label", async ({ page, request }) => {
  const busy = busiestSource(await architectureData(request));
  await openArchitecture(page, `?focus=${encodeURIComponent(busy)}&depth=1`);
  await openEveryBox(page);
  await expect.poll(async () => (await viewer(page, "lineLooks")).filter((look) => look.walk).length).toBeGreaterThan(0);

  const walked = (await viewer(page, "lineLooks")).filter((look) => look.walk).map((look) => look.id).sort();
  const followed = await viewer(page, "followed");
  expect(followed.edges.map((edge) => edge.id).sort()).toEqual(walked);
  expect(await viewer(page, "shownEdgeLabels")).toEqual([]);
});

test("a node's status moves nothing: every node and box is laid out where it is when no node has a status", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const flagged = (node) => (node.findings || []).length || node.doc_status === "stale" || node.lint_clean === false;
  requireShape(data.nodes.some(flagged), "no node has a finding or a stale doc");
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page);
  const flaggedLayout = { positions: await viewer(page, "positions"), boxes: (await viewer(page, "elkGeometry")).boxes };

  const calm = {
    ...data,
    nodes: data.nodes.map((node) => ({ ...node, findings: [], doc_status: "fresh", lint_clean: true })),
  };
  await page.unroute("**/architecture.data.json");
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: calm }));
  await openArchitecture(page);
  const calmLayout = { positions: await viewer(page, "positions"), boxes: (await viewer(page, "elkGeometry")).boxes };

  const apart = (a, b) => Math.max(...Object.keys(a).map((key) => Math.abs(a[key] - b[key])));
  const moved = Object.keys(calmLayout.positions).filter((id) => apart(calmLayout.positions[id], flaggedLayout.positions[id]) > ROUNDING);
  const resized = Object.keys(calmLayout.boxes).filter((id) => apart(calmLayout.boxes[id], flaggedLayout.boxes[id]) > ROUNDING);
  expect({ moved, resized }).toEqual({ moved: [], resized: [] });
});

test("an open box is drawn with a thin solid border, a light tint and its title inside at the top", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(data.nodes.some((node) => node.parent && node.parent !== node.id), "no node is inside a box");
  await openArchitecture(page);
  await openEveryBox(page);
  const boxes = (await viewer(page, "nodeLooks")).filter((look) => look.isParent);
  requireShape(boxes.length > 0, "no box is drawn open");
  // The box that holds everything, and no other, stands its title on a plate above it while its own
  // would read smaller than the smallest size a title is drawn at (`overview.spec.js`).
  const plated = new Set((await viewer(page, "boxTitles")).filter((title) => title.plate).map((title) => title.id));
  expect([...plated].filter((id) => boxes.find((box) => box.id === id)?.parent)).toEqual([]);

  // The box that holds everything is the project's frame, a pixel wide on screen at every zoom (the
  // frame's own case below); every other box's border is one layout unit.
  const { wrapper } = treeOf(data);
  const wrong = boxes.filter(
    (box) =>
      box.borderStyle !== "solid" ||
      (box.id !== wrapper && box.borderWidth > 1) ||
      box.fillOpacity > 0.1 ||
      (!plated.has(box.id) && (box.labelValign !== "top" || !(box.labelMarginY > 0)))
  );
  expect(wrong.map((box) => `${box.id}: ${box.borderStyle} ${box.borderWidth}, tint ${box.fillOpacity}, title ${box.labelValign} ${box.labelMarginY}`)).toEqual([]);
});

for (const colorScheme of ["light", "dark"]) {
  test.describe(`in the ${colorScheme} theme`, () => {
    test.use({ colorScheme });

    test("every node's title reads at WCAG AA against what it is drawn on, at the overview and at full detail", async ({
      page,
    }) => {
      await openArchitecture(page);
      const background = await canvasBackground(page);
      const lowContrast = async () => {
        const looks = await viewer(page, "nodeLooks");
        const byId = new Map(looks.map((look) => [look.id, look]));
        const outside = new Set((await viewer(page, "level")).collapsed.filter((box) => box.outside).map((box) => box.id));
        // What a node is drawn on: its parent's fill over what the parent is drawn on, the canvas at the top.
        const under = (id) => {
          const look = byId.get(id);
          if (!look) return background;
          return over(look.fill, under(look.parent), look.fillOpacity);
        };
        return looks
          .map((look) => ({ id: look.id, behind: outside.has(look.id) ? under(look.parent) : under(look.id), text: look.labelColour }))
          .map(({ id, behind, text }) => ({ id, ratio: contrastRatio(text, behind) }))
          .filter(({ ratio }) => ratio < AA_TEXT)
          .map(({ id, ratio }) => `${id}: ${ratio.toFixed(2)}`);
      };
      expect(await lowContrast()).toEqual([]);
      await openEveryBox(page);
      expect(await lowContrast()).toEqual([]);
    });

    // Before, the box that holds everything was drawn in the grey of a node in no
    // layer: a border at 1.35:1 (light) and 2.52:1 (dark) against the canvas, a
    // layout unit wide (a fifth of a pixel at the whole-graph fit), over a tint
    // at 1.02:1 and 1.05:1 — the project read as the viewer's background (owner,
    // 2026-10-06). A node in no layer had the same grey border: 1.33:1 and 2.38:1.
    test("every node's border keeps 3:1 against what it is drawn on, the box that holds everything included, at the overview and at full detail", async ({
      page,
    }) => {
      await openArchitecture(page);
      const background = await canvasBackground(page);
      const faint = async (state) => {
        const looks = await viewer(page, "nodeLooks");
        const drawn = drawnColours(looks, background);
        return looks
          .map((look) => ({ id: look.id, ratio: contrastRatio(look.borderColour, drawn(look.parent)) }))
          .filter(({ ratio }) => ratio < NON_TEXT)
          .map(({ id, ratio }) => `${state} ${id}: ${ratio.toFixed(2)}`);
      };
      const overview = await faint("overview");
      await openEveryBox(page, { edges: false });
      expect([...overview, ...(await faint("every box open"))]).toEqual([]);
    });

    // Before, every box's corners were Cytoscape's own 8 layout units, so they
    // shrank with the zoom: at this portal's whole-graph fit half a pixel, and
    // the overview's boxes read square beside the cards' rounded corners.
    test("every node and box is drawn with the nodes' rounded corners: one radius on screen at every zoom from zoomed out past the overview to full detail, a quarter of its shorter side where that is less, and never over a line's end", async ({
      page,
    }) => {
      await openArchitecture(page);
      const held = new Set();
      const off = await offCorners(page, "at the fit", held);
      // At the overview no box is held visibly smaller: the router keeps every line's end on the straight part of
      // a side, but where a small box's radius reaches under a pixel past the ports it always had (`overview.spec.js`).
      const fitZoom = await viewer(page, "zoom");
      const heldMuch = (await viewer(page, "nodeLooks"))
        .filter((look) => look.cornerRadius * fitZoom < Math.min(NODE_CORNER_PX / Math.sqrt(1.25), (Math.min(look.width, look.height) / 4) * fitZoom) - CORNER_SLACK_PX - 0.01)
        .map((look) => `${look.id}: ${(look.cornerRadius * fitZoom).toFixed(2)} px`);
      expect(heldMuch, "boxes held more than a pixel smaller by a line's end at the fit").toEqual([]);
      const half = Math.sqrt(1.25);
      for (let step = 1; step < 40 && (await viewer(page, "zoom")) < 1.5; step += 1) {
        await zoomIn(page, 1);
        await waitForViewer(page);
        off.push(...(await offCorners(page, `${step} step(s) in`, held)));
      }
      expect(await viewer(page, "zoom")).toBeGreaterThan(1.5 / half);
      // Zoomed out past the fit the routes stay where the fit planned them, so a line's end may hold a box's
      // corners smaller there (`overview.spec.js`).
      await openArchitecture(page);
      for (let step = 1; step <= OUT_STEPS; step += 1) {
        await zoomOut(page, 1);
        await waitForViewer(page);
        off.push(...(await offCorners(page, `${step} step(s) out`, held)));
      }
      await openEveryBox(page, { edges: false });
      await waitForViewer(page);
      await zoomToOne(page);
      await waitForViewer(page);
      off.push(...(await offCorners(page, "every box open at zoom 1", held)));
      test.info().annotations.push({ type: "measured", description: `held smaller by a line's end near a corner: ${[...held].sort().join(", ") || "none"}` });
      expect(off).toEqual([]);
    });

    test("the box that holds everything is a frame of its own: a border a pixel wide on screen at every zoom, a tint apart from the canvas and fainter than any node's", async ({
      page,
      request,
    }) => {
      const { wrapper } = treeOf(await architectureData(request));
      requireShape(Boolean(wrapper), "no single node holds every other node, so no box holds the project");
      await openArchitecture(page);
      const background = await canvasBackground(page);
      const readings = [];
      const read = async (state) => {
        const looks = await viewer(page, "nodeLooks");
        const drawn = drawnColours(looks, background);
        const frame = looks.find((look) => look.id === wrapper);
        const tint = contrastRatio(drawn(wrapper), background);
        const zoom = await viewer(page, "zoom");
        readings.push({
          state,
          borderPx: withinAStep(frame.borderWidth * zoom, PROJECT_BORDER_PX) ? PROJECT_BORDER_PX : +(frame.borderWidth * zoom).toFixed(2),
          tintApart: tint >= PROJECT_TINT_CONTRAST || +tint.toFixed(3),
          // A node it holds, closed or with nothing inside, stands further from it than it stands from
          // the canvas (an open box is drawn fainter on purpose), and no node is drawn as it is.
          louder: looks
            .filter((look) => look.parent === wrapper && !(look.isParent && !look.collapsed))
            .filter((look) => contrastRatio(drawn(look.id), drawn(wrapper)) <= tint)
            .map((look) => look.id),
          sameBorder: looks.filter((look) => look.id !== wrapper && look.borderColour === frame.borderColour).map((look) => look.id),
        });
      };
      await read("overview");
      await zoomIn(page, 3);
      await read("three steps in");
      await zoomToOne(page);
      await read("zoom 1");
      const held = { borderPx: PROJECT_BORDER_PX, tintApart: true, louder: [], sameBorder: [] };
      expect(readings).toEqual(["overview", "three steps in", "zoom 1"].map((state) => ({ state, ...held })));
    });
  });
}
