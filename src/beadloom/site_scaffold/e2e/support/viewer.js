// Helpers shared by the viewer's browser tests.
//
// Every assertion reads STATE through the read-only test handle
// `window.__beadloomViewer`, which the viewer exposes only under automation
// (`navigator.webdriver`). No test compares pixels.

import { expect } from "@playwright/test";

/** Cytoscape's colour for a style value it could not parse. */
export const CYTOSCAPE_FALLBACK_COLOUR = "rgb(153,153,153)";

/** Open the architecture page, optionally with a query string, and wait for the layout. */
export async function openArchitecture(page, query = "") {
  await page.goto(`architecture.html${query}`);
  await waitForViewer(page);
}

/** Wait until the viewer has laid out its graph. */
export async function waitForViewer(page) {
  await page.waitForFunction(() => window.__beadloomViewer?.ready() === true, null, {
    timeout: 45_000,
  });
}

/**
 * Do `navigate`, a move to another page inside the single-page app, and wait for
 * the viewer of the page it leads to.
 *
 * The app changes the URL before it has drawn the next page, so for a while the
 * page being left is still drawn and its viewer is still installed and ready.
 * Neither the URL nor "a ready viewer" says which page's viewer answers; only a
 * handle other than the one installed before the move does.
 */
export async function viewerAfter(page, navigate) {
  await page.evaluate(() => (window.__viewerBeforeMove = window.__beadloomViewer));
  await navigate();
  await page.waitForFunction(
    () => {
      const handle = window.__beadloomViewer;
      return Boolean(handle) && handle !== window.__viewerBeforeMove && handle.ready();
    },
    null,
    { timeout: 45_000 }
  );
}

/**
 * Draw the whole graph at full detail: every box open at once, and every edge
 * drawn as itself, as a reader sees each one by pointing at its node after
 * zooming into its box; with `{ edges: false }`, every box open and the edges
 * drawn as the map draws them at rest, as a reader sees the boxes zoomed into.
 *
 * At the whole-graph fit the viewer draws a map: the boxes at the top, closed,
 * with aggregated edges between them (`map.spec.js`), and an open box keeps its
 * edges to the outside on its box's lines (`levels.spec.js`). A case about every
 * node or every edge of the graph opens every box first, with the handle's one
 * action, which draws each node it names as itself, with its outward edges
 * unless told otherwise; `positions` names every node, drawn or not.
 */
export async function openEveryBox(page, { edges = true } = {}) {
  await page.evaluate((own) => {
    const handle = window.__beadloomViewer;
    handle.revealNodes(Object.keys(handle.positions()), { edges: own });
  }, edges);
}

/** Call a read-only method of the test handle and return its answer. */
export function viewer(page, method, ...args) {
  return page.evaluate(([name, params]) => window.__beadloomViewer[name](...params), [
    method,
    args,
  ]);
}

/** The data file the page was built from, as the browser receives it. */
export async function architectureData(request) {
  const response = await request.get("architecture.data.json");
  expect(response.ok()).toBe(true);
  return response.json();
}

/** Each node's parent, from the data file (a root that is its own parent has none). */
export function parentMap(data) {
  const ids = new Set(data.nodes.map((n) => n.id));
  const parents = {};
  for (const n of data.nodes) {
    parents[n.id] = n.parent && n.parent !== n.id && ids.has(n.parent) ? n.parent : null;
  }
  return parents;
}

/** Every ancestor of each id in `ids`, plus the ids themselves. */
export function withAncestors(ids, parents) {
  const out = new Set();
  for (const id of ids) {
    let cursor = id;
    while (cursor && !out.has(cursor)) {
      out.add(cursor);
      cursor = parents[cursor];
    }
  }
  return out;
}

/** The ids under `root` at any depth, `root` included. */
export function subtreeOf(root, parents) {
  const children = {};
  for (const [id, parent] of Object.entries(parents)) {
    if (parent) (children[parent] ||= []).push(id);
  }
  const out = new Set();
  const stack = [root];
  while (stack.length) {
    const id = stack.pop();
    if (out.has(id)) continue;
    out.add(id);
    stack.push(...(children[id] || []));
  }
  return out;
}

