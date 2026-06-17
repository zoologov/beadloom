<script setup>
// LandscapeMap — the interactive cross-service landscape (BDL-060 S4, G2).
//
// Renders `landscape.data.json` (the renderer-agnostic artifact built in Python
// by `beadloom.application.landscape_view`) with Cytoscape.js + the ELK layout
// (orthogonal edge routing + non-overlapping nodes — the readability the owner
// requires; the built-in cose force layout is NOT used). ELK runs with FIXED,
// seedless options (see landscapeTheme.ELK_OPTIONS) so the layout is
// deterministic given the same data: no view-time randomness.
//
// The front-end is purely presentational: every node/edge/contract field comes
// straight from the artifact. Honest degradation — a contract with no declared
// field/body surface shows "undeclared", never a fabricated field. All palette/
// geometry/typography lives in landscapeTheme.js so the visual is themeable
// without touching this logic; semantic colors follow health/verdict, neutral
// chrome follows the VitePress portal (auto light/dark via --vp-* CSS vars).

import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { useLandscapeData } from "../composables/useLandscapeData.js";
import {
  bucketOf,
  verdictColor,
  buildStylesheet,
  ELK_OPTIONS,
  GEOMETRY,
  COLORS,
} from "../landscapeTheme.js";

const { data, error } = useLandscapeData();

const container = ref(null);
let cy = null;

// --- Filters / focus state ----------------------------------------------------
const protocolFilter = ref("all"); // all | amqp | graphql
const verdictFilter = ref("all"); // all | broken | healthy | neutral
const hideHealthy = ref(false); // show only problems
const focusNode = ref(""); // blast-radius highlight

// --- Pop-up (contract card) state --------------------------------------------
const selected = ref(null); // { kind: 'edge'|'node', ... }

const nodes = computed(() => (Array.isArray(data.value?.nodes) ? data.value.nodes : []));
const edges = computed(() => (Array.isArray(data.value?.edges) ? data.value.edges : []));
const contracts = computed(() =>
  Array.isArray(data.value?.contracts) ? data.value.contracts : []
);
const contractByKey = computed(() => {
  const map = {};
  for (const c of contracts.value) {
    if (c && c.contract_key) map[c.contract_key] = c;
  }
  return map;
});

const protocols = computed(() => {
  const set = new Set();
  for (const c of contracts.value) if (c?.protocol) set.add(c.protocol);
  return ["all", ...Array.from(set).sort()];
});

function healthColor(bucket) {
  if (bucket === "broken") return COLORS.broken;
  if (bucket === "neutral") return COLORS.neutral;
  return COLORS.healthy;
}

