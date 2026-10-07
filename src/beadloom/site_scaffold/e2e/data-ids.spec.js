// A node is drawn whatever it is named, `__proto__` and the other names a plain object holds.
//
// The data file's ids are whatever a project named its nodes. A plain object keyed
// by such an id reads `constructor` or `toString` from its prototype when the key
// is absent, and assigning `__proto__` sets its prototype instead of a key: a node
// named `__proto__` was once absent from the drawing, its box, its routes and its
// edges with it, and no error said so.
//
// The graph here is made up for the case, in two namings of one shape: a box
// holding a box and a node busy enough to be bundled, the inner box holding two
// nodes, a second box of leaves the busy node depends on, and edges from boxes and
// between children. One naming calls the middle box `__proto__`, the other the
// busy node, so the name is crossed both as a box and as a leaf, everywhere the
// viewer keys something by a node's id or an edge's id.
//
// The expected answers come from the made-up file, never from the viewer's own
// functions. Every lookup that names a node runs in the page and answers with
// arrays or strings, so no name can turn into a prototype on the way back.

import { test, expect } from "@playwright/test";
import { edgeKey } from "./support/graph.js";
import { architectureData, openArchitecture, viewer, waitForViewer } from "./support/viewer.js";

const CARD = "[data-testid='node-card']";

/** The name that sets a plain object's prototype when it is assigned as a key. */
const PROTOTYPE_KEY = "__proto__";

/** The names a plain object answers for without being given them, `__proto__` first. */
const INHERITED_NAMES = [PROTOTYPE_KEY, "constructor", "toString", "valueOf", "hasOwnProperty"];

/** The handle's readers of the counts the map draws last, each a record keyed by node id. */
const COUNT_READERS = ["outwardMarks", "boxTallies"];

/** How many nodes the busy one depends on: more than the edges a node needs to be bundled. */
const BUSY_DEGREE = 22;

/**
 * The two namings of the graph's roles: `middle` is the box inside `outer`, `busy`
 * the node bundled, `inner` the box inside `middle`, `first` and `second` its nodes.
 */
const NAMINGS = [
  {
    name: "a box named __proto__",
    roles: { middle: PROTOTYPE_KEY, busy: "toString", inner: "constructor", first: "valueOf", second: "hasOwnProperty" },
  },
  {
    name: "a busy leaf named __proto__",
    roles: { middle: "constructor", busy: PROTOTYPE_KEY, inner: "valueOf", first: "toString", second: "hasOwnProperty" },
  },
];

function nodeOf(id, kind, parent, rank) {
  return {
    id,
    label: id,
    kind,
    parent: parent || id,
    ...(typeof rank === "number" ? { layer_rank: rank } : {}),
    findings: [],
    doc_status: "fresh",
    lint_clean: true,
  };
}

/**
 * `served` with its nodes and edges replaced by the graph of `roles`, its boxes in
 * the served file's first two layer ranks when it declares them.
 */
function objectNamedGraph(served, roles) {
  const { middle, busy, inner, first, second } = roles;
  const ranks = (Array.isArray(served.layers) ? served.layers : [])
    .map((layer) => layer.rank)
    .filter((rank) => typeof rank === "number");
  const [upper, lower] = [ranks[0], ranks[1] ?? ranks[0]];
  const leaves = Array.from({ length: BUSY_DEGREE }, (_, k) => `leaf-${k}`);
  const nodes = [
    nodeOf("outer", "domain", null, upper),
    nodeOf(middle, "feature", "outer", upper),
    nodeOf(busy, "component", middle, upper),
    nodeOf(inner, "feature", middle, upper),
    nodeOf(first, "component", inner, upper),
    nodeOf(second, "component", inner, upper),
    nodeOf("lower", "domain", null, lower),
    ...leaves.map((id) => nodeOf(id, "component", "lower", lower)),
  ];
  const dependsOn = (src, dst) => ({ src, dst, kind: "depends_on" });
  const edges = [
    ...nodes.filter((n) => n.parent !== n.id).map((n) => ({ src: n.id, dst: n.parent, kind: "part_of" })),
    ...leaves.map((leaf) => dependsOn(busy, leaf)),
    dependsOn(first, second),
    dependsOn(second, "leaf-0"),
    dependsOn(first, busy),
    dependsOn(middle, "leaf-1"),
    dependsOn(inner, "leaf-2"),
  ];
  return { ...served, nodes, edges };
}

