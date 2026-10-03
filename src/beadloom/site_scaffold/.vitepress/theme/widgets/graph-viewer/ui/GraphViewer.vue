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
// ELK lays the graph out in a Web Worker. Until it answers, the canvas says it is
// laying the graph out and the toolbar keeps working; a layout that fails is
// reported above the canvas, as a data file that cannot be read is.
//
// A node's edges are drawn bundled, several along one line. When the pointer is
// on a line that more than one edge runs along, a note over the canvas names
// them, since the line alone cannot say which edges it carries. A highlighted
// edge — under the pointer, or on a selection's walk — hops over every other
// edge it crosses, so it can be followed through a busy area.
//
// The graph is drawn like a map (`lib/levels.js`): at the whole-graph fit the
// boxes at the top and one aggregated edge per pair of them, more detail where
// the reader zooms in. A selection opens the boxes that hold its node, and those
// of every node its walk reaches unless the node is a hub selected with nothing
// more asked; a search opens the boxes that hold what it finds. The pointer on an
// aggregated edge names how many edges it carries each way.
//
// The toolbar, the canvas, the panel and the legend are all inside one root
// element, and that element is what goes full screen, so full screen and the
// embedded view are one UI. The panel shows what the page puts in its `panel`
// slot for the selected node — the page composes the card, because a widget
// does not import another — and, in impact mode, the impact summary above it.
//
// A selection is a walk from the selected node. In the neighbourhood it goes
// to the chosen depth and direction; in impact mode it goes to everything that
// depends on the node, without a limit, by the mode's walk: backwards along the
// dependency edges in the architecture, from a producer to its consumers on the
// landscape. What the walk leaves out is dimmed, or hidden when the reader
// asks; the containers of what it reached stay.

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { NodeStatusLegend, parentMapOf, statusesOf } from "../../../entities/graph-node/index.js";
import {
  EdgeLegend,
  NEIGHBOURHOOD_KINDS,
  adjacencyOf,
  dependentsOf,
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
  ringOf,
} from "../../../features/impact-view/index.js";
import { FullscreenButton, useFullscreen } from "../../../features/fullscreen/index.js";
import { useUrlState } from "../../../features/url-state/index.js";
import { withAncestors } from "../../../shared/lib/index.js";
import { useThemeTokens } from "../../../shared/theme-tokens/index.js";
import { buildElements } from "../lib/elements.js";
import { buildStylesheet } from "../lib/stylesheet.js";
import { AGGREGATE, selectionReveals } from "../lib/levels.js";
import { useGraphCanvas } from "../model/useGraphCanvas.js";
import { keyHandler } from "../model/viewerKeys.js";
import { exposeTestHandle } from "../model/testHandle.js";
import { usePanelId } from "../model/usePanelId.js";
import { DEFAULT_MODE, modeOf } from "../model/modes.js";

/** The selection's value for the neighbourhood, the default; the other is `IMPACT_VIEW`. */
const NEIGHBOURHOOD_VIEW = "neighbourhood";
/** How many edges along a hovered line the note names before it counts the rest. */
const NAMED_EDGES = 8;

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
// What depends on each node, by the mode's impact walk; empty where the mode offers none.
const dependents = computed(() =>
  mode.impact ? dependentsOf(edges.value, mode.impact.dependentEnds, ids.value) : new Map()
);
const impactMode = computed(() => Boolean(mode.impact) && state.view === IMPACT_VIEW);
// Whether the reader asked the neighbourhood for nothing more than a selection gives.
const neutralNeighbourhood = computed(
  () =>
    state.depth === NEIGHBOURHOOD_DEFAULTS.depth &&
    state.dir === NEIGHBOURHOOD_DEFAULTS.dir &&
    Boolean(state.hide) === NEIGHBOURHOOD_DEFAULTS.hide
);
// How many drawn edges a node has: a hub's walk opens only its own boxes.
const degreeOf = (id) =>
  (drawnAdjacency.value.out.get(id)?.length || 0) + (drawnAdjacency.value.in.get(id)?.length || 0);
// What the search box finds, whose boxes it opens.
const searched = computed(() => mode.searched(graph.value, state));

