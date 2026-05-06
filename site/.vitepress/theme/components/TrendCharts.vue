<script setup>
// TrendCharts — line charts of the recorded `trends` series from
// `dashboard.data.json` (lint / debt / coverage% / sync% over time). The series
// contains ONLY real recorded points (sparse at first, grows one point per
// `docs site` run) — no interpolation. With 0–1 points there is not yet enough
// history to draw an honest line, so we say so explicitly rather than faking a
// trend.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";
import { useEchartsTheme, VChart, palette } from "../composables/useEcharts.js";

const { data } = useDashboardData();
const { isDark } = useEchartsTheme();

const axisColor = computed(() => (isDark.value ? palette.axis.dark : palette.axis.light));
const splitColor = computed(() => (isDark.value ? palette.split.dark : palette.split.light));
const textColor = computed(() => (isDark.value ? palette.text.dark : palette.text.light));

const trends = computed(() => {
  const t = data.value?.trends;
  return Array.isArray(t) ? t : [];
});

// Honest gate: a line needs at least two real points to mean anything.
const enoughHistory = computed(() => trends.value.length >= 2);

function shortTs(ts) {
  // ISO timestamp -> "YYYY-MM-DD" (keep it compact + deterministic).
  return typeof ts === "string" ? ts.slice(0, 10) : String(ts);
}

function lineOption(title, key, color, suffix) {
  const t = trends.value;
  return {
    title: { text: title, left: "center", textStyle: { color: textColor.value, fontSize: 13 } },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => `${v}${suffix}`,
    },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: t.map((p) => shortTs(p.ts)),
      axisLabel: { color: axisColor.value, fontSize: 10 },
      axisLine: { lineStyle: { color: axisColor.value } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: axisColor.value, formatter: (v) => `${v}${suffix}` },
      splitLine: { lineStyle: { color: splitColor.value } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        data: t.map((p) => p[key]),
        itemStyle: { color },
        lineStyle: { color, width: 2 },
        areaStyle: { color, opacity: 0.08 },
      },
    ],
  };
}

const charts = computed(() => [
  { key: "lint", option: lineOption("Lint violations over time", "lint_violations", palette.bad, "") },
  { key: "debt", option: lineOption("Debt score over time", "debt_score", palette.accent, "") },
  { key: "coverage", option: lineOption("Doc coverage over time", "coverage_pct", palette.good, "%") },
  { key: "sync", option: lineOption("Doc freshness over time", "sync_pct", palette.info, "%") },
]);

const pointCount = computed(() => trends.value.length);
</script>

<template>
  <section v-if="data" class="bl-trends" aria-label="Trends over time">
    <div v-if="enoughHistory" class="bl-trend-grid">
      <div v-for="c in charts" :key="c.key" class="bl-trend-panel">
        <v-chart class="bl-trend-chart" :option="c.option" autoresize />
      </div>
    </div>
    <p v-else class="bl-trend-empty">
      <strong>Not enough history yet.</strong>
      Trends need at least two recorded points; this project has
      {{ pointCount }} so far. Each <code>beadloom docs site</code> run records one
      honest point — re-run over time and the lines will appear (no fabricated
      data is shown).
    </p>
  </section>
</template>

<style scoped>
.bl-trends {
  margin: 24px 0;
}
.bl-trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.bl-trend-panel {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 12px;
}
.bl-trend-chart {
  height: 240px;
  width: 100%;
}
.bl-trend-empty {
  border: 1px dashed var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 16px 20px;
  color: var(--vp-c-text-2);
}
</style>
