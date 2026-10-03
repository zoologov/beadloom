<script setup>
// beadloom:component=site-graph-node
// The legend of the node statuses that are drawn: one border sample per status.

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { NODE_STATUSES } from "../model/node.js";

const props = defineProps({
  statuses: { type: Array, required: true },
});

const entries = computed(() =>
  props.statuses
    .filter((status) => NODE_STATUSES[status])
    .map((status) => ({
      status,
      text: NODE_STATUSES[status].legend,
      sample: {
        borderStyle: NODE_STATUSES[status].border,
        borderColor: `var(${TOKEN_VARIABLES[NODE_STATUSES[status].tone]})`,
      },
    }))
);
</script>

<template>
  <template v-if="entries.length">
    <span class="bl-legend-group">Nodes:</span>
    <span
      v-for="entry in entries"
      :key="entry.status"
      class="bl-legend-item"
      :data-legend-status="entry.status"
    >
      <span class="bl-legend-sample" :style="entry.sample" />
      {{ entry.text }}
    </span>
  </template>
</template>

<style scoped>
.bl-legend-group {
  font-weight: 700;
  color: var(--vp-c-text-1);
}
.bl-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bl-legend-sample {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-width: 4px;
  border-radius: 3px;
}
</style>
