// Playwright configuration for the portal's browser tests (BDL-076 A2).
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

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// A port of its own, so a preview the developer already runs on 4173 is not reused.
const PORT = Number(process.env.BEADLOOM_E2E_PORT || 4178);
// The portal's base path, as `docs site` generated it from the project's `site:`
// block; `/` before the first generation.
async function configuredBase() {
  try {
    const { site } = await import("../.vitepress/site.generated.mjs");
    return site?.base || "/";
  } catch {
    return "/";
  }
}
const BASE = process.env.BEADLOOM_E2E_BASE || (await configuredBase());

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.js",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${PORT}${BASE}`,
    viewport: { width: 1400, height: 900 },
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1400, height: 900 } } }],
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
