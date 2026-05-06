<script setup>
// Recommendations — the prioritized, actionable panel from
// `dashboard.data.json.recommendations`. The list is already severity-ordered
// and deterministic in the data (errors first); this widget renders it verbatim
// and links each item to its `link` (a node/landscape page). Honest by
// construction — every item derives from an existing gate code path.

import { computed } from "vue";
import { withBase } from "vitepress";
import { useDashboardData } from "../composables/useDashboardData.js";

const { data } = useDashboardData();

const recs = computed(() => {
  const r = data.value?.recommendations;
  return Array.isArray(r) ? r.filter((x) => x && typeof x === "object") : [];
});

const empty = computed(() => Boolean(data.value) && recs.value.length === 0);

function severityClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "error" || s === "critical") return "bl-rec-error";
  if (s === "warn" || s === "warning") return "bl-rec-warn";
  return "bl-rec-info";
}

function href(link) {
  // Internal links (start with "/") are base-prefixed for the deployed site.
  return typeof link === "string" && link.startsWith("/") ? withBase(link) : String(link || "#");
}
</script>

<template>
  <section v-if="data" class="bl-recs" aria-label="Recommendations">
    <h2>Recommendations</h2>
    <p v-if="empty" class="bl-recs-clear">
      No outstanding recommendations — lint, contracts, docs and debt are all
      within healthy bounds.
    </p>
    <ul v-else class="bl-recs-list">
      <li v-for="(r, i) in recs" :key="i" :class="['bl-rec', severityClass(r.severity)]">
        <span class="bl-rec-badge">{{ r.severity }}</span>
        <span class="bl-rec-kind">{{ r.kind }}</span>
        <a class="bl-rec-target" :href="href(r.link)">{{ r.target }}</a>
        <span class="bl-rec-msg">{{ r.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.bl-recs {
  margin: 24px 0;
}
.bl-recs-list {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bl-rec {
  display: grid;
  grid-template-columns: auto auto auto 1fr;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--vp-c-divider);
  border-left-width: 4px;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}
.bl-rec-error {
  border-left-color: #e45649;
}
.bl-rec-warn {
  border-left-color: #e7b416;
}
.bl-rec-info {
  border-left-color: #5b8def;
}
.bl-rec-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.bl-rec-error .bl-rec-badge {
  color: #e45649;
}
.bl-rec-warn .bl-rec-badge {
  color: #b8890a;
}
.bl-rec-info .bl-rec-badge {
  color: #5b8def;
}
.bl-rec-kind {
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-rec-target {
  font-weight: 600;
}
.bl-rec-msg {
  color: var(--vp-c-text-2);
  min-width: 0;
}
.bl-recs-clear {
  color: var(--vp-c-text-2);
}
@media (max-width: 640px) {
  .bl-rec {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
