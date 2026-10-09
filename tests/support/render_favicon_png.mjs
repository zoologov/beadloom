// Beadloom's PNG favicon, rendered from its SVG favicon by a headless Chromium.
//
// BDL-080 S4e (`beadloom-af99.9`). The SVG favicon is theme-adaptive: a
// `prefers-color-scheme` query inside it picks the glyph's colour. A browser that
// takes no SVG favicon (Safari) takes the PNG instead, and a PNG cannot adapt, so
// it is the SVG drawn under the light scheme: the colour the SVG draws when no
// query matches. 32 by 32 pixels, on a transparent ground.
//
// The PNG is generated, never drawn by hand. Run from the repository root, naming a
// directory whose `node_modules` holds `@playwright/test` (a portal after `npm ci`):
//
//   node tests/support/render_favicon_png.mjs <portal-dir>
//
// It overwrites `src/beadloom/site_favicon/beadloom-favicon.png`, and
// `tests/unit/application/site/test_beadloom_favicon_png_is_the_light_scheme_glyph.py`
// reads the result back.

import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const SIZE = 32;
const SOURCE = "src/beadloom/site_favicon/beadloom-favicon.svg";
const TARGET = "src/beadloom/site_favicon/beadloom-favicon.png";

const portal = process.argv[2];
if (!portal) {
  console.error("usage: node tests/support/render_favicon_png.mjs <dir with node_modules>");
  process.exit(2);
}
const require = createRequire(join(resolve(portal), "package.json"));
const { chromium } = require("@playwright/test");

const svg = readFileSync(SOURCE);
const source = `data:image/svg+xml;base64,${svg.toString("base64")}`;
const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: SIZE, height: SIZE },
    deviceScaleFactor: 1,
    colorScheme: "light",
  });
  await page.setContent(
    `<html><body style="margin:0;background:transparent">` +
      `<img id="icon" src="${source}" width="${SIZE}" height="${SIZE}" style="display:block">` +
      `</body></html>`
  );
  await page.locator("#icon").evaluate((image) => image.decode());
  const png = await page.screenshot({
    omitBackground: true,
    clip: { x: 0, y: 0, width: SIZE, height: SIZE },
  });
  writeFileSync(TARGET, png);
  console.log(`${TARGET}: ${png.length} bytes, ${SIZE}x${SIZE}, light scheme`);
} finally {
  await browser.close();
}
