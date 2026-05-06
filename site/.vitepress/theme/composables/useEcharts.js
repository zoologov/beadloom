// useEcharts — shared ECharts wiring for the dashboard widgets.
//
// `vue-echarts` (and `echarts`) touch `document` at import time, which breaks
// VitePress's server-side bundle. We therefore load them LAZILY, only in the
// browser, via `defineAsyncComponent` — the dashboard widgets are mounted under
// `<ClientOnly>` so they never render during SSR. We import ONLY the chart /
// component modules the dashboard needs (tree-shaken) and register them once.

import { defineAsyncComponent, ref, onMounted, onBeforeUnmount } from "vue";

function isBrowser() {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

// Async <VChart> — resolves to the real `vue-echarts` component in the browser
// (after registering the needed ECharts modules); never imported during SSR.
export const VChart = defineAsyncComponent(async () => {
  const [{ default: VueECharts }, core, charts, components, renderers] = await Promise.all([
    import("vue-echarts"),
    import("echarts/core"),
    import("echarts/charts"),
    import("echarts/components"),
    import("echarts/renderers"),
  ]);
  core.use([
    renderers.CanvasRenderer,
    charts.BarChart,
    charts.GaugeChart,
    charts.LineChart,
    charts.PieChart,
    components.GridComponent,
    components.LegendComponent,
    components.TitleComponent,
    components.TooltipComponent,
  ]);
  return VueECharts;
});

function detectDark() {
  if (!isBrowser()) {
    return false;
  }
  return document.documentElement.classList.contains("dark");
}

// Brand-aligned palette (matches the VitePress default brand + state colors).
export const palette = {
  good: "#3eaf7c",
  warn: "#e7b416",
  bad: "#e45649",
  info: "#5b8def",
  accent: "#9a6ce0",
  axis: { light: "#8a8f98", dark: "#9ba3ae" },
  split: { light: "#e2e2e3", dark: "#2e2e32" },
  text: { light: "#3c3c43", dark: "#dfdfd6" },
};

export function useEchartsTheme() {
  const isDark = ref(detectDark());
  let observer = null;

  onMounted(() => {
    if (!isBrowser()) {
      return;
    }
    isDark.value = detectDark();
    observer = new MutationObserver(() => {
      isDark.value = detectDark();
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
  });

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  });

  return { isDark };
}
