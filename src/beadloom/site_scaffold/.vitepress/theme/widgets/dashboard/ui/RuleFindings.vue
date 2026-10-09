<script setup>
// beadloom:component=site-dashboard
// RuleFindings — lint's reach over the whole project, from
// `dashboard.data.json.lint`: its totals, how many nodes carry a finding, and
// every finding bound to no node, with the file and line it points at. A node's
// findings are on its card; these are the ones no card holds. A data file
// written before the reach was carried shows nothing here.

import { computed } from "vue";
import { useDashboardData } from "../../../entities/dashboard-data/index.js";

const { data } = useDashboardData();

const lint = computed(() => {
  const value = data.value?.lint;
  return value && Array.isArray(value.nodeless) ? value : null;
});

/** `count` followed by `one` when it is 1, and by `many` otherwise. */
const countOf = (count, one, many) => `${count} ${count === 1 ? one : many}`;

const totals = computed(() => {
  const value = lint.value;
  if (!value) return "";
  return (
    `${countOf(value.errors, "error", "errors")}, ${countOf(value.warnings, "warning", "warnings")} ` +
    `on ${countOf(value.nodes_with_findings, "node", "nodes")}`
  );
});

const placeOf = (finding) => (finding.file ? `${finding.file}${finding.line ? `:${finding.line}` : ""}` : "");
</script>

<template>
  <section v-if="lint" class="bl-reach" aria-label="Rule findings" data-testid="rule-findings">
    <h2>Rule findings</h2>
    <p data-reach="totals">This project: {{ totals }}.</p>
    <p data-reach="nodeless">
      {{ countOf(lint.nodeless.length, "finding is", "findings are") }} bound to no node<template v-if="lint.nodeless.length">:</template><template v-else>.</template>
    </p>
    <template v-if="lint.nodeless.length">
      <ul class="bl-reach-list">
        <li v-for="(finding, index) in lint.nodeless" :key="index" data-nodeless-finding>
          <code>{{ finding.rule }}</code>
          <span class="bl-reach-severity" :class="{ 'bl-reach-error': finding.severity === 'error' }">{{ finding.severity }}</span>
          <span>{{ finding.message }}</span>
          <code v-if="placeOf(finding)" class="bl-reach-place">{{ placeOf(finding) }}</code>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.bl-reach {
  margin: 24px 0;
}
.bl-reach-list {
  padding-left: 18px;
  font-size: 14px;
}
.bl-reach-list li {
  margin: 4px 0;
}
.bl-reach-severity {
  margin: 0 6px;
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-reach-error {
  color: var(--vp-c-danger-1);
  font-weight: 700;
}
.bl-reach-place {
  margin-left: 6px;
  color: var(--vp-c-text-3);
}
</style>
