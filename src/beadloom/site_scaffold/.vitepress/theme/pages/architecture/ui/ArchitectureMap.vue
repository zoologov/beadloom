<script setup>
// beadloom:component=site-architecture-page
// ArchitectureMap — the architecture graph, mounted by the generated
// `architecture.md` and by every node page.
//
// A thin page over the graph viewer: it shows the architecture mode and puts
// the node card in the viewer's panel. The viewer owns the toolbar,
// navigation, filters, the neighbourhood and impact modes, full screen and URL
// state; the page composes the two widgets, because a widget does not import
// another.
//
// A node page passes `focus`, its own node, with a depth and a height: the
// viewer opens with that node selected and its neighbourhood marked, and the
// reader moves on from there.

import { GraphViewer } from "../../../widgets/graph-viewer/index.js";
import { NodeCard } from "../../../widgets/node-card/index.js";

defineProps({
  focus: { type: String, default: "" },
  depth: { type: [Number, String], default: undefined },
  height: { type: String, default: undefined },
});
</script>

<template>
  <GraphViewer mode="architecture" :focus="focus" :depth="depth" :height="height">
    <template #panel="{ node, edges, layers, parents, select, close }">
      <NodeCard
        :node="node"
        :edges="edges"
        :layers="layers"
        :parents="parents"
        @select="select"
        @close="close"
      />
    </template>
  </GraphViewer>
</template>
