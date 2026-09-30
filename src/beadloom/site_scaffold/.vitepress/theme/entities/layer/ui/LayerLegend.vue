<script setup>
// beadloom:component=site-layer
// The legend of the layers, top to bottom, in their colours.

import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";

defineProps({
  layers: { type: Array, required: true },
});
</script>

<template>
  <template v-if="layers.length">
    <span class="bl-legend-group">Layers (top → bottom):</span>
    <span
      v-for="layer in layers"
      :key="layer.rank"
      class="bl-legend-item"
      :data-legend-layer="layer.name"
    >
      <span class="bl-legend-swatch" :style="{ background: `var(${TOKEN_VARIABLES[layer.tone]})` }" />
      {{ layer.name }}
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
.bl-legend-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}
</style>
