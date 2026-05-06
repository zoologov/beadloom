// Custom VitePress theme for the Beadloom showcase site.
//
// Extends the VitePress default theme and mounts a global diagram viewer that
// augments the Mermaid SVGs rendered by `vitepress-plugin-mermaid` with
// pan / wheel-zoom / reset (svg-pan-zoom) and a fullscreen toggle.
//
// Beadloom produces, VitePress renders: the Python generator emits the
// content + Mermaid; this theme only enhances the already-rendered output
// client-side. Mermaid itself stays enabled via `withMermaid` in config.mjs.
//
// BEAD-04 registers the ECharts dashboard widgets (HealthGauges / CategoryChart
// / TrendCharts / Recommendations) globally in `enhanceApp` below, alongside
// DiagramViewer. They read the deterministic `dashboard.data.json` and render
// client-side via `vue-echarts`; the dashboard page mounts them inside a
// `<ClientOnly>` wrapper so the static honest summary remains the fallback.

import { h } from "vue";
import DefaultTheme from "vitepress/theme";
import DiagramViewer from "./components/DiagramViewer.vue";
import HealthGauges from "./components/HealthGauges.vue";
import CategoryChart from "./components/CategoryChart.vue";
import TrendCharts from "./components/TrendCharts.vue";
import Recommendations from "./components/Recommendations.vue";
import "./custom.css";

/** @type {import('vitepress').Theme} */
export default {
  extends: DefaultTheme,
  // Wrap the default layout so the diagram viewer is mounted on every page; it
  // scans the rendered document for `.mermaid` SVGs and enhances each one. The
  // `doc-footer-before` slot keeps it inside the content area without altering
  // the default layout chrome.
  Layout() {
    return h(DefaultTheme.Layout, null, {
      "doc-footer-before": () => h(DiagramViewer),
    });
  },
  enhanceApp({ app }) {
    // Also expose it as a global component so pages can mount it explicitly.
    app.component("DiagramViewer", DiagramViewer);
    // Dashboard widgets (BEAD-04) — registered globally so the generated
    // `dashboard.md` can mount them by name. Each reads `dashboard.data.json`.
    app.component("HealthGauges", HealthGauges);
    app.component("CategoryChart", CategoryChart);
    app.component("TrendCharts", TrendCharts);
    app.component("Recommendations", Recommendations);
  },
};
