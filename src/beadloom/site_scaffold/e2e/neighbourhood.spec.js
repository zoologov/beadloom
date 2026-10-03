// A selected node's neighbourhood: depth, direction, and dim or hide.
//
// In an earlier version a selection marked the node and its own edges and nothing else:
// depth and direction were carried in the URL and read by nothing, and the rest
// of the graph stayed as it was.
//
// A case that reads what the walk leaves out reads it over the whole graph, every
// box open: at the whole-graph fit the viewer draws a map, and what a selection
// opens of it is `map.spec.js`'s. A case that reads only the walk opens nothing:
// a walk the reader asked for opens the boxes it reaches.

import { test, expect } from "@playwright/test";
import { architectureData, openArchitecture, openEveryBox, parentMap, viewer, withAncestors } from "./support/viewer.js";
import { NEIGHBOURHOOD_KINDS, edgeKey, neighbourhood } from "./support/graph.js";
import { requireShape } from "./support/shape.js";

const sorted = (ids) => [...ids].sort();

/**
 * The node whose outgoing neighbourhood grows most from depth 1 to depth 2 (between
 * equals, the first by id), so the case sees a second level whatever graph it runs on.
 */
function subjectOf(data) {
  const growth = (id) =>
    neighbourhood(data, id, 2, "out").ids.length - neighbourhood(data, id, 1, "out").ids.length;
  return data.nodes
    .map((n) => n.id)
    .sort()
    .sort((a, b) => growth(b) - growth(a))[0];
}

/** `subjectOf` when `holds` of it; otherwise the first node, by id, of which it does. */
function subjectWhere(data, holds) {
  const preferred = subjectOf(data);
  if (holds(preferred)) return preferred;
  return data.nodes.map((n) => n.id).sort().find(holds);
}

/** How many more nodes a walk of `depth` in `dir` reaches from `id` than a walk of one step. */
function growth(data, id, depth, dir) {
  return neighbourhood(data, id, depth, dir).ids.length - neighbourhood(data, id, 1, dir).ids.length;
}

/** The keys of every edge the viewer draws between two nodes of the file. */
function drawnEdges(data) {
  const ids = new Set(data.nodes.map((n) => n.id));
  return new Set(
    data.edges
      .filter((e) => NEIGHBOURHOOD_KINDS.includes(e.kind) && e.src !== e.dst && ids.has(e.src) && ids.has(e.dst))
      .map(edgeKey)
  );
}

/** Every node that is neither in the walk nor a container of a node in it. */
function outside(data, walked) {
  const kept = withAncestors(walked, parentMap(data));
  return sorted(data.nodes.map((n) => n.id).filter((id) => !kept.has(id)));
}

test("depth 2 outgoing shows the node, what it reaches in two steps and those edges; the rest is dimmed", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectWhere(data, (id) => growth(data, id, 2, "out") > 0);
  requireShape(subject, "no node reaches a node two steps out that it does not reach in one");
  const expected = neighbourhood(data, subject, 2, "out");

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Depth", { exact: true }).selectOption("2");
  await page.getByLabel("Direction", { exact: true }).selectOption("out");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
  await openEveryBox(page);
  expect(await viewer(page, "dimmedIds")).toEqual(outside(data, expected.ids));
});

test("switching the direction to incoming shows the nodes that reach it", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, 2, "in");

  await openArchitecture(page, `?focus=${subject}&depth=2&dir=out`);
  await page.getByLabel("Direction", { exact: true }).selectOption("in");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
  await openEveryBox(page);
  expect(await viewer(page, "dimmedIds")).toEqual(outside(data, expected.ids));
});

test("'all' walks without a depth limit in both directions", async ({ page, request }) => {
  const data = await architectureData(request);
  const subject = subjectWhere(data, (id) => growth(data, id, Infinity, "both") > 0);
  requireShape(subject, "no node is linked to another more than one step away, in either direction");
  const expected = neighbourhood(data, subject, Infinity, "both");

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Depth", { exact: true }).selectOption("all");

  await expect.poll(() => viewer(page, "neighbourhood")).toEqual(expected);
});

