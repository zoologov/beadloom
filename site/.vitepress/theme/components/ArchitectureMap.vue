<script setup>
// ArchitectureMap — the interactive local-architecture graph (BDL-060 S4 ext).
//
// Renders `architecture.data.json` (the renderer-agnostic artifact built in
// Python by `beadloom.application.architecture_view`) with Cytoscape.js + the
// ELK layout in COMPOUND mode: domains/services are parent boxes containing
// their features/components (via the artifact's `part_of` `parent`), with
// orthogonal `depends_on` edges over the layered stratification (service →
// application → domain → infra). This is the readability win over Mermaid the
// owner asked for. ELK runs with FIXED, seedless options
// (architectureTheme.ELK_OPTIONS) so the layout is deterministic.
//
// The front-end is purely presentational: every node/edge/layer/dependency
// comes straight from the artifact. Honest degradation — a node with no doc
// shows no link; an absent layer renders grey; the lint-clean flag is shown only
// when the artifact carries it. All palette/geometry/layout lives in
// architectureTheme.js; node/doc links are wrapped in VitePress `withBase()` so
// they resolve under the site base path (`/beadloom/…`), never a 404.

import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { withBase } from "vitepress";
import { useArchitectureData } from "../composables/useArchitectureData.js";
import {
  layerColor,
  STATUS_COLORS,
  buildStylesheet,
  ELK_OPTIONS,
} from "../architectureTheme.js";

const { data, error } = useArchitectureData();

const container = ref(null);
let cy = null;

// --- Filters / focus state ----------------------------------------------------
const kindFilter = ref("all");
const domainFilter = ref("all");
const layerFilter = ref("all");
const onlyViolations = ref(false); // stale docs OR lint violations
const focusNode = ref(""); // blast-radius highlight

// --- Pop-up (node card) state -------------------------------------------------
const selected = ref(null);

const nodes = computed(() => (Array.isArray(data.value?.nodes) ? data.value.nodes : []));
const edges = computed(() => (Array.isArray(data.value?.edges) ? data.value.edges : []));
const nodeById = computed(() => {
  const map = {};
  for (const n of nodes.value) if (n && n.id) map[n.id] = n;
  return map;
});

const kinds = computed(() => uniqueSorted(nodes.value.map((n) => n.kind)));
const layers = computed(() =>
  uniqueSorted(nodes.value.map((n) => n.layer).filter((l) => l))
);
// Domains = the set of compound parents that are domains (containment buckets).
const domains = computed(() =>
  uniqueSorted(nodes.value.filter((n) => n.kind === "domain").map((n) => n.id))
);

function uniqueSorted(values) {
  return ["all", ...Array.from(new Set(values.filter((v) => v))).sort()];
}

// A node is "flagged" when its docs are stale or it carries a lint violation.
function isFlagged(n) {
  return n.doc_status === "stale" || n.lint_clean === false;
}
function statusColor(n) {
  if (n.lint_clean === false) return STATUS_COLORS.violation;
  if (n.doc_status === "stale") return STATUS_COLORS.stale;
  return STATUS_COLORS.stale;
}

// Build Cytoscape elements (compound parents via `parent`) from the artifact.
function buildElements() {
  const els = [];
  for (const n of nodes.value) {
    const d = {
      id: n.id,
      label: n.label || n.id,
      kind: n.kind || "",
      layer: n.layer || "",
      layerColor: layerColor(n.layer),
      statusColor: statusColor(n),
    };
    // Only set `parent` when the container is itself a rendered node AND not the
    // node itself (the root service carries a `root part_of root` self-edge),
    // so ELK builds a valid compound (a dangling/self parent ref crashes cy).
    if (n.parent && n.parent !== n.id && nodeById.value[n.parent]) d.parent = n.parent;
    els.push({ group: "nodes", data: d, classes: isFlagged(n) ? "flagged" : "" });
  }
  for (let i = 0; i < edges.value.length; i++) {
    const e = edges.value[i];
    // part_of containment is expressed via `parent`; only depends_on is drawn.
    if (e.kind !== "depends_on") continue;
    els.push({
      group: "edges",
      data: { id: `e${i}:${e.src}->${e.dst}`, source: e.src, target: e.dst },
    });
  }
  return els;
}

async function render() {
  if (!container.value || !data.value) return;
  const [{ default: cytoscape }, { default: elk }] = await Promise.all([
    import("cytoscape"),
    import("cytoscape-elk"),
  ]);
  cytoscape.use(elk);
  if (cy) {
    cy.destroy();
    cy = null;
  }
  cy = cytoscape({
    container: container.value,
    elements: buildElements(),
    style: buildStylesheet(),
    layout: ELK_OPTIONS,
    wheelSensitivity: 0.2,
  });
  cy.on("tap", "node", (evt) => selectNode(evt.target.data("id")));
  cy.on("tap", (evt) => {
    if (evt.target === cy) selected.value = null;
  });
  applyFilters();
}

function selectNode(id) {
  const n = nodeById.value[id];
  if (!n) return;
  selected.value = n;
  // Clicking a node sets the blast-radius focus (impact highlight).
  focusNode.value = id;
}

