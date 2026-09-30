<script setup>
// beadloom:component=site-graph-viewer
// GraphViewer — the viewer's own space: a toolbar, the canvas and a collapsible panel.
//
// It renders a data file with Cytoscape.js and the ELK layout, in one of two
// modes (`model/modes.js`): the architecture, from `architecture.data.json`, in
// compound mode — domains and services are boxes around their features and
// components — or the landscape of contracts between services, from
// `landscape.data.json`. It composes the features below it — filters,
// navigation, the neighbourhood, the impact mode, full screen and URL state —
// and the entities it draws. Everything it shows comes from the data file; the
// mode supplies the filters in its slot of the toolbar.
//
// The toolbar, the canvas, the panel and the legend are all inside one root
// element, and that element is what goes full screen, so full screen and the
// embedded view are one UI. The panel shows what the page puts in its `panel`
// slot for the selected node — the page composes the card, because a widget
// does not import another — and, in impact mode, the impact summary above it.
//
// A selection is a walk from the selected node. In the neighbourhood it goes
// to the chosen depth and direction; in impact mode it goes backwards along the
// dependency edges without a limit. What the walk leaves out is dimmed, or
// hidden when the reader asks; the containers of what it reached stay.

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { NodeStatusLegend, parentMapOf, statusesOf } from "../../../entities/graph-node/index.js";
import {
  DEPENDENCY_KINDS,
  EdgeLegend,
  NEIGHBOURHOOD_KINDS,
  adjacencyOf,
  legendKeysOf,
} from "../../../entities/graph-edge/index.js";
import { LayerLegend, layerOfNode, layersOf } from "../../../entities/layer/index.js";
import {
  NAVIGATION_OPTIONS,
  NavigationControls,
  useGraphNavigation,
} from "../../../features/navigate-graph/index.js";
import {
  NEIGHBOURHOOD_DEFAULTS,
  NeighbourhoodControls,
  neighbourhoodOf,
} from "../../../features/select-neighbourhood/index.js";
import {
  IMPACT_VIEW,
  ImpactButton,
  ImpactSummary,
  impactOf,
  impactSummary,
  ringOf,
} from "../../../features/impact-view/index.js";
import { FullscreenButton, useFullscreen } from "../../../features/fullscreen/index.js";
import { useUrlState } from "../../../features/url-state/index.js";
import { withAncestors } from "../../../shared/lib/index.js";
import { useThemeTokens } from "../../../shared/theme-tokens/index.js";
import { buildElements } from "../lib/elements.js";
import { buildStylesheet } from "../lib/stylesheet.js";
import { useGraphCanvas } from "../model/useGraphCanvas.js";
import { keyHandler } from "../model/viewerKeys.js";
import { exposeTestHandle } from "../model/testHandle.js";
import { usePanelId } from "../model/usePanelId.js";
import { DEFAULT_MODE, modeOf } from "../model/modes.js";

/** The selection's value for the neighbourhood, the default; the other is `IMPACT_VIEW`. */
const NEIGHBOURHOOD_VIEW = "neighbourhood";

const props = defineProps({
  mode: { type: String, default: DEFAULT_MODE },
  focus: { type: String, default: "" },
  depth: { type: [Number, String], default: NEIGHBOURHOOD_DEFAULTS.depth },
  direction: { type: String, default: NEIGHBOURHOOD_DEFAULTS.dir },
  height: { type: String, default: "640px" },
});

// The data mode is the page's: it is read once, and the URL does not carry it.
const mode = modeOf(props.mode);

// The view's state. The URL query overrides the props, and every change is
// written back, so a view can be linked.
const state = useUrlState({
  ...mode.filterDefaults,
  focus: props.focus,
  depth: String(props.depth),
  dir: props.direction,
  hide: NEIGHBOURHOOD_DEFAULTS.hide,
  view: NEIGHBOURHOOD_VIEW,
});

const { data, error } = mode.useData();
const graph = computed(() => mode.graphOf(data.value));
const nodes = computed(() => graph.value.nodes);
const edges = computed(() => graph.value.edges);
const nodeById = computed(() => new Map(nodes.value.map((node) => [node.id, node])));
const parents = computed(() => parentMapOf(nodes.value));
const layers = computed(() => layersOf(nodes.value, graph.value.layers));
const options = computed(() => mode.filterOptions(graph.value, layers.value));
const statuses = computed(() => statusesOf(nodes.value));
const legendKeys = computed(() =>
  legendKeysOf(
    edges.value.filter((edge) => nodeById.value.has(edge.src) && nodeById.value.has(edge.dst))
  )
);
// `{ nodes, contracts }`: the node ids the filters show and, on the landscape,
// the contracts they show (null where the mode filters no contract).
const visible = computed(() =>
  mode.visible(graph.value, state, { parents: parents.value, layers: layers.value })
);
const selectedNode = computed(() => nodeById.value.get(state.focus) || null);
const selectedLayer = computed(() =>
  selectedNode.value ? layerOfNode(selectedNode.value, layers.value)?.name || "" : ""
);

const ids = computed(() => new Set(nodeById.value.keys()));
const drawnAdjacency = computed(() => adjacencyOf(edges.value, NEIGHBOURHOOD_KINDS, ids.value));
const dependencyAdjacency = computed(() => adjacencyOf(edges.value, DEPENDENCY_KINDS, ids.value));
const impactMode = computed(() => mode.impact && state.view === IMPACT_VIEW);

