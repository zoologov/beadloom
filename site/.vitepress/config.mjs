// Committed VitePress scaffold for the Beadloom showcase site.
//
// Beadloom produces, VitePress renders: `beadloom docs site --out site`
// regenerates the content tree (index.md, per-node pages, and
// .vitepress/config.generated.mjs with the nav/sidebar). This file is the
// stable shell that imports that generated nav/sidebar and enables Mermaid.
//
// Run `npm ci && npm run docs:build` to render (dogfooded in BEAD-05; not
// unit-tested — the Python generator is fully testable without node).

import { withMermaid } from "vitepress-plugin-mermaid";

// The generated nav/sidebar. Regenerate with `beadloom docs site` before build.
// Falls back to empty arrays if the site has not been generated yet. A single
// shared EN sidebar (BDL-046 BEAD-11): VitePress `locales` was dropped because
// its global /x↔/ru/x mapping translated the whole menu and 404'd off /ru/. The
// bilingual About is now an in-page cross-link (/ ↔ /ru/) emitted in the README
// transform, not a locale switcher.
let nav = [];
let sidebar = [];
try {
  const generated = await import("./config.generated.mjs");
  nav = generated.nav ?? [];
  sidebar = generated.sidebar ?? [];
} catch {
  // config.generated.mjs is produced by `beadloom docs site`; absent on a
  // fresh checkout before the first generation.
}

export default withMermaid({
  title: "Beadloom",
  description:
    "Living knowledge base: metrics dashboard, interactive architecture, and validated docs.",
  // Served as a GitHub *project page* at https://<owner>.github.io/beadloom/.
  // VitePress auto-prepends this base to markdown/nav links during build; the
  // Mermaid `click "/services/…"` directives are raw strings the plugin does
  // NOT rewrite, so DiagramViewer.vue prepends import.meta.env.BASE_URL to them
  // at runtime (keeps the generated Markdown base-agnostic + deterministic).
  base: "/beadloom/",
  lastUpdated: false,
  // Single shared EN sidebar (BDL-046 BEAD-11): VitePress `locales` was dropped.
  // The default theme still renders the appearance toggle + local search. The
  // bilingual About is an in-page cross-link: the EN About (/) links to the RU
  // About (/ru/) and back, generated from the README cross-link line.
  themeConfig: {
    nav,
    sidebar,
    // GitHub repo button in the nav bar (default-theme social link).
    socialLinks: [
      { icon: "github", link: "https://github.com/zoologov/beadloom" },
    ],
  },
  mermaid: {
    // Mermaid renderer options (C4 + flowchart render natively).
  },
});
