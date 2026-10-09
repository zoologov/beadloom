// The VitePress config of a portal written by `beadloom docs site`.
//
// Beadloom produces, VitePress renders. `beadloom docs site` writes this file
// from the installed beadloom package, next to two modules it generates on
// every run:
// - `site.generated.mjs`: the portal's identity (title, description, base path,
//   repository link and its icon, the project's logo and how it is drawn, the
//   favicons, the footer switch), from the `site:` block of `.beadloom/config.yml`;
// - `config.generated.mjs`: the nav and the sidebar, from the graph.
// Nothing here names a project. To change the portal, put a file under
// `.beadloom/site/` at the same path: it is copied over the output last.
//
// Render with `npm ci && npm run docs:build`.

import { withMermaid } from "vitepress-plugin-mermaid";
import { importGenerated } from "./generated.mjs";

// Empty before the first generation; a module that exists and fails to load stops the build.
const { nav = [], sidebar = [] } = await importGenerated(
  new URL("./config.generated.mjs", import.meta.url)
);
const { site = {} } = await importGenerated(new URL("./site.generated.mjs", import.meta.url));
const base = site.base || "/";
/** A path the identity names from the portal's root, under the base. */
const underBase = (path) => `${base}${path.replace(/^\//, "")}`;
// The favicons the identity names: the project's logo when it has one of its own,
// Beadloom's icon and its PNG otherwise. A `head` entry is written as it is, so
// the base is prepended here.
const favicons = (site.favicons || []).map((icon) => [
  "link",
  { rel: "icon", ...icon, href: underBase(icon.href) },
]);

/**
 * The project's logo in the nav; none without one. A logo drawn in `currentColor`
 * is marked for the theme's stylesheet (`theme/app/styles/nav-logo.css`), which
 * draws it in the text's colour through the file as a mask: an image cannot
 * inherit the page's colour, and would be black on the dark theme.
 */
function navLogo() {
  if (!site.logo) return undefined;
  if (!site.logoMonochrome) return site.logo;
  const mask = `--bl-nav-logo: url("${underBase(site.logo)}")`;
  return { src: site.logo, "data-monochrome": "", style: mask };
}

export default withMermaid({
  title: site.title,
  description: site.description,
  // VitePress prepends the base to Markdown and nav links during the build. The
  // Mermaid `click "/services/…"` directives are raw strings the plugin does not
  // rewrite, so the diagram viewer prepends `import.meta.env.BASE_URL` to them at
  // runtime, which keeps the generated Markdown independent of the base.
  base,
  head: favicons,
  lastUpdated: false,
  themeConfig: {
    nav,
    sidebar,
    // The project's own logo, copied under `public/` by `docs site`; none without one.
    logo: navLogo(),
    socialLinks: site.repoUrl ? [{ icon: site.repoIcon, link: site.repoUrl }] : [],
    // The "Powered by Beadloom" footer; on unless the project switched it off.
    poweredBy: site.poweredBy !== false,
  },
  mermaid: {},
  // The Mermaid plugin loads `mermaid` from inside VitePress's own client, which
  // the dev server serves without pre-bundling, so Mermaid's CommonJS
  // dependencies (`fastdom` first) reach the browser as they are and a page
  // throws before it mounts. Pre-bundling Mermaid turns them into ES modules.
  // The layout worker's ELK engine is named too: the optimizer does not scan
  // workers, so it would find the engine only on the first visit to the
  // architecture page and reload that page under the reader. The build bundles
  // everything and is not affected; `npm run dev-check` loads the pages under
  // the dev server to keep it that way.
  vite: {
    optimizeDeps: { include: ["mermaid", "elkjs/lib/elk-worker.min.js"] },
  },
});
