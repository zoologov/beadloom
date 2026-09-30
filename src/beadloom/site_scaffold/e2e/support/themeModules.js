// The theme's own modules, loaded into a blank page the way the browser runs them.
//
// Some behaviour cannot be produced on the built site: no generated page mounts
// two viewers, so what a viewer does beside another one is out of reach there.
// This harness serves the theme's source files and Vue's browser build from an
// origin Playwright fulfils itself, so a case imports a module as it ships and
// calls it directly. Only `vue` is mapped; a module that needs anything else
// cannot be loaded here, and a case says so by failing to import it.

import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const THEME = path.resolve(HERE, "..", "..", ".vitepress", "theme");
const VUE = path.resolve(HERE, "..", "..", "node_modules", "vue", "dist", "vue.esm-browser.prod.js");

/** The origin the harness serves from; nothing listens on it but the route below. */
const ORIGIN = "http://theme-modules.test";
const VUE_PATH = "/vue.js";

const PAGE = `<!doctype html>
<html><head><script type="importmap">{"imports":{"vue":"${VUE_PATH}"}}</script></head>
<body><div id="app"></div></body></html>`;

async function serve(route) {
  const { pathname } = new URL(route.request().url());
  if (pathname === "/") return route.fulfill({ contentType: "text/html", body: PAGE });
  if (pathname === VUE_PATH) return route.fulfill({ contentType: "text/javascript", path: VUE });
  const file = path.resolve(THEME, `.${decodeURIComponent(pathname)}`);
  if (!file.startsWith(`${THEME}${path.sep}`)) return route.fulfill({ status: 404 });
  return route.fulfill({ contentType: "text/javascript", path: file });
}

/** Open the blank page whose origin serves the theme's modules at their paths under the theme. */
export async function openThemeModules(page) {
  await page.route(`${ORIGIN}/**`, serve);
  await page.goto(`${ORIGIN}/`);
}
