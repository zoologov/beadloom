// beadloom:component=site-graph-edge
// Public API of the `graph-edge` entity.

export {
  CONTAINMENT_KIND,
  EDGE_STYLES,
  VIOLATION_KEY,
  isDrawnKind,
  isViolation,
  legendKeysOf,
  styleKeyOf,
} from "./model/edgeKinds.js";
export {
  DEPENDENCY_KINDS,
  NEIGHBOURHOOD_KINDS,
  adjacencyOf,
  edgeGroupsOf,
  edgeKeyOf,
} from "./model/adjacency.js";
export { default as EdgeLegend } from "./ui/EdgeLegend.vue";
