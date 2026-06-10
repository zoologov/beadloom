<script setup>
// AiTechwriterActivity — honest "AI tech-writer activity" widget (G9). Reads the
// `ai_techwriter` section of `dashboard.data.json` (built in Python from the
// append-only run-record store `.beadloom/ai_techwriter_runs.json`). It shows
// ONLY real recorded runs (no interpolation, sparse-at-first is correct — same
// honesty contract as `trends`):
//   - docs refreshed over time (per-run bars + cumulative line);
//   - input/output token spend per run, cumulative.
// Token counts are FACTS (from the model API `usage` in each record). The $
// figure is a CLEARLY-LABELED ESTIMATE at a configured rate — never a hard cost
// (tiered pricing makes it approximate). When no runs are recorded yet we say so
// explicitly rather than faking activity.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";
import { useEchartsTheme, VChart, palette } from "../composables/useEcharts.js";

const { data } = useDashboardData();
const { isDark } = useEchartsTheme();

const axisColor = computed(() => (isDark.value ? palette.axis.dark : palette.axis.light));
const splitColor = computed(() => (isDark.value ? palette.split.dark : palette.split.light));
const textColor = computed(() => (isDark.value ? palette.text.dark : palette.text.light));

const ai = computed(() => {
  const a = data.value?.ai_techwriter;
  return a && typeof a === "object" ? a : null;
});

const runs = computed(() => {
  const r = ai.value?.runs;
  return Array.isArray(r) ? r : [];
});

const totals = computed(() => ai.value?.totals ?? null);
const cost = computed(() => ai.value?.cost_estimate ?? null);

const hasRuns = computed(() => runs.value.length >= 1);

function shortTs(ts) {
  // ISO timestamp -> "YYYY-MM-DD" (compact + deterministic).
  return typeof ts === "string" ? ts.slice(0, 10) : String(ts);
}

const labels = computed(() => runs.value.map((r) => shortTs(r.ts)));

const docsOption = computed(() => ({
  title: {
    text: "Docs refreshed (per run + cumulative)",
    left: "center",
    textStyle: { color: textColor.value, fontSize: 13 },
  },
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { color: textColor.value, fontSize: 10 } },
  grid: { left: 8, right: 16, top: 40, bottom: 28, containLabel: true },
  xAxis: {
    type: "category",
    data: labels.value,
    axisLabel: { color: axisColor.value, fontSize: 10 },
    axisLine: { lineStyle: { color: axisColor.value } },
  },
  yAxis: {
    type: "value",
    minInterval: 1,
    axisLabel: { color: axisColor.value },
    splitLine: { lineStyle: { color: splitColor.value } },
  },
  series: [
    {
      name: "per run",
      type: "bar",
      data: runs.value.map((r) => r.docs_refreshed),
      itemStyle: { color: palette.info },
    },
    {
      name: "cumulative",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: runs.value.map((r) => r.cumulative_docs),
      itemStyle: { color: palette.good },
      lineStyle: { color: palette.good, width: 2 },
    },
  ],
}));

const tokensOption = computed(() => ({
  title: {
    text: "Token spend (cumulative)",
    left: "center",
    textStyle: { color: textColor.value, fontSize: 13 },
  },
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { color: textColor.value, fontSize: 10 } },
  grid: { left: 8, right: 16, top: 40, bottom: 28, containLabel: true },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: labels.value,
    axisLabel: { color: axisColor.value, fontSize: 10 },
    axisLine: { lineStyle: { color: axisColor.value } },
  },
  yAxis: {
    type: "value",
    axisLabel: { color: axisColor.value },
    splitLine: { lineStyle: { color: splitColor.value } },
  },
  series: [
    {
      name: "input (cumulative)",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: runs.value.map((r) => r.cumulative_input_tokens),
      itemStyle: { color: palette.accent },
      lineStyle: { color: palette.accent, width: 2 },
      areaStyle: { color: palette.accent, opacity: 0.08 },
    },
    {
      name: "output (cumulative)",
      type: "line",
      smooth: true,
      symbolSize: 6,
      data: runs.value.map((r) => r.cumulative_output_tokens),
      itemStyle: { color: palette.warn },
      lineStyle: { color: palette.warn, width: 2 },
      areaStyle: { color: palette.warn, opacity: 0.08 },
    },
  ],
}));
</script>

<template>
  <section v-if="ai" class="bl-ai" aria-label="AI tech-writer activity">
    <h2 class="bl-ai-heading">AI tech-writer activity</h2>
    <template v-if="hasRuns">
      <div class="bl-ai-summary">
        <span><strong>{{ totals?.runs }}</strong> run(s)</span>
        <span><strong>{{ totals?.docs_refreshed }}</strong> docs refreshed</span>
        <span>
          <strong>{{ totals?.input_tokens }}</strong> in /
          <strong>{{ totals?.output_tokens }}</strong> out tokens
        </span>
        <span v-if="cost" class="bl-ai-cost">
          ~${{ cost.usd }} <em>({{ cost.label }})</em>
        </span>
      </div>
      <p class="bl-ai-note">
        Token counts are <strong>facts</strong> from each run's model-API usage.
        The dollar figure is an <strong>estimate</strong> at a configured rate —
        not a hard cost (tiered pricing makes it approximate).
      </p>
      <div class="bl-ai-grid">
        <div class="bl-ai-panel">
          <v-chart class="bl-ai-chart" :option="docsOption" autoresize />
        </div>
        <div class="bl-ai-panel">
          <v-chart class="bl-ai-chart" :option="tokensOption" autoresize />
        </div>
      </div>
    </template>
    <p v-else class="bl-ai-empty">
      <strong>No AI tech-writer runs recorded yet.</strong>
      This widget fills in once the CI tech-writer harness records a run in
      <code>.beadloom/ai_techwriter_runs.json</code> — only real recorded runs
      are shown (no fabricated activity).
    </p>
  </section>
</template>

<style scoped>
.bl-ai {
  margin: 24px 0;
}
.bl-ai-heading {
  font-size: 1.1rem;
  margin: 0 0 8px;
  border: 0;
  padding: 0;
}
.bl-ai-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 6px;
  color: var(--vp-c-text-1);
}
.bl-ai-cost {
  color: var(--vp-c-text-2);
}
.bl-ai-note {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: var(--vp-c-text-2);
}
.bl-ai-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.bl-ai-panel {
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 12px;
}
.bl-ai-chart {
  height: 260px;
  width: 100%;
}
.bl-ai-empty {
  border: 1px dashed var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
  padding: 16px 20px;
  color: var(--vp-c-text-2);
}
</style>
