<script setup>
// beadloom:component=site-architecture-page
// ArchitectureMap — the architecture page's graph, mounted by the generated
// `architecture.md`.
//
// A thin page over the graph viewer: it shows the architecture mode and puts
// the node card in the viewer's panel. The viewer owns the toolbar,
// navigation, filters, full screen and URL state; the page decides what the
// panel shows for a selected node.

import { GraphViewer } from "../../../widgets/graph-viewer/index.js";
import { NodeCard } from "../../../entities/graph-node/index.js";
</script>

<template>
  <GraphViewer mode="architecture">
    <template #panel="{ node, layerName, select, close }">
      <NodeCard :node="node" :layer-name="layerName" @select="select" @close="close" />
    </template>
  </GraphViewer>
</template>
