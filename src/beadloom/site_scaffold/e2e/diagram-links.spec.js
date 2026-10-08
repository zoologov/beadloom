// A Mermaid click target under /other/ is served under the site's base path.
//
// Mermaid's `click` directives are raw strings VitePress does not rewrite, so
// the diagram viewer prepends the base to every internal target. In an earlier version it
// knew /services/, /domains/, /features/ and /docs/ only, so a landscape link to
// a page under /other/ would have left the base and ended on a missing page.
//
// Measured while writing this case: on the built site no target was rewritten
// at all, /services/ included. The Mermaid plugin renders a diagram again when
// an attribute of <html> changes, into the same container, and the viewer
// marked the container as enhanced, so the new SVG kept its raw targets and
// lost its pan and its controls.
//
// The case does not wait for the project to hold a landscape node under /other/.
// A project whose contract participants are all services holds none, and a node
// declared with the kind site reads as a service, so a case that needed one would
// be skipped there, or fail under BEADLOOM_E2E_NO_SKIP. It moves one drawn node's
// click target under /other/ in the page's own bundle instead, so the viewer is
// handed the link on every portal whose landscape links a node at all.

import { test, expect } from "@playwright/test";
import { landscapeData } from "./support/landscape.js";
import { requireShape } from "./support/shape.js";

const XLINK = "http://www.w3.org/1999/xlink";

/** The page's bundle chunks, which carry the diagram's Mermaid source URL-encoded. */
const DIAGRAM_CHUNKS = "**/assets/landscape-diagram.md.*.js";

/**
 * Serve the landscape diagram's page with the click target `from` replaced by `to`.
 *
 * Mermaid's `click` lines reach the browser inside the page's bundle chunk, as the
 * Mermaid component's URL-encoded `graph`, each target in its quotes. Returns a
 * reading of whether any chunk served held the target, so a bundle that carries the
 * source some other way fails the case instead of letting it check an unmoved link.
 */
async function serveDiagramWithTargetMoved(page, from, to) {
  const quoted = (url) => encodeURIComponent(`"${url}"`);
  let moved = false;
  await page.route(DIAGRAM_CHUNKS, async (route) => {
    const response = await route.fetch();
    const body = await response.text();
    const next = body.split(quoted(from)).join(quoted(to));
    moved ||= next !== body;
    await route.fulfill({ response, body: next });
  });
  return () => moved;
}

test("a landscape diagram link to a page under other/ carries the base path", async ({
  page,
  request,
  baseURL,
}) => {
  const data = await landscapeData(request);
  const node = data.nodes
    .filter((n) => n.url)
    .sort((a, b) => a.id.localeCompare(b.id))[0];
  requireShape(node, "no node of the landscape has a page for the diagram to link");
  const target = `/other/${node.id}`;
  const base = new URL(baseURL).pathname;
  const moved = await serveDiagramWithTargetMoved(page, node.url, target);

  await page.goto("landscape-diagram.html");

  const anchors = page.locator(".mermaid svg[data-bl-pz] a");
  await expect.poll(() => anchors.count()).toBeGreaterThan(0);
  expect(moved(), `no chunk matching ${DIAGRAM_CHUNKS} held the click target ${node.url}`).toBe(
    true
  );
  const hrefs = await anchors.evaluateAll(
    (items, ns) => items.map((a) => a.getAttributeNS(ns, "href") || a.getAttribute("href")),
    XLINK
  );
  expect(hrefs).toContain(`${base}${target.slice(1)}`);
  expect(hrefs.filter((href) => href.startsWith("/") && !href.startsWith(base))).toEqual([]);
});

test("a diagram rendered again by a theme switch keeps its base-aware links and its controls", async ({
  page,
  request,
  baseURL,
}) => {
  const data = await landscapeData(request);
  requireShape(data.nodes.some((n) => n.url), "no node of the landscape has a page for the diagram to link");
  const base = new URL(baseURL).pathname;
  await page.goto("landscape-diagram.html");
  await expect.poll(() => page.locator(".mermaid svg[data-bl-pz] a").count()).toBeGreaterThan(0);
  // Tag the SVG that is there now, so the case can see a new one replace it.
  await page.locator(".mermaid svg").evaluate((svg) => svg.setAttribute("data-e2e-old", ""));

  await page.evaluate(() => document.documentElement.classList.toggle("dark"));

  await expect(page.locator(".mermaid svg:not([data-e2e-old])")).toHaveCount(1);
  await expect(page.locator(".mermaid svg[data-bl-pz]:not([data-e2e-old])")).toHaveCount(1);
  await expect(page.locator(".mermaid .bl-pz-controls")).toHaveCount(1);
  const hrefs = await page
    .locator(".mermaid svg a")
    .evaluateAll((items, ns) => items.map((a) => a.getAttributeNS(ns, "href")), XLINK);
  expect(hrefs.length).toBeGreaterThan(0);
  expect(hrefs.filter((href) => !href.startsWith(base))).toEqual([]);
});
