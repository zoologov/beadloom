<script setup>
// beadloom:component=site-dashboard
// PageMap — the pages this portal's `beadloom docs site` run wrote, from
// `dashboard.data.json.pages`: how many, by section in the sidebar's order, each
// section's pages listed, and the language of each About page. A section the
// run wrote nothing for says 0. A data file written before the map was carried
// shows nothing here.

import { computed } from "vue";
import { useDashboardData } from "../../../entities/dashboard-data/index.js";

const { data } = useDashboardData();

const pages = computed(() => {
  const value = data.value?.pages;
  return value && Array.isArray(value.sections) ? value : null;
});

const languages = computed(() => (pages.value?.languages || []).map((entry) => `${entry.language} (${entry.page})`).join(", "));
</script>

<template>
  <section v-if="pages" class="bl-pages" aria-label="Pages" data-testid="page-map">
    <h2>Pages</h2>
    <p data-pages="count">
      This portal has {{ pages.count }} {{ pages.count === 1 ? "page" : "pages" }}, written by
      <code>beadloom docs site</code><template v-if="languages">; the About page in {{ languages }}</template>.
    </p>
    <details v-for="section in pages.sections" :key="section.name" class="bl-pages-section" :data-pages-section="section.name">
      <summary>{{ section.name }}: {{ section.count }}</summary>
      <ul v-if="section.pages.length">
        <li v-for="page in section.pages" :key="page"><code>{{ page }}</code></li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.bl-pages {
  margin: 24px 0;
}
.bl-pages-section summary {
  cursor: pointer;
}
.bl-pages-section ul {
  max-height: 240px;
  overflow: auto;
  font-size: 13px;
}
</style>
