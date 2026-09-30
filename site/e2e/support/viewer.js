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
