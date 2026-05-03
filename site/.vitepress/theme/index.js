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
// NOTE: room is intentionally left in `enhanceApp` for BEAD-04 to register the
// ECharts dashboard widgets (HealthGauges / CategoryChart / TrendCharts /
// Recommendations). Do not add those here — that is a separate bead.

import { h } from "vue";
import DefaultTheme from "vitepress/theme";
import DiagramViewer from "./components/DiagramViewer.vue";
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
    // BEAD-04 registers dashboard widgets here (HealthGauges, CategoryChart,
    // TrendCharts, Recommendations) — intentionally left unregistered.
  },
};
