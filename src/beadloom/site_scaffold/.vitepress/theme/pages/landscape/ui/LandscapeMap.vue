<script setup>
// beadloom:component=site-landscape-page
// LandscapeMap — the landscape page's map of contracts between services,
// mounted by the generated `landscape.md`.
//
// A thin page over the graph viewer in its landscape mode: the
// viewer owns the toolbar with the landscape's filters in the mode's slot,
// navigation, the neighbourhood, full screen and URL state, and the page puts
// the landscape card in the viewer's panel. In an earlier version this page drew its own
// Cytoscape graph, with filters in component refs, a card that stayed behind
// in full screen, and theme colours that Cytoscape could not read.

import { GraphViewer } from "../../../widgets/graph-viewer/index.js";
import LandscapeCard from "./LandscapeCard.vue";
</script>

<template>
  <GraphViewer mode="landscape" height="560px">
    <template #panel="{ node, contracts, select, close }">
      <LandscapeCard :node="node" :contracts="contracts" @select="select" @close="close" />
    </template>
  </GraphViewer>
</template>
