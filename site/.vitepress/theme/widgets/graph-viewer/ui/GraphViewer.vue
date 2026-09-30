<script setup>
// beadloom:component=site-graph-viewer
// GraphViewer — the viewer's own space: a toolbar, the canvas and a collapsible panel.
//
// It renders `architecture.data.json` with Cytoscape.js and the ELK layout, in
// compound mode: domains and services are boxes around their features and
// components. It composes the features below it — filters, navigation, full
// screen and URL state — and the entities it draws. Everything it shows comes
// from the data file.
//
// The toolbar, the canvas, the panel and the legend are all inside one root
// element, and that element is what goes full screen, so full screen and the
// embedded view are one UI. The panel shows what the page puts in its `panel`
// slot for the selected node; the page composes the card, so a richer card can
// replace it without the viewer knowing.

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useArchitectureData } from "../../../entities/architecture-data/index.js";
import { parentMapOf } from "../../../entities/graph-node/index.js";
import { EdgeLegend, legendKeysOf } from "../../../entities/graph-edge/index.js";
import { LayerLegend, layerOfNode, layersOf } from "../../../entities/layer/index.js";
import {
  FILTER_DEFAULTS,
  FilterControls,
  filterOptions,
  visibleNodeIds,
} from "../../../features/filter-graph/index.js";
import {
  NAVIGATION_OPTIONS,
  NavigationControls,
  useGraphNavigation,
} from "../../../features/navigate-graph/index.js";
import { FullscreenButton, useFullscreen } from "../../../features/fullscreen/index.js";
import { useUrlState } from "../../../features/url-state/index.js";
import { useThemeTokens } from "../../../shared/theme-tokens/index.js";
import { buildElements } from "../lib/elements.js";
import { buildStylesheet } from "../lib/stylesheet.js";
import { useGraphCanvas } from "../model/useGraphCanvas.js";
import { keyHandler } from "../model/viewerKeys.js";
import { exposeTestHandle } from "../model/testHandle.js";

const props = defineProps({
  mode: { type: String, default: "architecture" },
  focus: { type: String, default: "" },
  depth: { type: [Number, String], default: 1 },
  direction: { type: String, default: "both" },
  height: { type: String, default: "640px" },
});

// The view's state. The URL query overrides the props, and every change is
// written back, so a view can be linked. Depth and direction are carried for
// the neighbourhood selection that builds on this viewer.
const state = useUrlState({
  ...FILTER_DEFAULTS,
  focus: props.focus,
  depth: String(props.depth),
  dir: props.direction,
  mode: props.mode,
});

const { data, error } = useArchitectureData();
const nodes = computed(() => (Array.isArray(data.value?.nodes) ? data.value.nodes : []));
const edges = computed(() => (Array.isArray(data.value?.edges) ? data.value.edges : []));
const nodeById = computed(() => new Map(nodes.value.map((node) => [node.id, node])));
const parents = computed(() => parentMapOf(nodes.value));
const layers = computed(() => layersOf(nodes.value));
const options = computed(() => filterOptions(nodes.value, layers.value));
const legendKeys = computed(() =>
  legendKeysOf(
    edges.value.filter((edge) => nodeById.value.has(edge.src) && nodeById.value.has(edge.dst))
  )
);
const visibleIds = computed(() =>
  visibleNodeIds(nodes.value, state, { parents: parents.value, layers: layers.value })
);
const selectedNode = computed(() => nodeById.value.get(state.focus) || null);
const selectedLayer = computed(() =>
  selectedNode.value ? layerOfNode(selectedNode.value, layers.value)?.name || "" : ""
);

const root = ref(null);
const container = ref(null);
// The panel opens when a node is selected; the toolbar's "Panel" button toggles it.
const panelOpen = ref(Boolean(state.focus));
const { tokens } = useThemeTokens(root);

function select(id) {
  if (nodeById.value.has(id)) state.focus = id;
}
function clearSelection() {
  state.focus = "";
}
function focusCanvas() {
  container.value?.focus({ preventScroll: true });
}

const canvas = useGraphCanvas(container, {
  options: NAVIGATION_OPTIONS,
  onNodeTap: (id) => {
    select(id);
    focusCanvas();
  },
  onBackgroundTap: () => {
    clearSelection();
    focusCanvas();
  },
});
const navigation = useGraphNavigation(() => canvas.cy.value);

function refit() {
  nextTick(() => {
    canvas.resize();
    navigation.fit();
  });
}
const fullscreen = useFullscreen(root, { onChange: refit });

const onKeydown = keyHandler({
  zoomIn: navigation.zoomIn,
  zoomOut: navigation.zoomOut,
  fit: navigation.fit,
  fullscreen: fullscreen.toggle,
  clear: () => {
    if (state.focus) clearSelection();
    else if (fullscreen.fallback.value) fullscreen.exit();
  },
});

async function render() {
  if (!data.value || !tokens.value || !container.value) return;
  const elements = buildElements(nodes.value, edges.value, {
    parents: parents.value,
    layers: layers.value,
  });
  const mounted = await canvas.mount(elements, buildStylesheet(tokens.value));
  if (!mounted) return;
  navigation.applyArrangePolicy();
  canvas.showOnly(visibleIds.value);
  canvas.highlight(state.focus);
  navigation.fit();
}

