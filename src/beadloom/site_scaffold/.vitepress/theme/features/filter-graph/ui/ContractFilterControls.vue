<script setup>
// beadloom:component=site-filter-graph
// The landscape's filter controls in the viewer's toolbar: protocol, verdict,
// and a switch to show only the problems. It shows the filters it is given and
// reports each change; the viewer owns the state.

import { VERDICT_CHOICES } from "../lib/contractFilters.js";

const props = defineProps({
  filters: { type: Object, required: true },
  options: { type: Object, required: true },
});
const emit = defineEmits(["change"]);

function change(key, value) {
  if (props.filters[key] !== value) emit("change", key, value);
}
</script>

<template>
  <div class="bl-filters">
    <label class="bl-filter">
      <span>Protocol</span>
      <select aria-label="Protocol" :value="filters.protocol" @change="change('protocol', $event.target.value)">
        <option v-for="value in options.protocols" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <label class="bl-filter">
      <span>Verdict</span>
      <select aria-label="Verdict" :value="filters.verdict" @change="change('verdict', $event.target.value)">
        <option v-for="choice in VERDICT_CHOICES" :key="choice.value" :value="choice.value">
          {{ choice.label }}
        </option>
      </select>
    </label>
    <label class="bl-filter bl-filter-check">
      <input
        type="checkbox"
        aria-label="Only problems"
        :checked="filters.problems"
        @change="change('problems', $event.target.checked)"
      />
      <span>Only problems</span>
    </label>
  </div>
</template>

<style scoped>
.bl-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.bl-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--vp-c-text-2);
  font-weight: 600;
}
.bl-filter select {
  padding: 3px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
}
</style>
