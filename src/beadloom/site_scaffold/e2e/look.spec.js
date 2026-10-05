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
// of everything with a casing.
//
// What the cases cannot see. A line's sizes are restyled when the zoom crosses a
// step of 1.25, so a size on screen is held within half a step of its own. ELK
// ends a line 10 layout units after its last bend where the line arrives from the
// layer above (on a portal of 436 routes, a quarter of them; the shortest 6): a
// head of 6 px sits on a straight run of its own at full size, which is where the
// head case reads them, and not below about zoom 0.6, where such a run is shorter
// than the head. Lengthening those runs would change the layout.

import { test, expect } from "@playwright/test";
import {
  AA_TEXT,
  canvasBackground,
  contrastRatio,
  finalRunGroups,
  hasTargetHead,
  headLength,
  over,
  straightFinalRun,
  withinAStep,
} from "./support/look.js";
import { architectureData, openArchitecture, openEveryBox, serveEveryEdgeKind, viewer } from "./support/viewer.js";
import { requireShape } from "./support/shape.js";

/** The one weight every line is drawn at, in pixels on screen. */
const LINE_PX = 1.35;
/** The one length every arrowhead is drawn at, in pixels on screen. */
const HEAD_PX = 6;
/** The radius every rounded corner is drawn at, in pixels on screen, where its runs leave room for it. */
const CORNER_PX = 6;
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

/** The drawn lines whose width on screen is not the one weight, named with what they measure. */
async function offWeight(page) {
  const zoom = await viewer(page, "zoom");
  return (await viewer(page, "lineLooks"))
    .filter((look) => !withinAStep(look.width * zoom, LINE_PX))
    .map((look) => `${look.id} ${look.styleKey}: ${(look.width * zoom).toFixed(2)} px`);
}

/** The drawn arrowheads whose length on screen is not the one size, named with what they measure. */
async function offHead(page) {
  const zoom = await viewer(page, "zoom");
  return (await viewer(page, "lineLooks"))
    .filter((look) => look.targetArrow !== "none" || look.sourceArrow !== "none")
    .filter((look) => !withinAStep(headLength(look) * zoom, HEAD_PX))
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

test("every arrowhead has one size on screen, at the overview, zoomed in and at full detail", async ({ page, request }) => {
  await serveEveryEdgeKind(page, request);
  await openArchitecture(page);
  expect(await offHead(page)).toEqual([]);
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
  await openEveryBox(page);
  const routed = (await viewer(page, "lineLooks")).filter((look) => look.cornerRadii.length && !look.aggregated);
  const groups = finalRunGroups(routed);
  requireShape(groups.some((group) => group.length > 1), "no two drawn lines share their last run");

  const heads = (group) => group.filter(hasTargetHead).length;
  expect(groups.filter((group) => heads(group) !== 1).map((group) => group.map((look) => look.id).join(" + "))).toEqual([]);
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

test("no bridge and no junction dot is drawn: the one layer over the canvas draws the followed lines, above Cytoscape's", async ({
  page,
}) => {
  await openArchitecture(page);
  await openEveryBox(page);
  expect(await viewer(page, "overlayLayers")).toEqual(["followed"]);
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
  // Every casing is drawn before any line, so the lines of one bundle cut no slit into each other.
  expect(followed.passes.map((pass) => pass.name)).toEqual(["casings", "lines", "heads", "labels"]);
  // The pointer is over one edge, though not always the one whose middle it aimed at (`edges.spec.js`).
  expect(followed.passes[3].edges).toHaveLength(1);
  expect(along).toContain(followed.passes[3].edges[0]);
  expect(await viewer(page, "shownEdgeLabels")).toEqual(followed.passes[3].edges);

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

test("an open box is drawn with a thin solid border, a light tint and its title inside at the top", async ({ page, request }) => {
  const data = await architectureData(request);
  requireShape(data.nodes.some((node) => node.parent && node.parent !== node.id), "no node is inside a box");
  await openArchitecture(page);
  await openEveryBox(page);
  const boxes = (await viewer(page, "nodeLooks")).filter((look) => look.isParent);
  requireShape(boxes.length > 0, "no box is drawn open");

  const wrong = boxes.filter(
    (box) =>
      box.borderStyle !== "solid" ||
      box.borderWidth > 1 ||
      box.fillOpacity > 0.1 ||
      box.labelValign !== "top" ||
      !(box.labelMarginY > 0)
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
  });
}
