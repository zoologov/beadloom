<script setup>
// beadloom:component=site-navigate-graph
// The navigation buttons of the viewer's toolbar.

defineProps({
  arranging: { type: Boolean, default: false },
});
const emit = defineEmits(["zoom-in", "zoom-out", "fit", "centre", "arrange"]);
</script>

<template>
  <div class="bl-nav" role="group" aria-label="Navigation">
    <button type="button" aria-label="Zoom in" title="Zoom in (+)" @click="emit('zoom-in')">+</button>
    <button type="button" aria-label="Zoom out" title="Zoom out (−)" @click="emit('zoom-out')">−</button>
    <button type="button" aria-label="Fit" title="Fit the visible graph (0)" @click="emit('fit')">Fit</button>
    <button type="button" aria-label="Centre" title="Centre on the selection" @click="emit('centre')">
      Centre
    </button>
    <button
      type="button"
      aria-label="Arrange"
      title="Arrange: drag nodes to move them"
      :aria-pressed="arranging"
      :class="{ 'bl-nav-on': arranging }"
      @click="emit('arrange')"
    >
      Arrange
    </button>
  </div>
</template>

<style scoped>
.bl-nav {
  display: inline-flex;
  gap: 4px;
}
.bl-nav button {
  min-width: 30px;
  padding: 3px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.bl-nav button:hover {
  border-color: var(--vp-c-brand-1);
}
.bl-nav .bl-nav-on {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
</style>
