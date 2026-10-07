<script setup>
// beadloom:component=site-layer
// The legend of the layers, top to bottom, in their colours: a small card per layer, as the canvas draws its nodes,
// and one more for a node in no layer where the graph has such a node.

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { LAYER_FILL_SHARE, UNLAYERED_NAME, UNLAYERED_TONE } from "../model/layers.js";

const props = defineProps({
  layers: { type: Array, required: true },
  // Whether a node in no layer is drawn, in `UNLAYERED_TONE`.
  unlayered: { type: Boolean, default: false },
});

const heading = computed(() => (props.layers.length ? "Layers (top → bottom):" : "Layers:"));

/** A layer's sample: a border in the layer's tone over a light tint of it, as each of its nodes is drawn. */
function sampleOf({ tone: name }) {
  const tone = `var(${TOKEN_VARIABLES[name]})`;
  return { borderColor: tone, background: `color-mix(in srgb, ${tone} ${LAYER_FILL_SHARE * 100}%, var(--vp-c-bg))` };
}
</script>

<template>
  <template v-if="layers.length || unlayered">
    <span class="bl-legend-group">{{ heading }}</span>
    <span
      v-for="layer in layers"
      :key="layer.rank"
      class="bl-legend-item"
      :data-legend-layer="layer.name"
    >
      <span class="bl-legend-swatch" :style="sampleOf(layer)" />
      {{ layer.name }}
    </span>
    <span v-if="unlayered" class="bl-legend-item" data-legend-unlayered>
      <span class="bl-legend-swatch" :style="sampleOf({ tone: UNLAYERED_TONE })" />
      {{ UNLAYERED_NAME }}
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
