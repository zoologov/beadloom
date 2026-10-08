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
// reported above the canvas, as a data file that cannot be read is, with what
// failed. No node of a graph that was not laid out has a place, so its canvas
// stays hidden and the controls that act on the graph are turned off; the
// panel and full screen act on the viewer and stay on.
//
// A node's edges are drawn bundled, several along one line. When the pointer is
// on a line that more than one edge runs along, a note over the canvas names
// them, since the line alone cannot say which edges it carries. A followed
// edge — under the pointer, or on a selection's walk — is drawn on top of every
// edge it crosses, over a casing, so it can be followed through a busy area.
//
// The graph is drawn like a map (`lib/levels.js`): at the whole-graph fit the
// boxes at the top and one aggregated edge per pair of them, more detail where
// the reader zooms in: a box opens once its nodes are readable. An open box keeps
// its edges to the outside on its own lines; a node in it says how many of its
// edges those carry ("+N"), and the pointer on it, or a selection of it, draws
// them. Selecting a node — by a tap, the URL, the card or the impact list —
// frames its neighbourhood, never below the zoom at which the node is drawn as
// itself and readable, in an animated move unless the reader asks for reduced
// motion. A selection with nothing more asked opens the boxes that hold its
// node, and only those. A walk the reader asked for (deeper, one way, the rest
// hidden, or the impact) also opens those of every node it reaches
// (`selectionReveals`). A search frames what it finds, readably, and opens the
// boxes that hold it. The pointer on an aggregated edge names how many edges
// it carries each way. At the overview the lines between top-level nodes are
// routed together, thin and light, with their counts on pills; the pointer on a
// node draws its lines in front of the rest.
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
import { LayerLegend, hasUnlayeredNode, layerBoxesOf, layerOfNode, layersOf } from "../../../entities/layer/index.js";
import {
  NAVIGATION_OPTIONS,
  NavigationControls,
  useGraphNavigation,
} from "../../../features/navigate-graph/index.js";
import {
  NEIGHBOURHOOD_DEFAULTS,
  NeighbourhoodControls,
  boxNeighbourhoodOf,
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
import { childrenOf, subtreeOf, withAncestors } from "../../../shared/lib/index.js";
import { useThemeTokens } from "../../../shared/theme-tokens/index.js";
import { buildElements } from "../lib/elements.js";
import { buildStylesheet } from "../lib/stylesheet.js";
import { edgePaletteOf } from "../lib/edgePalette.js";
import { AGGREGATE, boxTreeOf, endsOfLine, selectionReveals } from "../lib/levels.js";
import { useGraphCanvas } from "../model/useGraphCanvas.js";
import { SAID } from "../model/aggregateElements.js";
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
const layers = computed(() => layersOf(nodes.value, graph.value.layers, graph.value.layerRules));
// The boxes a layer rule scoped to a box draws inside it, one per layer, and the
// containment the canvas draws: the file's, with each such layer's parts in its
// box. What is drawn, kept or hidden is read from it; the card and the impact
// summary read the file's own.
const layered = computed(() => layerBoxesOf(nodes.value, parents.value, layers.value, graph.value.layerRules));
const drawnParents = computed(() => layered.value.parents);
// Whether the legend names a node in no layer: one is drawn in that tone. The
// box that holds everything is not, whatever its layer: it is the project's frame.
const unlayered = computed(() => {
  if (!mode.layered) return false;
  const { wrapper } = boxTreeOf(nodes.value.map((node) => ({ id: node.id, parent: parents.value[node.id] })));
  return hasUnlayeredNode(nodes.value.filter((node) => node.id !== wrapper), layers.value);
});
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
  mode.visible(graph.value, state, { parents: drawnParents.value, layers: layers.value })
);
const selectedNode = computed(() => nodeById.value.get(state.focus) || null);
const selectedLayer = computed(() =>
  selectedNode.value ? layerOfNode(selectedNode.value, layers.value)?.caption || "" : ""
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
const children = computed(() => childrenOf(drawnParents.value));
// What a selected box holds, itself included, or null when the selection is no
// box. The impact mode walks from the box's own node, as from any other.
const selectedBox = computed(() =>
  !impactMode.value && children.value.has(state.focus) ? subtreeOf(state.focus, children.value) : null
);
// The boxes that hold the selected node: an edge onto one of them is no neighbour's.
const holdersOfFocus = computed(() => {
  const held = withAncestors([state.focus], drawnParents.value);
  held.delete(state.focus);
  return held;
});
// What the search box finds, whose boxes it opens.
const searched = computed(() => mode.searched(graph.value, state));

// The walk from the selected node, or null when nothing is selected. A box's
// neighbourhood is everything it holds taken as one node: its edges cross its border.
const walk = computed(() => {
  if (!selectedNode.value) return null;
  const options = { depth: state.depth, dir: state.dir };
  if (impactMode.value) return impactOf(state.focus, dependents.value);
  if (selectedBox.value) return boxNeighbourhoodOf(state.focus, selectedBox.value, holdersOfFocus.value, drawnAdjacency.value, options);
  return neighbourhoodOf(state.focus, drawnAdjacency.value, options);
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
  const inside = selectedBox.value;
  return {
    focus: state.focus,
    distances,
    edges: walked,
    keep: new Set([...withAncestors(distances.keys(), drawnParents.value), ...(inside || [])]),
    hide: Boolean(state.hide),
    rings: summary.value
      ? new Map([...distances].map(([id, distance]) => [id, ringOf(distance)]))
      : null,
    risks: summary.value ? new Set(summary.value.risky.map((entry) => entry.id)) : null,
    reveal: selectionReveals(state.focus, [...distances.keys()], {
      wholeWalk: impactMode.value || !neutralNeighbourhood.value,
    }),
    box: inside ? state.focus : null,
    inside,
    holders: inside ? holdersOfFocus.value : null,
  };
});

const root = ref(null);
const container = ref(null);
const panel = ref(null);
const panelId = usePanelId();
// The panel opens when a node is selected; the toolbar's "Panel" button toggles it.
const panelOpen = ref(Boolean(state.focus));
const { tokens } = useThemeTokens(root);
// The colour of each edge style at rest, as the canvas draws it: the legend draws its samples in them.
const legendColours = computed(() =>
  tokens.value
    ? Object.fromEntries(Object.entries(edgePaletteOf(tokens.value)).map(([key, colours]) => [key, colours.rest]))
    : {}
);

// A selection made anywhere — a tap on the canvas, the URL, the card, the impact
// list — is framed, so the neighbourhood the reader asked for is in view and
// readable (the owner's ruling 7). A selected box is framed whole, open: the box
// is what the reader asked to see, and zooms further in himself. A box holding
// the boxes a layer rule draws opens where they are readable (`canvasMap`): below
// that, their titles would stand on plates over each other (owner, 2026-10-08).
function select(id) {
  if (!nodeById.value.has(id) || state.focus === id) return;
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
  fitZoom: (options) => navigation.fitZoom(options),
  tokens: () => tokens.value,
  onNodeTap: (id) => {
    select(id);
    focusCanvas();
  },
  onBackgroundTap: () => {
    clearSelection();
    focusCanvas();
  },
});
// Until ELK has placed the nodes, every one stands at one point: the canvas is not shown.
const unplaced = computed(() => canvas.layingOut.value || Boolean(canvas.layoutError.value));
// The graph could not be laid out: there is nothing to zoom, filter or walk.
const graphControlsOff = computed(() => Boolean(canvas.layoutError.value));
/** What a note calls a drawn end: its node's label, or the title of a box a layer rule draws, which is no node of the file. */
function drawnLabelOf(id, instance) {
  return nodeById.value.get(id)?.label || instance.getElementById(id).data("label") || id;
}
// The edges along the line under the pointer, named, when the line carries more than one.
const bundleNote = computed(() => {
  const ids = canvas.hoveredEdges.value;
  const instance = canvas.cy.value;
  if (ids.length < 2 || !instance) return "";
  const labelOf = (id) => drawnLabelOf(id, instance);
  const named = ids.slice(0, NAMED_EDGES).map((id) => {
    const ends = endsOfLine(instance.getElementById(id));
    return `${labelOf(ends.source)} → ${labelOf(ends.target)}`;
  });
  const rest = ids.length - named.length;
  return `${ids.length} edges along this line: ${named.join(", ")}${rest > 0 ? `, and ${rest} more` : ""}`;
});
// The edges an aggregated edge under the pointer carries, each way, named by its
// two ends; during a selection, the walk's edges it carries first, as its pill says.
const aggregateNote = computed(() => {
  const ids = canvas.hoveredEdges.value;
  const instance = canvas.cy.value;
  if (ids.length !== 1 || !instance) return "";
  const edge = instance.getElementById(ids[0]);
  if (edge.empty() || !edge.data(AGGREGATE)) return "";
  const labelOf = (id) => drawnLabelOf(id, instance);
  const way = (count, from, to) =>
    count ? `${count} ${count === 1 ? "edge" : "edges"} ${labelOf(from)} → ${labelOf(to)}` : "";
  const [a, b] = [edge.data("source"), edge.data("target")];
  const both = ({ forward, backward }) => [way(forward, a, b), way(backward, b, a)].filter(Boolean).join("; ");
  const all = both({ forward: edge.data("forward"), backward: edge.data("backward") });
  const said = edge.data(SAID);
  return said ? `${both(said)} of the selection's walk, of ${all} in all` : all;
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

/** The laid-out box around the nodes `ids` the filters show, or null. */
function laidOutBoxOf(ids) {
  const boxes = canvas.layout.value?.geometry.boxes;
  const shown = visible.value.nodes;
  const held = boxes ? ids.filter((id) => boxes[id] && (!shown || shown.has(id))).map((id) => boxes[id]) : [];
  if (!held.length) return null;
  return held.reduce((a, b) => ({ x1: Math.min(a.x1, b.x1), y1: Math.min(a.y1, b.y1), x2: Math.max(a.x2, b.x2), y2: Math.max(a.y2, b.y2) }));
}

/**
 * Frame the selection's neighbourhood, at no less than the zoom at which its
 * node, and every node the selection draws as itself, is drawn readably, centred
 * on the node where the walk does not fit at that zoom; a selected box whole,
 * open at whatever zoom it fits at (one holding a layer rule's boxes where they
 * are readable); with nothing selected, fit everything visible.
 */
function frameSelection({ animate }) {
  nextTick(() => {
    fitCanvasToContainer();
    const focus = selection.value?.focus;
    const map = canvas.map();
    const whole = selection.value?.box ? laidOutBoxOf([focus]) : null;
    if (whole && map) {
      navigation.frame({ box: whole, focus: whole }, { animate });
      return;
    }
    const box = focus ? laidOutBoxOf([...selection.value.distances.keys()]) : null;
    if (!box || !map) {
      navigation.fit();
      return;
    }
    const leastZoom = Math.max(...[focus, ...selection.value.reveal].map((id) => map.zoomDrawing(id)));
    navigation.frame({ box, focus: laidOutBoxOf([focus]), leastZoom }, { animate });
  });
}

/**
 * Frame what the search box finds, when it finds anything and nothing is
 * selected, at no less than the zoom at which what it finds is drawn readably,
 * centred on the first where it does not fit; else fit everything visible.
 */
function frameSearch() {
  nextTick(() => {
    const found = selection.value ? [] : searched.value;
    const box = laidOutBoxOf(found);
    const map = canvas.map();
    if (!box || !map) {
      navigation.fit();
      return;
    }
    const leastZoom = Math.max(...found.map((id) => map.zoomDrawing(id)));
    navigation.frame({ box, focus: laidOutBoxOf(found.slice(0, 1)), leastZoom });
  });
}

/**
 * Have the canvas take its container's size where the panel, opened by the
 * selection, took room from it beside the canvas, as in full screen: a frame is
 * measured on the canvas as it will be seen.
 */
function fitCanvasToContainer() {
  const instance = canvas.cy.value;
  const element = container.value;
  if (instance && element && (element.clientWidth !== instance.width() || element.clientHeight !== instance.height())) canvas.resize();
}

/** Fit the canvas to its new size: the selection framed again, or everything visible. */
function refit() {
  nextTick(() => {
    canvas.resize();
    if (selection.value) frameSelection({ animate: false });
    else navigation.fit();
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
    parents: drawnParents.value,
    layers: layers.value,
    layerBoxes: layered.value.boxes,
  });
  const mounted = await canvas.mount(elements, buildStylesheet(tokens.value));
  if (!mounted) return;
  navigation.panOnNodes();
  canvas.reveal("search", searched.value);
  canvas.showOnly(visible.value.nodes, visible.value.contracts);
  canvas.markSelection(selection.value);
  if (selection.value) frameSelection({ animate: false });
  else frameSearch();
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
  frameSearch();
});
watch(selection, (current) => {
  if (!canvas.ready.value) return;
  canvas.markSelection(current);
  if (current) frameSelection({ animate: true });
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
    followed: () => canvas.followed(),
    labelled: () => canvas.labelled(),
    frames: () => canvas.frames(),
    droppedHeads: () => canvas.droppedHeads(),
    pills: () => canvas.pills(),
    tallies: () => canvas.tallies(),
    outward: () => canvas.outward(),
    hoveredEdges: () => canvas.hoveredEdges.value,
    map: () => canvas.map(),
    revealNodes: (ids, options) => canvas.revealNow("test", ids, options),
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
      <fieldset class="bl-viewer-controls" :disabled="graphControlsOff">
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
      </fieldset>
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
        :class="{ 'is-unplaced': unplaced }"
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
          :parents="parents"
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
      <LayerLegend :layers="layers" :unlayered="unlayered" />
      <NodeStatusLegend :statuses="statuses" />
      <EdgeLegend :keys="legendKeys" :colours="legendColours" />
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
/* The controls that act on the graph, one group to turn off; laid out as the toolbar's own items. */
.bl-viewer-controls {
  display: contents;
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
  /* The layer of followed lines lies over Cytoscape's drawing, inside the same border. */
  position: relative;
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
.bl-viewer-canvas.is-unplaced {
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