/**
 * The made-up graph of `roles` served in place of the portal's, and the page
 * opened on it; `extend` adds to the graph what one case needs.
 */
async function openObjectNamed(page, request, roles, query = "", extend = (graph) => graph) {
  const data = extend(objectNamedGraph(await architectureData(request), roles));
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  await openArchitecture(page, query);
  return data;
}

/** Every box of the graph opened, as the handle's one action opens them. */
async function openEveryBox(page, data) {
  await viewer(page, "revealNodes", data.nodes.map((n) => n.id));
}

/**
 * The names among `ids` that the handle's answer to `method` does not hold as its
 * own keys; `field` names the map inside the answer, when the answer holds one.
 */
function missingFrom(page, ids, method, field = null) {
  return page.evaluate(
    ([wanted, name, inside]) => {
      const answer = window.__beadloomViewer[name]();
      const map = inside ? answer?.[inside] : answer;
      return wanted.filter((id) => !map || !Object.hasOwn(map, id));
    },
    [ids, method, field]
  );
}

/** The readers among `readers` whose answer does not hold `id` as its own key, each as `reader: id`. */
async function readersMissing(page, id, readers) {
  const missing = await Promise.all(readers.map((reader) => missingFrom(page, [id], reader)));
  return readers.filter((_, k) => missing[k].length).map((reader) => `${reader}: ${id}`);
}

/** How many own keys the map inside the handle's answer to `method` holds. */
function sizeOf(page, method, field) {
  return page.evaluate(
    ([name, inside]) => Object.keys(window.__beadloomViewer[name]()[inside]).length,
    [method, field]
  );
}

/** Press "Zoom out" until `done()` answers true, at most `steps` times; whether it did. */
async function zoomOutUntil(page, done, steps = 20) {
  for (let taken = 0; taken < steps && !(await done()); taken += 1) {
    await page.getByRole("button", { name: "Zoom out", exact: true }).click();
    await waitForViewer(page);
  }
  return done();
}

/**
 * The answers among `COUNT_READERS` that hold something for a name they were never
 * given, each as `reader: name`; read in the page, where an inherited name answers.
 */
function inheritedAnswers(page) {
  return page.evaluate(
    ([readers, names]) =>
      readers.flatMap((reader) => {
        const answer = window.__beadloomViewer[reader]();
        return names.filter((name) => !Object.hasOwn(answer, name) && answer[name] !== undefined).map((name) => `${reader}: ${name}`);
      }),
    [COUNT_READERS, INHERITED_NAMES]
  );
}

const drawnKeys = (data) => data.edges.filter((e) => e.kind === "depends_on").map(edgeKey).sort();

