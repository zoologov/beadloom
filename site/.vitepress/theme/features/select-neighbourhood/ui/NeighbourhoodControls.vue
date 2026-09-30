<script setup>
// beadloom:component=site-select-neighbourhood
// The neighbourhood controls of the viewer's toolbar: depth, direction, and
// whether what lies outside is dimmed or hidden. It shows the values it is
// given and reports each change; the viewer owns the state.

import { DEPTH_CHOICES, DIRECTION_CHOICES } from "../model/options.js";

const props = defineProps({
  depth: { type: String, required: true },
  dir: { type: String, required: true },
  hide: { type: Boolean, default: false },
});
const emit = defineEmits(["change"]);

function change(key, value) {
  if (props[key] !== value) emit("change", key, value);
}
</script>

<template>
  <div class="bl-neighbourhood" role="group" aria-label="Neighbourhood">
    <label class="bl-neighbourhood-field">
      <span>Depth</span>
      <select aria-label="Depth" :value="depth" @change="change('depth', $event.target.value)">
        <option v-for="value in DEPTH_CHOICES" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <label class="bl-neighbourhood-field">
      <span>Direction</span>
      <select aria-label="Direction" :value="dir" @change="change('dir', $event.target.value)">
        <option v-for="choice in DIRECTION_CHOICES" :key="choice.value" :value="choice.value">
          {{ choice.label }}
        </option>
      </select>
    </label>
    <label class="bl-neighbourhood-field">
      <input type="checkbox" :checked="hide" @change="change('hide', $event.target.checked)" />
      <span>Hide the rest</span>
    </label>
  </div>
</template>

<style scoped>
.bl-neighbourhood {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.bl-neighbourhood-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--vp-c-text-2);
  font-weight: 600;
}
.bl-neighbourhood-field select {
  padding: 3px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
}
</style>