// The walk from the selected node, or null when nothing is selected.
const walk = computed(() => {
  if (!selectedNode.value) return null;
  return impactMode.value
    ? impactOf(state.focus, dependents.value)
    : neighbourhoodOf(state.focus, drawnAdjacency.value, { depth: state.depth, dir: state.dir });
});
const summary = computed(() => {
  if (!walk.value || !impactMode.value) return null;
  return mode.impact.summarise(state.focus, walk.value, {
    nodeById: nodeById.value,
    parents: parents.value,
    layers: layers.value,
    edges: edges.value,
    contracts: graph.value.contracts,
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
    reveal: selectionReveals(state.focus, [...distances.keys()], {
      degree: degreeOf(state.focus),
      wholeWalk: impactMode.value || !neutralNeighbourhood.value,
    }),
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
  fitZoom: () => navigation.fitZoom(),
  background: () => tokens.value?.bg,
  onNodeTap: (id) => {
    select(id, { frame: false });
    focusCanvas();
  },
  onBackgroundTap: () => {
    clearSelection();
    focusCanvas();
  },
});
// The edges along the line under the pointer, named, when the line carries more than one.
const bundleNote = computed(() => {
  const ids = canvas.hoveredEdges.value;
  const instance = canvas.cy.value;
  if (ids.length < 2 || !instance) return "";
  const labelOf = (id) => nodeById.value.get(id)?.label || id;
  const named = ids.slice(0, NAMED_EDGES).map((id) => {
    const edge = instance.getElementById(id);
    return `${labelOf(edge.data("source"))} → ${labelOf(edge.data("target"))}`;
  });
  const rest = ids.length - named.length;
  return `${ids.length} edges along this line: ${named.join(", ")}${rest > 0 ? `, and ${rest} more` : ""}`;
});
// The edges an aggregated edge under the pointer carries, each way, named by its two ends.
const aggregateNote = computed(() => {
  const ids = canvas.hoveredEdges.value;
  const instance = canvas.cy.value;
  if (ids.length !== 1 || !instance) return "";
  const edge = instance.getElementById(ids[0]);
  if (edge.empty() || !edge.data(AGGREGATE)) return "";
  const labelOf = (id) => nodeById.value.get(id)?.label || id;
  const way = (count, from, to) =>
    count ? `${count} ${count === 1 ? "edge" : "edges"} ${labelOf(from)} → ${labelOf(to)}` : "";
  const [a, b] = [edge.data("source"), edge.data("target")];
  return [way(edge.data("forward"), a, b), way(edge.data("backward"), b, a)].filter(Boolean).join("; ");
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

/** Fit the selection's walk, with the closed boxes that hold part of it, when there is one; else everything visible. */
function frameSelection() {
  nextTick(() => navigation.fit(selection.value ? ".in-walk, .holds-walk" : undefined));
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
  navigation.panOnNodes();
  canvas.reveal("search", searched.value);
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
  canvas.reveal("search", searched.value);
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
    impactSummary: () => summary.value,
    layout: () => canvas.layout.value,
    bundles: () => canvas.bundles.value,
    junctions: () => canvas.junctions(),
    bridges: () => canvas.bridges(),
    bridgeFrames: () => canvas.bridgeFrames(),
    hoveredEdges: () => canvas.hoveredEdges.value,
    map: () => canvas.map(),
    revealNodes: (ids) => canvas.revealNow("test", ids),
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
        @zoom-in="navigation.zoomIn"
        @zoom-out="navigation.zoomOut"
        @fit="navigation.fit"
        @centre="navigation.centre(state.focus)"
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

    <p v-if="canvas.layoutError.value" class="bl-viewer-note" role="alert">
      The graph could not be laid out ({{ canvas.layoutError.value.message }}). The static summary
      on this page is the source of truth.
    </p>

    <div class="bl-viewer-body">
      <p
        v-if="canvas.layingOut.value"
        class="bl-viewer-status"
        role="status"
        data-testid="layout-status"
      >
        Laying out the graph…
      </p>
      <p v-if="bundleNote" class="bl-viewer-bundle-note" role="status" data-testid="edge-bundle-note">
        {{ bundleNote }}
      </p>
      <p
        v-if="aggregateNote"
        class="bl-viewer-bundle-note"
        role="status"
        data-testid="aggregated-edge-note"
      >
        {{ aggregateNote }}
      </p>
      <div
        ref="container"
        class="bl-viewer-canvas"
        :class="{ 'is-laying-out': canvas.layingOut.value }"
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
          on it</template>. Drag to pan and scroll to zoom. Keys: <kbd>+</kbd> <kbd>−</kbd> zoom, <kbd>0</kbd> fit, <kbd>f</kbd> full screen,
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
/* Until ELK answers, every node stands at one point; the canvas is shown once they are placed. */
.bl-viewer-canvas.is-laying-out {
  visibility: hidden;
}
.bl-viewer-status {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1;
  margin: 0;
  color: var(--vp-c-text-2);
}
.bl-viewer-bundle-note {
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 2;
  max-width: 60%;
  margin: 0;
  padding: 4px 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  font-size: 12px;
  pointer-events: none;
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
