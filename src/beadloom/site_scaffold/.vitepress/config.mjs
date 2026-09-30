// The VitePress config of a portal written by `beadloom docs site`.
//
// Beadloom produces, VitePress renders. `beadloom docs site` writes this file
// from the installed beadloom package, next to two modules it generates on
// every run:
// - `site.generated.mjs`: the portal's identity (title, description, base path,
//   repository link), from the `site:` block of `.beadloom/config.yml`;
// - `config.generated.mjs`: the nav and the sidebar, from the graph.
// Nothing here names a project. To change the portal, put a file under
// `.beadloom/site/` at the same path: it is copied over the output last.
//
// Render with `npm ci && npm run docs:build`.

import { withMermaid } from "vitepress-plugin-mermaid";

/** A module `docs site` generates, or an empty one before the first generation. */
async function generated(name) {
  try {
    return await import(name);
  } catch {
    return {};
  }
}

const { nav = [], sidebar = [] } = await generated("./config.generated.mjs");
const { site = {} } = await generated("./site.generated.mjs");

export default withMermaid({
  title: site.title,
  description: site.description,
  // VitePress prepends the base to Markdown and nav links during the build. The
  // Mermaid `click "/services/…"` directives are raw strings the plugin does not
  // rewrite, so the diagram viewer prepends `import.meta.env.BASE_URL` to them at
  // runtime, which keeps the generated Markdown independent of the base.
  base: site.base || "/",
  lastUpdated: false,
  themeConfig: {
    nav,
    sidebar,
    socialLinks: site.repoUrl ? [{ icon: site.repoIcon, link: site.repoUrl }] : [],
  },
  mermaid: {},
});
