<script setup>
// beadloom:component=site-graph-edge
// The legend of the edges that are drawn: one line sample per style key.

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { EDGE_STYLES } from "../model/edgeKinds.js";

const props = defineProps({
  keys: { type: Array, required: true },
});

const entries = computed(() =>
  props.keys
    .filter((key) => EDGE_STYLES[key])
    .map((key) => ({
      key,
      text: EDGE_STYLES[key].legend,
      sample: {
        borderTopStyle: EDGE_STYLES[key].line,
        borderTopColor: `var(${TOKEN_VARIABLES[EDGE_STYLES[key].tone]})`,
      },
    }))
);
</script>

<template>
  <span class="bl-legend-group">Edges:</span>
  <span
    v-for="entry in entries"
    :key="entry.key"
    class="bl-legend-item"
    :data-legend-edge="entry.key"
  >
    <span class="bl-legend-line" :style="entry.sample" />
    {{ entry.text }}
  </span>
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
.bl-legend-line {
  display: inline-block;
  width: 24px;
  height: 0;
  border-top-width: 2px;
}
</style>