// Apply the live filters/focus to the rendered graph (presentational only).
function applyFilters() {
  if (!cy) return;
  cy.batch(() => {
    cy.nodes().forEach((node) => {
      const n = nodeById.value[node.data("id")];
      let visible = true;
      if (n) {
        if (kindFilter.value !== "all" && n.kind !== kindFilter.value) visible = false;
        if (layerFilter.value !== "all" && n.layer !== layerFilter.value) visible = false;
        if (
          domainFilter.value !== "all" &&
          n.id !== domainFilter.value &&
          n.parent !== domainFilter.value
        )
          visible = false;
        if (onlyViolations.value && !isFlagged(n)) visible = false;
      }
      node.toggleClass("hidden", !visible);
    });
    // Impact highlight: emphasize the focused node's upstream+downstream.
    cy.elements().removeClass("dimmed impact");
    if (focusNode.value) {
      const target = cy.getElementById(focusNode.value);
      if (target.nonempty()) {
        const radius = target.closedNeighborhood();
        cy.elements().not(radius).addClass("dimmed");
        target.connectedEdges().addClass("impact");
      }
    }
  });
}

watch([kindFilter, domainFilter, layerFilter, onlyViolations, focusNode], applyFilters);
watch(data, render);

onMounted(render);
onBeforeUnmount(() => {
  if (cy) {
    cy.destroy();
    cy = null;
  }
});
</script>

<template>
  <div class="bl-arch">
    <p v-if="error" class="bl-arch-note">
      Could not load <code>architecture.data.json</code>. The static summary above
      is the source of truth.
    </p>

    <div v-if="data" class="bl-arch-controls">
      <label>
        Kind
        <select v-model="kindFilter">
          <option v-for="k in kinds" :key="k" :value="k">{{ k }}</option>
        </select>
      </label>
      <label>
        Domain
        <select v-model="domainFilter">
          <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
        </select>
      </label>
      <label>
        Layer
        <select v-model="layerFilter">
          <option v-for="l in layers" :key="l" :value="l">{{ l }}</option>
        </select>
      </label>
      <label>
        Focus
        <select v-model="focusNode">
          <option value="">(none)</option>
          <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.label }}</option>
        </select>
      </label>
      <label class="bl-arch-check">
        <input type="checkbox" v-model="onlyViolations" />
        Show only violations
      </label>
    </div>

    <div class="bl-arch-stage">
      <div ref="container" class="bl-arch-canvas" />
      <aside v-if="selected" class="bl-arch-card">
        <button class="bl-arch-close" @click="selected = null" aria-label="Close">
          ×
        </button>
        <h3>{{ selected.id }}</h3>
        <dl>
          <dt>Kind</dt>
          <dd>{{ selected.kind || "unknown" }}</dd>
          <dt>Layer</dt>
          <dd>{{ selected.layer || "—" }}</dd>
          <dt>Symbols</dt>
          <dd>{{ selected.symbols }}</dd>
          <dt>Docs</dt>
          <dd :class="selected.doc_status === 'stale' ? 'bl-arch-warn' : ''">
            {{ selected.doc_status }}
          </dd>
          <template v-if="selected.lint_clean !== undefined">
            <dt>Lint</dt>
            <dd :class="selected.lint_clean ? '' : 'bl-arch-warn'">
              {{ selected.lint_clean ? "clean" : "violation" }}
            </dd>
          </template>
        </dl>

        <p v-if="selected.summary" class="bl-arch-summary">{{ selected.summary }}</p>

        <h4>Depends on</h4>
        <ul v-if="(selected.depends_on || []).length">
          <li v-for="d in selected.depends_on" :key="d"><code>{{ d }}</code></li>
        </ul>
        <p v-else class="bl-arch-none">nothing</p>

        <h4>Depended on by</h4>
        <ul v-if="(selected.depended_on_by || []).length">
          <li v-for="d in selected.depended_on_by" :key="d"><code>{{ d }}</code></li>
        </ul>
        <p v-else class="bl-arch-none">nothing</p>

        <template v-if="(selected.doc_links || []).length">
          <h4>Docs</h4>
          <ul>
            <li v-for="l in selected.doc_links" :key="l">
              <a :href="withBase(l)">{{ l }}</a>
            </li>
          </ul>
        </template>

        <p v-if="selected.url">
          <a :href="withBase(selected.url)">Open page →</a>
        </p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.bl-arch {
  margin: 16px 0;
}
.bl-arch-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
}
.bl-arch-controls label {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  color: var(--vp-c-text-2);
  font-weight: 600;
}
.bl-arch-controls select {
  padding: 4px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
}
.bl-arch-check {
  flex-direction: row !important;
  align-items: center;
  gap: 6px !important;
}
.bl-arch-stage {
  position: relative;
  display: flex;
  gap: 12px;
}
.bl-arch-canvas {
  flex: 1 1 auto;
  height: 620px;
  min-width: 0;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg);
}
.bl-arch-card {
  position: relative;
  flex: 0 0 300px;
  max-height: 620px;
  overflow-y: auto;
  padding: 16px 18px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
  font-size: 13px;
}
.bl-arch-card h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.bl-arch-card h4 {
  margin: 14px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-arch-card dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 0;
}
.bl-arch-card dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-arch-card dd {
  margin: 0;
}
.bl-arch-card ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-arch-summary {
  margin: 10px 0 0;
  color: var(--vp-c-text-2);
}
.bl-arch-close {
  position: absolute;
  top: 8px;
  right: 10px;
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: var(--vp-c-text-2);
}
.bl-arch-none {
  color: var(--vp-c-text-3);
  font-style: italic;
  margin: 4px 0;
}
.bl-arch-warn {
  color: #d29922;
  font-weight: 700;
}
</style>
