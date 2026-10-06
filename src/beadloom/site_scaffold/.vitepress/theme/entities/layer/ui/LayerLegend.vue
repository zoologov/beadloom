<script setup>
// beadloom:component=site-layer
// The legend of the layers, top to bottom, in their colours: a small card per layer, as the canvas draws its nodes.

import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { LAYER_FILL_SHARE } from "../model/layers.js";

defineProps({
  layers: { type: Array, required: true },
});

/** A layer's sample: a border in the layer's tone over a light tint of it, as each of its nodes is drawn. */
function sampleOf(layer) {
  const tone = `var(${TOKEN_VARIABLES[layer.tone]})`;
  return { borderColor: tone, background: `color-mix(in srgb, ${tone} ${LAYER_FILL_SHARE * 100}%, var(--vp-c-bg))` };
}
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
      <span class="bl-legend-swatch" :style="sampleOf(layer)" />
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
  width: 20px;
  height: 12px;
  border: 1.5px solid;
  border-radius: 3px;
}
</style>
