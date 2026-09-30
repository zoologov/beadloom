<script setup>
// beadloom:component=site-graph-node
// A node's card: what the version 1 data file says about one node.
//
// Every value comes from the data file. A node with no document shows no link,
// and the lint line appears only when the file carries the lint result. A click
// on a dependency asks the viewer to select that node.

import { withBase } from "vitepress";

defineProps({
  node: { type: Object, required: true },
  layerName: { type: String, default: "" },
});
const emit = defineEmits(["select", "close"]);

const RELATIONS = [
  { key: "depends_on", title: "Depends on" },
  { key: "depended_on_by", title: "Depended on by" },
  { key: "uses", title: "Uses at runtime (declared)" },
  { key: "used_by", title: "Used at runtime by (declared)" },
];
</script>

<template>
  <article class="bl-card" :aria-label="`Node ${node.id}`">
    <button type="button" class="bl-card-close" aria-label="Close the card" @click="emit('close')">
      ×
    </button>
    <h3>{{ node.id }}</h3>
    <dl>
      <dt>Kind</dt>
      <dd>{{ node.kind || "unknown" }}</dd>
      <dt>Layer</dt>
      <dd>{{ layerName || node.layer || "—" }}</dd>
      <dt>Symbols</dt>
      <dd>{{ node.symbols ?? "—" }}</dd>
      <dt>Docs</dt>
      <dd :class="{ 'bl-card-warn': node.doc_status === 'stale' }">{{ node.doc_status || "—" }}</dd>
      <template v-if="node.lint_clean !== undefined">
        <dt>Lint</dt>
        <dd :class="{ 'bl-card-warn': !node.lint_clean }">
          {{ node.lint_clean ? "clean" : "violation" }}
        </dd>
      </template>
    </dl>
    <p v-if="node.summary" class="bl-card-summary">{{ node.summary }}</p>

    <template v-for="relation in RELATIONS" :key="relation.key">
      <template v-if="relation.key.startsWith('depend') || (node[relation.key] || []).length">
        <h4>{{ relation.title }}</h4>
        <ul v-if="(node[relation.key] || []).length">
          <li v-for="id in node[relation.key]" :key="id">
            <button type="button" class="bl-card-link" @click="emit('select', id)">{{ id }}</button>
          </li>
        </ul>
        <p v-else class="bl-card-none">nothing</p>
      </template>
    </template>

    <template v-if="(node.doc_links || []).length">
      <h4>Docs</h4>
      <ul>
        <li v-for="link in node.doc_links" :key="link">
          <a :href="withBase(link)">{{ link }}</a>
        </li>
      </ul>
    </template>
    <p v-if="node.url"><a :href="withBase(node.url)">Open page →</a></p>
  </article>
</template>

<style scoped>
.bl-card {
  position: relative;
  font-size: 13px;
}
.bl-card h3 {
  margin: 0 28px 10px 0;
  font-size: 15px;
  word-break: break-word;
}
.bl-card h4 {
  margin: 14px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-card dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 0;
}
.bl-card dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-card dd {
  margin: 0;
}
.bl-card ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-card-summary {
  margin: 10px 0 0;
  color: var(--vp-c-text-2);
}
.bl-card-close {
  position: absolute;
  top: -4px;
  right: 0;
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: var(--vp-c-text-2);
}
.bl-card-link {
  padding: 0;
  border: none;
  background: none;
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  color: var(--vp-c-brand-1);
  cursor: pointer;
  text-align: left;
}
.bl-card-link:hover {
  text-decoration: underline;
}
.bl-card-none {
  color: var(--vp-c-text-3);
  font-style: italic;
  margin: 4px 0;
}
.bl-card-warn {
  color: var(--vp-c-warning-1);
  font-weight: 700;
}
</style>
