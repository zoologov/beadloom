<script setup>
// beadloom:component=site-filter-graph
// The filter controls of the viewer's toolbar: kind, domain, layer, violations
// and a search box. It shows the filters it is given and reports each change;
// the viewer owns the state.

const props = defineProps({
  filters: { type: Object, required: true },
  options: { type: Object, required: true },
});
const emit = defineEmits(["change"]);

const SELECTS = [
  { key: "kind", label: "Kind", optionsKey: "kinds" },
  { key: "domain", label: "Domain", optionsKey: "domains" },
  { key: "layer", label: "Layer", optionsKey: "layers" },
];

/** A choice's value and the text it is shown by: a value alone is shown as itself. */
const valueOf = (choice) => (typeof choice === "object" && choice !== null ? choice.value : choice);
const textOf = (choice) => (typeof choice === "object" && choice !== null ? choice.text : choice);

function change(key, value) {
  if (props.filters[key] !== value) emit("change", key, value);
}
</script>

<template>
  <div class="bl-filters">
    <label v-for="select in SELECTS" :key="select.key" class="bl-filter">
      <span>{{ select.label }}</span>
      <select
        :aria-label="select.label"
        :value="filters[select.key]"
        @change="change(select.key, $event.target.value)"
      >
        <option v-for="choice in options[select.optionsKey]" :key="valueOf(choice)" :value="valueOf(choice)">
          {{ textOf(choice) }}
        </option>
      </select>
    </label>
    <label class="bl-filter bl-filter-check">
      <input
        type="checkbox"
        :checked="filters.violations"
        @change="change('violations', $event.target.checked)"
      />
      <span>Only flagged</span>
    </label>
    <input
      class="bl-filter-search"
      type="search"
      placeholder="Search nodes"
      aria-label="Search nodes"
      :value="filters.q"
      @input="change('q', $event.target.value)"
    />
  </div>
</template>

<style scoped>
.bl-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.bl-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--vp-c-text-2);
  font-weight: 600;
}
.bl-filter select,
.bl-filter-search {
  padding: 3px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
}
.bl-filter-search {
  width: 150px;
}
</style>