test("'Hide the rest' hides what the neighbourhood leaves out, and keeps its containers", async ({
  page,
  request,
}) => {
  const data = await architectureData(request);
  const subject = subjectOf(data);
  const expected = neighbourhood(data, subject, 1, "both");

  await openArchitecture(page, `?focus=${subject}`);
  await page.getByLabel("Hide the rest", { exact: true }).check();

  await expect
    .poll(() => viewer(page, "visibleIds"))
    .toEqual(sorted(withAncestors(expected.ids, parentMap(data))));
  expect(await viewer(page, "dimmedIds")).toEqual([]);
  expect(new URL(page.url()).searchParams.get("hide")).toBe("1");
});

test("clearing the selection shows the whole graph again", async ({ page, request }) => {
  const data = await architectureData(request);
  // The default direction is both ways: a node outside that walk is dimmed.
  const subject = subjectWhere(data, (id) => outside(data, neighbourhood(data, id, 2, "both").ids).length > 0);
  requireShape(
    subject,
    "no node lies more than two steps from another: each node's two-step neighbourhood, with its containers, is the whole graph"
  );

  await openArchitecture(page, `?focus=${subject}&depth=2`);
  await expect.poll(async () => (await viewer(page, "dimmedIds")).length).toBeGreaterThan(0);
  await page.getByTestId("graph-canvas").focus();
  await page.keyboard.press("Escape");

  await expect.poll(() => viewer(page, "dimmedIds")).toEqual([]);
  expect(await viewer(page, "neighbourhood")).toEqual({ ids: [], edges: [] });
});

// The rest of the graph is its nodes AND its edges: an edge the walk did not
// take is dimmed, or hidden with "Hide the rest", and every edge it took is
// shown at full strength. A dimmed edge is drawn opaque in a colour faded towards
// the background, so edges drawn along one trunk do not darken it: its line
// colour differs from the one it is drawn in with nothing selected.
const OUTSIDE_LOOKS = [
  {
    choice: "dimmed",
    query: "",
    outside: (look, plain) => look.visible && look.opacity === 1 && look.lineColour !== plain.lineColour,
  },
  { choice: "hidden", query: "&hide=1", outside: (look) => !look.visible },
];

for (const { choice, query, outside: looksOutside } of OUTSIDE_LOOKS) {
  test(`depth 2 outgoing shows only the walk's edges at full strength; every other edge is ${choice}`, async ({
    page,
    request,
  }) => {
    const data = await architectureData(request);
    const walkedFrom = (id) => neighbourhood(data, id, 2, "out").edges;
    // A walk that takes an edge and leaves one out, so both looks are read.
    const subject = subjectWhere(
      data,
      (id) => walkedFrom(id).length > 0 && walkedFrom(id).length < drawnEdges(data).size
    );
    requireShape(subject, "no node's two-step outgoing walk takes one drawn edge and leaves another out");
    const walked = new Set(walkedFrom(subject));

    await openArchitecture(page);
    await openEveryBox(page);
    const plain = Object.fromEntries((await viewer(page, "edgeLooks")).map((look) => [look.key, look]));
    await openArchitecture(page, `?focus=${subject}&depth=2&dir=out${query}`);
    await expect.poll(async () => (await viewer(page, "neighbourhood")).edges.length).toBe(walked.size);
    await openEveryBox(page);

    const looks = await viewer(page, "edgeLooks");
    expect(looks.length).toBeGreaterThan(walked.size);
    const fullStrength = (look) =>
      look.visible && look.opacity === 1 && look.lineColour === plain[look.key].lineColour;
    const wrong = looks.filter((look) =>
      walked.has(look.key) ? !fullStrength(look) : !looksOutside(look, plain[look.key])
    );
    expect(wrong).toEqual([]);
  });
}
