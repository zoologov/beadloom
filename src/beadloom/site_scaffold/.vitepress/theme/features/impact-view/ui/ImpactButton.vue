<script setup>
// beadloom:component=site-impact-view
// The toolbar's switch between the neighbourhood and the impact mode.

defineProps({
  active: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle"]);
</script>

<template>
  <button
    type="button"
    class="bl-impact-button"
    :aria-pressed="active"
    aria-label="Impact"
    title="Impact: everything that depends on the selected node"
    @click="emit('toggle')"
  >
    Impact
  </button>
</template>

<style scoped>
.bl-impact-button {
  padding: 3px 10px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.bl-impact-button:hover,
.bl-impact-button[aria-pressed="true"] {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
</style>