for (const { name, roles } of NAMINGS) {
  test.describe(`a graph with ${name}`, () => {
    test("every node is laid out, drawn in its box and every edge drawn", async ({ page, request }) => {
      const data = await openObjectNamed(page, request, roles);
      await openEveryBox(page, data);
      const ids = data.nodes.map((n) => n.id);

      expect(await missingFrom(page, ids, "positions")).toEqual([]);
      expect(await missingFrom(page, ids, "elkGeometry", "boxes")).toEqual([]);
      expect(await sizeOf(page, "elkGeometry", "routes")).toBe(drawnKeys(data).length);

      const parents = await page.evaluate(() =>
        Object.entries(window.__beadloomViewer.boxes()).map(([id, box]) => [id, box.parent])
      );
      const expected = data.nodes.map((n) => [n.id, n.parent === n.id ? null : n.parent]);
      expect(parents.sort()).toEqual(expected.sort());

      const drawn = (await viewer(page, "edgeRoutes")).filter((route) => !route.aggregated);
      expect(drawn.map((route) => route.key).sort()).toEqual(drawnKeys(data));
    });

    test("the busy node is bundled and every route is kept", async ({ page, request }) => {
      const data = await openObjectNamed(page, request, roles);
      await openEveryBox(page, data);

      expect(await sizeOf(page, "bundles", "routes")).toBe(drawnKeys(data).length);
      const bundledAt = await page.evaluate(() => {
        const { trunks, buses } = window.__beadloomViewer.bundles();
        return [...trunks, ...buses].map((bundle) => bundle.node);
      });
      expect(bundledAt).toContain(roles.busy);
    });

    test("a box opens for what it holds, and for itself", async ({ page, request }) => {
      await openObjectNamed(page, request, roles);

      await viewer(page, "revealNodes", [roles.first]);
      expect(await viewer(page, "openBoxes")).toEqual(
        expect.arrayContaining(["outer", roles.middle, roles.inner])
      );

      await viewer(page, "revealNodes", [roles.middle]);
      expect(await viewer(page, "openBoxes")).toEqual(expect.arrayContaining(["outer", roles.middle]));
    });

    test("the counts drawn on the node named __proto__ are kept for the handle", async ({ page, request }) => {
      // A node beside it in its holder with an edge into it, so a line of its holder ends at it.
      const besideIt = (graph) => {
        const holder = graph.nodes.find((n) => n.id === PROTOTYPE_KEY).parent;
        const rank = graph.nodes.find((n) => n.id === holder).layer_rank;
        return {
          ...graph,
          nodes: [...graph.nodes, nodeOf("beside", "component", holder, rank)],
          edges: [...graph.edges, { src: "beside", dst: holder, kind: "part_of" }, { src: "beside", dst: PROTOTYPE_KEY, kind: "depends_on" }],
        };
      };
      const data = await openObjectNamed(page, request, roles, "", besideIt);
      const named = data.nodes.find((n) => n.id === PROTOTYPE_KEY);
      const isBox = data.nodes.some((n) => n.parent === named.id && n.id !== named.id);
      // Its holder open and the node drawn closed in it: a box says its tally, and a node inside an open box its "+N".
      await viewer(page, "revealNodes", [named.parent], { edges: false });
      const closed = async () => !(await viewer(page, "openBoxes")).includes(named.id);
      if (isBox) expect(await zoomOutUntil(page, closed), `${named.id} is drawn closed`).toBe(true);

      const readers = isBox ? ["outwardMarks", "boxTallies"] : ["outwardMarks"];
      await expect.poll(() => readersMissing(page, named.id, readers)).toEqual([]);
    });

    for (const id of Object.values(roles)) {
      test(`'${id}' is selected from the URL and its card shows it`, async ({ page, request }) => {
        await openObjectNamed(page, request, roles, `?focus=${encodeURIComponent(id)}`);
        expect(await viewer(page, "selection")).toBe(id);
        await expect(page.locator(CARD).locator("h3")).toHaveText(id);
      });
    }
  });
}

test("the counts the map drew answer nothing for a name they were not given", async ({ page }) => {
  await openArchitecture(page);
  expect(await inheritedAnswers(page)).toEqual([]);
});

test("before the map draws any count, the counts answer nothing for any name", async ({ page }) => {
  // The layout's worker cannot load, so the map and its counts are never drawn.
  await page.route("**/elk.worker*.js", (route) => route.abort());
  await page.goto("architecture.html");
  await expect(page.getByRole("alert")).toContainText("could not be laid out", { timeout: 45_000 });
  expect(await inheritedAnswers(page)).toEqual([]);
});
