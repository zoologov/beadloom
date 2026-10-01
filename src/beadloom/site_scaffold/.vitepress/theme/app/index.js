// beadloom:component=site-app
// The theme: the VitePress default theme, extended by the site's pages and widgets.
//
// Feature-Sliced Design. This is the `app` layer: it wires the slices
// below it into VitePress and holds no behaviour of its own. It mounts the
// Mermaid diagram viewer on every page and registers, by name, the components
// the generated Markdown mounts: the architecture and landscape pages and the
// dashboard's panels. Each is SSR-safe under the `<ClientOnly>` the generated
// page puts around it, where the static summary is the fallback.
//
// Layers, top to bottom, each importing only the ones below it: app, pages,
// widgets, features, entities, shared.

import { h } from "vue";
import DefaultTheme from "vitepress/theme";
import { ArchitectureMap } from "../pages/architecture/index.js";
import { LandscapeMap } from "../pages/landscape/index.js";
import {
  AiTechwriterActivity,
  AlertBanner,
  CategoryChart,
  HealthGauges,
  Recommendations,
  StatusCards,
  TrendCharts,
} from "../widgets/dashboard/index.js";
import { DiagramViewer } from "../widgets/diagram-viewer/index.js";

/** The components the generated pages mount by name. */
const GLOBAL_COMPONENTS = {
  DiagramViewer,
  AlertBanner,
  StatusCards,
  HealthGauges,
  CategoryChart,
  TrendCharts,
  AiTechwriterActivity,
  Recommendations,
  LandscapeMap,
  ArchitectureMap,
};

/** @type {import('vitepress').Theme} */
export default {
  extends: DefaultTheme,
  // The diagram viewer is mounted on every page, in the content area, where it
  // enhances each `.mermaid` SVG the page rendered.
  Layout() {
    return h(DefaultTheme.Layout, null, {
      "doc-footer-before": () => h(DiagramViewer),
    });
  },
  enhanceApp({ app }) {
    for (const [name, component] of Object.entries(GLOBAL_COMPONENTS)) {
      app.component(name, component);
    }
  },
};
