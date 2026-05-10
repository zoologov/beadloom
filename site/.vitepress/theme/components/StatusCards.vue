<script setup>
// StatusCards — compact, threshold-colored status cards from
// `dashboard.data.json.status_cards`, one per metric group (Lint, Debt, Docs,
// Doctor, and Contracts when federated). The card `status` (ok/warn/error) is
// computed deterministically in Python — the severity is DATA, this widget only
// paints the color (green/amber/red). Values are the exact gate figures; the
// front-end never invents a number or a threshold. With JS disabled the static
// status table in `dashboard.md` remains the source of truth.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";

const { data } = useDashboardData();

const cards = computed(() => {
  const c = data.value?.status_cards;
  return Array.isArray(c) ? c.filter((x) => x && typeof x === "object") : [];
});

function statusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "error") return "bl-card-error";
  if (s === "warn") return "bl-card-warn";
  return "bl-card-ok";
}
</script>

<template>
  <section v-if="data && cards.length" class="bl-cards" aria-label="Status">
    <div
      v-for="(c, i) in cards"
      :key="i"
      :class="['bl-card', statusClass(c.status)]"
    >
      <div class="bl-card-label">{{ c.label }}</div>
      <div class="bl-card-value">{{ c.value }}</div>
      <div class="bl-card-detail">{{ c.detail }}</div>
    </div>
  </section>
</template>

<style scoped>
.bl-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 16px 0 24px;
}
.bl-card {
  padding: 14px 16px;
  border: 1px solid var(--vp-c-divider);
  border-top-width: 4px;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}
.bl-card-ok {
  border-top-color: #3fb950;
}
.bl-card-warn {
  border-top-color: #e7b416;
}
.bl-card-error {
  border-top-color: #e45649;
}
.bl-card-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-card-value {
  font-size: 22px;
  font-weight: 700;
  margin: 4px 0 2px;
}
.bl-card-ok .bl-card-value {
  color: #2da44e;
}
.bl-card-warn .bl-card-value {
  color: #b8890a;
}
.bl-card-error .bl-card-value {
  color: #e45649;
}
.bl-card-detail {
  font-size: 13px;
  color: var(--vp-c-text-2);
}
</style>
