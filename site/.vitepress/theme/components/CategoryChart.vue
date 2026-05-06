<script setup>
// CategoryChart — two breakdowns from `dashboard.data.json`:
//  - debt by category (horizontal bar, from `debt.categories`)
//  - lint by severity (donut, from `lint.by_severity`)
// Values are the exact serialized figures; this widget only visualizes them.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";
import { useEchartsTheme, VChart, palette } from "../composables/useEcharts.js";

const { data } = useDashboardData();
const { isDark } = useEchartsTheme();

const axisColor = computed(() => (isDark.value ? palette.axis.dark : palette.axis.light));
const splitColor = computed(() => (isDark.value ? palette.split.dark : palette.split.light));
const textColor = computed(() => (isDark.value ? palette.text.dark : palette.text.light));

const severityColor = {
  error: palette.bad,
  critical: palette.bad,
  warn: palette.warn,
  warning: palette.warn,
  info: palette.info,
};

const debtCategories = computed(() => {
  const cats = data.value?.debt?.categories;
  if (!Array.isArray(cats)) return [];
  // Keep the generator's order; reverse so the largest sits at the top of a
  // horizontal bar (ECharts y-axis renders bottom-up).
  return cats
    .filter((c) => c && typeof c === "object")
    .map((c) => ({ name: String(c.name ?? ""), score: Number(c.score ?? 0) }));
});

const debtOption = computed(() => {
  const cats = debtCategories.value;
  return {
    title: { text: "Debt by category", left: "center", textStyle: { color: textColor.value, fontSize: 13 } },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      axisLabel: { color: axisColor.value },
      splitLine: { lineStyle: { color: splitColor.value } },
    },
    yAxis: {
      type: "category",
      data: cats.map((c) => c.name).reverse(),
      axisLabel: { color: axisColor.value },
      axisLine: { lineStyle: { color: axisColor.value } },
    },
    series: [
      {
        type: "bar",
        data: cats.map((c) => c.score).reverse(),
        itemStyle: { color: palette.accent, borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 22,
      },
    ],
  };
});

const lintSeverity = computed(() => {
  const by = data.value?.lint?.by_severity;
  if (!by || typeof by !== "object") return [];
  return Object.entries(by)
    .map(([name, value]) => ({ name, value: Number(value) }))
    .filter((d) => d.value > 0);
});

const lintOption = computed(() => {
  const entries = lintSeverity.value;
  return {
    title: { text: "Lint by severity", left: "center", textStyle: { color: textColor.value, fontSize: 13 } },
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, textStyle: { color: axisColor.value } },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: true,
        label: { color: textColor.value },
        data: entries.map((e) => ({
          name: e.name,
          value: e.value,
          itemStyle: { color: severityColor[e.name] ?? palette.info },
        })),
      },
    ],
  };
});

const hasDebt = computed(() => debtCategories.value.length > 0);
const hasLint = computed(() => lintSeverity.value.length > 0);
const show = computed(() => Boolean(data.value) && (hasDebt.value || hasLint.value));
</script>

<template>
  <section v-if="show" class="bl-cat" aria-label="Category breakdowns">
    <div v-if="hasDebt" class="bl-cat-panel">
      <v-chart class="bl-cat-chart" :option="debtOption" autoresize />
    </div>
    <div v-if="hasLint" class="bl-cat-panel">
      <v-chart class="bl-cat-chart" :option="lintOption" autoresize />
    </div>
  </section>
</template>

<style scoped>
.bl-cat {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  margin: 24px 0;
}
.bl-cat-panel {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 12px;
}
.bl-cat-chart {
  height: 280px;
  width: 100%;
}
</style>
