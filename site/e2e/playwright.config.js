// Playwright configuration for the portal's browser tests (BDL-076 A2).
//
// The tests drive the BUILT portal, not the dev server: `support/serve.mjs`
// runs `vitepress build` and then `vitepress preview`, so what is tested is the
// bundle that is deployed. The content must be generated first, with
// `beadloom docs site --out site`; the server script refuses to start without it.
//
// Run from `site/`: `npm run test:e2e`.

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SITE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// A port of its own, so a preview the developer already runs on 4173 is not reused.
const PORT = Number(process.env.BEADLOOM_E2E_PORT || 4178);
// The site's configured base path (`base` in `.vitepress/config.mjs`).
const BASE = process.env.BEADLOOM_E2E_BASE || "/beadloom/";

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
