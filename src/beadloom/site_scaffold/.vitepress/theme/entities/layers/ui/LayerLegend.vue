<script setup>
// beadloom:component=site-layers
// The legend of the layers, top to bottom, in their colours: a small card per layer, as the canvas draws its nodes,
// and one more for a node in no layer where the graph has such a node.
//
// Where more than one layer rule is drawn, the layers are grouped per rule under
// the rule's title, or its name where it declares none: each rule's layers take
// the tones by their own position, so a tone says which layer only beside the
// rule it belongs to. One rule, or a file that names one order, is one group
// under the rule's title where it declares one, else under "Layers", as it
// always was.

import { computed } from "vue";
import { TOKEN_VARIABLES } from "../../../shared/theme-tokens/index.js";
import { LAYER_FILL_SHARE, UNLAYERED_NAME, UNLAYERED_TONE, layerRulesOf } from "../model/layers.js";

/** How the legend says a group's layers run. */
const DIRECTION = "(top → bottom):";

const props = defineProps({
  layers: { type: Array, required: true },
  // Whether a node in no layer is drawn, in `UNLAYERED_TONE`.
  unlayered: { type: Boolean, default: false },
});

/** The groups the legend shows, `[{ rule, heading, layers }]`: one per rule, or one under "Layers" or its rule's title. */
const groups = computed(() => {
  const rules = layerRulesOf(props.layers);
  if (rules.length > 1) return rules.map(({ rule, title, layers }) => ({ rule, heading: `${title || rule} ${DIRECTION}`, layers }));
  const [only] = rules;
  const heading = props.layers.length ? `${only?.title || "Layers"} ${DIRECTION}` : "Layers:";
  return [{ rule: only?.rule ?? null, heading, layers: props.layers }];
});

/** A layer's sample: a border in the layer's tone over a light tint of it, as each of its nodes is drawn. */
function sampleOf({ tone: name }) {
  const tone = `var(${TOKEN_VARIABLES[name]})`;
  return { borderColor: tone, background: `color-mix(in srgb, ${tone} ${LAYER_FILL_SHARE * 100}%, var(--vp-c-bg))` };
}
</script>

<template>
  <template v-if="layers.length || unlayered">
    <span
      v-for="group in groups"
      :key="group.rule ?? ''"
      class="bl-legend-rule"
      :data-legend-rule="group.rule ?? undefined"
    >
      <span class="bl-legend-group">{{ group.heading }}</span>
      <span
        v-for="layer in group.layers"
        :key="layer.key"
        class="bl-legend-item"
        :data-legend-layer="layer.label"
      >
        <span class="bl-legend-swatch" :style="sampleOf(layer)" />
        {{ layer.name }}
      </span>
    </span>
    <span v-if="unlayered" class="bl-legend-item" data-legend-unlayered>
      <span class="bl-legend-swatch" :style="sampleOf({ tone: UNLAYERED_TONE })" />
      {{ UNLAYERED_NAME }}
    </span>
  </template>
</template>

<style scoped>
.bl-legend-rule {
  display: contents;
}
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