// The walk from the selected node, or null when nothing is selected.
const walk = computed(() => {
  if (!selectedNode.value) return null;
  return impactMode.value
    ? impactOf(state.focus, dependencyAdjacency.value)
    : neighbourhoodOf(state.focus, drawnAdjacency.value, { depth: state.depth, dir: state.dir });
});
const summary = computed(() => {
  if (!walk.value || !impactMode.value) return null;
  return impactSummary(state.focus, walk.value, {
    nodeById: nodeById.value,
    parents: parents.value,
    layers: layers.value,
    edges: edges.value,
  });
});
const selection = computed(() => {
  if (!walk.value) return null;
  const { distances, edges: walked } = walk.value;
  return {
    focus: state.focus,
    distances,
    edges: walked,
    keep: withAncestors(distances.keys(), parents.value),
    hide: Boolean(state.hide),
    rings: summary.value
      ? new Map([...distances].map(([id, distance]) => [id, ringOf(distance)]))
      : null,
    risks: summary.value ? new Set(summary.value.risky.map((entry) => entry.id)) : null,
  };
});

const root = ref(null);
const container = ref(null);
const panel = ref(null);
const panelId = usePanelId();
// The panel opens when a node is selected; the toolbar's "Panel" button toggles it.
const panelOpen = ref(Boolean(state.focus));
const { tokens } = useThemeTokens(root);

// A selection made anywhere but on the canvas — the URL, the card, the impact
// list, the toolbar — is framed, so what the reader asked for is in view. A tap
// on the canvas is not: the reader is already looking at the node.
let frameNextSelection = true;

function select(id, { frame = true } = {}) {
  if (!nodeById.value.has(id) || state.focus === id) return;
  frameNextSelection = frame;
  state.focus = id;
}
function clearSelection() {
  state.focus = "";
}
function focusCanvas() {
  container.value?.focus({ preventScroll: true });
}
function toggleImpact() {
  if (!mode.impact) return;
  state.view = impactMode.value ? NEIGHBOURHOOD_VIEW : IMPACT_VIEW;
}

const canvas = useGraphCanvas(container, {
  options: NAVIGATION_OPTIONS,
  onNodeTap: (id) => {
    select(id, { frame: false });
    focusCanvas();
  },
  onBackgroundTap: () => {
    clearSelection();
    focusCanvas();
  },
});
// How much of the canvas's right edge the panel lies over: in the page it
// overlays the canvas, in full screen it sits beside it and covers nothing.
function coveredRight() {
  const over = panel.value;
  const under = container.value;
  if (!panelOpen.value || !over || !under) return 0;
  const p = over.getBoundingClientRect();
  const c = under.getBoundingClientRect();
  if (!p.width || p.left >= c.right || p.right <= c.left) return 0;
  return Math.max(0, c.right - p.left);
}
const navigation = useGraphNavigation(() => canvas.cy.value, {
  getInset: () => ({ right: coveredRight() }),
});

/** Fit the selection's walk when there is one, else everything visible. */
function frameSelection() {
  nextTick(() => navigation.fit(selection.value ? ".in-walk" : undefined));
}

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
  canvas.showOnly(visible.value.nodes, visible.value.contracts);
  canvas.markSelection(selection.value);
  frameSelection();
}

watch(data, render);
watch(tokens, (current, previous) => {
  if (!current) return;
  if (!previous || !canvas.ready.value) render();
  else canvas.setStyle(buildStylesheet(current));
});
watch(visible, (shown) => {
  if (!canvas.ready.value) return;
  canvas.showOnly(shown.nodes, shown.contracts);
  navigation.fit();
});
watch(selection, (current) => {
  if (!canvas.ready.value) return;
  canvas.markSelection(current);
  if (current && frameNextSelection) frameSelection();
  frameNextSelection = true;
});
watch(
  () => state.focus,
  (id) => {
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
    state: () => ({ ...state, mode: props.mode }),
    arranging: () => navigation.arranging.value,
    impactSummary: () => summary.value,
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
      <component
        :is="mode.filterControls"
        :filters="state"
        :options="options"
        @change="(key, value) => (state[key] = value)"
      />
      <NeighbourhoodControls
        :depth="state.depth"
        :dir="state.dir"
        :hide="Boolean(state.hide)"
        @change="(key, value) => (state[key] = value)"
      />
      <ImpactButton v-if="mode.impact" :active="impactMode" @toggle="toggleImpact" />
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
        :aria-controls="panelId"
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
        :aria-label="`${mode.label}: drag to pan, scroll to zoom; keys + − 0 f Esc`"
      />
      <aside
        v-show="panelOpen"
        ref="panel"
        :id="panelId"
        class="bl-viewer-panel"
        data-testid="viewer-panel"
        aria-label="Details"
      >
        <ImpactSummary
          v-if="summary"
          :summary="summary"
          :source="selectedNode?.source || ''"
          @select="select"
        />
        <slot
          v-if="selectedNode"
          name="panel"
          :node="selectedNode"
          :layer-name="selectedLayer"
          :edges="edges"
          :layers="layers"
          :contracts="graph.contracts"
          :select="select"
          :close="clearSelection"
        />
        <p v-else class="bl-viewer-hint">
          Select a node to see its card and its neighbourhood; "Depth" and "Direction" choose how
          far it reaches<template v-if="mode.impact">, and "Impact" shows everything that depends
          on it</template>. Drag to pan and scroll to zoom; "Arrange" lets you move nodes. Keys: <kbd>+</kbd> <kbd>−</kbd> zoom, <kbd>0</kbd> fit, <kbd>f</kbd> full screen,
          <kbd>Esc</kbd> clear.
        </p>
      </aside>
    </div>

    <div class="bl-viewer-legend" aria-label="Legend">
      <LayerLegend :layers="layers" />
      <NodeStatusLegend :statuses="statuses" />
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
  width: min(340px, 60%);
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
  flex: 0 0 380px;
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
