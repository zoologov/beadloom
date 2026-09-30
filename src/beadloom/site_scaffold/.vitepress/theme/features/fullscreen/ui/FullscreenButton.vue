<script setup>
// beadloom:component=site-fullscreen
// The full-screen button of the viewer's toolbar.

defineProps({
  active: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle"]);
</script>

<template>
  <button
    type="button"
    class="bl-fullscreen"
    :aria-pressed="active"
    :aria-label="active ? 'Exit full screen' : 'Full screen'"
    title="Full screen (f)"
    @click="emit('toggle')"
  >
    {{ active ? "Exit full screen" : "Full screen" }}
  </button>
</template>

<style scoped>
.bl-fullscreen {
  padding: 3px 10px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.bl-fullscreen:hover {
  border-color: var(--vp-c-brand-1);
}
</style>
