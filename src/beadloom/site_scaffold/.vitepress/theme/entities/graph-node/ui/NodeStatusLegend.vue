<script setup>
// beadloom:component=site-graph-node
// The legend of the node statuses that are drawn: a small card per status, with its mark in the corner.
//
// A sample is drawn as the canvas draws a node with that status: a card whose
// border is a layer's, never the status's, and the status's mark in its top
// right corner, filled or a ring (`NODE_STATUSES`).

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { NODE_STATUSES } from "../model/node.js";

const props = defineProps({
  statuses: { type: Array, required: true },
});

const entries = computed(() =>
  props.statuses
    .filter((status) => NODE_STATUSES[status])
    .map((status) => {
      const look = NODE_STATUSES[status];
      const tone = `var(${TOKEN_VARIABLES[look.tone]})`;
      return {
        status,
        text: look.legend,
        shape: look.mark,
        mark: { borderColor: tone, backgroundColor: look.mark === "filled" ? tone : "transparent" },
      };
    })
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
      <span class="bl-legend-card">
        <span class="bl-legend-mark" :data-legend-mark="entry.shape" :style="entry.mark" />
      </span>
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
.bl-legend-card {
  position: relative;
  display: inline-block;
  width: 20px;
  height: 12px;
  border: 1.5px solid var(--vp-c-gray-1);
  border-radius: 3px;
  background: var(--vp-c-bg-soft);
}
.bl-legend-mark {
  position: absolute;
  top: 1px;
  right: 1px;
  box-sizing: border-box;
  width: 6px;
  height: 6px;
  border: 1.5px solid;
  border-radius: 50%;
}
</style>
