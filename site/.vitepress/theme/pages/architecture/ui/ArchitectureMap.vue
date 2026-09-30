<script setup>
// beadloom:component=site-architecture-page
// ArchitectureMap — the architecture page's graph, mounted by the generated
// `architecture.md`.
//
// A thin page over the graph viewer: it shows the architecture mode and puts
// the node card in the viewer's panel. The viewer owns the toolbar,
// navigation, filters, the neighbourhood and impact modes, full screen and URL
// state; the page composes the two widgets, because a widget does not import
// another.

import { GraphViewer } from "../../../widgets/graph-viewer/index.js";
import { NodeCard } from "../../../widgets/node-card/index.js";
</script>

<template>
  <GraphViewer mode="architecture">
    <template #panel="{ node, edges, layers, repository, select, close }">
      <NodeCard
        :node="node"
        :edges="edges"
        :layers="layers"
        :repository="repository"
        @select="select"
        @close="close"
      />
    </template>
  </GraphViewer>
</template>
