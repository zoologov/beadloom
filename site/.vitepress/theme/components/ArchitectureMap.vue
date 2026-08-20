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
  LAYER_LANES,
  EDGE_LEGEND,
} from "../architectureTheme.js";

const { data, error } = useArchitectureData();

const container = ref(null);
const stage = ref(null);
let cy = null;

// Legend data (layers + edge meaning) — read straight from the theme.
const layerLanes = LAYER_LANES.map((l) => ({ ...l, color: layerColor(l.layer) }));
const edgeLegend = EDGE_LEGEND;

// --- Fullscreen state ---------------------------------------------------------
const isFullscreen = ref(false);

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
// Each node gets a `partition` = its layer rank so ELK pins it into its layer
// lane (the canonical layered-lanes layout). A depends_on edge that points UP /
// cross-cuts the layer order (`violation`) is flagged so the view dogfoods our
// own layering rule visually.
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
    // The layer rank drives the ELK partition (the lane). Honest: a node with
    // no resolvable rank (`layer_rank == null`) carries no partition.
    if (typeof n.layer_rank === "number") d.partition = n.layer_rank;
    // Only set `parent` when the container is itself a rendered node AND not the
    // node itself (the root service carries a `root part_of root` self-edge),
    // so ELK builds a valid compound (a dangling/self parent ref crashes cy).
    if (n.parent && n.parent !== n.id && nodeById.value[n.parent]) d.parent = n.parent;
    els.push({ group: "nodes", data: d, classes: isFlagged(n) ? "flagged" : "" });
  }
  for (let i = 0; i < edges.value.length; i++) {
    const e = edges.value[i];
    // part_of containment is expressed via `parent`. Two flow kinds are drawn:
    // `depends_on` (an import) solid, and `uses` (a DECLARED runtime coupling —
    // a subprocess call, a file-format contract) dashed. `uses` is never
    // flagged as a violation: crossing a process boundary to call a published
    // interface is not a layering break the way an import is.
    if (e.kind !== "depends_on" && e.kind !== "uses") continue;
    const runtime = e.kind === "uses";
    els.push({
      group: "edges",
      data: { id: `e${i}:${e.src}->${e.dst}`, source: e.src, target: e.dst },
      classes: runtime ? "runtime" : e.violation === true ? "violation" : "",
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
    // A tap on the background closes the card AND clears the blast-radius
    // highlight, so the graph returns to FULL opacity (never stays greyed).
    if (evt.target === cy) closeCard();
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

// Close the pop-up AND clear the focus so the dim/blast-radius highlight is
// removed and the whole graph restores to full opacity (bug: grey-after-close).
function closeCard() {
  selected.value = null;
  focusNode.value = "";
}

// Whether any filter is active (an empty filter set => show everything).
const anyFilterActive = computed(
  () =>
    kindFilter.value !== "all" ||
    domainFilter.value !== "all" ||
    layerFilter.value !== "all" ||
    onlyViolations.value === true
);

// Apply the live filters/focus to the rendered graph (presentational only).
// Filtering HIDES non-matching elements (display:none via `.hidden`) rather
// than removing+relayouting into emptiness; the layout/viewport is preserved
// and we re-fit to the visible set so the matched graph stays on screen.
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
  // Re-fit to the currently VISIBLE set (an empty filter fits the whole graph),
  // so a filter never leaves the viewport parked on an emptied region.
  const visible = cy.elements(":visible");
  if (visible.nonempty()) cy.fit(visible, 40);
}

// Fullscreen toggle for the map stage (uses the Fullscreen API when present,
// falling back to a CSS full-viewport class for environments without it).
function toggleFullscreen() {
  const el = stage.value;
  if (!el) return;
  const doc = typeof document !== "undefined" ? document : null;
  if (doc && doc.fullscreenElement) {
    doc.exitFullscreen?.();
    return;
  }
  if (el.requestFullscreen) {
    el.requestFullscreen().catch(() => {
      isFullscreen.value = !isFullscreen.value;
    });
  } else {
    isFullscreen.value = !isFullscreen.value;
  }
  // Re-fit shortly after the resize so the graph fills the enlarged stage.
  if (cy) setTimeout(() => cy.resize() || cy.fit(cy.elements(":visible"), 40), 60);
}

function onFullscreenChange() {
  if (typeof document === "undefined") return;
  isFullscreen.value = Boolean(document.fullscreenElement);
  if (cy) setTimeout(() => cy.resize() || cy.fit(cy.elements(":visible"), 40), 60);
}

watch([kindFilter, domainFilter, layerFilter, onlyViolations, focusNode], applyFilters);
watch(data, render);

onMounted(() => {
  render();
  if (typeof document !== "undefined") {
    document.addEventListener("fullscreenchange", onFullscreenChange);
  }
});
onBeforeUnmount(() => {
  if (typeof document !== "undefined") {
    document.removeEventListener("fullscreenchange", onFullscreenChange);
  }
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
      <button
        type="button"
        class="bl-arch-fs"
        @click="toggleFullscreen"
        :aria-pressed="isFullscreen"
      >
        {{ isFullscreen ? "Exit fullscreen" : "Fullscreen" }}
      </button>
    </div>

    <div
      v-if="data"
      class="bl-arch-legend"
      aria-label="Legend: layers and edge meaning"
    >
      <span class="bl-arch-legend-group">Layers (top → bottom):</span>
      <span v-for="l in layerLanes" :key="l.rank" class="bl-arch-legend-item">
        <span class="bl-arch-swatch" :style="{ background: l.color }" />
        {{ l.label }}
      </span>
      <span class="bl-arch-legend-group">Edges:</span>
      <span v-for="e in edgeLegend" :key="e.cls" class="bl-arch-legend-item">
        <span class="bl-arch-line" :class="`bl-arch-line-${e.cls}`" />
        {{ e.label }}
      </span>
    </div>

    <div ref="stage" class="bl-arch-stage" :class="{ 'bl-arch-fullscreen': isFullscreen }">
      <div ref="container" class="bl-arch-canvas" />
      <aside v-if="selected" class="bl-arch-card">
        <button class="bl-arch-close" @click="closeCard" aria-label="Close">
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

        <!-- Declared runtime coupling. Shown only when it exists, and never
             merged into the import lists above: a subprocess call or a file
             contract is real, but calling it a dependency would assert an
             import binding that is not there. -->
        <template v-if="(selected.uses || []).length">
          <h4>Uses at runtime <span class="bl-arch-hint">(declared)</span></h4>
          <ul>
            <li v-for="d in selected.uses" :key="d"><code>{{ d }}</code></li>
          </ul>
        </template>

        <template v-if="(selected.used_by || []).length">
          <h4>Used at runtime by <span class="bl-arch-hint">(declared)</span></h4>
          <ul>
            <li v-for="d in selected.used_by" :key="d"><code>{{ d }}</code></li>
          </ul>
        </template>

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
.bl-arch-fs {
  align-self: flex-end;
  padding: 5px 12px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.bl-arch-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 14px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-arch-legend-group {
  font-weight: 700;
  color: var(--vp-c-text-1);
}
.bl-arch-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bl-arch-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}
.bl-arch-line {
  display: inline-block;
  width: 22px;
  height: 0;
  border-top: 2px solid var(--vp-c-text-3);
}
.bl-arch-line-healthy {
  border-top-color: var(--vp-c-text-3);
}
.bl-arch-line-violation {
  border-top: 2px dashed #e45649;
}
.bl-arch-line-containment {
  border-top: 2px dotted var(--vp-c-text-3);
}
.bl-arch-line-runtime {
  border-top: 2px dotted var(--vp-c-text-3);
  opacity: 0.75;
}
.bl-arch-hint {
  font-weight: 400;
  color: var(--vp-c-text-3);
  font-size: 0.85em;
}
.bl-arch-stage {
  position: relative;
  display: flex;
  gap: 12px;
}
.bl-arch-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 200;
  margin: 0;
  padding: 16px;
  background: var(--vp-c-bg);
}
.bl-arch-fullscreen .bl-arch-canvas {
  height: 100%;
}
.bl-arch-stage:fullscreen {
  background: var(--vp-c-bg);
  padding: 16px;
}
.bl-arch-stage:fullscreen .bl-arch-canvas {
  height: 100%;
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
