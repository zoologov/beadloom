// A Mermaid click target under /other/ is served under the site's base path (BDL-076 A4).
//
// Mermaid's `click` directives are raw strings VitePress does not rewrite, so
// the diagram viewer prepends the base to every internal target. Before A4 it
// knew /services/, /domains/, /features/ and /docs/ only, so a landscape link to
// a page under /other/ would have left the base and ended on a missing page.
//
// Measured while writing this case: on the built site no target was rewritten
// at all, /services/ included. The Mermaid plugin renders a diagram again when
// an attribute of <html> changes, into the same container, and the viewer
// marked the container as enhanced, so the new SVG kept its raw targets and
// lost its pan and its controls.

import { test, expect } from "@playwright/test";
import { landscapeData } from "./support/landscape.js";

const XLINK = "http://www.w3.org/1999/xlink";

test("a landscape diagram link to a page under other/ carries the base path", async ({
  page,
  request,
  baseURL,
}) => {
  const data = await landscapeData(request);
  const target = data.nodes.map((n) => n.url).find((url) => url && url.startsWith("/other/"));
  expect(target, "this landscape has a node whose page is under other/").toBeTruthy();
  const base = new URL(baseURL).pathname;

  await page.goto("landscape-diagram.html");

  const anchors = page.locator(".mermaid svg[data-bl-pz] a");
  await expect.poll(() => anchors.count()).toBeGreaterThan(0);
  const hrefs = await anchors.evaluateAll(
    (items, ns) => items.map((a) => a.getAttributeNS(ns, "href") || a.getAttribute("href")),
    XLINK
  );
  expect(hrefs).toContain(`${base}${target.slice(1)}`);
  expect(hrefs.filter((href) => href.startsWith("/") && !href.startsWith(base))).toEqual([]);
});

test("a diagram rendered again by a theme switch keeps its base-aware links and its controls", async ({
  page,
  baseURL,
}) => {
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
