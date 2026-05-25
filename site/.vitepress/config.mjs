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
// Falls back to empty arrays if the site has not been generated yet.
// `navRu`/`sidebarRu` drive the RU locale (curated About-only): the RU sidebar
// translates only the top-level labels + points About at /ru/; every other link
// stays on the EN routes (BDL-046).
let nav = [];
let sidebar = [];
let navRu = [];
let sidebarRu = [];
try {
  const generated = await import("./config.generated.mjs");
  nav = generated.nav ?? [];
  sidebar = generated.sidebar ?? [];
  navRu = generated.navRu ?? [];
  sidebarRu = generated.sidebarRu ?? [];
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
  // Curated bilingual entry (BDL-046): only the About page is translated. The
  // default theme renders the locale switcher (the visible language toggle) plus
  // the appearance toggle + local search regardless of the empty top nav. The RU
  // locale serves /ru/ (About from README.ru.md); its other menu links return to
  // the EN routes — switching to RU and opening a doc shows the EN doc by design.
  locales: {
    root: {
      label: "English",
      lang: "en",
      themeConfig: { nav, sidebar },
    },
    ru: {
      label: "Русский",
      lang: "ru",
      link: "/ru/",
      themeConfig: { nav: navRu, sidebar: sidebarRu },
    },
  },
  mermaid: {
    // Mermaid renderer options (C4 + flowchart render natively).
  },
});