watch(data, render);
watch(tokens, (current, previous) => {
  if (!current) return;
  if (!previous || !canvas.ready.value) render();
  else canvas.setStyle(buildStylesheet(current));
});
watch(visibleIds, (ids) => {
  if (!canvas.ready.value) return;
  canvas.showOnly(ids);
  navigation.fit();
});
watch(
  () => state.focus,
  (id) => {
    canvas.highlight(id);
    if (id) panelOpen.value = true;
  }
);

let disposeHandle = () => {};
onMounted(() => {
  render();
  disposeHandle = exposeTestHandle({
    cy: () => canvas.cy.value,
    container: () => container.value,
    ready: () => canvas.ready.value,
    selection: () => state.focus,
    state: () => state,
    arranging: () => navigation.arranging.value,
  });
});
onBeforeUnmount(() => disposeHandle());
</script>

<template>
  <div
    ref="root"
    class="bl-viewer"
    :class="{ 'is-fallback-fullscreen': fullscreen.fallback.value }"
    :data-fullscreen-fallback="fullscreen.fallback.value ? 'on' : 'off'"
    :style="{ '--bl-viewer-height': height }"
    @keydown="onKeydown"
  >
    <p v-if="error" class="bl-viewer-note" role="alert">
      The graph could not be shown: {{ error.message }} The static summary on this page is the
      source of truth.
    </p>

    <div role="toolbar" aria-label="Graph viewer tools" class="bl-viewer-toolbar">
      <FilterControls :filters="state" :options="options" @change="(key, value) => (state[key] = value)" />
      <span class="bl-viewer-spacer" />
      <NavigationControls
        :arranging="navigation.arranging.value"
        @zoom-in="navigation.zoomIn"
        @zoom-out="navigation.zoomOut"
        @fit="navigation.fit"
        @centre="navigation.centre(state.focus)"
        @arrange="navigation.toggleArrange"
      />
      <button
        type="button"
        class="bl-viewer-button"
        :aria-expanded="panelOpen"
        aria-controls="bl-viewer-panel"
        @click="(panelOpen = !panelOpen), refit()"
      >
        Panel
      </button>
      <FullscreenButton :active="fullscreen.active.value" @toggle="fullscreen.toggle" />
    </div>

    <div class="bl-viewer-body">
      <div
        ref="container"
        class="bl-viewer-canvas"
        data-testid="graph-canvas"
        tabindex="0"
        aria-label="Architecture graph: drag to pan, scroll to zoom; keys + − 0 f Esc"
      />
      <aside
        v-show="panelOpen"
        id="bl-viewer-panel"
        class="bl-viewer-panel"
        data-testid="viewer-panel"
        aria-label="Details"
      >
        <slot
          v-if="selectedNode"
          name="panel"
          :node="selectedNode"
          :layer-name="selectedLayer"
          :select="select"
          :close="clearSelection"
        />
        <p v-else class="bl-viewer-hint">
          Select a node to see its card. Drag to pan and scroll to zoom; "Arrange" lets you move
          nodes. Keys: <kbd>+</kbd> <kbd>−</kbd> zoom, <kbd>0</kbd> fit, <kbd>f</kbd> full screen,
          <kbd>Esc</kbd> clear.
        </p>
      </aside>
    </div>

    <div class="bl-viewer-legend" aria-label="Legend">
      <LayerLegend :layers="layers" />
      <EdgeLegend :keys="legendKeys" />
    </div>
  </div>
</template>

<style scoped>
.bl-viewer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 16px 0;
  padding: 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg);
  font-size: 13px;
}
.bl-viewer:fullscreen,
.bl-viewer.is-fallback-fullscreen {
  margin: 0;
  border: none;
  border-radius: 0;
  padding: 12px;
  height: 100vh;
  width: 100vw;
  box-sizing: border-box;
}
.bl-viewer.is-fallback-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 200;
}
.bl-viewer-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.bl-viewer-spacer {
  flex: 1 1 auto;
}
.bl-viewer-button {
  padding: 3px 10px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.bl-viewer-button[aria-expanded="true"] {
  border-color: var(--vp-c-brand-1);
}
.bl-viewer-body {
  position: relative;
  display: flex;
  gap: 8px;
  min-height: 0;
}
.bl-viewer:fullscreen .bl-viewer-body,
.bl-viewer.is-fallback-fullscreen .bl-viewer-body {
  flex: 1 1 auto;
}
.bl-viewer-canvas {
  flex: 1 1 auto;
  min-width: 0;
  height: var(--bl-viewer-height);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
}
.bl-viewer:fullscreen .bl-viewer-canvas,
.bl-viewer.is-fallback-fullscreen .bl-viewer-canvas {
  height: auto;
}
.bl-viewer-canvas:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 1px;
}
/* In the page the panel lies over the canvas's right edge, so the canvas keeps
   the content column's full width; in full screen it sits beside the canvas. */
.bl-viewer-panel {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: min(300px, 55%);
  max-height: calc(var(--bl-viewer-height) - 16px);
  box-sizing: border-box;
  overflow-y: auto;
  padding: 14px 16px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg-soft);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}
.bl-viewer:fullscreen .bl-viewer-panel,
.bl-viewer.is-fallback-fullscreen .bl-viewer-panel {
  position: static;
  flex: 0 0 340px;
  width: auto;
  max-height: none;
  box-shadow: none;
}
.bl-viewer-hint {
  margin: 0;
  color: var(--vp-c-text-2);
}
.bl-viewer-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 14px;
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.bl-viewer-note {
  margin: 0;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--vp-c-danger-soft);
  color: var(--vp-c-text-1);
}
</style>
