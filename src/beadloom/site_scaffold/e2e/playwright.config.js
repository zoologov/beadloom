// Playwright configuration for the portal's browser tests.
//
// The tests drive the BUILT portal, not the dev server: `support/serve.mjs`
// runs `vitepress build` and then `vitepress preview`, so what is tested is the
// bundle that is deployed. The content must be generated first, with
// `beadloom docs site`; the server script refuses to start without it.
//
// Run from the portal's root: `npm run test:e2e`.
//
// A case written about a shape your graph does not hold, such as declared layers
// or a contract in the landscape, is skipped and the report names that shape
// (`support/shape.js`). With BEADLOOM_E2E_NO_SKIP=1 such a case fails instead.
//
// The cases that time the viewer (`performance.spec.js`) run in a project of
// their own, one at a time, after every other case has finished: a case timed
// beside other browsers would time them as well. If another case fails they are
// not run. Their bounds are stated per environment (`support/environment.js`).
// To run them alone: `npx playwright test -c e2e --project performance --no-deps`.
//
// The cases tagged `@adopter-sized` run on a made-up graph of an adopter's size
// rather than on the portal's own (`support/adopterGraph.js`), which takes only
// the served file's declared layer ranks. With BEADLOOM_E2E_NO_ADOPTER_SIZED=1
// they are left out of the run, in every project: a run over several portals
// that declare the same ranks checks them on one of those portals only. The
// filter is set here rather than with `--grep-invert`, because a filter on the
// command line leaves out nothing from `chromium`, which `performance` depends on.

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { importGenerated } from "../.vitepress/generated.mjs";
import { ADOPTER_SIZED, NO_ADOPTER_SIZED } from "./support/adopterGraph.js";

const SITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// A port of its own, so a preview the developer already runs on 4173 is not reused.
const PORT = Number(process.env.BEADLOOM_E2E_PORT || 4178);
// The portal's base path, as `docs site` generated it from the project's `site:`
// block; `/` before the first generation. A module that exists and fails to load
// stops the run rather than aiming every test at `/`.
async function configuredBase() {
  const { site } = await importGenerated(
    new URL("../.vitepress/site.generated.mjs", import.meta.url)
  );
  return site?.base || "/";
}
const BASE = process.env.BEADLOOM_E2E_BASE || (await configuredBase());
/** The browser every case runs in. */
const BROWSER = { ...devices["Desktop Chrome"], viewport: { width: 1400, height: 900 } };
/** The cases that time the viewer, which run alone. */
const PERFORMANCE = "performance.spec.js";

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.js",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 60_000,
  ...(process.env[NO_ADOPTER_SIZED] === "1" ? { grepInvert: new RegExp(ADOPTER_SIZED) } : {}),
  use: {
    baseURL: `http://localhost:${PORT}${BASE}`,
    viewport: { width: 1400, height: 900 },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", testIgnore: PERFORMANCE, use: BROWSER },
    { name: "performance", testMatch: PERFORMANCE, dependencies: ["chromium"], workers: 1, use: BROWSER },
  ],
  webServer: {
    command: `node e2e/support/serve.mjs ${PORT}`,
    cwd: SITE_ROOT,
    url: `http://localhost:${PORT}${BASE}`,
    reuseExistingServer: !process.env.CI,
    timeout: 300_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