// Build Cytoscape elements from the deterministic artifact.
function buildElements() {
  const els = [];
  for (const n of nodes.value) {
    els.push({
      group: "nodes",
      data: {
        id: n.id,
        label: n.label || n.id,
        kind: n.kind || "",
        groupName: n.group || "other",
        url: n.url || "",
        health: n.health || "healthy",
        healthColor: healthColor(n.health || "healthy"),
      },
    });
  }
  for (let i = 0; i < edges.value.length; i++) {
    const e = edges.value[i];
    const bucket = bucketOf(e.verdict);
    const isProblem = bucket === "broken";
    els.push({
      group: "edges",
      data: {
        id: `e${i}:${e.src}->${e.dst}`,
        source: e.src,
        target: e.dst,
        verdict: e.verdict,
        contractKey: e.contract_key || "",
        verdictColor: verdictColor(e.verdict),
        width: isProblem ? GEOMETRY.problemEdgeWidth : GEOMETRY.healthyEdgeWidth,
        // A badge ONLY on problem edges so the map reads "where it hurts".
        badge: isProblem ? String(e.verdict || "").toUpperCase() : "",
      },
      classes: isProblem ? "problem" : "",
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
  cy.on("tap", "edge", (evt) => selectEdge(evt.target));
  cy.on("tap", "node", (evt) => selectNode(evt.target));
  cy.on("tap", (evt) => {
    if (evt.target === cy) selected.value = null;
  });
  applyFilters();
}

function selectEdge(edge) {
  const key = edge.data("contractKey");
  selected.value = {
    kind: "edge",
    verdict: edge.data("verdict"),
    contract: contractByKey.value[key] || null,
  };
}

function selectNode(node) {
  const id = node.data("id");
  const related = contracts.value.filter(
    (c) =>
      (Array.isArray(c.producers) && c.producers.includes(id)) ||
      (Array.isArray(c.consumers) && c.consumers.includes(id))
  );
  selected.value = {
    kind: "node",
    id,
    nodeKind: node.data("kind"),
    url: node.data("url"),
    contracts: related,
  };
}

// Apply the live filters/focus to the rendered graph (presentational only).
function applyFilters() {
  if (!cy) return;
  cy.batch(() => {
    cy.edges().forEach((edge) => {
      const verdict = String(edge.data("verdict") || "").toLowerCase();
      const bucket = bucketOf(verdict);
      const key = edge.data("contractKey");
      const proto = contractByKey.value[key]?.protocol || "";
      let visible = true;
      if (protocolFilter.value !== "all" && proto !== protocolFilter.value) visible = false;
      if (verdictFilter.value !== "all" && bucket !== verdictFilter.value) visible = false;
      if (hideHealthy.value && bucket !== "broken") visible = false;
      edge.toggleClass("hidden", !visible);
    });
    // A node stays visible if any incident edge is visible.
    cy.nodes().forEach((node) => {
      const incident = node.connectedEdges().filter((e) => !e.hasClass("hidden"));
      node.toggleClass("hidden", incident.length === 0);
    });
    // Blast-radius focus: dim everything not adjacent to the focused node.
    cy.elements().removeClass("dimmed");
    if (focusNode.value) {
      const target = cy.getElementById(focusNode.value);
      if (target.nonempty()) {
        const neighborhood = target.closedNeighborhood();
        cy.elements().not(neighborhood).addClass("dimmed");
      }
    }
  });
}

watch([protocolFilter, verdictFilter, hideHealthy, focusNode], applyFilters);
watch(data, render);

onMounted(render);
onBeforeUnmount(() => {
  if (cy) {
    cy.destroy();
    cy = null;
  }
});

// --- Pop-up helpers (honest "undeclared" when a surface is absent) ------------
function isEmpty(obj) {
  return !obj || (typeof obj === "object" && Object.keys(obj).length === 0);
}
function gqlFieldEntries(surface) {
  if (isEmpty(surface)) return [];
  return Object.keys(surface)
    .sort()
    .map((name) => ({ name, type: surface[name]?.type || "unknown" }));
}
function amqpProps(body) {
  const props = body?.properties;
  if (isEmpty(props)) return [];
  return Object.keys(props)
    .sort()
    .map((name) => ({ name, type: props[name]?.type || "unknown" }));
}
</script>

<template>
  <div class="bl-landscape">
    <p v-if="error" class="bl-ls-note">
      Could not load <code>landscape.data.json</code>. The static summary above is
      the source of truth.
    </p>

    <div v-if="data" class="bl-ls-controls">
      <label>
        Protocol
        <select v-model="protocolFilter">
          <option v-for="p in protocols" :key="p" :value="p">{{ p }}</option>
        </select>
      </label>
      <label>
        Verdict
        <select v-model="verdictFilter">
          <option value="all">all</option>
          <option value="broken">problems</option>
          <option value="healthy">healthy</option>
          <option value="neutral">neutral</option>
        </select>
      </label>
      <label>
        Focus
        <select v-model="focusNode">
          <option value="">(none)</option>
          <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.label }}</option>
        </select>
      </label>
      <label class="bl-ls-check">
        <input type="checkbox" v-model="hideHealthy" />
        Hide healthy edges
      </label>
    </div>

    <div class="bl-ls-stage">
      <div ref="container" class="bl-ls-canvas" />
      <aside v-if="selected" class="bl-ls-card">
        <button class="bl-ls-close" @click="selected = null" aria-label="Close">×</button>

        <template v-if="selected.kind === 'edge' && selected.contract">
          <h3>{{ selected.contract.name || selected.contract.contract_key }}</h3>
          <dl>
            <dt>Protocol</dt>
            <dd>{{ selected.contract.protocol || "unknown" }}</dd>
            <dt>Verdict</dt>
            <dd :class="`bl-v-${bucketOf(selected.contract.verdict)}`">
              {{ String(selected.contract.verdict).toUpperCase() }}
            </dd>
            <dt>Producer ↔ Consumer</dt>
            <dd>
              {{ (selected.contract.producers || []).join(", ") || "—" }}
              ↔
              {{ (selected.contract.consumers || []).join(", ") || "—" }}
            </dd>
            <template v-if="selected.contract.protocol === 'amqp'">
              <dt>Routing</dt>
              <dd>
                {{ selected.contract.routing?.exchange || "*" }} /
                {{ selected.contract.routing?.routing_key || "*" }}
                ({{ selected.contract.routing?.message_type || "?" }})
              </dd>
            </template>
            <template v-else-if="selected.contract.protocol === 'graphql'">
              <dt>Schema</dt>
              <dd>{{ selected.contract.routing?.schema || selected.contract.name }}</dd>
            </template>
          </dl>

          <!-- GraphQL typed field surface (S2) -->
          <template v-if="selected.contract.protocol === 'graphql'">
            <h4>Exposed fields (producer)</h4>
            <ul v-if="gqlFieldEntries(selected.contract.fields?.exposed).length">
              <li v-for="f in gqlFieldEntries(selected.contract.fields?.exposed)" :key="f.name">
                <code>{{ f.name }}</code>: {{ f.type }}
              </li>
            </ul>
            <p v-else class="bl-ls-undeclared">undeclared</p>
            <h4>Referenced fields (consumer)</h4>
            <ul v-if="gqlFieldEntries(selected.contract.fields?.referenced).length">
              <li v-for="f in gqlFieldEntries(selected.contract.fields?.referenced)" :key="f.name">
                <code>{{ f.name }}</code>: {{ f.type }}
              </li>
            </ul>
            <p v-else class="bl-ls-undeclared">undeclared</p>
          </template>

          <!-- AMQP body JSON-Schema surface (S3) -->
          <template v-else-if="selected.contract.protocol === 'amqp'">
            <h4>Body (producer)</h4>
            <ul v-if="amqpProps(selected.contract.body?.exposed).length">
              <li v-for="f in amqpProps(selected.contract.body?.exposed)" :key="f.name">
                <code>{{ f.name }}</code>: {{ f.type }}
              </li>
            </ul>
            <p v-else class="bl-ls-undeclared">undeclared</p>
          </template>

          <template v-if="(selected.contract.missing || []).length">
            <h4 class="bl-v-broken">Breaking</h4>
            <ul>
              <li v-for="m in selected.contract.missing" :key="m"><code>{{ m }}</code></li>
            </ul>
          </template>
        </template>

        <template v-else-if="selected.kind === 'node'">
          <h3>{{ selected.id }}</h3>
          <dl>
            <dt>Kind</dt>
            <dd>{{ selected.nodeKind || "unknown" }}</dd>
            <dt>Contracts</dt>
            <dd>{{ selected.contracts.length }}</dd>
          </dl>
          <ul v-if="selected.contracts.length">
            <li v-for="c in selected.contracts" :key="c.contract_key">
              <code>{{ c.name || c.contract_key }}</code>
              <span :class="`bl-v-${bucketOf(c.verdict)}`">
                {{ String(c.verdict).toUpperCase() }}
              </span>
            </li>
          </ul>
          <p v-if="selected.url">
            <a :href="selected.url">Open page →</a>
          </p>
        </template>

        <p v-else class="bl-ls-undeclared">No contract data for this element.</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.bl-landscape {
  margin: 16px 0;
}
.bl-ls-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
}
.bl-ls-controls label {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  color: var(--vp-c-text-2);
  font-weight: 600;
}
.bl-ls-controls select {
  padding: 4px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
}
.bl-ls-check {
  flex-direction: row !important;
  align-items: center;
  gap: 6px !important;
}
.bl-ls-stage {
  position: relative;
  display: flex;
  gap: 12px;
}
.bl-ls-canvas {
  flex: 1 1 auto;
  height: 560px;
  min-width: 0;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg);
}
.bl-ls-card {
  position: relative;
  flex: 0 0 300px;
  max-height: 560px;
  overflow-y: auto;
  padding: 16px 18px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
  font-size: 13px;
}
.bl-ls-card h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.bl-ls-card h4 {
  margin: 14px 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--vp-c-text-2);
}
.bl-ls-card dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  margin: 0;
}
.bl-ls-card dt {
  font-weight: 700;
  color: var(--vp-c-text-2);
}
.bl-ls-card dd {
  margin: 0;
}
.bl-ls-card ul {
  margin: 4px 0;
  padding-left: 18px;
}
.bl-ls-close {
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
.bl-ls-undeclared {
  color: var(--vp-c-text-3);
  font-style: italic;
}
.bl-v-broken {
  color: #e45649;
  font-weight: 700;
}
.bl-v-healthy {
  color: #2da44e;
  font-weight: 700;
}
.bl-v-neutral {
  color: #8b949e;
  font-weight: 700;
}
</style>
