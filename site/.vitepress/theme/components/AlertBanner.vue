<script setup>
// AlertBanner — the critical-first attention banner from
// `dashboard.data.json.alerts`. The list is already severity-ordered and
// deterministic in the data (BREAKING contracts first, then errors, then
// warnings); this widget renders it verbatim. Honest by construction — every
// alert derives from an existing gate code path (lint / doctor / sync-check /
// debt / federate); the front-end never invents a problem or a severity.
//
// When `alerts` is empty the project is all-clear and a single green line is
// shown. With JS disabled the static text fallback in `dashboard.md` (the
// "Attention" list / "All clear" line) remains the source of truth.

import { computed } from "vue";
import { useDashboardData } from "../composables/useDashboardData.js";

const { data } = useDashboardData();

const alerts = computed(() => {
  const a = data.value?.alerts;
  return Array.isArray(a) ? a.filter((x) => x && typeof x === "object") : [];
});

const clear = computed(() => Boolean(data.value) && alerts.value.length === 0);

function severityClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "critical") return "bl-alert-critical";
  if (s === "error") return "bl-alert-error";
  if (s === "warn" || s === "warning") return "bl-alert-warn";
  return "bl-alert-info";
}
</script>

<template>
  <section v-if="data" class="bl-attention" aria-label="Attention">
    <p v-if="clear" class="bl-allclear" role="status">
      <span class="bl-allclear-dot" aria-hidden="true"></span>
      All clear — no breaking/drift contracts, lint errors, stale docs, doctor
      errors or high debt.
    </p>
    <div v-else class="bl-banner" role="alert">
      <h2 class="bl-banner-title">Attention</h2>
      <ul class="bl-banner-list">
        <li
          v-for="(a, i) in alerts"
          :key="i"
          :class="['bl-alert', severityClass(a.severity)]"
        >
          <span class="bl-alert-badge">{{ a.severity }}</span>
          <span class="bl-alert-msg">{{ a.message }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.bl-attention {
  margin: 16px 0 24px;
}
.bl-allclear {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid var(--vp-c-divider);
  border-left: 4px solid #3fb950;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-weight: 600;
}
.bl-allclear-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #3fb950;
  flex: none;
}
.bl-banner {
  padding: 14px 18px;
  border: 1px solid var(--vp-c-divider);
  border-left: 4px solid #e45649;
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
}
.bl-banner-title {
  margin: 0 0 8px;
  font-size: 16px;
  border: 0;
  padding: 0;
}
.bl-banner-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bl-alert {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: baseline;
  gap: 10px;
}
.bl-alert-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.bl-alert-critical .bl-alert-badge {
  color: #c9302c;
}
.bl-alert-error .bl-alert-badge {
  color: #e45649;
}
.bl-alert-warn .bl-alert-badge {
  color: #b8890a;
}
.bl-alert-info .bl-alert-badge {
  color: #5b8def;
}
.bl-alert-msg {
  color: var(--vp-c-text-1);
  min-width: 0;
}
@media (max-width: 640px) {
  .bl-alert {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