/** The node's depth below the top of the containment tree. */
export function depthOf(id, parents) {
  let depth = 0;
  for (let cursor = parents[id]; cursor; cursor = parents[cursor]) depth += 1;
  return depth;
}

/**
 * The colour entries that did not resolve: Cytoscape's fallback grey, or a
 * `var(...)` string that reached a style unresolved.
 */
export function unresolvedColours(colours) {
  return colours.filter(
    (c) => c.value.replace(/\s+/g, "") === CYTOSCAPE_FALLBACK_COLOUR || /var\(/.test(c.value)
  );
}

/**
 * Start collecting every style Cytoscape rejects on `page`; returns the live list.
 *
 * Cytoscape validates a stylesheet when it is applied and logs each value it
 * cannot parse, then keeps the property's previous value. A rejected colour is
 * therefore not always visible as the fallback grey, and this list is what
 * shows it. Call it before the page loads.
 */
export function collectRejectedStyles(page) {
  const rejected = [];
  page.on("console", (message) => {
    if (/style property .* is invalid/i.test(message.text())) rejected.push(message.text());
  });
  return rejected;
}

/** The nodes the "Only flagged" filter keeps: a rule violation, or stale docs. */
export function flaggedIds(data) {
  return data.nodes
    .filter((n) => n.lint_clean === false || n.doc_status === "stale")
    .map((n) => n.id);
}

/**
 * What full screen shows, read from the element that is full screen now.
 *
 * `{ active, fills, shown }`: whether anything is full screen, whether it
 * covers the viewport, and for each name of `selectors` whether its element is
 * inside it and laid out on screen: not hidden, and not wholly outside the viewport.
 */
export function fullscreenView(page, selectors) {
  return page.evaluate((wanted) => {
    const element =
      document.fullscreenElement || document.querySelector("[data-fullscreen-fallback='on']");
    // Laid out and at least partly on screen: a long card scrolls inside its panel.
    const inView = (rect) =>
      rect.width > 0 &&
      rect.height > 0 &&
      rect.left < window.innerWidth &&
      rect.top < window.innerHeight &&
      rect.right > 0 &&
      rect.bottom > 0;
    const shown = {};
    for (const [name, selector] of Object.entries(wanted)) {
      const target = document.querySelector(selector);
      shown[name] = Boolean(
        element && target && element.contains(target) && inView(target.getBoundingClientRect())
      );
    }
    const box = element?.getBoundingClientRect();
    return {
      active: Boolean(element),
      fills: Boolean(box && box.width >= window.innerWidth - 1 && box.height >= window.innerHeight - 1),
      shown,
    };
  }, selectors);
}

/** What a reader of a selected node needs on screen: the tools, the canvas, the card, the legend. */
export const SELECTED_VIEW = Object.freeze({
  toolbar: "[role='toolbar']",
  canvas: "[data-testid='graph-canvas']",
  card: "[data-testid='node-card']",
  legend: "[aria-label='Legend']",
});

/**
 * The data file with every drawn kind present: one `depends_on` edge marked as a
 * violation, and one `uses`, one `consumes` and one `produces` edge added, so the
 * styles are checked whether or not the served graph carries them. A project whose
 * graph has only `depends_on` edges, as most do, still has every style read.
 */
export async function serveEveryEdgeKind(page, request) {
  const data = await architectureData(request);
  const plain = data.edges.filter((e) => e.kind === "depends_on" && !e.violation);
  const [first, second] = plain;
  first.violation = true;
  data.edges.push({ src: second.src, dst: second.dst, kind: "uses" });
  data.edges.push({ src: second.src, dst: second.dst, kind: "consumes" });
  data.edges.push({ src: second.dst, dst: second.src, kind: "produces" });
  await page.route("**/architecture.data.json", (route) => route.fulfill({ json: data }));
  return data;
}
