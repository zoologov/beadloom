<script setup>
// HealthGauges — four ECharts gauges summarizing project health straight from
// `dashboard.data.json`: lint violations (0 = good), debt score, documentation
// coverage %, and doc freshness (sync) %. Numbers are the exact gate figures;
// this widget only visualizes them.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";
import { useEchartsTheme, VChart, palette } from "../composables/useEcharts.js";

const { data } = useDashboardData();
const { isDark } = useEchartsTheme();

const axisColor = computed(() => (isDark.value ? palette.axis.dark : palette.axis.light));
const textColor = computed(() => (isDark.value ? palette.text.dark : palette.text.light));

// lint: 0 is good; color worsens as violations climb (cap the gauge at a
// readable ceiling but always show the true number in the label).
function lintColor(v) {
  if (v === 0) return palette.good;
  if (v <= 3) return palette.warn;
  return palette.bad;
}
function pctColor(v) {
  if (v >= 80) return palette.good;
  if (v >= 50) return palette.warn;
  return palette.bad;
}

function gaugeOption(title, value, max, color, suffix) {
  return {
    series: [
      {
        type: "gauge",
        min: 0,
        max,
        radius: "92%",
        progress: { show: true, width: 10, itemStyle: { color } },
        axisLine: { lineStyle: { width: 10, color: [[1, isDark.value ? "#2e2e32" : "#ececef"]] } },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { color: axisColor.value } },
        axisLabel: { distance: 14, color: axisColor.value, fontSize: 9 },
        pointer: { width: 4, itemStyle: { color } },
        anchor: { show: true, size: 8, itemStyle: { color } },
        title: { offsetCenter: [0, "72%"], color: textColor.value, fontSize: 12 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, "40%"],
          color,
          fontSize: 22,
          fontWeight: "bold",
          formatter: (val) => `${val}${suffix}`,
        },
        data: [{ value, name: title }],
      },
    ],
  };
}

const gauges = computed(() => {
  const d = data.value;
  if (!d) return [];
  const lint = d.lint?.violations ?? 0;
  const debt = d.debt?.debt_score ?? 0;
  const coverage = d.docs?.coverage_pct ?? 0;
  const sync = d.docs?.freshness_pct ?? 0;
  // lint gauge ceiling scales with the value so a single violation is visible.
  const lintMax = Math.max(5, lint);
  return [
    { key: "lint", option: gaugeOption("Lint violations", lint, lintMax, lintColor(lint), "") },
    { key: "debt", option: gaugeOption("Debt score", debt, 100, pctColor(100 - debt), "") },
    { key: "coverage", option: gaugeOption("Doc coverage", coverage, 100, pctColor(coverage), "%") },
    { key: "sync", option: gaugeOption("Doc freshness", sync, 100, pctColor(sync), "%") },
  ];
});
</script>

<template>
  <section v-if="gauges.length" class="bl-gauges" aria-label="Health gauges">
    <div v-for="g in gauges" :key="g.key" class="bl-gauge">
      <v-chart class="bl-gauge-chart" :option="g.option" autoresize />
    </div>
  </section>
</template>

<style scoped>
.bl-gauges {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin: 24px 0;
}
.bl-gauge {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 8px;
}
.bl-gauge-chart {
  height: 200px;
  width: 100%;
}
</style>
