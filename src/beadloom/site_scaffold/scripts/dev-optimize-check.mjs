// The portal's pages load under the VitePress dev server.
//
// `vitepress build` (the production bundle) and the VitePress *dev* server
// resolve dependencies differently: the dev server pre-bundles them with Vite's
// optimizer and serves the rest as they are, so a dependency chain the build
// resolves can still crash a page under the dev server. That happened twice:
// once when the theme reached elkjs through cytoscape-elk, whose `web-worker`
// dependency did not resolve under the optimizer, and once when Mermaid's
// `fastdom`, a CommonJS module, was served unbundled and a page threw "does not
// provide an export named default" before anything mounted. A server that only
// boots catches neither, because both fail in the browser.
//
// This script boots the dev server programmatically, opens a page with a
// Mermaid diagram and the architecture page in a headless browser, and waits
// for each to finish: the diagram drawn as SVG, the graph viewer laid out by
// its layout worker. Any uncaught page error, or a page that never finishes,
// fails the check. Run it from the portal's root after `beadloom docs site`:
// `npm run dev-check`.

import { chromium } from "@playwright/test";
import { createServer } from "vitepress";
import { importGenerated } from "../.vitepress/generated.mjs";

const ROOT = new URL("..", import.meta.url).pathname;
const PORT = Number(process.env.BEADLOOM_DEV_CHECK_PORT || 5199);
/** The first load waits for the optimizer, so a page gets this long to finish, in ms. */
const PAGE_TIMEOUT_MS = 120_000;

/** The pages loaded, each with the condition that says it has finished. */
const PAGES = [
  {
    path: "architecture-diagram.html",
    what: "a Mermaid diagram drawn as SVG",
    done: () => document.querySelector(".mermaid svg") !== null,
  },
  {
    path: "architecture.html",
    what: "the graph viewer laid out by its worker",
    done: () => window.__beadloomViewer?.ready() === true,
  },
];

/**
 * Open `path` and wait until it is done or raises its first page error; the
 * errors it raised, empty when none. A page that threw is not waited for: a
 * throw on load leaves nothing mounted, so the wait would only run out.
 */
async function loadPage(browser, baseUrl, { path, what, done }) {
  const page = await browser.newPage();
  const errors = [];
  const firstError = new Promise((resolve) => {
    page.on("pageerror", (error) => {
      errors.push(error.message);
      resolve();
    });
  });
  try {
    await page.goto(new URL(path, baseUrl).href);
    await Promise.race([page.waitForFunction(done, null, { timeout: PAGE_TIMEOUT_MS }), firstError]);
  } catch (error) {
    errors.push(`${what} never appeared: ${error.message.split("\n")[0]}`);
  } finally {
    await page.close();
  }
  return errors.map((message) => `${path}: ${message}`);
}

async function main() {
  const { site = {} } = await importGenerated(new URL("../.vitepress/site.generated.mjs", import.meta.url));
  const baseUrl = `http://localhost:${PORT}${site.base || "/"}`;
  const server = await createServer(ROOT, { port: PORT, strictPort: true });
  const browser = await chromium.launch();
  const failures = [];
  try {
    await server.listen();
    for (const entry of PAGES) {
      failures.push(...(await loadPage(browser, baseUrl, entry)));
    }
  } finally {
    await browser.close();
    await server.close();
  }
  if (failures.length > 0) {
    throw new Error(`the dev server served a page that failed:\n  ${failures.join("\n  ")}`);
  }
  process.stdout.write(`DEV-OPTIMIZE-CHECK OK: ${PAGES.length} pages loaded under the dev server\n`);
}

main().catch((err) => {
  process.stderr.write(`DEV-OPTIMIZE-CHECK FAIL: ${err?.stack || err}\n`);
  process.exit(1);
});
